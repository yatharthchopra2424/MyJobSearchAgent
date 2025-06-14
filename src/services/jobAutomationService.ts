// Job Automation Service to integrate with the Python backend
export interface ResumeAnalysisResult {
  job_profile: string;
  experience: string;
  resume_stored: boolean;
}

export interface JobSearchResult {
  message: string;
  jobs: Array<{
    title: string;
    company: string;
    location: string;
    job_url: string;
    apply_url?: string;
    description?: string;
  }>;
  search_criteria: {
    job_profile: string;
    experience: string;
  };
}

export interface JobApplicationResult {
  message: string;
  job_url: string;
  status: string;
  note?: string;
}

export class JobAutomationService {
  private static readonly BASE_URL = 'http://localhost:8000';

  // Upload and analyze resume
  static async uploadAndAnalyzeResume(file: File): Promise<ResumeAnalysisResult> {
    try {
      const formData = new FormData();
      formData.append('resume', file);

      const response = await fetch(`${this.BASE_URL}/upload-resume`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to upload resume');
      }

      return await response.json();
    } catch (error) {
      console.error('Error uploading resume:', error);
      throw error;
    }
  }

  // Start LinkedIn job search automation
  static async startJobSearch(jobProfile: string, experience: string): Promise<{ message: string; success: boolean }> {
    try {
      const response = await fetch(`${this.BASE_URL}/apply-job`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          job_profile: jobProfile,
          experience: experience,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to start job search');
      }

      const result = await response.json();
      return {
        message: result.message,
        success: !result.error
      };
    } catch (error) {
      console.error('Error starting job search:', error);
      throw error;
    }
  }

  // Get job listings from automation service
  static async getJobListings(jobProfile?: string, experience?: string, maxJobs: number = 10): Promise<JobSearchResult> {
    try {
      const params = new URLSearchParams();
      if (jobProfile) params.append('job_profile', jobProfile);
      if (experience) params.append('experience', experience);
      params.append('max_jobs', maxJobs.toString());

      const response = await fetch(`${this.BASE_URL}/get-jobs?${params.toString()}`);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to get job listings');
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting job listings:', error);
      throw error;
    }
  }

  // Apply to a specific job using the automation service
  static async applyToJob(jobUrl: string): Promise<JobApplicationResult> {
    try {
      const response = await fetch(`${this.BASE_URL}/apply-to-job`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `job_url=${encodeURIComponent(jobUrl)}`,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to apply to job');
      }

      return await response.json();
    } catch (error) {
      console.error('Error applying to job:', error);
      throw error;
    }
  }

  // Get current resume status
  static async getResumeStatus(): Promise<{
    resume_uploaded: boolean;
    filename?: string;
    job_profile?: string;
    experience?: string;
    text_length?: number;
  }> {
    try {
      const response = await fetch(`${this.BASE_URL}/resume-status`);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to get resume status');
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting resume status:', error);
      throw error;
    }
  }

  // Check if the automation backend is available
  static async checkBackendStatus(): Promise<boolean> {
    try {
      const response = await fetch(`${this.BASE_URL}/`, {
        method: 'GET',
        timeout: 5000
      } as any);

      return response.ok;
    } catch (error) {
      console.error('Backend not available:', error);
      return false;
    }
  }
}
