# 1️⃣ Use an official lightweight Python image
FROM python:3.9

# 2️⃣ Set the working directory
WORKDIR /app

# 3️⃣ Copy all files to the container
COPY . /app/

# 4️⃣ Install system dependencies for Poppler and Tesseract
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# 5️⃣ Upgrade pip before installing dependencies
RUN pip install --upgrade pip

# 6️⃣ Install required Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 7️⃣ Expose the Streamlit port
EXPOSE 8501

# 8️⃣ Run the correct Streamlit script (REPLACE HERE)
CMD ["streamlit", "run", "quiz_deep.py", "--server.port=8501", "--server.address=0.0.0.0"]
