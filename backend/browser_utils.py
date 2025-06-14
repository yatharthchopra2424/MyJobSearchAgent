import os
import platform
import webbrowser
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def is_chrome_installed():
    """Check if Chrome browser is installed on the system"""
    if platform.system() == "Windows":
        chrome_paths = [
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
            os.path.join(os.environ.get('LOCALAPPDATA', ''), r'Google\Chrome\Application\chrome.exe')
        ]
        return any(os.path.exists(path) for path in chrome_paths)
    elif platform.system() == "Darwin":  # macOS
        chrome_paths = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        ]
        return any(os.path.exists(path) for path in chrome_paths)
    else:  # Linux
        try:
            os.system('which google-chrome')
            return True
        except:
            return False

def fallback_linkedin_search(job_profile, experience):
    """Fallback method to open LinkedIn in the default browser"""
    search_query = f"{job_profile} AND {experience} AND Hiring"
    search_url = f"https://www.linkedin.com/jobs/search/?keywords={search_query}"
    
    print(f"Opening LinkedIn search in default browser: {search_url}")
    webbrowser.open(search_url)
    return True

def linkedin_job_search(job_profile, experience):
    """Search for jobs on LinkedIn using Selenium if available, fallback to simple browser otherwise"""
    if not is_chrome_installed():
        print("Chrome not detected. Using fallback method.")
        return fallback_linkedin_search(job_profile, experience)
    
    driver = None
    try:
        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--incognito")  # Open in incognito mode
        chrome_options.add_argument("--start-maximized")  # Start with maximized window
        
        # Create a user data directory to ensure a clean session
        import tempfile
        user_data_dir = tempfile.mkdtemp()
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        chrome_options.add_argument("--no-default-browser-check")
        
        # Try to set up the Chrome WebDriver
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print("Successfully launched Chrome with ChromeDriverManager")
        except Exception as manager_error:
            print(f"Error with ChromeDriverManager: {str(manager_error)}")
            raise Exception("ChromeDriver setup failed")
        
        # Navigate to LinkedIn jobs search
        try:
            search_query = f"{job_profile} AND {experience} AND Hiring"
            
            # Go directly to LinkedIn jobs
            driver.get("https://www.linkedin.com/jobs/")
            
            # Wait for search box to be available (max 10 seconds)
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[aria-label*='Search by title']"))
                )
                
                # Find search box and enter query
                search_box = driver.find_element(By.CSS_SELECTOR, "input[aria-label*='Search by title']")
                search_box.clear()
                search_box.send_keys(search_query)
                search_box.send_keys(Keys.RETURN)
                
                print(f"Job search initiated for: {search_query}")
                print("Browser will remain open for manual interaction")
                
                # Keep browser open for user interaction
                return True
            except Exception as wait_error:
                print(f"Error waiting for search box: {str(wait_error)}")
                # If we can't find the search box, try a direct URL approach
                search_url = f"https://www.linkedin.com/jobs/search/?keywords={search_query}"
                driver.get(search_url)
                print(f"Redirected to search URL: {search_url}")
                return True
                
        except Exception as e:
            print(f"Error during LinkedIn navigation: {str(e)}")
            return False
            
    except Exception as e:
        print(f"Critical error in LinkedIn automation: {str(e)}")
        if driver:
            driver.quit()
        return fallback_linkedin_search(job_profile, experience)

def scrape_linkedin_jobs(job_profile, experience, max_jobs=10):
    """Scrape job listings from LinkedIn and return structured data"""
    if not is_chrome_installed():
        print("Chrome not detected. Cannot scrape jobs.")
        return []
    
    driver = None
    jobs = []
    
    try:
        # Configure Chrome options for scraping
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--headless")  # Run in background for scraping
        
        # Set up ChromeDriver
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print("Successfully launched Chrome for job scraping")
        except Exception as e:
            print(f"Error setting up ChromeDriver for scraping: {str(e)}")
            return []
        
        # Search for jobs
        search_query = f"{job_profile} AND {experience}"
        search_url = f"https://www.linkedin.com/jobs/search/?keywords={search_query}&location=&geoId=&f_TPR=r604800&position=1&pageNum=0"
        
        driver.get(search_url)
        time.sleep(3)  # Wait for page to load
        
        # Find job listings
        try:
            job_cards = driver.find_elements(By.CSS_SELECTOR, ".job-search-card")
            
            for i, card in enumerate(job_cards[:max_jobs]):
                try:
                    # Extract job details
                    title_element = card.find_element(By.CSS_SELECTOR, ".base-search-card__title")
                    company_element = card.find_element(By.CSS_SELECTOR, ".base-search-card__subtitle")
                    location_element = card.find_element(By.CSS_SELECTOR, ".job-search-card__location")
                    job_link = card.find_element(By.CSS_SELECTOR, ".base-card__full-link")
                    
                    job_data = {
                        "title": title_element.text.strip(),
                        "company": company_element.text.strip(),
                        "location": location_element.text.strip(),
                        "job_url": job_link.get_attribute("href"),
                        "apply_url": None,
                        "description": None
                    }
                    
                    # Try to get apply link by clicking on the job
                    try:
                        job_link.click()
                        time.sleep(2)
                        
                        # Look for apply button
                        apply_buttons = driver.find_elements(By.CSS_SELECTOR, 
                            ".jobs-apply-button, .jobs-s-apply-button, [data-control-name='jobdetails_topcard_inapply']")
                        
                        if apply_buttons:
                            job_data["apply_url"] = apply_buttons[0].get_attribute("href") or driver.current_url
                        
                        # Get job description
                        desc_elements = driver.find_elements(By.CSS_SELECTOR, 
                            ".jobs-description__content, .jobs-description-content__text")
                        if desc_elements:
                            job_data["description"] = desc_elements[0].text.strip()[:500]  # Limit description length
                        
                        # Go back to search results
                        driver.back()
                        time.sleep(1)
                        
                    except Exception as detail_error:
                        print(f"Error getting job details for {job_data['title']}: {str(detail_error)}")
                    
                    jobs.append(job_data)
                    print(f"Scraped job {i+1}: {job_data['title']} at {job_data['company']}")
                    
                except Exception as card_error:
                    print(f"Error processing job card {i+1}: {str(card_error)}")
                    continue
                    
        except Exception as scraping_error:
            print(f"Error during job scraping: {str(scraping_error)}")
        
        print(f"Successfully scraped {len(jobs)} jobs")
        return jobs
        
    except Exception as e:
        print(f"Critical error in job scraping: {str(e)}")
        return []
    finally:
        if driver:
            driver.quit()

def apply_to_job_with_resume(job_url, resume_data):
    """Attempt to apply to a job using the stored resume data"""
    if not is_chrome_installed():
        print("Chrome not detected. Cannot auto-apply to jobs.")
        return False
    
    driver = None
    
    try:
        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--start-maximized")
        
        # Set up ChromeDriver
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print("Successfully launched Chrome for job application")
        except Exception as e:
            print(f"Error setting up ChromeDriver for application: {str(e)}")
            return False
        
        # Navigate to job URL
        driver.get(job_url)
        time.sleep(3)
        
        # Look for apply button
        apply_buttons = driver.find_elements(By.CSS_SELECTOR, 
            ".jobs-apply-button, .jobs-s-apply-button, [data-control-name='jobdetails_topcard_inapply']")
        
        if not apply_buttons:
            print("No apply button found on the job page")
            return False
        
        # Click apply button
        apply_buttons[0].click()
        time.sleep(3)
        
        # Check if we need to upload resume
        file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        
        if file_inputs:
            # Save resume to temporary file for upload
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(resume_data["content"])
                temp_file_path = temp_file.name
            
            try:
                # Upload resume
                file_inputs[0].send_keys(temp_file_path)
                time.sleep(2)
                print("Resume uploaded successfully")
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
        
        # Look for submit/apply button
        submit_buttons = driver.find_elements(By.CSS_SELECTOR, 
            "[data-control-name='continue_unify'], .artdeco-button--primary, button[type='submit']")
        
        if submit_buttons:
            print("Found submit button - application process initiated")
            # Note: We don't actually click submit to avoid unwanted applications
            # Instead, we leave the form filled for user review
            return True
        
        print("Application form opened - please complete manually")
        return True
        
    except Exception as e:
        print(f"Error during job application: {str(e)}")
        return False
    # Note: We don't close the driver here to allow manual completion
