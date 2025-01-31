import streamlit as st
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import google.generativeai as genai
import os
from dotenv import load_dotenv
import tempfile

# Load Google API key from environment variable
load_dotenv()  # Load environment variables from .env file

# Configure Gemini with API key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Function to extract text from images using OCR
def extract_text_from_image(image):
    text = pytesseract.image_to_string(image)
    return text

# Function to extract text from PDF using OCR (page by page)
def extract_text_from_pdf(pdf_file):
    # Save the uploaded PDF to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(pdf_file.read())
        temp_pdf_path = temp_pdf.name

    # Convert the PDF to images and perform OCR
    images = convert_from_path(temp_pdf_path)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img)
    
    # Optionally, delete the temporary file after processing
    os.remove(temp_pdf_path)

    return text

# Function to use Gemini model for quiz generation
def generate_quiz(text, num_questions=5):
    prompt = f"""
    Generate {num_questions} multiple-choice questions (MCQs) based on the following text. Each question should have 4 options and a correct answer.

    Text:
    {text}

    Format the output as follows:
    - Question 1: [Question text]
      a) [Option 1]
      b) [Option 2]
      c) [Option 3]
      d) [Option 4]
      Correct Answer: [Correct option]

    Continue for all {num_questions} questions.
    """
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text

# Function to format quiz output with horizontal questions and vertical answers
def format_quiz(quiz_text):
    questions = quiz_text.split("\n\n")  # Split questions by double newlines
    quiz_data = []
    for i, question in enumerate(questions):
        if question.strip() == "":
            continue
        lines = question.split("\n")
        if len(lines) < 3:  # Skip incomplete questions
            continue
        question_text = lines[0].replace("- ", "")  # Remove the bullet point
        options = lines[1:-1]  # Extract options
        correct_answer = lines[-1].replace("Correct Answer: ", "")  # Extract correct answer

        # Ensure there are exactly 4 options (pad with empty strings if necessary)
        while len(options) < 4:
            options.append("")  # Add empty options if fewer than 4 are provided

        quiz_data.append({
            "question": question_text,
            "options": [opt.strip() for opt in options],
            "correct_answer": correct_answer.strip()
        })
    return quiz_data

# Streamlit UI for the Quiz Generator Chatbot
st.set_page_config(page_title="Quiz Generator", layout="wide")

# Main Content
st.title("📝 Quiz Generator")
st.markdown("Upload an image or PDF, and we'll generate a quiz for you!")

# Create two columns for layout
left_column, right_column = st.columns([1, 2])

# Left Column: File Upload and Extracted Text
with left_column:
    st.markdown("### 📂 Upload File")
    uploaded_file = st.file_uploader("Choose an image or PDF file...", type=["jpg", "jpeg", "png", "pdf"])

    if uploaded_file is not None:
        file_type = uploaded_file.type

        # Display image if uploaded file is an image
        if file_type in ["image/jpeg", "image/png", "image/jpg"]:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Image", use_column_width=True)
            text = extract_text_from_image(image)

        elif file_type == "application/pdf":
            text = extract_text_from_pdf(uploaded_file)

        # Show extracted text
        st.markdown("### 📝 Extracted Text")
        st.text_area("Extracted Text", text, height=300)

# Right Column: Quiz Generation and Display
with right_column:
    if uploaded_file is not None:
        st.markdown("### 🎯 Generate Quiz")
        num_questions = st.slider("Number of questions", 1, 10, 5)

        if st.button("Generate Quiz"):
            with st.spinner("Generating quiz..."):
                try:
                    quiz = generate_quiz(text, num_questions)
                    quiz_data = format_quiz(quiz)
                    if not quiz_data:
                        st.error("Failed to generate a valid quiz. Please try again.")
                    else:
                        st.session_state.quiz_data = quiz_data
                        st.success("Quiz generated successfully! Scroll down to answer the quiz.")
                except Exception as e:
                    st.error(f"An error occurred: {e}")

        if "quiz_data" in st.session_state:
            st.markdown("### 📝 Answer the Quiz")
            user_answers = []
            for i, question_data in enumerate(st.session_state.quiz_data):
                st.markdown(f"**Question {i+1}: {question_data['question']}**")
                user_answer = st.radio(
                    f"Select an answer for Question {i+1}",
                    question_data['options'],
                    key=f"question_{i}"
                )
                user_answers.append(user_answer)

            if st.button("Submit Answers"):
                correct_count = 0
                results = []
                for i, (user_answer, question_data) in enumerate(zip(user_answers, st.session_state.quiz_data)):
                    if user_answer == question_data['correct_answer']:
                        correct_count += 1
                        results.append(f"✅ Question {i+1}: Correct!")
                    else:
                        results.append(f"❌ Question {i+1}: Incorrect. The correct answer was **{question_data['correct_answer']}**.")

                st.markdown("### 📝 Quiz Results")
                for result in results:
                    st.write(result)
                st.write(f"**Total Score: {correct_count}/{len(st.session_state.quiz_data)}**")
    else:
        st.markdown("### 🎯 Generate Quiz")
        st.info("Please upload a file to generate a quiz.")

# Footer
st.markdown("---")
st.markdown("Developed with ❤️ by **Fiftheye Eduvision**")