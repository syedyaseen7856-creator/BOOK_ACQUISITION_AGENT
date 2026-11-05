'use client';

import React, { useState } from 'react';
import {
  X,
  BookOpen,
  ExternalLink,
  Maximize2,
  Minimize2,
  ShieldCheck,
} from 'lucide-react';
import { BookCandidate } from '@/types/book';

interface ReaderModalProps {
  candidate: BookCandidate | null;
  isOpen: boolean;
  onClose: () => void;
}

export const ReaderModal: React.FC<ReaderModalProps> = ({
  candidate,
  isOpen,
  onClose,
}) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [iframeError, setIframeError] = useState(false);

  if (!isOpen || !candidate) return null;

  const activeReaderUrl =
    candidate.reader_url ||
    candidate.preview_url ||
    candidate.source_url;

  const readerLabel = candidate.reader_url
    ? 'Verified Full-Text Digital Reader'
    : candidate.preview_url
    ? 'Authorized Book Preview'
    : 'Official Repository / Publisher Access';

  const canEmbedIframe =
    candidate.can_embed ||
    (candidate.reader_url && candidate.reader_url.includes('gutenberg.org/ebooks/'));

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/60 backdrop-blur-md flex items-center justify-center p-2 sm:p-4 animate-fadeIn">
      <div
        className={`relative w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl shadow-2xl flex flex-col transition-all duration-200 overflow-hidden ${
          isFullscreen
            ? 'h-[98vh] max-w-[98vw]'
            : 'h-[88vh] max-w-5xl'
        }`}
      >
        {/* Reader Top Bar */}
        <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-2 rounded-xl bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800 shrink-0">
              <BookOpen className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                  {readerLabel}
                </span>
                <span className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
                  {candidate.source_name}
                </span>
              </div>
              <h2 className="text-sm sm:text-base font-bold text-slate-900 dark:text-slate-100 truncate">
                {candidate.title}
              </h2>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {/* Launch in new tab */}
            {activeReaderUrl && (
              <a
                href={activeReaderUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-slate-100 border border-slate-200 dark:border-slate-700 transition-colors"
                title="Open reader in new tab"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Open in New Tab</span>
              </a>
            )}

            {/* Toggle Fullscreen */}
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-2 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors"
              title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
              aria-label="Toggle Fullscreen"
            >
              {isFullscreen ? (
                <Minimize2 className="w-4 h-4" />
              ) : (
                <Maximize2 className="w-4 h-4" />
              )}
            </button>

            {/* Close */}
            <button
              onClick={onClose}
              className="p-2 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors"
              aria-label="Close reader"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Reader Notification Bar */}
        <div className="px-5 py-2 bg-slate-100/60 dark:bg-slate-800/30 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs text-slate-600 dark:text-slate-400">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>
              <strong>Zero-Download Guarantee:</strong> Viewing or streaming reader pages does
              not download or acquire file copies to disk.
            </span>
          </div>
          {candidate.access_message && (
            <span className="hidden md:inline text-slate-500 font-mono text-[11px]">
              {candidate.access_message}
            </span>
          )}
        </div>

        {/* Reader Frame / View */}
        <div className="flex-1 bg-slate-50 dark:bg-slate-950 relative overflow-hidden flex flex-col">
          {canEmbedIframe && !iframeError && activeReaderUrl ? (
            <iframe
              src={activeReaderUrl}
              title={`Digital Reader — ${candidate.title}`}
              className="w-full h-full border-0 bg-white"
              sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
              onError={() => setIframeError(true)}
            />
          ) : (
            /* External Reader or Blocked Embed View */
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center max-w-xl mx-auto space-y-5">
              <div className="w-16 h-16 rounded-2xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shadow-md">
                <BookOpen className="w-8 h-8" />
              </div>

              <div className="space-y-2">
                <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                  Authorized Online Reading Access
                </h3>
                <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
                  {candidate.source_name} hosts the verified full text or preview on its official
                  platform. To protect copyright headers and security policies, launch the
                  legitimate reader in a new browser tab.
                </p>
              </div>

              {/* Resolved URLs table */}
              <div className="w-full text-left text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 space-y-2 font-mono shadow-xs">
                <div className="flex justify-between items-center pb-2 border-b border-slate-200 dark:border-slate-800">
                  <span className="text-slate-500 font-sans">Access Tier:</span>
                  <span className="text-indigo-600 dark:text-indigo-400 font-sans font-semibold">
                    {candidate.access_type}
                  </span>
                </div>
                {candidate.reader_url && (
                  <div className="truncate">
                    <span className="text-slate-500 font-sans block text-[11px]">
                      Verified Reader:
                    </span>
                    <span className="text-slate-700 dark:text-slate-300 text-[11px] truncate block">
                      {candidate.reader_url}
                    </span>
                  </div>
                )}
                {candidate.preview_url && (
                  <div className="truncate">
                    <span className="text-slate-500 font-sans block text-[11px]">
                      Preview Link:
                    </span>
                    <span className="text-slate-700 dark:text-slate-300 text-[11px] truncate block">
                      {candidate.preview_url}
                    </span>
                  </div>
                )}
                <div className="truncate">
                  <span className="text-slate-500 font-sans block text-[11px]">
                    Bibliographic Provenance:
                  </span>
                  <span className="text-slate-700 dark:text-slate-300 text-[11px] truncate block">
                    {candidate.source_url}
                  </span>
                </div>
              </div>

              <div className="pt-2 flex flex-col sm:flex-row gap-3">
                <a
                  href={activeReaderUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm tracking-wide shadow-md shadow-indigo-600/20 flex items-center justify-center gap-2 transition-all active:scale-95"
                >
                  <BookOpen className="w-4 h-4" />
                  <span>Launch Official Reader</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
                <button
                  type="button"
                  onClick={onClose}
                  className="px-5 py-3 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-sm font-semibold transition-colors"
                >
                  Return to Discovery
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
