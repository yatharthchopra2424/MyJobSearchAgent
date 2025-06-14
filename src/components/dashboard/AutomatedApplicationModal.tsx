import React, { useState, useEffect } from 'react';
import { X, Upload, Calendar, Building, FileText, User, Bot, Search, ExternalLink, Loader, CheckCircle, AlertCircle } from 'lucide-react';
import { ApplicationStatus } from '../../types/jobApplication';
import { FileUploadService } from '../../services/fileUploadService';
import { JobAutomationService, ResumeAnalysisResult, JobSearchResult } from '../../services/jobAutomationService';
import { useAuth } from '../../hooks/useAuth';

interface AutomatedApplicationModalProps {
  onSave: (applications: any[]) => void;
  onClose: () => void;
}

const AutomatedApplicationModal: React.FC<AutomatedApplicationModalProps> = ({ onSave, onClose }) => {
  const [currentStep, setCurrentStep] = useState<'manual' | 'automation' | 'jobs' | 'applying'>('automation');  const [formData, setFormData] = useState({
    company_name: '',
    position: '',
    status: ApplicationStatus.APPLIED as keyof typeof ApplicationStatus,
    application_date: '',
    job_description: '',
    notes: '',
    resume_url: '',
    cover_letter_url: ''
  });
  const [uploading, setUploading] = useState({ resume: false, cover_letter: false });
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  
  // Automation states
  const [resumeAnalysis, setResumeAnalysis] = useState<ResumeAnalysisResult | null>(null);
  const [jobListings, setJobListings] = useState<JobSearchResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [backendAvailable, setBackendAvailable] = useState(false);
  const [selectedJobs, setSelectedJobs] = useState<Set<string>>(new Set());

  const { user } = useAuth();
  useEffect(() => {
    checkBackendStatus();    // Initialize form with default values for new application
    setFormData({
      company_name: '',
      position: '',
      status: ApplicationStatus.APPLIED as keyof typeof ApplicationStatus,
      application_date: new Date().toISOString().split('T')[0],
      job_description: '',
      notes: '',
      resume_url: '',
      cover_letter_url: ''
    });
  }, []);

  const checkBackendStatus = async () => {
    const available = await JobAutomationService.checkBackendStatus();
    setBackendAvailable(available);
    if (available) {
      // Check if resume is already uploaded
      try {
        const status = await JobAutomationService.getResumeStatus();
        if (status.resume_uploaded) {
          setResumeAnalysis({
            job_profile: status.job_profile!,
            experience: status.experience!,
            resume_stored: true
          });
        }
      } catch (error) {
        console.error('Error checking resume status:', error);
      }
    }
  };
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    const submitData = {
      ...formData,
      application_date: new Date(formData.application_date).toISOString(),
    };

    // Pass as array to match expected interface
    onSave([submitData]);
  };

  const handleFileUpload = async (field: 'resume_url' | 'cover_letter_url', file: File) => {
    if (!user) return;
    
    const type = field === 'resume_url' ? 'resume' : 'cover_letter';
    
    try {
      setError('');
      setUploading(prev => ({ ...prev, [type]: true }));

      // Validate file
      const validation = FileUploadService.validateFile(file);
      if (!validation.isValid) {
        throw new Error(validation.error);
      }

      // Upload file
      const downloadURL = await FileUploadService.uploadFile(file, user.uid, type);
      setFormData(prev => ({ ...prev, [field]: downloadURL }));
    } catch (err: any) {
      setError(err.message || 'Failed to upload file');
    } finally {
      setUploading(prev => ({ ...prev, [type]: false }));
    }
  };

  const handleFileInputChange = (field: 'resume_url' | 'cover_letter_url') => (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileUpload(field, file);
    }
  };

  const handleResumeAnalysis = async (file: File) => {
    if (!backendAvailable) {
      setError('Automation backend is not available. Please ensure the Python server is running.');
      return;
    }

    try {
      setIsAnalyzing(true);
      setError('');
      setMessage('Analyzing your resume...');
      
      const result = await JobAutomationService.uploadAndAnalyzeResume(file);
      setResumeAnalysis(result);
      setMessage(`Resume analyzed! Detected profile: ${result.job_profile}, Experience: ${result.experience}`);
      setCurrentStep('automation');
    } catch (err: any) {
      setError(err.message || 'Failed to analyze resume');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleJobSearch = async () => {
    if (!resumeAnalysis || !backendAvailable) {
      setError('Please analyze your resume first');
      return;
    }

    try {
      setIsSearching(true);
      setError('');
      setMessage('Starting automated job search...');
      
      // Start LinkedIn automation
      const searchResult = await JobAutomationService.startJobSearch(
        resumeAnalysis.job_profile, 
        resumeAnalysis.experience
      );
      
      setMessage(searchResult.message);
      
      // Get job listings
      const jobsResult = await JobAutomationService.getJobListings(
        resumeAnalysis.job_profile,
        resumeAnalysis.experience,
        10
      );
      
      setJobListings(jobsResult);
      setCurrentStep('jobs');
      setMessage(`Found ${jobsResult.jobs.length} job opportunities`);
    } catch (err: any) {
      setError(err.message || 'Failed to search for jobs');
    } finally {
      setIsSearching(false);
    }
  };
  const handleBulkApply = async () => {
    if (!jobListings || selectedJobs.size === 0) {
      setError('Please select at least one job to apply to');
      return;
    }

    try {
      setIsApplying(true);
      setCurrentStep('applying');
      setError('');
      
      const selectedJobsList = jobListings.jobs.filter(job => selectedJobs.has(job.job_url));
      let successCount = 0;
      let failCount = 0;
      const successfulApplications: any[] = [];

      for (const job of selectedJobsList) {
        try {
          setMessage(`Applying to ${job.title} at ${job.company}...`);
          
          const result = await JobAutomationService.applyToJob(job.job_url);
          
          if (result.status === 'application_started') {            const applicationData = {
              company_name: job.company,
              position: job.title,
              status: ApplicationStatus.APPLIED,
              application_date: new Date().toISOString(),
              job_description: job.description || '',
              notes: `Applied via automation: ${result.message}`,
              resume_url: formData.resume_url,
              cover_letter_url: formData.cover_letter_url
            };
            
            successfulApplications.push(applicationData);
            successCount++;
          } else {
            failCount++;
          }
          
          // Add delay between applications
          await new Promise(resolve => setTimeout(resolve, 2000));
        } catch (jobError) {
          console.error(`Failed to apply to ${job.title}:`, jobError);
          failCount++;
        }
      }

      // Save all successful applications at once
      if (successfulApplications.length > 0) {
        onSave(successfulApplications);
      }

      setMessage(`Application process completed! Successfully applied to ${successCount} jobs. ${failCount} applications failed.`);
    } catch (err: any) {
      setError(err.message || 'Failed to apply to jobs');
    } finally {
      setIsApplying(false);
    }
  };

  const toggleJobSelection = (jobUrl: string) => {
    const newSelected = new Set(selectedJobs);
    if (newSelected.has(jobUrl)) {
      newSelected.delete(jobUrl);
    } else {
      newSelected.add(jobUrl);
    }
    setSelectedJobs(newSelected);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-4">            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              AI Job Application Assistant
            </h2>
            {backendAvailable && (
              <div className="flex gap-2">
                <button
                  onClick={() => setCurrentStep('manual')}
                  className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                    currentStep === 'manual' 
                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' 
                      : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                  }`}
                >
                  Manual Entry
                </button>
                <button
                  onClick={() => setCurrentStep('automation')}
                  className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors flex items-center gap-1 ${
                    currentStep === 'automation' || currentStep === 'jobs' || currentStep === 'applying'
                      ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' 
                      : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                  }`}
                >
                  <Bot size={16} />
                  Automation
                </button>
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X size={24} />
          </button>
        </div>

        <div className="p-6">
          {/* Status Messages */}
          {error && (
            <div className="bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 p-3 rounded-lg text-sm mb-4 flex items-center gap-2">
              <AlertCircle size={16} />
              {error}
            </div>
          )}
          
          {message && !error && (
            <div className="bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 p-3 rounded-lg text-sm mb-4 flex items-center gap-2">
              <CheckCircle size={16} />
              {message}
            </div>
          )}

          {!backendAvailable && currentStep !== 'manual' && (
            <div className="bg-yellow-50 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400 p-3 rounded-lg text-sm mb-4">
              Automation backend is not available. Please ensure the Python server is running on localhost:8000, or use manual entry.
            </div>
          )}

          {/* Manual Entry Form */}
          {currentStep === 'manual' && (
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    <Building size={16} className="inline mr-2" />
                    Company Name
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.company_name}
                    onChange={(e) => setFormData(prev => ({ ...prev, company_name: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    placeholder="Enter company name"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    <User size={16} className="inline mr-2" />
                    Position
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.position}
                    onChange={(e) => setFormData(prev => ({ ...prev, position: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    placeholder="Enter position title"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    <Calendar size={16} className="inline mr-2" />
                    Application Date
                  </label>
                  <input
                    type="date"
                    required
                    value={formData.application_date}
                    onChange={(e) => setFormData(prev => ({ ...prev, application_date: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Status
                  </label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData(prev => ({ ...prev, status: e.target.value as keyof typeof ApplicationStatus }))}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                  >
                    {Object.values(ApplicationStatus).map(status => (
                      <option key={status} value={status}>
                        {status.charAt(0).toUpperCase() + status.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  <FileText size={16} className="inline mr-2" />
                  Job Description
                </label>
                <textarea
                  value={formData.job_description}
                  onChange={(e) => setFormData(prev => ({ ...prev, job_description: e.target.value }))}
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                  placeholder="Paste or type the job description here..."
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Resume
                  </label>
                  <div className="space-y-2">
                    <input
                      type="url"
                      value={formData.resume_url}
                      onChange={(e) => setFormData(prev => ({ ...prev, resume_url: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                      placeholder="Resume URL"
                    />
                    <div className="flex items-center gap-2">
                      <input
                        type="file"
                        accept=".pdf,.doc,.docx"
                        onChange={handleFileInputChange('resume_url')}
                        className="hidden"
                        id="resume-upload"
                        disabled={uploading.resume}
                      />
                      <label
                        htmlFor="resume-upload"
                        className={`px-3 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center gap-1 cursor-pointer ${
                          uploading.resume ? 'opacity-50 cursor-not-allowed' : ''
                        }`}
                      >
                        <Upload size={16} />
                        {uploading.resume ? 'Uploading...' : 'Upload File'}
                      </label>
                      <span className="text-xs text-gray-500">PDF, DOC, DOCX (max 10MB)</span>
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Cover Letter
                  </label>
                  <div className="space-y-2">
                    <input
                      type="url"
                      value={formData.cover_letter_url}
                      onChange={(e) => setFormData(prev => ({ ...prev, cover_letter_url: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                      placeholder="Cover letter URL"
                    />
                    <div className="flex items-center gap-2">
                      <input
                        type="file"
                        accept=".pdf,.doc,.docx"
                        onChange={handleFileInputChange('cover_letter_url')}
                        className="hidden"
                        id="cover-letter-upload"
                        disabled={uploading.cover_letter}
                      />
                      <label
                        htmlFor="cover-letter-upload"
                        className={`px-3 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center gap-1 cursor-pointer ${
                          uploading.cover_letter ? 'opacity-50 cursor-not-allowed' : ''
                        }`}
                      >
                        <Upload size={16} />
                        {uploading.cover_letter ? 'Uploading...' : 'Upload File'}
                      </label>
                      <span className="text-xs text-gray-500">PDF, DOC, DOCX (max 10MB)</span>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Notes
                </label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                  placeholder="Add any notes about this application..."
                />
              </div>

              <div className="flex gap-4 pt-4">
                <button
                  type="submit"
                  disabled={uploading.resume || uploading.cover_letter}
                  className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white py-2 px-4 rounded-lg font-medium transition-all disabled:opacity-50"                >
                  Add Application
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 py-2 px-4 rounded-lg font-medium hover:bg-gray-200 dark:hover:bg-gray-600 transition-all"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          {/* Automation Setup */}
          {currentStep === 'automation' && backendAvailable && (
            <div className="space-y-6">
              <div className="text-center">
                <Bot size={48} className="mx-auto text-purple-600 mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  Automated Job Application System
                </h3>
                <p className="text-gray-600 dark:text-gray-400 mb-6">
                  Upload your resume to analyze your profile and automatically search for relevant jobs
                </p>
              </div>

              {!resumeAnalysis ? (
                <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-8 text-center">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleResumeAnalysis(file);
                    }}
                    className="hidden"
                    id="resume-analysis-upload"
                    disabled={isAnalyzing}
                  />
                  <label
                    htmlFor="resume-analysis-upload"
                    className={`cursor-pointer flex flex-col items-center ${isAnalyzing ? 'opacity-50' : ''}`}
                  >
                    {isAnalyzing ? (
                      <Loader className="animate-spin h-12 w-12 text-purple-600 mb-4" />
                    ) : (
                      <Upload className="h-12 w-12 text-purple-600 mb-4" />
                    )}
                    <span className="text-lg font-medium text-gray-900 dark:text-white">
                      {isAnalyzing ? 'Analyzing Resume...' : 'Upload Resume for Analysis'}
                    </span>
                    <span className="text-sm text-gray-500 mt-2">
                      PDF format only. Your resume will be analyzed to determine job profile and experience level.
                    </span>
                  </label>
                </div>
              ) : (
                <div className="bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <CheckCircle className="text-green-600 dark:text-green-400" size={24} />
                    <h4 className="text-lg font-semibold text-green-800 dark:text-green-200">
                      Resume Analysis Complete
                    </h4>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                    <div>
                      <span className="text-sm font-medium text-green-700 dark:text-green-300">Job Profile:</span>
                      <p className="text-green-800 dark:text-green-200 font-semibold">
                        {resumeAnalysis.job_profile}
                      </p>
                    </div>
                    <div>
                      <span className="text-sm font-medium text-green-700 dark:text-green-300">Experience Level:</span>
                      <p className="text-green-800 dark:text-green-200 font-semibold">
                        {resumeAnalysis.experience}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={handleJobSearch}
                    disabled={isSearching}
                    className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white py-3 px-6 rounded-lg font-medium transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {isSearching ? (
                      <>
                        <Loader className="animate-spin" size={20} />
                        Searching for Jobs...
                      </>
                    ) : (
                      <>
                        <Search size={20} />
                        Start Automated Job Search
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Job Listings */}
          {currentStep === 'jobs' && jobListings && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Found {jobListings.jobs.length} Job Opportunities
                </h3>
                <div className="flex gap-2">
                  <button
                    onClick={() => setSelectedJobs(new Set(jobListings.jobs.map(job => job.job_url)))}
                    className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    Select All
                  </button>
                  <button
                    onClick={() => setSelectedJobs(new Set())}
                    className="text-sm text-gray-600 dark:text-gray-400 hover:underline"
                  >
                    Clear All
                  </button>
                </div>
              </div>

              <div className="grid gap-4 max-h-96 overflow-y-auto">
                {jobListings.jobs.map((job, index) => (
                  <div
                    key={index}
                    className={`border rounded-lg p-4 cursor-pointer transition-all ${
                      selectedJobs.has(job.job_url)
                        ? 'border-purple-300 bg-purple-50 dark:border-purple-600 dark:bg-purple-900/30'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                    }`}
                    onClick={() => toggleJobSelection(job.job_url)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <input
                            type="checkbox"
                            checked={selectedJobs.has(job.job_url)}
                            onChange={() => toggleJobSelection(job.job_url)}
                            className="text-purple-600 rounded"
                          />
                          <h4 className="font-semibold text-gray-900 dark:text-white">
                            {job.title}
                          </h4>
                        </div>
                        <p className="text-gray-700 dark:text-gray-300 font-medium mb-1">
                          {job.company}
                        </p>
                        <p className="text-gray-500 dark:text-gray-400 text-sm mb-2">
                          {job.location}
                        </p>
                        {job.description && (
                          <p className="text-gray-600 dark:text-gray-400 text-sm line-clamp-2">
                            {job.description}
                          </p>
                        )}
                      </div>
                      <a
                        href={job.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 ml-4"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <ExternalLink size={20} />
                      </a>
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex gap-4">
                <button
                  onClick={handleBulkApply}
                  disabled={selectedJobs.size === 0 || isApplying}
                  className="flex-1 bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 text-white py-3 px-6 rounded-lg font-medium transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isApplying ? (
                    <>
                      <Loader className="animate-spin" size={20} />
                      Applying...
                    </>
                  ) : (
                    <>
                      <Bot size={20} />
                      Apply to Selected Jobs ({selectedJobs.size})
                    </>
                  )}
                </button>
                <button
                  onClick={onClose}
                  className="px-6 py-3 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg font-medium hover:bg-gray-200 dark:hover:bg-gray-600 transition-all"
                >
                  Close
                </button>
              </div>
            </div>
          )}

          {/* Application Progress */}
          {currentStep === 'applying' && (
            <div className="space-y-6 text-center">
              <div>
                <Loader className="animate-spin h-16 w-16 text-purple-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  Applying to Jobs
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  Please wait while we automatically apply to your selected positions...
                </p>
              </div>
              
              {message && (
                <div className="bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 p-4 rounded-lg">
                  {message}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AutomatedApplicationModal;
