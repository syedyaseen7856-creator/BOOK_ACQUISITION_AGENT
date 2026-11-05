'use client';

import React, { useState } from 'react';
import {
  X,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Download,
  CheckCircle2,
  Lock,
  Loader2,
} from 'lucide-react';
import { BookCandidate, ApprovalRecord, DownloadJob } from '@/types/book';
import { approveCandidate, triggerDownload, getJob } from '@/lib/api';

interface ApprovalModalProps {
  candidate: BookCandidate | null;
  isOpen: boolean;
  onClose: () => void;
  onApprovalComplete: () => void;
}

export const ApprovalModal: React.FC<ApprovalModalProps> = ({
  candidate,
  isOpen,
  onClose,
  onApprovalComplete,
}) => {
  const [affirmed, setAffirmed] = useState(false);
  const [userNote, setUserNote] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [approvalRecord, setApprovalRecord] = useState<ApprovalRecord | null>(null);
  const [downloadJob, setDownloadJob] = useState<DownloadJob | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);

  if (!isOpen || !candidate) return null;

  const isDownloadPermitted = candidate.licensing?.is_legally_downloadable;
  const licensing = candidate.licensing;

  const handleApproveAndDownload = async () => {
    if (!affirmed) {
      setErrorMsg('You must provide explicit affirmation before proceeding.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      // Step 1: Submit formal server-side approval request
      const approval = await approveCandidate(
        candidate.candidate_id,
        true,
        userNote.trim() || undefined
      );
      setApprovalRecord(approval);
      setJobStatus('Approval verified by server. Initiating download pipeline...');

      // Step 2: Trigger safe downloader
      const job = await triggerDownload(candidate.candidate_id, approval.approval_id, false);
      setDownloadJob(job);
      setJobStatus(`Job status: ${job.status}`);

      // Step 3: Poll job status until COMPLETED or FAILED
      let currentJob = job;
      let attempts = 0;
      while (
        attempts < 30 &&
        (currentJob.status === 'PENDING' ||
          currentJob.status === 'DOWNLOADING' ||
          currentJob.status === 'VALIDATING')
      ) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        attempts++;
        try {
          currentJob = await getJob(currentJob.job_id);
          setDownloadJob(currentJob);
          setJobStatus(`Job status: ${currentJob.status}`);
        } catch {
          break;
        }
      }

      onApprovalComplete();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Approval/download failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetState = () => {
    setAffirmed(false);
    setUserNote('');
    setIsSubmitting(false);
    setErrorMsg(null);
    setApprovalRecord(null);
    setDownloadJob(null);
    setJobStatus(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6 animate-fadeIn">
      <div className="relative w-full max-w-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`p-2 rounded-xl border ${
                isDownloadPermitted
                  ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800'
                  : 'bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 border-rose-200 dark:border-rose-800'
              }`}
            >
              {isDownloadPermitted ? (
                <ShieldCheck className="w-5 h-5" />
              ) : (
                <Lock className="w-5 h-5" />
              )}
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Acquisition Approval &amp; Licensing Gate
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Independent Legal Verification for Repository Acquisition
              </p>
            </div>
          </div>
          <button
            onClick={resetState}
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4 text-xs text-slate-600 dark:text-slate-300">
          {/* Target Book Info */}
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-2">
            <div className="flex justify-between items-start gap-3">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 block">
                  Target Work &amp; Edition
                </span>
                <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-slate-100">
                  {candidate.title}
                </h3>
                <p className="text-slate-600 dark:text-slate-300">
                  {candidate.authors?.join(', ') || 'Unknown Author'}
                </p>
              </div>
              <span className="px-2 py-0.5 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-[11px] font-semibold text-slate-700 dark:text-slate-300 shrink-0">
                {candidate.published_year || 'Year N/A'}
              </span>
            </div>

            <div className="pt-2 border-t border-slate-200 dark:border-slate-700 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-500 dark:text-slate-400">
              <span>Source: <strong className="text-slate-700 dark:text-slate-200">{candidate.source_name}</strong></span>
              {candidate.edition && <span>Edition: <strong className="text-slate-700 dark:text-slate-200">{candidate.edition}</strong></span>}
              {candidate.isbns?.[0] && <span>ISBN: <strong className="text-slate-700 dark:text-slate-200">{candidate.isbns[0]}</strong></span>}
            </div>
          </div>

          {/* Legal Licensing Determination */}
          <div
            className={`p-4 rounded-2xl border space-y-2.5 ${
              isDownloadPermitted
                ? 'bg-emerald-50/60 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800'
                : 'bg-rose-50/60 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5 text-xs">
                {isDownloadPermitted ? (
                  <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                ) : (
                  <ShieldAlert className="w-4 h-4 text-rose-600 dark:text-rose-400" />
                )}
                Eligibility Status: {licensing?.status}
              </span>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                  isDownloadPermitted
                    ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-700'
                    : 'bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border-rose-300 dark:border-rose-800'
                }`}
              >
                {isDownloadPermitted ? 'Authorized for Acquisition' : 'Acquisition Blocked'}
              </span>
            </div>

            <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
              {isDownloadPermitted
                ? 'This work has been verified under an authorized open access or public domain license. Downloading is legally permitted subject to the recorded repository terms.'
                : 'This work is protected by commercial copyright or lacks an explicit open-distribution license. In accordance with institutional policy, file downloading is strictly disabled. You may continue to view authorized online previews or official publisher records.'}
            </p>

            <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400 bg-white dark:bg-slate-950/60 p-2 rounded-xl border border-slate-200 dark:border-slate-800">
              Rights: {licensing?.rights_statement}
            </div>
          </div>

          {/* Error Banner */}
          {errorMsg && (
            <div className="p-3 rounded-2xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Download Completed View */}
          {downloadJob && downloadJob.status === 'COMPLETED' ? (
            <div className="p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 space-y-3">
              <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400 font-bold text-sm">
                <CheckCircle2 className="w-5 h-5" />
                <span>Acquisition Completed &amp; Verified</span>
              </div>
              <div className="space-y-1 text-slate-700 dark:text-slate-300 font-mono text-[11px]">
                <p>
                  <strong className="text-slate-500">Approval ID:</strong>{' '}
                  {approvalRecord?.approval_id}
                </p>
                <p className="truncate">
                  <strong className="text-slate-500">SHA-256 Hash:</strong>{' '}
                  {downloadJob.sha256_hash}
                </p>
                <p>
                  <strong className="text-slate-500">File Size:</strong>{' '}
                  {downloadJob.file_size_bytes
                    ? `${(downloadJob.file_size_bytes / (1024 * 1024)).toFixed(2)} MB`
                    : 'Verified'}
                </p>
                <p className="text-emerald-700 dark:text-emerald-300">
                  <strong className="text-slate-500">Audit Status:</strong> Persisted to local SQLite audit ledger.
                </p>
              </div>
            </div>
          ) : isDownloadPermitted ? (
            /* Affirmation Form */
            <div className="space-y-4 pt-1">
              <label className="flex items-start gap-3 p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 cursor-pointer hover:border-slate-300 dark:hover:border-slate-600 transition-colors">
                <input
                  type="checkbox"
                  checked={affirmed}
                  onChange={(e) => setAffirmed(e.target.checked)}
                  disabled={isSubmitting}
                  className="mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="text-slate-700 dark:text-slate-300 leading-relaxed text-xs">
                  I explicitly affirm that this acquisition is for authorized educational, syllabus, or
                  reference use, and conforms to the repository terms of{' '}
                  <strong className="text-slate-900 dark:text-slate-100">{candidate.source_name}</strong>.
                </span>
              </label>

              <div>
                <label className="block text-slate-600 dark:text-slate-400 font-semibold mb-1 text-xs">
                  Optional Acquisition Justification / Reference Note:
                </label>
                <input
                  type="text"
                  value={userNote}
                  onChange={(e) => setUserNote(e.target.value)}
                  disabled={isSubmitting}
                  placeholder="e.g. Course syllabus reference verification"
                  className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-indigo-500 text-xs"
                />
              </div>

              {jobStatus && (
                <div className="flex items-center gap-2 p-2.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 text-xs">
                  <Loader2 className="w-4 h-4 animate-spin shrink-0" />
                  <span>{jobStatus}</span>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={resetState}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
          >
            {downloadJob && downloadJob.status === 'COMPLETED' ? 'Done' : 'Cancel'}
          </button>

          {isDownloadPermitted && (!downloadJob || downloadJob.status !== 'COMPLETED') && (
            <button
              type="button"
              onClick={handleApproveAndDownload}
              disabled={!affirmed || isSubmitting}
              className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs tracking-wide shadow-sm shadow-emerald-600/25 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-all active:scale-95"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Processing Verification...</span>
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  <span>Authorize &amp; Acquire</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
