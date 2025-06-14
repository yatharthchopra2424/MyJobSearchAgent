from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from resume import extract_text_from_pdf, analyze_resume_with_gemini
from job_search import search_jobs_with_jsearch
from utils import configure_tesseract

load_dotenv()
configure_tesseract()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stored_resume_data = None

class JobApplicationRequest(BaseModel):
    job_profile: str
    experience: str
    location: str = None

@app.post("/upload-resume")
async def upload_resume(resume: UploadFile = File(...)):
    global stored_resume_data
    if not resume.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    content = await resume.read()
    resume_text = extract_text_from_pdf(content)
    job_profile, experience, location = analyze_resume_with_gemini(resume_text)
    stored_resume_data = {
        "filename": resume.filename,
        "content": content,
        "job_profile": job_profile,
        "experience": experience,
        "location": location,
        "resume_text": resume_text
    }
    return {
        "message": "Resume analyzed successfully",
        "job_profile": job_profile,
        "experience": experience,
        "location": location,
        "resume_stored": True,
        "analysis_summary": f"Job Profile: {job_profile}\nExperience Level: {experience}\nPreferred Location: {location}"
    }

@app.post("/apply-job")
async def apply_job(request: JobApplicationRequest):
    global stored_resume_data
    location = request.location or (stored_resume_data.get("location") if stored_resume_data else "chicago")
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

@app.get("/get-jobs")
async def get_jobs(job_profile: str = None, experience: str = None, location: str = None):
    global stored_resume_data
    if not job_profile or not experience or not location:
        if not stored_resume_data:
            raise HTTPException(status_code=400, detail="No resume data found. Please upload a resume first.")
        job_profile = job_profile or stored_resume_data["job_profile"]
        experience = experience or stored_resume_data["experience"]
        location = location or stored_resume_data.get("location", "chicago")
    jobs = search_jobs_with_jsearch(job_profile, experience, location, num_pages=1)
    return {
        "message": f"Found {len(jobs)} jobs",
        "jobs": jobs,
        "search_criteria": {
            "job_profile": job_profile,
            "experience": experience,
            "location": location
        }
    }

@app.post("/apply-to-job")
async def apply_to_specific_job(job_url: str):
    global stored_resume_data
    if not stored_resume_data:
        raise HTTPException(status_code=400, detail="No resume data found. Please upload a resume first.")
    if not job_url:
        raise HTTPException(status_code=400, detail="Job URL is required")
    import webbrowser
    webbrowser.open(job_url)
    return {
        "message": "Job application opened in browser",
        "job_url": job_url,
        "status": "application_opened",
        "note": "Please complete the application manually in the opened browser window"
    }

@app.get("/resume-status")
async def get_resume_status():
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
    uvicorn.run(app, host="127.0.0.1", port=8000)
