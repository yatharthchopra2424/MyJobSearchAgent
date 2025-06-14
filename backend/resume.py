import os
import io
import tempfile
from fastapi import HTTPException
from google import genai
from google.genai import types
import pytesseract
from PIL import Image
import pdf2image
import platform
import PyPDF2

# Configure Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
    client = genai.Client(api_key=GEMINI_API_KEY)
    model = "gemini-2.0-flash-exp"
else:
    client = None
    model = None

# Configure Tesseract for Windows
if platform.system() == "Windows":
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

def extract_text_from_pdf(pdf_file):
    try:
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file))
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                text += page_text + "\n"
            if text.strip():
                return text.strip()
        except Exception:
            pass
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            temp_pdf.write(pdf_file)
            temp_pdf_path = temp_pdf.name
        try:
            images = pdf2image.convert_from_path(temp_pdf_path, dpi=300)
            text = ""
            for image in images:
                gray_image = image.convert('L')
                custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
                page_text = pytesseract.image_to_string(gray_image, lang='eng', config=custom_config)
                text += page_text + "\n"
            os.unlink(temp_pdf_path)
            if not text.strip():
                raise HTTPException(status_code=400, detail="No text could be extracted from the PDF.")
            return text.strip()
        except Exception as processing_error:
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
            raise processing_error
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading PDF: {str(e)}")

def analyze_resume_with_gemini(resume_text):
    try:
        if not client or not model:
            raise HTTPException(status_code=500, detail="Gemini AI not configured. Please add your API key to .env file")
        max_text_length = 8000
        if len(resume_text) > max_text_length:
            resume_text = resume_text[:max_text_length] + "..."
        prompt = f"""
        Analyze the following resume text and extract:
        1. Job profile/role (e.g., 'Data Scientist', ...)
        2. Experience level (either 'Fresher' or 'Experienced')
        3. Preferred location (city or region mentioned in the resume, or 'Remote' if remote work is preferred)
        Resume text:
        {resume_text}
        Please provide the response in this exact format:
        Job Profile: [job profile]
        Experience: [Fresher/Experienced]
        Location: [city/region or Remote]
        """
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ]
        generate_content_config = types.GenerateContentConfig(response_mime_type="text/plain")
        response_text = ""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if chunk.text:
                response_text += chunk.text
        lines = response_text.strip().split('\n')
        job_profile = ""
        experience = ""
        location = ""
        for line in lines:
            line = line.strip()
            if line.startswith("Job Profile:"):
                job_profile = line.replace("Job Profile:", "").strip()
            elif line.startswith("Experience:"):
                experience = line.replace("Experience:", "").strip()
            elif line.startswith("Location:"):
                location = line.replace("Location:", "").strip()
        if not job_profile or not experience or not location:
            response_lower = response_text.lower()
            if not job_profile:
                if "data scientist" in response_lower:
                    job_profile = "Data Scientist"
                elif "full stack" in response_lower or "fullstack" in response_lower:
                    job_profile = "Full Stack Developer"
                elif "software developer" in response_lower or "software engineer" in response_lower:
                    job_profile = "Software Developer"
                elif "frontend" in response_lower or "front-end" in response_lower:
                    job_profile = "Frontend Developer"
                elif "backend" in response_lower or "back-end" in response_lower:
                    job_profile = "Backend Developer"
                else:
                    job_profile = "Software Developer"
            if not experience:
                if "fresher" in response_lower or "fresh" in response_lower or "entry" in response_lower:
                    experience = "Fresher"
                elif "experienced" in response_lower or "experience" in response_lower:
                    experience = "Experienced"
                else:
                    experience = "Fresher"
            if not location:
                cities = ["new york", "san francisco", "chicago", "austin", "seattle", "boston", "denver", "atlanta"]
                location_found = False
                for city in cities:
                    if city in response_lower:
                        location = city.title()
                        location_found = True
                        break
                if not location_found:
                    if "remote" in response_lower:
                        location = "Remote"
                    else:
                        location = "chicago"
        return job_profile, experience, location
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing resume: {str(e)}")
