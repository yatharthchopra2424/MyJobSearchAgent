from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pdf2image
import pytesseract
from PIL import Image
import io
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import base64
from pydantic import BaseModel
import time
import tempfile
import platform
import webbrowser
import requests
from bs4 import BeautifulSoup
import json

# Load environment variables
load_dotenv()

# Set up paths for external dependencies
# Check if we're on Windows and configure paths accordingly
if platform.system() == "Windows":
    # Check for poppler in common locations
    poppler_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "poppler", "bin")
    if os.path.exists(poppler_path):
        os.environ["PATH"] = poppler_path + os.pathsep + os.environ["PATH"]
        print(f"✓ Poppler path configured: {poppler_path}")
    else:
        print("Warning: Poppler path not found. PDF processing may fail.")
    
    # Configure pytesseract path if needed
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        print("✓ Tesseract OCR configured successfully")
    else:
        print("Warning: Tesseract OCR not found at default location.")

app = FastAPI()

# CORS middleware to allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JSearch API configuration
JSEARCH_API_KEY = "dfa377a0fbmsh8df80548e982bc2p1300b3jsnd59691bcf380"
JSEARCH_BASE_URL = "https://jsearch.p.rapidapi.com/search"

# Configure Gemini AI
gemini_api_key = os.getenv("GEMINI_API_KEY")
if gemini_api_key and gemini_api_key != "your_gemini_api_key_here":
    client = genai.Client(api_key=gemini_api_key)
    model = "gemini-2.0-flash-exp"
    print("✓ Gemini AI configured successfully")
else:
    print("Warning: Gemini API key not configured. Please update .env file")
    client = None
    model = None

# Global variable to store resume data for job applications
stored_resume_data = None

class JobApplicationRequest(BaseModel):
    job_profile: str
    experience: str
    location: str = None

class JobData(BaseModel):
    title: str
    company: str
    location: str
    job_url: str
    apply_url: str = None
    description: str = None

class ResumeData(BaseModel):
    filename: str
    content: bytes
    job_profile: str
    experience: str
    location: str
    resume_text: str

def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF file using OCR or fallback methods"""
    try:
        print(f"Processing PDF file of size: {len(pdf_file)} bytes")
        
        # First try PyPDF2 for text-based PDFs (faster)
        try:
            import PyPDF2
            print("Trying PyPDF2 extraction first...")
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file))
            text = ""
            
            for i, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    text += page_text + "\n"
                    print(f"Extracted {len(page_text)} characters from page {i+1}")
                except Exception:
                    continue
            
            if text.strip():
                print(f"PyPDF2 extraction successful: {len(text)} characters")
                return text.strip()
            else:
                print("PyPDF2 extraction yielded no text, trying OCR...")
        except ImportError:
            print("PyPDF2 not available, using OCR...")
        except Exception as e:
            print(f"PyPDF2 extraction failed: {str(e)}, trying OCR...")
        
        # Create a temporary file to save the PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            temp_pdf.write(pdf_file)
            temp_pdf_path = temp_pdf.name
            
        try:
            # Convert PDF pages to images
            print("Converting PDF to images with OCR...")
            try:
                # Try path-based conversion first
                images = pdf2image.convert_from_path(temp_pdf_path, dpi=300)
            except Exception as poppler_error:
                print(f"Error with poppler (pdf2image): {str(poppler_error)}")
                print("Trying alternative conversion method...")
                try:
                    # Try with bytes instead
                    images = pdf2image.convert_from_bytes(pdf_file, dpi=300)
                except Exception as bytes_error:
                    print(f"Bytes conversion also failed: {str(bytes_error)}")
                    # Clean up temp file
                    if os.path.exists(temp_pdf_path):
                        os.unlink(temp_pdf_path)
                    raise HTTPException(
                        status_code=400, 
                        detail="PDF processing failed. Please install poppler-utils."
                    )
            
            print(f"PDF has {len(images)} pages")
            
            text = ""
            
            # Extract text from each page using OCR
            for i, image in enumerate(images):
                try:
                    print(f"Processing page {i+1} with OCR...")
                    
                    # Use pytesseract to extract text from the image
                    gray_image = image.convert('L')  # Convert to grayscale
                    
                    # Apply OCR with custom config for better accuracy
                    custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
                    page_text = pytesseract.image_to_string(gray_image, lang='eng', config=custom_config)
                    
                    text += page_text + "\n"
                    print(f"Extracted {len(page_text)} characters from page {i+1}")
                    
                except Exception as page_error:
                    print(f"Error extracting text from page {i+1}: {str(page_error)}")
                    continue
            
            print(f"Total extracted text length: {len(text)} characters")
            
            # Clean up the temporary file
            os.unlink(temp_pdf_path)
            
            if not text.strip():
                raise HTTPException(status_code=400, detail="No text could be extracted from the PDF.")
            
            return text.strip()
            
        except Exception as processing_error:
            # Clean up the temporary file in case of error
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
            raise processing_error
    except Exception as e:
        print(f"Error in extract_text_from_pdf: {str(e)}")
        error_msg = str(e)
        if "poppler" in error_msg.lower():
            raise HTTPException(status_code=400, detail="PDF processing failed: Poppler not found. Please install poppler-utils.")
        else:
            raise HTTPException(status_code=400, detail=f"Error reading PDF: {error_msg}")

def analyze_resume_with_gemini(resume_text):
    """Analyze resume text using Gemini AI to extract job profile and experience level"""
    try:
        if not client or not model:
            raise HTTPException(status_code=500, detail="Gemini AI not configured. Please add your API key to .env file")
          # Truncate resume text if too long to avoid API limits
        max_text_length = 8000
        if len(resume_text) > max_text_length:
            resume_text = resume_text[:max_text_length] + "..."
        
        prompt = f"""
        Analyze the following resume text and extract:
        1. Job profile/role (e.g., "Data Scientist", "Full Stack Developer", "Software Developer", "Frontend Developer", "Backend Developer", "DevOps Engineer", etc.)
        2. Experience level (either "Fresher" or "Experienced")
        3. Preferred location (city or region mentioned in the resume, or "Remote" if remote work is preferred)

        Resume text:
        {resume_text}

        Please provide the response in this exact format:
        Job Profile: [job profile]
        Experience: [Fresher/Experienced]
        Location: [city/region or Remote]

        Be specific about the job profile based on the skills, projects, and experience mentioned in the resume.
        """
        
        print(f"Sending prompt to Gemini AI (text length: {len(resume_text)} chars)")
        
        # Create content using the new API format
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                ],
            ),
        ]
        
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="text/plain",
        )
        
        # Generate content using streaming API and collect the response
        response_text = ""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if chunk.text:
                response_text += chunk.text
        
        print(f"Gemini AI response: {response_text}")
          # Parse the response
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
        
        # Fallback parsing if exact format not found
        if not job_profile or not experience or not location:
            response_lower = response_text.lower()
            
            # Try to extract job profile from common patterns
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
                    job_profile = "Software Developer"  # Default
            
            # Try to extract experience level
            if not experience:
                if "fresher" in response_lower or "fresh" in response_lower or "entry" in response_lower:
                    experience = "Fresher"
                elif "experienced" in response_lower or "experience" in response_lower:
                    experience = "Experienced"
                else:
                    experience = "Fresher"  # Default for safety
              # Try to extract location
            if not location:
                # Look for common city patterns
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
                        location = "chicago"  # Default location
        
        print(f"Extracted - Job Profile: {job_profile}, Experience: {experience}, Location: {location}")
        return job_profile, experience, location
    
    except Exception as e:
        print(f"Error in analyze_resume_with_gemini: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing resume: {str(e)}")

def search_jobs_with_jsearch(job_profile, experience, location="chicago", num_pages=1):
    """Search for jobs using JSearch API"""
    try:
        # Construct the search query based on job profile and experience
        query = f"{job_profile} jobs in {location}"
        
        # Add experience level to the query
        if experience.lower() == "experienced":
            query += " senior"
        elif experience.lower() == "fresher":
            query += " entry level"
        
        # JSearch API parameters
        params = {
            'query': query,
            'page': 1,
            'num_pages': num_pages,
            'country': 'us',
            'date_posted': 'all'
        }
        
        headers = {
            'x-rapidapi-host': 'jsearch.p.rapidapi.com',
            'x-rapidapi-key': JSEARCH_API_KEY
        }
        
        print(f"Searching jobs with query: {query}")
        
        response = requests.get(JSEARCH_BASE_URL, params=params, headers=headers)
        
        if response.status_code != 200:
            print(f"JSearch API error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=500, detail=f"Job search API error: {response.status_code}")
        
        data = response.json()
        
        if 'data' not in data:
            print("No jobs found in API response")
            return []
        
        jobs = []
        for job_data in data['data']:
            try:
                # Improved location extraction
                city = job_data.get('job_city', '')
                state = job_data.get('job_state', '')
                country = job_data.get('job_country', '')
                location = ', '.join(filter(None, [city, state, country]))
                if not location:
                    location = job_data.get('job_location', job_data.get('employer_location', 'N/A'))
                job = {
                    'title': job_data.get('job_title', 'N/A'),
                    'company': job_data.get('employer_name', 'N/A'),
                    'location': location,
                    'job_url': job_data.get('job_apply_link', job_data.get('job_url', '')),
                    'apply_url': job_data.get('job_apply_link', ''),
                    'description': job_data.get('job_description', 'No description available'),
                    'employment_type': job_data.get('job_employment_type', 'N/A'),
                    'posted_at': job_data.get('job_posted_at_datetime_utc', 'N/A'),
                    'salary': job_data.get('job_min_salary', 'N/A')
                }
                jobs.append(job)
            except Exception as e:
                print(f"Error processing job data: {e}")
                continue
        
        print(f"Found {len(jobs)} jobs")
        return jobs
        
    except requests.exceptions.RequestException as e:
        print(f"Network error with JSearch API: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
    except Exception as e:
        print(f"Error in search_jobs_with_jsearch: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching jobs: {str(e)}")

@app.post("/upload-resume")
async def upload_resume(resume: UploadFile = File(...)):
    """Upload and analyze resume"""
    global stored_resume_data
    
    try:
        print(f"Received file upload: {resume.filename}")
        
        # Validate file type
        if not resume.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Read file content
        content = await resume.read()
        print(f"File content read successfully, size: {len(content)} bytes")
          # Extract text from PDF
        resume_text = extract_text_from_pdf(content)
        
        if not resume_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF. Please ensure the PDF contains readable text.")
        
        print(f"Text extracted successfully, length: {len(resume_text)} characters")
        
        # Analyze with Gemini AI
        job_profile, experience, location = analyze_resume_with_gemini(resume_text)
        
        if not job_profile or not experience or not location:
            raise HTTPException(status_code=500, detail="Could not extract job profile, experience, and location from resume")
        
        # Store resume data globally for job applications
        stored_resume_data = {
            "filename": resume.filename,
            "content": content,
            "job_profile": job_profile,
            "experience": experience,
            "location": location,
            "resume_text": resume_text
        }
        
        print(f"Analysis complete - Profile: {job_profile}, Experience: {experience}, Location: {location}")
        
        return {
            "message": "Resume analyzed successfully",
            "job_profile": job_profile,
            "experience": experience,
            "location": location,
            "resume_stored": True,
            "analysis_summary": f"Job Profile: {job_profile}\nExperience Level: {experience}\nPreferred Location: {location}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in upload_resume: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.post("/apply-job")
async def apply_job(request: JobApplicationRequest):
    """Search for jobs using JSearch API"""
    
    if not request.job_profile or not request.experience:
        raise HTTPException(status_code=400, detail="Job profile and experience are required")
    
    # Use location from request or default to stored resume data
    location = request.location
    if not location and stored_resume_data:
        location = stored_resume_data.get("location", "chicago")
    elif not location:
        location = "chicago"  # Default location
    
    try:
        # Search for jobs using JSearch API
        jobs = search_jobs_with_jsearch(request.job_profile, request.experience, location)
        
        return {
            "message": f"Found {len(jobs)} jobs for {request.job_profile} in {location}",
            "jobs": jobs,
            "search_criteria": {
                "job_profile": request.job_profile,
                "experience": request.experience,
                "location": location
            },
            "success": True
        }
        
    except Exception as e:
        print(f"Error in apply_job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching for jobs: {str(e)}")

@app.get("/get-jobs")
async def get_jobs(job_profile: str = None, experience: str = None, location: str = None, max_jobs: int = 10):
    """Get job listings based on profile, experience, and location using JSearch API"""
    global stored_resume_data
    
    # Use stored resume data if no parameters provided
    if not job_profile or not experience or not location:
        if not stored_resume_data:
            raise HTTPException(status_code=400, detail="No resume data found. Please upload a resume first.")
        job_profile = job_profile or stored_resume_data["job_profile"]
        experience = experience or stored_resume_data["experience"]
        location = location or stored_resume_data.get("location", "chicago")
    
    try:
        # Use JSearch API to get jobs
        jobs = search_jobs_with_jsearch(job_profile, experience, location, num_pages=1)
        
        # Limit the number of jobs returned
        if len(jobs) > max_jobs:
            jobs = jobs[:max_jobs]
        
        return {
            "message": f"Found {len(jobs)} jobs",
            "jobs": jobs,
            "search_criteria": {
                "job_profile": job_profile,
                "experience": experience,
                "location": location
            }
        }
    except Exception as e:
        print(f"Error getting jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving jobs: {str(e)}")

@app.post("/apply-to-job")
async def apply_to_specific_job(job_url: str):
    """Open job application URL in browser"""
    global stored_resume_data
    
    if not stored_resume_data:
        raise HTTPException(status_code=400, detail="No resume data found. Please upload a resume first.")
    
    if not job_url:
        raise HTTPException(status_code=400, detail="Job URL is required")
    
    try:
        import webbrowser
        webbrowser.open(job_url)
        
        return {
            "message": "Job application opened in browser",
            "job_url": job_url,
            "status": "application_opened",
            "note": "Please complete the application manually in the opened browser window"
        }
            
    except Exception as e:
        print(f"Error opening job application: {str(e)}")
        return {
            "message": "Could not open job application automatically",
            "job_url": job_url,
            "status": "failed",
            "suggestion": "Please copy and paste the URL into your browser manually"
        }

@app.get("/resume-status")
async def get_resume_status():
    """Get the current status of stored resume data"""
    global stored_resume_data
    
    if stored_resume_data:
        return {
            "resume_uploaded": True,
            "filename": stored_resume_data["filename"],
            "job_profile": stored_resume_data["job_profile"],
            "experience": stored_resume_data["experience"],
            "location": stored_resume_data.get("location", "N/A"),
            "text_length": len(stored_resume_data["resume_text"])
        }
    else:
        return {
            "resume_uploaded": False,
            "message": "No resume data found. Please upload a resume."
        }

@app.get("/")
async def root():
    return {"message": "JobX Backend API is running"}

if __name__ == "__main__":
    import uvicorn
    print("Starting JobX Backend...")
    print("Make sure to:")
    print("1. Update .env file with your Gemini API key")
    print("2. Install Tesseract OCR for PDF processing")
    print("3. JSearch API configured for job searching")
    print("4. Frontend should be running on http://localhost:5173")
    print("")
    uvicorn.run(app, host="127.0.0.1", port=8000)
    uvicorn.run(app, host="127.0.0.1", port=8000)
