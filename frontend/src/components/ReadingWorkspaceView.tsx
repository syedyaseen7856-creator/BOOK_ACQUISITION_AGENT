'use client';

import React, { useState } from 'react';
import {
  BookOpen,
  Download,
  ExternalLink,
  ShieldAlert,
  ChevronLeft,
  ChevronRight,
  ArrowLeft,
  Sparkles,
  Info,
  Maximize2,
  Copy,
  Check,
  FileCode,
  ShieldCheck,
  Lock,
} from 'lucide-react';
import { BookCandidate } from '@/types/book';

interface ReadingWorkspaceViewProps {
  candidate: BookCandidate | null;
  candidatesList?: BookCandidate[];
  onBackToSyllabus: () => void;
  onOpenDownloadApproval: (candidate: BookCandidate) => void;
  onFindAlternative: (candidate: BookCandidate) => void;
}

export const ReadingWorkspaceView: React.FC<ReadingWorkspaceViewProps> = ({
  candidate,
  candidatesList = [],
  onBackToSyllabus,
  onOpenDownloadApproval,
  onFindAlternative,
}) => {
  const [copiedFormat, setCopiedFormat] = useState<string | null>(null);
  const [currentIndex, setCurrentIndex] = useState<number>(() => {
    if (!candidate || candidatesList.length === 0) return 0;
    const idx = candidatesList.findIndex((c) => c.candidate_id === candidate.candidate_id);
    return idx >= 0 ? idx : 0;
  });

  const activeCand = candidatesList.length > 0 ? candidatesList[currentIndex] : candidate;

  if (!activeCand) {
    return (
      <div className="max-w-4xl mx-auto p-12 text-center rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm text-slate-500 space-y-4 animate-fadeIn">
        <div className="w-14 h-14 rounded-2xl bg-indigo-50 dark:bg-indigo-950/50 flex items-center justify-center text-indigo-600 dark:text-indigo-400 mx-auto">
          <BookOpen className="w-8 h-8" />
        </div>
        <div className="space-y-1">
          <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
            No Book Currently Selected in Reading Workspace
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
            Select a book candidate from Book Discovery or Syllabus Finder to inspect its reader, legal
            metadata, citations, and authorized access channels.
          </p>
        </div>
        <div className="pt-2">
          <button
            onClick={onBackToSyllabus}
            className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm shadow-indigo-600/20 transition-all active:scale-95"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Go to Book Discovery</span>
          </button>
        </div>
      </div>
    );
  }

  const handlePrev = () => {
    if (currentIndex > 0) setCurrentIndex(currentIndex - 1);
  };

  const handleNext = () => {
    if (currentIndex < candidatesList.length - 1) setCurrentIndex(currentIndex + 1);
  };

  const isEligible = activeCand.licensing.is_legally_downloadable;
  const isPublicDomainOrOA =
    activeCand.licensing.status === 'VERIFIED_FOR_PERMITTED_DOWNLOAD';

  const readerUrl = activeCand.reader_url || activeCand.preview_url || activeCand.source_url;

  // Citation exports
  const generateBibTeX = () => {
    const author = activeCand.authors?.[0]?.split(' ').pop()?.toLowerCase() || 'book';
    const year = activeCand.published_year || 'nodate';
    const cleanTitle = activeCand.title.replace(/[^a-zA-Z0-9 ]/g, '');
    const key = `${author}${year}`;
    return `@book{${key},
  title = {${activeCand.title}},
  author = {${activeCand.authors?.join(' and ') || 'Unknown'}},
  year = {${activeCand.published_year || ''}},
  publisher = {${activeCand.publisher || ''}},
  isbn = {${activeCand.isbns?.[0] || ''}},
  url = {${activeCand.source_url}}
}`;
  };

  const generateAPA = () => {
    const authors = activeCand.authors?.join(', ') || 'Unknown Author';
    const year = activeCand.published_year ? ` (${activeCand.published_year})` : '';
    const publisher = activeCand.publisher ? `. ${activeCand.publisher}` : '';
    return `${authors}${year}. ${activeCand.title}${publisher}. ${activeCand.source_url}`;
  };

  const copyToClipboard = (text: string, formatName: string) => {
    navigator.clipboard.writeText(text);
    setCopiedFormat(formatName);
    setTimeout(() => setCopiedFormat(null), 2500);
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto animate-fadeIn">
      {/* Top Navigation & Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
        <button
          onClick={onBackToSyllabus}
          className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-xl text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Candidate List</span>
        </button>

        {candidatesList.length > 1 && (
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrev}
              disabled={currentIndex === 0}
              className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 disabled:opacity-40 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
              title="Previous Book"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs text-slate-500 font-mono">
              Book {currentIndex + 1} of {candidatesList.length}
            </span>
            <button
              onClick={handleNext}
              disabled={currentIndex === candidatesList.length - 1}
              className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 disabled:opacity-40 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
              title="Next Book"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {readerUrl && (
            <a
              href={readerUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-indigo-700 dark:text-indigo-300 border border-slate-200 dark:border-slate-700 transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>Repository Source</span>
            </a>
          )}

          {isEligible ? (
            <button
              onClick={() => onOpenDownloadApproval(activeCand)}
              className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-bold rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm shadow-emerald-600/20 transition-all active:scale-95"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Review &amp; Approve Download</span>
            </button>
          ) : (
            <button
              onClick={() => onFindAlternative(activeCand)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-xl bg-purple-50 dark:bg-purple-950/50 hover:bg-purple-100 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" />
              <span>Find Open Alternative</span>
            </button>
          )}
        </div>
      </div>

      {/* Book Metadata Card */}
      <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col md:flex-row items-start gap-6">
        {activeCand.thumbnail_url ? (
          <img
            src={activeCand.thumbnail_url}
            alt={activeCand.title}
            className="w-24 sm:w-28 h-36 sm:h-40 object-cover rounded-2xl shadow-md border border-slate-200 dark:border-slate-800 shrink-0"
          />
        ) : (
          <div className="w-24 sm:w-28 h-36 sm:h-40 rounded-2xl bg-gradient-to-br from-indigo-950 to-slate-900 flex items-center justify-center text-white shrink-0 shadow-md">
            <BookOpen className="w-10 h-10 text-indigo-400" />
          </div>
        )}

        <div className="flex-1 space-y-3 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 dark:text-slate-100">
              {activeCand.title}
            </h1>
            <span
              className={`px-2.5 py-0.5 text-xs font-bold rounded-full ${
                isPublicDomainOrOA
                  ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                  : activeCand.access_type === 'PREVIEW'
                  ? 'bg-amber-50 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800'
                  : 'bg-rose-50 dark:bg-rose-950/50 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
              }`}
            >
              {isPublicDomainOrOA
                ? '✓ Verified Permitted Download'
                : activeCand.access_type === 'PREVIEW'
                ? 'Preview Only'
                : 'Commercial Copyright'}
            </span>
            <span className="px-2 py-0.5 text-xs font-semibold rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
              {activeCand.source_name}
            </span>
          </div>

          <p className="text-sm text-slate-700 dark:text-slate-300">
            By <strong className="text-slate-900 dark:text-slate-100">{activeCand.authors?.join(', ') || 'Unknown Author'}</strong>
            {activeCand.publisher && <span> • {activeCand.publisher}</span>}
            {activeCand.published_year && <span> ({activeCand.published_year})</span>}
            {activeCand.edition && <span> • {activeCand.edition}</span>}
          </p>

          <p className="text-xs text-slate-600 dark:text-slate-400 max-w-3xl leading-relaxed">
            {activeCand.description || 'No descriptive abstract provided by repository metadata.'}
          </p>

          {/* Citation & Provenance Bar */}
          <div className="pt-2 flex flex-wrap items-center gap-2 border-t border-slate-100 dark:border-slate-800 text-xs">
            <span className="text-slate-500 font-semibold text-[11px]">Copy Citation:</span>
            <button
              onClick={() => copyToClipboard(generateAPA(), 'APA')}
              className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 flex items-center gap-1 text-[11px]"
            >
              {copiedFormat === 'APA' ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3 text-slate-400" />}
              <span>{copiedFormat === 'APA' ? 'Copied APA!' : 'APA'}</span>
            </button>
            <button
              onClick={() => copyToClipboard(generateBibTeX(), 'BibTeX')}
              className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 flex items-center gap-1 text-[11px]"
            >
              {copiedFormat === 'BibTeX' ? <Check className="w-3 h-3 text-emerald-600" /> : <FileCode className="w-3 h-3 text-slate-400" />}
              <span>{copiedFormat === 'BibTeX' ? 'Copied BibTeX!' : 'BibTeX'}</span>
            </button>

            {activeCand.confidence && (
              <span className="ml-auto text-[11px] text-slate-500 dark:text-slate-400">
                Match Score: <strong className="text-indigo-600 dark:text-indigo-400">{activeCand.confidence.total_score} pts</strong>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Embedded Reader or Authorized Access Options Viewport */}
      <div className="rounded-3xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
        <div className="px-5 py-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 flex items-center justify-between text-xs text-slate-600 dark:text-slate-300">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            <span className="font-bold">Reading Viewport &amp; Access Channel</span>
          </div>
          {readerUrl && (
            <a
              href={readerUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 font-semibold"
            >
              <span>Full Screen Original</span>
              <Maximize2 className="w-3.5 h-3.5" />
            </a>
          )}
        </div>

        <div className="min-h-[500px] flex items-center justify-center p-6">
          {activeCand.can_embed && readerUrl ? (
            <iframe
              src={readerUrl}
              title={activeCand.title}
              className="w-full h-[650px] border-0 rounded-2xl bg-white shadow-inner"
              sandbox="allow-scripts allow-same-origin allow-popups"
            />
          ) : isPublicDomainOrOA ? (
            /* Authorized online reading options */
            <div className="max-w-md text-center space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-emerald-600 dark:text-emerald-400 mx-auto shadow-sm">
                <BookOpen className="w-8 h-8" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  Authorized Academic Access Verified
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  This volume is legally verified for academic use on{' '}
                  <strong className="text-indigo-600 dark:text-indigo-400">{activeCand.source_name}</strong>.
                  Repository security headers prevent in-frame rendering; open the official reader directly or review for acquisition.
                </p>
              </div>

              <div className="pt-2 flex flex-wrap items-center justify-center gap-3">
                <a
                  href={readerUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition-all active:scale-95"
                >
                  <ExternalLink className="w-4 h-4" />
                  <span>Launch Official Reader</span>
                </a>
                <button
                  onClick={() => onOpenDownloadApproval(activeCand)}
                  className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-bold rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-all active:scale-95"
                >
                  <Download className="w-4 h-4" />
                  <span>Review &amp; Approve Download</span>
                </button>
              </div>
            </div>
          ) : (
            /* Restricted Commercial Book */
            <div className="max-w-lg text-center space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-800 flex items-center justify-center text-rose-600 dark:text-rose-400 mx-auto shadow-sm">
                <ShieldAlert className="w-8 h-8" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  Commercial Copyright — Full-Text Downloading Strictly Prohibited
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  This work is protected by commercial copyright by{' '}
                  <strong className="text-slate-700 dark:text-slate-300">{activeCand.publisher || 'the copyright holder'}</strong>.
                  Automated full-text downloading is strictly blocked by our compliance safeguards.
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-left space-y-2 text-xs">
                <p className="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                  <Info className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                  <span>Permitted Academic Access Alternatives:</span>
                </p>
                <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-400 pl-1">
                  <li>Borrow via university library Controlled Digital Lending (CDL) service</li>
                  <li>Access via official campus bookstore or publisher portal</li>
                  <li>Discover peer-reviewed open-access alternative textbooks (e.g. OpenStax)</li>
                </ul>
              </div>

              <div className="pt-2">
                <button
                  onClick={() => onFindAlternative(activeCand)}
                  className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-bold rounded-xl bg-purple-600 hover:bg-purple-700 text-white shadow-sm transition-all active:scale-95"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>Find Open-Access Alternative Textbooks</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
