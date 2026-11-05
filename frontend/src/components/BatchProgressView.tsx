'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  RefreshCw,
  XCircle,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  BookOpen,
  Filter,
  Sparkles,
  Layers,
  ArrowRight,
  Download,
} from 'lucide-react';
import {
  BatchSearchStatusResponse,
  BookCandidate,
} from '@/types/book';
import {
  getBatchStatus,
  cancelBatch,
  retryBatch,
} from '@/lib/api';

interface BatchProgressViewProps {
  batchId: string;
  onOpenReader: (candidate: BookCandidate) => void;
  onOpenDetails: (candidate: BookCandidate) => void;
  onOpenAlternative: (candidate: BookCandidate) => void;
}

type AccessFilter =
  | 'ALL'
  | 'FREE_FULL_TEXT'
  | 'DOWNLOADABLE'
  | 'PREVIEW'
  | 'BORROW'
  | 'NOT_ELIGIBLE'
  | 'IN_PROGRESS'
  | 'FAILED';

export const BatchProgressView: React.FC<BatchProgressViewProps> = ({
  batchId,
  onOpenReader,
  onOpenDetails,
  onOpenAlternative,
}) => {
  const [batchData, setBatchData] = useState<BatchSearchStatusResponse | null>(null);
  const [filter, setFilter] = useState<AccessFilter>('ALL');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const batchStatusRef = useRef(batchData?.status);
  useEffect(() => {
    batchStatusRef.current = batchData?.status;
  }, [batchData?.status]);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await getBatchStatus(batchId, filter);
      setBatchData(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch batch progress.');
    }
  }, [batchId, filter]);

  // Polling loop while batch is running or pending
  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const data = await getBatchStatus(batchId, filter);
        if (active) setBatchData(data);
      } catch (err: unknown) {
        if (active) setError(err instanceof Error ? err.message : 'Failed to fetch batch progress.');
      }
    };

    poll();
    const interval = setInterval(() => {
      if (
        batchStatusRef.current === 'RUNNING' ||
        batchStatusRef.current === 'PENDING' ||
        !batchStatusRef.current
      ) {
        poll();
      }
    }, 2000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [batchId, filter]);

  const handleCancel = async () => {
    try {
      await cancelBatch(batchId);
      await fetchStatus();
    } catch {}
  };

  const handleRetry = async () => {
    setIsLoading(true);
    try {
      await retryBatch(batchId);
      await fetchStatus();
    } catch {} finally {
      setIsLoading(false);
    }
  };

  const handleDownloadFile = async (candidate: BookCandidate, format: 'PDF' | 'EPUB') => {
    try {
      const endpoint = `/api/candidates/${encodeURIComponent(candidate.candidate_id)}/download-file?format=${format}`;
      const res = await fetch(endpoint);
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const cleanTitle = (candidate.title || 'book')
          .replace(/[^a-zA-Z0-9_\-\s]/g, '')
          .trim()
          .replace(/\s+/g, '_');
        a.download = `${cleanTitle || 'book'}.${format.toLowerCase()}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        const fallbackUrl = format === 'EPUB' ? candidate.epub_url : (candidate.pdf_url || candidate.download_url);
        if (fallbackUrl && candidate.licensing?.is_legally_downloadable) {
          window.open(fallbackUrl, '_blank', 'noopener,noreferrer');
        }
      }
    } catch {
      const fallbackUrl = format === 'EPUB' ? candidate.epub_url : (candidate.pdf_url || candidate.download_url);
      if (fallbackUrl && candidate.licensing?.is_legally_downloadable) {
        window.open(fallbackUrl, '_blank', 'noopener,noreferrer');
      }
    }
  };

  const books = batchData?.books || [];

  return (
    <div className="space-y-6 max-w-5xl mx-auto animate-fadeIn">
      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Batch Header & Progress Bar */}
      <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-extrabold text-slate-900 dark:text-slate-100">
                Parallel Multi-Book Acquisition Search
              </h2>
              <span
                className={`px-2.5 py-0.5 text-xs font-bold rounded-full ${
                  batchData?.status === 'COMPLETED'
                    ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                    : batchData?.status === 'RUNNING'
                    ? 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 animate-pulse'
                    : batchData?.status === 'CANCELLED'
                    ? 'bg-amber-50 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                }`}
              >
                {batchData?.status || 'INITIALIZING'}
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Batch ID: <span className="font-mono text-indigo-600 dark:text-indigo-400">{batchId}</span> • Bounded concurrent worker queue active
            </p>
          </div>

          <div className="flex items-center gap-2">
            {batchData?.status === 'RUNNING' && (
              <button
                onClick={handleCancel}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-rose-50 dark:bg-rose-950/50 hover:bg-rose-100 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800 transition-colors"
              >
                <XCircle className="w-3.5 h-3.5" />
                <span>Cancel Batch</span>
              </button>
            )}

            <button
              onClick={handleRetry}
              disabled={isLoading || batchData?.status === 'RUNNING'}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 disabled:opacity-50 transition-colors"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Retry Failed</span>
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-slate-700 dark:text-slate-300 font-semibold">
            <span>
              {batchData?.completed_books || 0} of {batchData?.total_books || 0} Books Evaluated
            </span>
            <span className="text-indigo-600 dark:text-indigo-400 font-mono font-bold">
              {batchData?.progress_percentage || 0}%
            </span>
          </div>
          <div className="w-full h-3 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-indigo-600 to-cyan-500 transition-all duration-500 rounded-full shadow-sm"
              style={{ width: `${batchData?.progress_percentage || 0}%` }}
            />
          </div>
        </div>

        {/* Minimum 3-Book Acquisition Target Banner */}
        {(() => {
          const acquiredCount = batchData?.acquired_books ?? books.filter((b) => b.is_downloaded).length;
          const target = 3;
          const isTargetMet = acquiredCount >= target;

          return (
            <div
              className={`p-4 rounded-2xl border transition-all ${
                isTargetMet
                  ? 'bg-emerald-50/80 dark:bg-emerald-950/30 border-emerald-300 dark:border-emerald-800'
                  : 'bg-indigo-50/60 dark:bg-indigo-950/30 border-indigo-200 dark:border-indigo-800'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${
                      isTargetMet ? 'bg-emerald-600 text-white' : 'bg-indigo-600 text-white'
                    }`}
                  >
                    {isTargetMet ? (
                      <CheckCircle2 className="w-5 h-5" />
                    ) : (
                      <Download className="w-5 h-5" />
                    )}
                  </div>
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                      <span>
                        {isTargetMet
                          ? '✓ Target 3-Book Reference Acquisition Complete'
                          : 'Reference Book Auto-Acquisition Engine'}
                      </span>
                      {isTargetMet && (
                        <span className="px-2 py-0.2 rounded-full text-[10px] bg-emerald-100 dark:bg-emerald-900 text-emerald-800 dark:text-emerald-200">
                          Goal Achieved
                        </span>
                      )}
                    </h4>
                    <p className="text-xs text-slate-600 dark:text-slate-400">
                      {acquiredCount} of {target} reference book PDFs automatically acquired, verified, and saved to local library
                      {acquiredCount > target ? ` (${acquiredCount} total acquired)` : ''}.
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 self-start sm:self-center">
                  {[1, 2, 3].map((step) => (
                    <span
                      key={step}
                      className={`px-2.5 py-1 text-[11px] font-bold rounded-lg border ${
                        acquiredCount >= step
                          ? 'bg-emerald-100 dark:bg-emerald-900/60 text-emerald-800 dark:text-emerald-200 border-emerald-300 dark:border-emerald-700'
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-400 border-slate-200 dark:border-slate-700'
                      }`}
                    >
                      PDF {step} {acquiredCount >= step ? '✓' : ''}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          );
        })()}

        {/* Filter Pills Bar */}
        <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
          <span className="text-slate-500 text-[11px] font-semibold flex items-center gap-1 mr-1">
            <Filter className="w-3 h-3" /> Filter:
          </span>
          {(
            [
              ['ALL', 'All Books'],
              ['FREE_FULL_TEXT', 'Free Full Text'],
              ['DOWNLOADABLE', 'Download Authorized'],
              ['PREVIEW', 'Preview Only'],
              ['BORROW', 'Borrow Required'],
              ['NOT_ELIGIBLE', 'Restricted In-Copyright'],
              ['IN_PROGRESS', 'Searching...'],
              ['FAILED', 'Failed / No Results'],
            ] as const
          ).map(([val, label]) => (
            <button
              key={val}
              onClick={() => setFilter(val)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors ${
                filter === val
                  ? 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 font-bold'
                  : 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 border border-slate-200 dark:border-slate-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Book Search Items List */}
      <div className="space-y-4">
        {books.length === 0 ? (
          <div className="p-12 text-center rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-500">
            <p className="text-sm font-semibold">No books match the selected filter in this batch.</p>
          </div>
        ) : (
          books.map((b) => {
            const cand = b.top_candidate;
            return (
              <div
                key={b.id}
                className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 shadow-sm transition-all space-y-4"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">{b.title}</h3>
                      {b.subject && (
                        <span className="px-2 py-0.5 text-[10px] font-medium rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                          {b.subject}
                        </span>
                      )}
                    </div>
                    {b.author && (
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Query Author: <strong className="text-slate-700 dark:text-slate-300">{b.author}</strong>
                        {b.isbn && (
                          <span className="ml-2 font-mono text-slate-500">ISBN: {b.isbn}</span>
                        )}
                      </p>
                    )}
                  </div>

                  {/* Status Badge */}
                  <div className="shrink-0 flex items-center gap-2">
                    {b.status === 'SEARCHING' && (
                      <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 animate-pulse">
                        <RefreshCw className="w-3 h-3 animate-spin" />
                        <span>Searching Providers...</span>
                      </span>
                    )}
                    {b.status === 'COMPLETED' && (
                      <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Match Found ({b.results_count})</span>
                      </span>
                    )}
                    {b.status === 'NO_RESULTS' && (
                      <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                        <AlertCircle className="w-3.5 h-3.5" />
                        <span>No Matches Found</span>
                      </span>
                    )}
                    {b.status === 'FAILED' && (
                      <span className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full bg-rose-50 dark:bg-rose-950/50 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
                        <AlertCircle className="w-3.5 h-3.5" />
                        <span>Search Failed</span>
                      </span>
                    )}
                  </div>
                </div>

                {/* Top Candidate Result Box */}
                {cand ? (
                  <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                    <div className="flex items-start gap-3">
                      {cand.thumbnail_url ? (
                        <img
                          src={cand.thumbnail_url}
                          alt={cand.title}
                          className="w-12 h-16 object-cover rounded-lg shadow-xs border border-slate-200 dark:border-slate-700 shrink-0"
                        />
                      ) : (
                        <div className="w-12 h-16 rounded-lg bg-slate-200 dark:bg-slate-800 flex items-center justify-center text-slate-500 shrink-0">
                          <BookOpen className="w-6 h-6" />
                        </div>
                      )}
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">{cand.title}</h4>
                          <span className="px-2 py-0.5 text-[10px] font-mono font-bold rounded bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                            Score: {cand.confidence?.total_score || 0}/100
                          </span>
                          <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                            {cand.source_name}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                          {cand.authors?.join(', ')} • {cand.publisher} • {cand.published_year || 'Unknown year'}
                        </p>

                        {/* Access Status classification */}
                        <div className="flex flex-wrap items-center gap-2 mt-2">
                          {b.is_downloaded ? (
                            <span className="px-2.5 py-0.5 text-[11px] font-bold rounded-full bg-emerald-100 dark:bg-emerald-950/70 text-emerald-800 dark:text-emerald-200 border border-emerald-300 dark:border-emerald-700 flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                              <span>✓ PDF Acquired &amp; Verified</span>
                              {b.download_size_bytes ? (
                                <span className="text-[10px] opacity-80">
                                  ({(b.download_size_bytes / (1024 * 1024)).toFixed(1)} MB)
                                </span>
                              ) : null}
                            </span>
                          ) : (
                            <span
                              className={`px-2.5 py-0.5 text-[11px] font-bold rounded-full ${
                                cand.licensing?.is_legally_downloadable
                                  ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                                  : cand.access_type === 'FULL_TEXT'
                                  ? 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800'
                                  : cand.access_type === 'PREVIEW'
                                  ? 'bg-amber-50 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800'
                                  : 'bg-rose-50 dark:bg-rose-950/50 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
                              }`}
                            >
                              {cand.licensing?.is_legally_downloadable
                                ? '✓ Verified Authorized Download'
                                : cand.access_type === 'FULL_TEXT'
                                ? '✓ Free Full-Text Reading'
                                : cand.access_type === 'PREVIEW'
                                ? 'Preview Only'
                                : 'Commercial / Restricted'}
                            </span>
                          )}
                          {cand.access_message && (
                            <span className="text-[11px] text-slate-500 truncate max-w-sm">
                              {cand.access_message}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex flex-wrap items-center gap-2 self-end md:self-center shrink-0">
                      {b.is_downloaded ? (
                        <button
                          onClick={() => handleDownloadFile(cand, 'PDF')}
                          className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs transition-colors"
                        >
                          <Download className="w-3.5 h-3.5" />
                          <span>Download File</span>
                        </button>
                      ) : cand.licensing?.is_legally_downloadable ? (
                        <button
                          onClick={() => handleDownloadFile(cand, 'PDF')}
                          className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs transition-colors"
                        >
                          <Download className="w-3.5 h-3.5" />
                          <span>Download PDF</span>
                        </button>
                      ) : null}

                      <button
                        onClick={() => onOpenReader(cand)}
                        className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs transition-colors"
                      >
                        <BookOpen className="w-3.5 h-3.5" />
                        <span>Read Online</span>
                      </button>

                      <button
                        onClick={() => onOpenDetails(cand)}
                        className="px-3 py-1.5 text-xs font-semibold rounded-xl bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 transition-colors"
                      >
                        Details
                      </button>

                      {!cand.licensing?.is_legally_downloadable && (
                        <button
                          onClick={() => onOpenAlternative(cand)}
                          className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-xl bg-purple-50 dark:bg-purple-950/50 hover:bg-purple-100 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 transition-colors"
                        >
                          <Sparkles className="w-3 h-3 text-purple-600 dark:text-purple-400" />
                          <span>Find Alternative</span>
                        </button>
                      )}
                    </div>
                  </div>
                ) : (
                  b.error_message && (
                    <p className="text-xs text-slate-500 italic">{b.error_message}</p>
                  )
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
