'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { startDownload, getJobStatus, getDownloadUrl, JobStatus } from '@/lib/api';

type AppState = 'idle' | 'loading' | 'downloading' | 'completed' | 'error';

export default function Home() {
  const [url, setUrl] = useState('');
  const [state, setState] = useState<AppState>('idle');
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isValidSpotifyUrl = (url: string) => {
    return /^https:\/\/open\.spotify\.com\/(playlist|album|track)\/[a-zA-Z0-9]+/.test(url);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValidSpotifyUrl(url)) {
      setError('Please enter a valid Spotify playlist, album, or track URL');
      return;
    }

    setError(null);
    setState('loading');

    try {
      const response = await startDownload(url);
      setJobId(response.job_id);
      setState('downloading');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start download');
      setState('error');
    }
  };

  const pollStatus = useCallback(async () => {
    if (!jobId) return;

    try {
      const jobStatus = await getJobStatus(jobId);
      setStatus(jobStatus);

      if (jobStatus.status === 'completed') {
        setState('completed');
      } else if (jobStatus.status === 'error') {
        setError(jobStatus.error || 'Download failed');
        setState('error');
      }
    } catch {
      setError('Failed to check status');
      setState('error');
    }
  }, [jobId]);

  useEffect(() => {
    if (state !== 'downloading' || !jobId) return;

    const interval = setInterval(pollStatus, 1000);
    return () => clearInterval(interval);
  }, [state, jobId, pollStatus]);

  const handleDownload = () => {
    if (jobId) {
      window.open(getDownloadUrl(jobId), '_blank');
    }
  };

  const handleReset = () => {
    setUrl('');
    setState('idle');
    setJobId(null);
    setStatus(null);
    setError(null);
  };

  return (
    <main className="gradient-bg min-h-screen flex flex-col items-center justify-center p-8">
      {/* Logo and Title */}
      <div className="text-center mb-12 animate-slide-up">
        <div className="inline-flex items-center gap-3 mb-4">
          <MusicIcon className="w-12 h-12 text-primary" />
          <h1 className="text-5xl font-bold bg-gradient-to-r from-primary to-green-300 bg-clip-text text-transparent">
            Musify
          </h1>
        </div>
        <p className="text-muted-foreground text-lg">
          Convert Spotify playlists to downloadable MP3s
        </p>
      </div>

      {/* Main Card */}
      <Card className="glass-card w-full max-w-xl animate-slide-up" style={{ animationDelay: '0.1s' }}>
        <CardContent className="p-8">
          {state === 'idle' || state === 'loading' || state === 'error' ? (
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground">
                  Spotify URL
                </label>
                <Input
                  type="url"
                  placeholder="https://open.spotify.com/playlist/..."
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="h-14 text-lg bg-secondary/50 border-border focus:border-primary focus:ring-primary"
                  disabled={state === 'loading'}
                />
                {error && (
                  <p className="text-destructive text-sm mt-2">{error}</p>
                )}
              </div>

              <Button
                type="submit"
                className="w-full h-14 text-lg font-semibold bg-primary hover:bg-primary/90 text-primary-foreground transition-all hover:scale-[1.02] active:scale-[0.98]"
                disabled={state === 'loading' || !url}
              >
                {state === 'loading' ? (
                  <span className="flex items-center gap-2">
                    <LoadingSpinner />
                    Starting download...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <DownloadIcon className="w-5 h-5" />
                    Download Playlist
                  </span>
                )}
              </Button>
            </form>
          ) : state === 'downloading' ? (
            <div className="space-y-6">
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/20 mb-4 animate-pulse-glow">
                  <LoadingSpinner className="w-8 h-8 text-primary" />
                </div>
                <h3 className="text-xl font-semibold mb-2">Downloading...</h3>
                <p className="text-muted-foreground">
                  {status?.song_count || 0} songs processed
                </p>
              </div>

              <Progress value={status ? (status.progress.length / Math.max(status.song_count, 1)) * 100 : 0} className="h-2" />

              {status && status.progress.length > 0 && (
                <div className="max-h-48 overflow-y-auto space-y-2">
                  {status.progress.slice(-5).map((item, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm text-muted-foreground">
                      {item.status === 'completed' ? (
                        <CheckIcon className="w-4 h-4 text-primary" />
                      ) : (
                        <LoadingSpinner className="w-4 h-4" />
                      )}
                      <span className="truncate">{item.song}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : state === 'completed' ? (
            <div className="text-center space-y-6">
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-primary/20 mb-2">
                <CheckIcon className="w-10 h-10 text-primary" />
              </div>
              <div>
                <h3 className="text-2xl font-semibold mb-2">Download Ready!</h3>
                <p className="text-muted-foreground">
                  {status?.song_count || 0} songs packaged into ZIP
                </p>
              </div>

              <div className="flex flex-col gap-3">
                <Button
                  onClick={handleDownload}
                  className="w-full h-14 text-lg font-semibold bg-primary hover:bg-primary/90 text-primary-foreground transition-all hover:scale-[1.02] active:scale-[0.98]"
                >
                  <DownloadIcon className="w-5 h-5 mr-2" />
                  Download ZIP
                </Button>
                <Button
                  onClick={handleReset}
                  variant="secondary"
                  className="w-full h-12"
                >
                  Download Another
                </Button>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* Footer */}
      <p className="mt-8 text-sm text-muted-foreground/60 animate-slide-up" style={{ animationDelay: '0.2s' }}>
        For personal use only • Powered by spotdl
      </p>
    </main>
  );
}

// Icons
function MusicIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z" />
    </svg>
  );
}

function DownloadIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function LoadingSpinner({ className }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  );
}
