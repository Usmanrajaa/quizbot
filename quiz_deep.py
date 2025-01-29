import os
import streamlit as st
import subprocess
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
import tempfile
import re

# ✅ Install Poppler if missing (For Streamlit Cloud)
def install_poppler():
    try:
        subprocess.run(["apt-get", "update"], check=True)
        subprocess.run(["apt-get", "install", "-y", "poppler-utils"], check=True)
    except subprocess.CalledProcessError as e:
        st.error(f"Error installing Poppler: {e}")

install_poppler()  # Ensure Poppler is installed

# ✅ Set Paths for Poppler and Tesseract
POPPLER_PATH = "/usr/bin/"
TESSERACT_PATH = "/usr/bin/tesseract"
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# ✅ Load Google API key from environment variable
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    st.error("Google API key not found. Make sure to set it in the environment variables.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# ✅ Function to extract text from images using OCR
def extract_text_from_image(image):
    try:
        return pytesseract.image_to_string(image)
    except Exception as e:
        st.error(f"OCR Error: {e}")
        return ""

# ✅ Function to extract text from PDFs using OCR
def extract_text_from_pdf(pdf_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(pdf_file.read())
        temp_pdf_path = temp_pdf.name

    try:
        images = convert_from_path(temp_pdf_path, poppler_path=POPPLER_PATH)
        extracted_text = "".join(pytesseract.image_to_string(img) for img in images)
    except Exception as e:
        st.error(f"PDF OCR Error: {e}")
        extracted_text = ""
    
    os.remove(temp_pdf_path)
    return extracted_text

# ✅ Function to use Gemini model for quiz generation
def generate_quiz(text, num_questions=5):
    prompt = f"""
    Generate {num_questions} multiple-choice questions (MCQs) based on the following text. Each question should have exactly 4 options and a correct answer.

    Text:
    {text}

    Format the output as follows:
    1. [Question]
    a) [Option 1]
    b) [Option 2]
    c) [Option 3]
    d) [Option 4]
    Correct Answer: [Correct option]

    Continue for all {num_questions} questions.
    """
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"AI Quiz Generation Error: {e}")
        return ""

# ✅ Function to format the quiz properly
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

# ✅ Streamlit UI
st.set_page_config(page_title="Quiz Generator", layout="wide")
st.title("📝 Quiz Generator")
st.markdown("Upload an image or PDF, and we'll generate a **structured quiz** for you!")

# ✅ Initialize session state for quiz data
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False  # Track submission status

left_column, right_column = st.columns([1, 2])

# ✅ Left Column: File Upload and Extracted Text
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

# ✅ Right Column: Quiz Generation
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
                        st.session_state.user_answers = {}  # Reset answers on new quiz
                        st.session_state.quiz_submitted = False  # Reset submission state
                        st.success("✅ Quiz generated successfully! Scroll down to answer.")
                except Exception as e:
                    st.error(f"An error occurred: {e}")

        if st.session_state.quiz_data:
            st.markdown("### 📝 Answer the Quiz")

            for i, question_data in enumerate(st.session_state.quiz_data):
                question_text = re.sub(r"^(Question\s*\d+:?)\s*", "", question_data['question']).strip()
                st.markdown(f"**Question {i+1}: {question_text}**")

                # Use session state for storing answers persistently
                selected_option = st.radio(
                    f"Select an answer for Question {i+1}:",
                    question_data['options'],
                    index=question_data['options'].index(st.session_state.user_answers.get(i, question_data['options'][0])),
                    key=f"question_{i}"
                )
                st.session_state.user_answers[i] = selected_option

            # ✅ Submit button to show results
            if st.button("Submit Answers"):
                st.session_state.quiz_submitted = True  # Mark quiz as submitted

        # ✅ Display Quiz Results if submitted
        if st.session_state.quiz_submitted:
            correct_count = sum(1 for i, q in enumerate(st.session_state.quiz_data) if st.session_state.user_answers[i] == q['correct_answer'])
            st.markdown(f"**🎯 Total Score: {correct_count}/{len(st.session_state.quiz_data)}**")

# ✅ Footer
st.markdown("---")
st.markdown("Developed with ❤️ by **Fiftheye Eduvision**")
