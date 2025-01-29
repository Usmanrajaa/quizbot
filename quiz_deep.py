import streamlit as st

# ✅ MUST be the first Streamlit command!
st.set_page_config(page_title="Quiz Generator", layout="wide")

import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import google.generativeai as genai
import os
import tempfile
import re
from dotenv import load_dotenv
import platform
import shutil

# ✅ Load API Key from .env file
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    st.error("Google API key not found. Set it in the .env file.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# ✅ Auto-detect Tesseract & Poppler paths
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract") or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    
    # 🔥 NEW: Find correct Poppler path dynamically
    POPPLER_PATHS = [
        r"C:\poppler-24.08.0\Library\bin",
        r"C:\Program Files\Release-24.08.0-0\poppler-24.08.0\Library\bin"
    ]
    
    POPPLER_PATH = next((path for path in POPPLER_PATHS if os.path.exists(os.path.join(path, "pdftoppm.exe"))), None)

else:  # Linux / Railway
    pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract") or "/usr/bin/tesseract"
    POPPLER_PATH = shutil.which("pdftoppm") or "/usr/bin"

if not POPPLER_PATH:
    st.error("⚠️ Poppler is not installed or not in PATH! Install Poppler and restart.")
    st.stop()

st.sidebar.write(f"🔍 **Tesseract Path:** {pytesseract.pytesseract.tesseract_cmd}")
st.sidebar.write(f"🔍 **Poppler Path:** {POPPLER_PATH}")

def extract_text_from_image(image):
    return pytesseract.image_to_string(image)

def extract_text_from_pdf(pdf_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(pdf_file.read())
        temp_pdf_path = temp_pdf.name

    try:
        images = convert_from_path(temp_pdf_path, poppler_path=POPPLER_PATH)
        extracted_text = "\n".join(pytesseract.image_to_string(img) for img in images)
    except Exception as e:
        os.remove(temp_pdf_path)
        st.error(f"Error processing PDF: {e}")
        return ""

    os.remove(temp_pdf_path)
    return extracted_text.strip()

def generate_quiz(text, num_questions=5):
    prompt = f"""
    Generate {num_questions} multiple-choice questions (MCQs) based on the following text.
    Each question should have exactly 4 options and a correct answer.

    **Text:**
    {text}

    **Format:**
    1: [Question]
       a) [Option 1]
       b) [Option 2]
       c) [Option 3]
       d) [Option 4]
       Correct Answer: [Correct option]
    """
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text

def format_quiz(quiz_text):
    questions = quiz_text.strip().split("\n\n")
    quiz_data = []
    
    for question in questions:
        lines = question.split("\n")
        if len(lines) < 3:
            continue
        question_text = re.sub(r"^(Question\s*\d+:?)\s*", "", lines[0]).strip()
        options = lines[1:-1]
        correct_answer = lines[-1].replace("Correct Answer: ", "").strip()
        while len(options) < 4:
            options.append("")
        quiz_data.append({
            "question": question_text,
            "options": [opt.strip() for opt in options],
            "correct_answer": correct_answer
        })
    
    return quiz_data

st.title("📝 Quiz Generator")
st.markdown("Upload an image or PDF, and we'll generate a **structured quiz** for you!")

if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False

left_column, right_column = st.columns([1, 2])

with left_column:
    st.markdown("### 📂 Upload File")
    uploaded_file = st.file_uploader("Choose an image or PDF file...", type=["jpg", "jpeg", "png", "pdf"])

    if uploaded_file:
        file_type = uploaded_file.type
        if file_type in ["image/jpeg", "image/png", "image/jpg"]:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Image", use_column_width=True)
            extracted_text = extract_text_from_image(image)
        elif file_type == "application/pdf":
            extracted_text = extract_text_from_pdf(uploaded_file)

        st.markdown("### 📝 Extracted Text")
        st.text_area("Extracted Text", extracted_text, height=250)

with right_column:
    if uploaded_file:
        st.markdown("### 🎯 Generate Quiz")
        num_questions = st.slider("Number of questions", 1, 10, 5)

        if st.button("Generate Quiz"):
            with st.spinner("Generating quiz..."):
                try:
                    quiz_text = generate_quiz(extracted_text, num_questions)
                    quiz_data = format_quiz(quiz_text)
                    
                    if not quiz_data:
                        st.error("Failed to generate a valid quiz. Please try again.")
                    else:
                        st.session_state.quiz_data = quiz_data
                        st.session_state.user_answers = {}
                        st.session_state.quiz_submitted = False
                        st.success("✅ Quiz generated successfully! Scroll down to answer.")
                except Exception as e:
                    st.error(f"An error occurred: {e}")

        if st.session_state.quiz_data:
            st.markdown("### 📝 Answer the Quiz")
            for i, question_data in enumerate(st.session_state.quiz_data):
                question_text = re.sub(r"^(Question\s*\d+:?)\s*", "", question_data['question']).strip()
                st.markdown(f"**Question {i+1}: {question_text}**")
                selected_option = st.radio(
                    f"Select an answer for Question {i+1}:",
                    question_data['options'],
                    index=question_data['options'].index(st.session_state.user_answers.get(i, question_data['options'][0])),
                    key=f"question_{i}"
                )
                st.session_state.user_answers[i] = selected_option

            if st.button("Submit Answers"):
                st.session_state.quiz_submitted = True

        if st.session_state.quiz_submitted:
            correct_count = sum(
                1 for i, q in enumerate(st.session_state.quiz_data) if st.session_state.user_answers[i] == q['correct_answer']
            )
            st.markdown(f"### 🎯 Your Score: **{correct_count}/{len(st.session_state.quiz_data)}**")

st.markdown("---")
st.markdown("Developed with ❤️ by **Fiftheye Eduvision**")

# ✅ **Railway Deployment Fix: Run Streamlit properly inside Docker**
if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 8501))
    CMD = f"streamlit run {__file__} --server.port {PORT} --server.address 0.0.0.0"
    os.system(CMD)
