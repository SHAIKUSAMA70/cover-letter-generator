import streamlit as st
import requests
from pypdf import PdfReader
from docx import Document
import io
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes

# -------------------------------
# Tesseract path (Windows)
# -------------------------------
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# -------------------------------
# Page config
# -------------------------------
st.set_page_config(
    page_title="AI Cover Letter Generator",
    page_icon="🤖",
    layout="wide"
)

# -------------------------------
# Ollama
# -------------------------------
def query_ollama(messages, model="llama3"):
    url = "http://localhost:11434/api/generate"
    prompt = ""
    for m in messages:
        prompt += f"{m['role'].upper()}: {m['content']}\n"

    payload = {"model": model, "prompt": prompt, "stream": False}

    try:
        r = requests.post(url, json=payload, timeout=300)
        r.raise_for_status()
        return r.json()["response"]
    except Exception as e:
        return f"Ollama error: {e}"

# -------------------------------
# Text Extraction
# -------------------------------
def extract_text(file):
    try:
        if file.type == "application/pdf":
            data = file.read()
            reader = PdfReader(io.BytesIO(data))
            text = ""
            for p in reader.pages:
                if p.extract_text():
                    text += p.extract_text() + "\n"
            if text.strip():
                return text
            images = convert_from_bytes(data)
            return "".join(pytesseract.image_to_string(i) for i in images)

        elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = Document(io.BytesIO(file.read()))
            return "\n".join(p.text for p in doc.paragraphs)

        elif file.type.startswith("image/"):
            return pytesseract.image_to_string(Image.open(file))

        elif file.type == "text/plain":
            return file.read().decode("utf-8")

    except Exception as e:
        return f"Extraction error: {e}"

    return ""

# -------------------------------
# Session State (Chat History)
# -------------------------------
if "chats" not in st.session_state:
    st.session_state.chats = {1: []}
    st.session_state.current_chat = 1
    st.session_state.chat_id = 1

# -------------------------------
# Sidebar
# -------------------------------
st.sidebar.title("💬 Chat History")

if st.sidebar.button("➕ New Chat"):
    st.session_state.chat_id += 1
    st.session_state.chats[st.session_state.chat_id] = []
    st.session_state.current_chat = st.session_state.chat_id

st.sidebar.divider()

for cid in st.session_state.chats:
    if st.sidebar.button(f"Chat {cid}", key=f"chat_{cid}"):
        st.session_state.current_chat = cid

# -------------------------------
# Main UI
# -------------------------------
st.title("🤖 AI Cover Letter Generator")

current_chat = st.session_state.chats[st.session_state.current_chat]

for msg in current_chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -------------------------------
# Input Form
# -------------------------------
with st.form("cover_form"):
    col1, col2 = st.columns(2)

    with col1:
        job_title = st.text_input("Job Title")
        company = st.text_input("Company Name")
        skills = st.text_area("Skills")

    with col2:
        experience = st.text_area("Experience")

        uploaded_files = st.file_uploader(
            "📎 Upload Resume & Job Description (Files or Images)",
            type=["pdf", "docx", "txt", "png", "jpg", "jpeg"],
            accept_multiple_files=True
        )

    submit = st.form_submit_button("Generate Cover Letter")

# -------------------------------
# Generate
# -------------------------------
if submit:
    if not all([job_title, company, skills, experience]) or not uploaded_files:
        st.warning("Please fill all fields and upload files.")
    else:
        combined_text = ""
        for f in uploaded_files:
            combined_text += extract_text(f) + "\n"

        prompt = f"""
Write a professional, ATS-friendly cover letter.

Job Title: {job_title}
Company: {company}

Skills:
{skills}

Experience:
{experience}

Uploaded Resume & Job Description Content:
{combined_text[:3000]}

Tone: Formal, confident, employer-focused.
"""

        current_chat.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner("Generating..."):
                reply = query_ollama(current_chat)
                st.markdown(reply)

        current_chat.append({"role": "assistant", "content": reply})
        st.rerun()