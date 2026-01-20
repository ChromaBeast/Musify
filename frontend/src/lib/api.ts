const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface DownloadResponse {
  job_id: string;
  message: string;
}

export interface JobStatus {
  job_id: string;
  status: 'pending' | 'downloading' | 'completed' | 'error';
  progress: { song: string; status: string; message: string }[];
  song_count: number;
  download_url: string | null;
  error: string | null;
}

export async function startDownload(url: string): Promise<DownloadResponse> {
  const response = await fetch(`${API_URL}/api/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to start download');
  }

  return response.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${API_URL}/api/status/${jobId}`);

  if (!response.ok) {
    throw new Error('Failed to get job status');
  }

  return response.json();
}

export function getDownloadUrl(jobId: string): string {
  return `${API_URL}/api/download/${jobId}/zip`;
}
