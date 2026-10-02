import streamlit as st
import google.generativeai as genai
from PIL import Image

from prompts import SYSTEM_PROMPT, EMAIL_SUMMARY_PROMPT
from email_utils import send_email

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SnapStudy 📸",
    page_icon="📸",
    layout="centered",
)

# ── Gemini setup ─────────────────────────────────────────────────────────────
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel(
    model_name="gemini-3.8-flash",
    system_instruction=SYSTEM_PROMPT,
)

# ── Session-state defaults ────────────────────────────────────────────────────
if "onboarded" not in st.session_state:
    st.session_state.onboarded = False
if "student_name" not in st.session_state:
    st.session_state.student_name = ""
if "student_email" not in st.session_state:
    st.session_state.student_email = ""
if "chat" not in st.session_state:
    st.session_state.chat = None          # Gemini chat session
if "messages" not in st.session_state:
    st.session_state.messages = []        # list of {"role", "content"}
if "image_analysed" not in st.session_state:
    st.session_state.image_analysed = False
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None


# ═════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — Onboarding
# ═════════════════════════════════════════════════════════════════════════════
def show_onboarding():
    st.title("📸 SnapStudy")
    st.subheader("Snap a photo. Get an instant explanation. Save it to your inbox.")
    st.markdown(
        "Upload any photo of a problem, diagram, equation, or set of notes "
        "and SnapStudy will explain it clearly — then email you the summary "
        "so you always have it handy."
    )

    st.divider()

    with st.form("onboarding_form"):
        name = st.text_input("Your first name", placeholder="e.g. Priya")
        email = st.text_input(
            "Email address (we'll send your study notes here)",
            placeholder="e.g. priya@example.com",
        )
        submitted = st.form_submit_button("Let's Study! 🚀")

    if submitted:
        if not name.strip():
            st.error("Please enter your name.")
        elif "@" not in email or "." not in email.split("@")[-1]:
            st.error("Please enter a valid email address.")
        else:
            st.session_state.student_name = name.strip()
            st.session_state.student_email = email.strip()
            st.session_state.onboarded = True
            # Start a Gemini multi-turn chat session
            st.session_state.chat = model.start_chat(history=[])
            st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# SCREEN 2 — Main chat + image upload
# ═════════════════════════════════════════════════════════════════════════════
def show_chat():
    name = st.session_state.student_name

    st.title("📸 SnapStudy")
    st.caption(f"Hi {name}! Upload a photo below to get started.")

    # ── Image uploader (shown only until an image has been analysed) ──────────
    if not st.session_state.image_analysed:
        uploaded_file = st.file_uploader(
            "📷 Upload your photo (PNG, JPG, JPEG, WEBP)",
            type=["png", "jpg", "jpeg", "webp"],
            key="uploader",
        )

        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="Your uploaded image", use_container_width=True)

            if st.button("✨ Explain This!"):
                with st.spinner("SnapStudy is reading your image…"):
                    try:
                        response = st.session_state.chat.send_message(
                            [
                                "Please explain this study material to me.",
                                image,
                            ]
                        )
                        explanation = response.text

                        # Store the image and the first exchange
                        st.session_state.uploaded_image = image
                        st.session_state.messages.append(
                            {"role": "user", "content": "📷 [Image uploaded]"}
                        )
                        st.session_state.messages.append(
                            {"role": "assistant", "content": explanation}
                        )
                        st.session_state.image_analysed = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gemini error: {e}")

    # ── Chat history ──────────────────────────────────────────────────────────
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Follow-up chat input (shown after first image analysis) ───────────────
    if st.session_state.image_analysed:
        user_input = st.chat_input("Ask a follow-up question…")
        if user_input:
            # Show the user message immediately
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("Thinking…"):
                    try:
                        response = st.session_state.chat.send_message(user_input)
                        reply = response.text
                        st.markdown(reply)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": reply}
                        )
                    except Exception as e:
                        st.error(f"Gemini error: {e}")

        # ── Send to email button ──────────────────────────────────────────────
        st.divider()
        st.markdown("### 📩 Save your study notes")
        st.write(
            f"Click below to email a clean summary of this explanation to "
            f"**{st.session_state.student_email}**."
        )

        if st.button("📧 Send Study Notes to My Email"):
            with st.spinner("Generating summary and sending email…"):
                try:
                    # Ask Gemini to write the formatted study note
                    summary_response = st.session_state.chat.send_message(
                        EMAIL_SUMMARY_PROMPT
                    )
                    summary_text = summary_response.text

                    send_email(
                        to_address=st.session_state.student_email,
                        subject=f"SnapStudy Notes for {st.session_state.student_name}",
                        body=summary_text,
                    )
                    st.success(
                        f"Study notes sent to {st.session_state.student_email}! "
                        "Check your inbox 📬"
                    )
                except Exception as e:
                    st.error(f"Could not send email: {e}")

        # ── Start over button ─────────────────────────────────────────────────
        st.divider()
        if st.button("🔄 Start Over (upload a new image)"):
            # Keep name and email, reset everything else
            st.session_state.chat = model.start_chat(history=[])
            st.session_state.messages = []
            st.session_state.image_analysed = False
            st.session_state.uploaded_image = None
            st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# Router
# ═════════════════════════════════════════════════════════════════════════════
if not st.session_state.onboarded:
    show_onboarding()
else:
    show_chat()
