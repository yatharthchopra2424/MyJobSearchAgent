import os
import requests
from fastapi import HTTPException

JSEARCH_API_KEY = "dfa377a0fbmsh8df80548e982bc2p1300b3jsnd59691bcf380"
JSEARCH_BASE_URL = "https://jsearch.p.rapidapi.com/search"

def search_jobs_with_jsearch(job_profile, experience, location="chicago", num_pages=1):
    """Search for jobs using JSearch API"""
    try:
        # Use only state for location if possible
        state = location.split(",")[-1].strip() if "," in location else location
        query = f"{job_profile} jobs in {state}"
        if experience.lower() == "experienced":
            query += " senior"
        elif experience.lower() == "fresher":
            query += " entry level"
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
        response = requests.get(JSEARCH_BASE_URL, params=params, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Job search API error: {response.status_code}")
        data = response.json()
        if 'data' not in data:
            return []
        jobs = []
        for job_data in data['data']:
            try:
                city = job_data.get('job_city', '')
                state = job_data.get('job_state', '')
                country = job_data.get('job_country', '')
                location_str = ', '.join(filter(None, [city, state, country]))
                if not location_str:
                    location_str = job_data.get('job_location', job_data.get('employer_location', 'N/A'))
                job = {
                    'title': job_data.get('job_title', 'N/A'),
                    'company': job_data.get('employer_name', 'N/A'),
                    'location': location_str,
                    'job_url': job_data.get('job_apply_link', job_data.get('job_url', '')),
                    'apply_url': job_data.get('job_apply_link', ''),
                    'description': job_data.get('job_description', 'No description available'),
                    'employment_type': job_data.get('job_employment_type', 'N/A'),
                    'posted_at': job_data.get('job_posted_at_datetime_utc', 'N/A'),
                    'salary': job_data.get('job_min_salary', 'N/A')
                }
                jobs.append(job)
            except Exception:
                continue
        return jobs
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching jobs: {str(e)}")
