'use client';

/* eslint-disable @next/next/no-img-element */
import React from 'react';
import {
  X,
  BookOpen,
  Download,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  Sparkles,
  Lock,
} from 'lucide-react';
import { BookCandidate } from '@/types/book';

interface BookDetailsModalProps {
  candidate: BookCandidate | null;
  isOpen: boolean;
  onClose: () => void;
  onReadOnline: (candidate: BookCandidate) => void;
  onRequestDownload: (candidate: BookCandidate) => void;
}

export const BookDetailsModal: React.FC<BookDetailsModalProps> = ({
  candidate,
  isOpen,
  onClose,
  onReadOnline,
  onRequestDownload,
}) => {
  if (!isOpen || !candidate) return null;

  const score = candidate.confidence?.total_score ?? 0;
  const breakdown = candidate.confidence;
  const licensing = candidate.licensing;
  const isEligible = licensing?.is_legally_downloadable;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6 animate-fadeIn">
      <div className="relative w-full max-w-4xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-800/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Bibliographic Record &amp; Provenance
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Provider ID: <span className="font-mono text-indigo-600 dark:text-indigo-400">{candidate.candidate_id}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors"
            aria-label="Close details"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body (Scrollable) */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-sm text-slate-600 dark:text-slate-300">
          {/* Main Book Overview */}
          <div className="flex flex-col sm:flex-row gap-5 pb-6 border-b border-slate-200 dark:border-slate-800">
            {candidate.thumbnail_url ? (
              <div className="shrink-0 w-28 sm:w-36 h-40 sm:h-52 rounded-2xl overflow-hidden bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 shadow-md">
                <img
                  src={candidate.thumbnail_url}
                  alt={candidate.title}
                  className="w-full h-full object-cover"
                />
              </div>
            ) : (
              <div className="shrink-0 w-28 sm:w-36 h-40 sm:h-52 rounded-2xl bg-gradient-to-br from-indigo-950 to-slate-900 flex items-center justify-center text-white shadow-md">
                <BookOpen className="w-10 h-10 text-indigo-400" />
              </div>
            )}
            <div className="space-y-2.5 flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/70 border border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300">
                  {candidate.source_name}
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300">
                  {candidate.format || 'Standard Record'}
                </span>
                {candidate.access_type && (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-50 dark:bg-purple-950/70 border border-purple-200 dark:border-purple-800 text-purple-700 dark:text-purple-300">
                    Access: {candidate.access_type}
                  </span>
                )}
              </div>

              <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 dark:text-slate-100 leading-snug">
                {candidate.title}
              </h1>
              {candidate.subtitle && (
                <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">{candidate.subtitle}</p>
              )}

              <p className="text-sm font-semibold text-indigo-600 dark:text-indigo-400">
                {candidate.authors && candidate.authors.length > 0
                  ? candidate.authors.join(', ')
                  : 'Unknown Author'}
              </p>

              {/* Metadata Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 text-xs">
                <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-400 block text-[11px]">Publisher</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200 truncate block">
                    {candidate.publisher || 'Unknown'}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-400 block text-[11px]">Published Year</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200 block">
                    {candidate.published_year || 'Unknown'}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-400 block text-[11px]">Edition</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200 block">
                    {candidate.edition || 'Standard'}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-400 block text-[11px]">Pages</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200 block">
                    {candidate.page_count ? `${candidate.page_count} pp.` : 'N/A'}
                  </span>
                </div>
              </div>

              {/* ISBNs */}
              {candidate.isbns && candidate.isbns.length > 0 && (
                <div className="pt-2 text-xs flex items-center gap-2">
                  <span className="text-slate-400 font-medium">ISBNs:</span>
                  <div className="flex flex-wrap gap-1.5 font-mono text-[11px] text-slate-700 dark:text-slate-300">
                    {candidate.isbns.map((isbn, i) => (
                      <span key={i} className="px-2 py-0.5 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                        {isbn}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Description */}
          {candidate.description && (
            <div className="space-y-1.5 pb-6 border-b border-slate-200 dark:border-slate-800">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Syllabus &amp; Work Description
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed max-h-40 overflow-y-auto pr-2">
                {candidate.description}
              </p>
            </div>
          )}

          {/* Confidence Breakdown Grid */}
          {breakdown && (
            <div className="space-y-3 pb-6 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4" />
                  Deterministic Identity Confidence Breakdown
                </h3>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-50 dark:bg-indigo-950/80 border border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300">
                  Total: {score.toFixed(1)} / 100 pts ({breakdown.confidence_tier})
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center text-xs">
                <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-400 text-[11px] block">Title (max 30)</span>
                  <span className="font-bold text-slate-900 dark:text-slate-100">{breakdown.title_score.toFixed(1)}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-400 text-[11px] block">Author (max 25)</span>
                  <span className="font-bold text-slate-900 dark:text-slate-100">{breakdown.author_score.toFixed(1)}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-400 text-[11px] block">ISBN (max 20)</span>
                  <span className="font-bold text-slate-900 dark:text-slate-100">{breakdown.isbn_score.toFixed(1)}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-400 text-[11px] block">Edition/Year (max 15)</span>
                  <span className="font-bold text-slate-900 dark:text-slate-100">
                    {breakdown.edition_year_score.toFixed(1)}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <span className="text-slate-400 text-[11px] block">Publisher (max 10)</span>
                  <span className="font-bold text-slate-900 dark:text-slate-100">{breakdown.publisher_score.toFixed(1)}</span>
                </div>
              </div>

              {/* Explanations & Evidence */}
              {breakdown.explanation && breakdown.explanation.length > 0 && (
                <div className="p-3 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs space-y-1">
                  <span className="text-slate-500 font-semibold block">Scoring Rationale:</span>
                  <ul className="list-disc pl-4 space-y-0.5 text-slate-600 dark:text-slate-300">
                    {breakdown.explanation.map((exp, i) => (
                      <li key={i}>{exp}</li>
                    ))}
                  </ul>
                </div>
              )}

              {breakdown.mismatches_and_uncertainty && breakdown.mismatches_and_uncertainty.length > 0 && (
                <div className="p-3 rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/60 text-xs text-amber-700 dark:text-amber-200 flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-500" />
                  <div>
                    <span className="font-bold block">Uncertainty &amp; Field Mismatches:</span>
                    <ul className="list-disc pl-4 space-y-0.5 mt-0.5">
                      {breakdown.mismatches_and_uncertainty.map((m, i) => (
                        <li key={i}>{m}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Licensing & Rights Evidence */}
          {licensing && (
            <div className="space-y-3 pb-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4" />
                Legal Licensing &amp; Rights Verification
              </h3>

              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <span className="text-slate-400 text-xs block">Declared License</span>
                    <span className="text-sm font-bold text-slate-900 dark:text-slate-100">{licensing.license_name}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-slate-400 text-xs block">Eligibility Status</span>
                    <span
                      className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${
                        licensing.is_legally_downloadable
                          ? 'bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-700'
                          : 'bg-rose-50 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-800'
                      }`}
                    >
                      {licensing.status}
                    </span>
                  </div>
                </div>

                <div className="text-xs space-y-1">
                  <span className="text-slate-400 block">Rights Statement:</span>
                  <p className="text-slate-700 dark:text-slate-300 font-mono text-[11px] p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                    {licensing.rights_statement}
                  </p>
                </div>

                {licensing.evidence_details && licensing.evidence_details.length > 0 && (
                  <div className="text-xs space-y-1">
                    <span className="text-slate-400 block font-medium">Verification Factors:</span>
                    <ul className="list-disc pl-4 space-y-0.5 text-slate-600 dark:text-slate-300">
                      {licensing.evidence_details.map((ev, i) => (
                        <li key={i}>{ev}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer Actions */}
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 flex flex-wrap items-center justify-between gap-3">
          <a
            href={candidate.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs text-indigo-600 dark:text-indigo-400 hover:underline font-semibold"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span>Open Official Source ({candidate.source_name})</span>
          </a>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onReadOnline(candidate)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 transition-colors"
            >
              <BookOpen className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <span>Open in Reader</span>
            </button>

            {isEligible ? (
              <button
                type="button"
                onClick={() => onRequestDownload(candidate)}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 transition-colors shadow-sm shadow-emerald-600/20 active:scale-95"
              >
                <Download className="w-4 h-4" />
                <span>Acquisition Approval</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={() => onRequestDownload(candidate)}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium text-slate-400 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 cursor-not-allowed"
              >
                <Lock className="w-3.5 h-3.5" />
                <span>Download Restricted</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
