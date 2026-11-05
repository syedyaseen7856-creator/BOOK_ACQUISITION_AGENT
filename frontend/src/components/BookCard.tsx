'use client';

/* eslint-disable @next/next/no-img-element */
import React, { useState } from 'react';
import {
  BookOpen,
  Eye,
  Download,
  ShieldCheck,
  AlertTriangle,
  BookMarked,
  Sparkles,
  Lock,
  ChevronDown,
  ChevronUp,
  FileCheck,
  ExternalLink,
  Loader2,
  XCircle,
} from 'lucide-react';
import { BookCandidate } from '@/types/book';

interface BookCardProps {
  candidate: BookCandidate;
  onViewDetails: (candidate: BookCandidate) => void;
  onReadOnline: (candidate: BookCandidate) => void;
  onRequestDownload?: (candidate: BookCandidate) => void;
  onApprove?: (candidate: BookCandidate) => void;
  onFindAlternative?: (candidate: BookCandidate) => void;
  onDownloadFile?: (candidate: BookCandidate, format: 'PDF' | 'EPUB') => void;
}

export const BookCard: React.FC<BookCardProps> = ({
  candidate,
  onViewDetails,
  onReadOnline,
  onRequestDownload,
  onApprove,
  onFindAlternative,
  onDownloadFile,
}) => {
  const [imageError, setImageError] = useState(false);
  const [showScoreBreakdown, setShowScoreBreakdown] = useState(false);
  const [downloadingFormat, setDownloadingFormat] = useState<'PDF' | 'EPUB' | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const handleApprovalClick = () => {
    if (onApprove) onApprove(candidate);
    else if (onRequestDownload) onRequestDownload(candidate);
  };

  const handleDownload = async (format: 'PDF' | 'EPUB') => {
    if (onDownloadFile) {
      onDownloadFile(candidate, format);
      return;
    }

    setDownloadingFormat(format);
    setDownloadError(null);

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
        let errMsg = `Download failed (HTTP ${res.status})`;
        try {
          const errData = await res.json();
          if (errData?.detail) errMsg = errData.detail;
        } catch {
          // ignore JSON parse error
        }

        // Link Validation Guardrail: If 403 Forbidden, 429 Rate Limit, or paywall encountered,
        // gracefully fallback to the Reading Workspace preview URL instead of throwing a broken error.
        const isRestrictedOrRateLimited =
          res.status === 403 ||
          res.status === 429 ||
          errMsg.includes('403') ||
          errMsg.includes('429') ||
          errMsg.toLowerCase().includes('paywall') ||
          errMsg.toLowerCase().includes('restricted');

        if (isRestrictedOrRateLimited) {
          onReadOnline(candidate);
          return;
        }

        // Fallback to direct provider authorized URL if available
        const fallbackUrl =
          format === 'EPUB'
            ? candidate.epub_url
            : candidate.pdf_url || candidate.download_url;

        if (fallbackUrl && candidate.licensing?.is_legally_downloadable) {
          window.open(fallbackUrl, '_blank', 'noopener,noreferrer');
        } else {
          setDownloadError(errMsg);
        }
      }
    } catch (err: unknown) {
      // Graceful fallback to Reading Workspace preview URL on network/paywall error
      if (candidate.reader_url || candidate.embed_url || candidate.source_url) {
        onReadOnline(candidate);
        return;
      }

      const fallbackUrl =
        format === 'EPUB'
          ? candidate.epub_url
          : candidate.pdf_url || candidate.download_url;

      if (fallbackUrl && candidate.licensing?.is_legally_downloadable) {
        window.open(fallbackUrl, '_blank', 'noopener,noreferrer');
      } else {
        setDownloadError(err instanceof Error ? err.message : 'Download failed');
      }
    } finally {
      setDownloadingFormat(null);
    }
  };

  const score = candidate.confidence?.total_score ?? 0;
  const tier = candidate.confidence?.confidence_tier ?? 'LOW_CONFIDENCE';
  const isApproximate = candidate.is_approximate_suggestion;
  const isEligible = Boolean(candidate.licensing?.is_legally_downloadable);
  const confidence = candidate.confidence;

  // Genuine PDF & EPUB availability check
  const hasAuthorizedPdf =
    isEligible &&
    Boolean(
      candidate.pdf_url ||
        (candidate.download_url &&
          candidate.format?.toUpperCase() === 'PDF') ||
        (candidate.access_state === 'AUTHORIZED_DOWNLOAD' &&
          candidate.access_type === 'FULL_TEXT')
    );

  const hasAuthorizedEpub =
    isEligible &&
    Boolean(
      candidate.epub_url ||
        (candidate.download_url &&
          candidate.format?.toUpperCase() === 'EPUB')
    );

  // Match tier styling
  let tierBadge = {
    bg: 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300',
    label: 'Strong Match',
  };
  if (tier === 'PLAUSIBLE_MATCH') {
    tierBadge = {
      bg: 'bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300',
      label: 'Plausible Match',
    };
  } else if (tier === 'LOW_CONFIDENCE') {
    tierBadge = {
      bg: 'bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-300',
      label: 'Low Match',
    };
  }

  // Licensing badge styling
  const licenseStatus = candidate.licensing?.status;
  let licenseBadge = {
    bg: 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800',
    label: 'Needs Human Review',
  };
  if (licenseStatus === 'VERIFIED_FOR_PERMITTED_DOWNLOAD') {
    licenseBadge = {
      bg: 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
      label: 'Authorized for Download',
    };
  } else if (licenseStatus === 'COMMERCIAL_RESTRICTED') {
    licenseBadge = {
      bg: 'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-800',
      label: 'Commercial In-Copyright',
    };
  } else if (licenseStatus === 'NOT_ELIGIBLE') {
    licenseBadge = {
      bg: 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-400 border-slate-200 dark:border-slate-700',
      label: 'Acquisition Prohibited',
    };
  }

  // Access badge styling
  let accessBadge = {
    bg: 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700',
    label: 'Bibliographic Metadata',
  };
  if (candidate.access_type === 'FULL_TEXT') {
    accessBadge = {
      bg: 'bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800',
      label: 'Full Text Reader',
    };
  } else if (candidate.access_type === 'PREVIEW') {
    accessBadge = {
      bg: 'bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-800',
      label: 'Digital Preview',
    };
  } else if (candidate.access_type === 'PUBLISHER_PAGE') {
    accessBadge = {
      bg: 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700',
      label: 'Publisher Catalog',
    };
  }

  return (
    <div
      className={`group relative flex flex-col sm:flex-row gap-4 p-5 rounded-2xl bg-white dark:bg-slate-900 border transition-all duration-200 shadow-sm hover:shadow-md min-w-0 w-full box-border overflow-hidden ${
        isApproximate
          ? 'border-amber-300 dark:border-amber-800/80 bg-amber-50/20 dark:bg-slate-900'
          : 'border-slate-200 dark:border-slate-800 hover:border-indigo-400 dark:hover:border-indigo-600'
      }`}
    >
      {/* Cover Image or Styled Academic Fallback */}
      <div className="shrink-0 w-24 sm:w-28 h-36 sm:h-40 rounded-xl overflow-hidden bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex items-center justify-center relative shadow-sm">
        {candidate.thumbnail_url && !imageError ? (
          <img
            src={candidate.thumbnail_url}
            alt={candidate.title}
            onError={() => setImageError(true)}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            loading="lazy"
          />
        ) : (
          <div className="flex flex-col items-center justify-center p-2 text-center h-full w-full bg-gradient-to-br from-indigo-950 via-slate-900 to-slate-950 text-white">
            <BookMarked className="w-8 h-8 mb-1 text-indigo-400" />
            <span className="text-[10px] text-slate-300 line-clamp-2 px-1 font-semibold leading-tight break-words">
              {candidate.title}
            </span>
            <span className="text-[9px] text-indigo-300/80 mt-1 uppercase font-bold truncate max-w-full px-1">
              {candidate.source_name}
            </span>
          </div>
        )}

        {/* Source Provider tag over cover */}
        <div className="absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded-md bg-slate-900/85 backdrop-blur-xs text-[9px] font-bold text-slate-200 border border-slate-700 max-w-[90%] truncate">
          {candidate.source_name}
        </div>
      </div>

      {/* Main Content Info */}
      <div className="flex-1 flex flex-col justify-between min-w-0 space-y-3">
        <div className="min-w-0">
          {/* Approximate match warning banner */}
          {isApproximate && (
            <div className="mb-2 flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-200 text-xs font-medium">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
              <span>Partial / approximate match candidate</span>
            </div>
          )}

          {/* Badges Row */}
          <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 mb-2 min-w-0">
            {/* Match category badge (Exact Match / Alternate Edition / Related Work) */}
            {candidate.match_type === 'EXACT_MATCH' && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-bold border bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800 flex items-center gap-1 shrink-0">
                <span>Exact Match</span>
              </span>
            )}
            {candidate.match_type === 'ALTERNATE_EDITION' && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold border bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 flex items-center gap-1 shrink-0">
                <span>Alternate Edition</span>
              </span>
            )}
            {candidate.match_type === 'RELATED_PUBLICATION' && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold border bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800 flex items-center gap-1 shrink-0">
                <span>Related Publication</span>
              </span>
            )}

            {/* Identity match score badge */}
            <button
              type="button"
              onClick={() => setShowScoreBreakdown(!showScoreBreakdown)}
              className={`px-2 py-0.5 rounded-full text-[11px] font-bold border flex items-center gap-1 transition-transform active:scale-95 shrink-0 ${tierBadge.bg}`}
              title="Click to inspect 0-100 match point breakdown"
            >
              <Sparkles className="w-3 h-3" />
              <span>{tierBadge.label}</span>
              <span className="font-mono text-[10px]">({score.toFixed(0)} pts)</span>
              {showScoreBreakdown ? (
                <ChevronUp className="w-3 h-3 ml-0.5" />
              ) : (
                <ChevronDown className="w-3 h-3 ml-0.5" />
              )}
            </button>

            {/* Access Type badge */}
            <span
              className={`px-2 py-0.5 rounded-full text-[11px] font-medium border flex items-center gap-1 shrink-0 ${accessBadge.bg}`}
            >
              <BookOpen className="w-3 h-3" />
              <span>{accessBadge.label}</span>
            </span>

            {/* Independent Licensing Status badge */}
            <span
              className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border flex items-center gap-1 shrink-0 ${licenseBadge.bg}`}
            >
              <ShieldCheck className="w-3 h-3" />
              <span>{licenseBadge.label}</span>
            </span>
          </div>

          {/* Expandable Score Breakdown Panel */}
          {showScoreBreakdown && confidence && (
            <div className="p-3 mb-3 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-xs space-y-2 animate-fadeIn min-w-0">
              <div className="flex items-center justify-between font-bold text-slate-800 dark:text-slate-200">
                <span>Deterministic Match Point Breakdown (0–100)</span>
                <span className="font-mono text-indigo-600 dark:text-indigo-400">
                  Total: {score.toFixed(1)} / 100
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-[11px] text-slate-600 dark:text-slate-300">
                <div className="p-1.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center">
                  <span className="block text-slate-400 text-[10px]">Title (30)</span>
                  <span className="font-bold text-slate-800 dark:text-slate-100">
                    {confidence.title_score.toFixed(1)}
                  </span>
                </div>
                <div className="p-1.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center">
                  <span className="block text-slate-400 text-[10px]">Author (25)</span>
                  <span className="font-bold text-slate-800 dark:text-slate-100">
                    {confidence.author_score.toFixed(1)}
                  </span>
                </div>
                <div className="p-1.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center">
                  <span className="block text-slate-400 text-[10px]">ISBN (20)</span>
                  <span className="font-bold text-slate-800 dark:text-slate-100">
                    {confidence.isbn_score.toFixed(1)}
                  </span>
                </div>
                <div className="p-1.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center">
                  <span className="block text-slate-400 text-[10px]">Year/Ed (15)</span>
                  <span className="font-bold text-slate-800 dark:text-slate-100">
                    {confidence.edition_year_score.toFixed(1)}
                  </span>
                </div>
                <div className="p-1.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center">
                  <span className="block text-slate-400 text-[10px]">Publisher (10)</span>
                  <span className="font-bold text-slate-800 dark:text-slate-100">
                    {confidence.publisher_score.toFixed(1)}
                  </span>
                </div>
              </div>

              {confidence.has_hard_mismatch && (
                <div className="p-2 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-[11px] font-semibold flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                  <span>Hard Mismatch Detected: Score capped at ≤ 64 pts.</span>
                </div>
              )}
            </div>
          )}

          {/* Book Title & Subtitle */}
          <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors line-clamp-2 break-words min-w-0">
            {candidate.title}
          </h3>
          {candidate.subtitle && (
            <p className="text-xs text-slate-500 dark:text-slate-400 font-medium line-clamp-1 mt-0.5 break-words min-w-0">
              {candidate.subtitle}
            </p>
          )}

          {/* Match explanation narrative */}
          {candidate.match_explanation && (
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 italic break-words min-w-0">
              {candidate.match_explanation}
            </p>
          )}

          {/* Authors & Publication Metadata */}
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-600 dark:text-slate-400 mt-1.5 min-w-0">
            <span className="font-semibold text-slate-800 dark:text-slate-200 break-words">
              {candidate.authors && candidate.authors.length > 0
                ? candidate.authors.join(', ')
                : 'Unknown Author'}
            </span>
            {candidate.published_year && (
              <>
                <span className="text-slate-300 dark:text-slate-700">•</span>
                <span className="shrink-0">{candidate.published_year}</span>
              </>
            )}
            {candidate.publisher && (
              <>
                <span className="text-slate-300 dark:text-slate-700">•</span>
                <span className="truncate max-w-[160px] sm:max-w-[220px]" title={candidate.publisher}>
                  {candidate.publisher}
                </span>
              </>
            )}
            {candidate.edition && (
              <>
                <span className="text-slate-300 dark:text-slate-700">•</span>
                <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-[10px] font-medium text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 shrink-0">
                  {candidate.edition}
                </span>
              </>
            )}
            {candidate.isbns && candidate.isbns.length > 0 && (
              <>
                <span className="text-slate-300 dark:text-slate-700">•</span>
                <span className="font-mono text-[11px] text-slate-500 shrink-0">
                  ISBN: {candidate.isbns[0]}
                </span>
              </>
            )}
          </div>

          {/* Description snippet */}
          {candidate.description && (
            <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 mt-2 leading-relaxed break-words min-w-0">
              {candidate.description}
            </p>
          )}

          {/* Inline Download Error Banner */}
          {downloadError && (
            <div className="mt-2 p-2 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs flex items-center justify-between gap-2 animate-fadeIn">
              <div className="flex items-center gap-1.5 min-w-0">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                <span className="break-words font-medium">{downloadError}</span>
              </div>
              <button
                type="button"
                onClick={() => setDownloadError(null)}
                className="text-rose-500 hover:text-rose-700 p-0.5 shrink-0"
                aria-label="Dismiss"
              >
                <XCircle className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>

        {/* Action Buttons Row */}
        <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2.5 w-full min-w-0">
          {/* Left: View Details */}
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => onViewDetails(candidate)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 transition-colors shrink-0 whitespace-nowrap"
            >
              <Eye className="w-3.5 h-3.5 text-slate-500" />
              <span>Full Details</span>
            </button>
          </div>

          {/* Right: Actions (Read, Download, Approve, Alternative/Prohibited) */}
          <div className="flex flex-wrap items-center gap-2 min-w-0 justify-end">
            {/* Read Online button */}
            {candidate.reader_url || candidate.access_type === 'FULL_TEXT' || candidate.can_embed ? (
              <button
                type="button"
                onClick={() => onReadOnline(candidate)}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-950/50 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 border border-indigo-200 dark:border-indigo-800 transition-colors shadow-xs shrink-0 whitespace-nowrap"
                title="Launch digital reader in Reading Workspace"
              >
                <BookOpen className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                <span>Read Online</span>
              </button>
            ) : null}

            {/* Genuinely Available Download PDF */}
            {hasAuthorizedPdf && (
              <button
                type="button"
                disabled={downloadingFormat !== null}
                onClick={() => handleDownload('PDF')}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 shadow-sm shadow-emerald-600/20 transition-all active:scale-95 shrink-0 whitespace-nowrap disabled:opacity-60 cursor-pointer"
                title="Download verified authorized PDF file directly"
              >
                {downloadingFormat === 'PDF' ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Download className="w-3.5 h-3.5" />
                )}
                <span>Download PDF</span>
              </button>
            )}

            {/* Genuinely Available Download EPUB */}
            {hasAuthorizedEpub && (
              <button
                type="button"
                disabled={downloadingFormat !== null}
                onClick={() => handleDownload('EPUB')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-emerald-800 dark:text-emerald-200 bg-emerald-50 dark:bg-emerald-950/50 hover:bg-emerald-100 dark:hover:bg-emerald-900/60 border border-emerald-300 dark:border-emerald-800 transition-colors shadow-xs shrink-0 whitespace-nowrap disabled:opacity-60 cursor-pointer"
                title="Download verified authorized EPUB file directly"
              >
                {downloadingFormat === 'EPUB' ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Download className="w-3.5 h-3.5" />
                )}
                <span>Download EPUB</span>
              </button>
            )}

            {/* Review & Approve (if eligible) or Alternative / Prohibited */}
            {isEligible ? (
              <button
                type="button"
                onClick={handleApprovalClick}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 transition-all shrink-0 whitespace-nowrap"
                title="Review legal terms & record server-side human approval"
              >
                <FileCheck className="w-3.5 h-3.5 text-emerald-600" />
                <span>Review &amp; Approve</span>
              </button>
            ) : (
              <div className="flex flex-wrap items-center gap-1.5 min-w-0">
                {/* Legitimate Provider Access Link for Borrowing, Commercial, or Login */}
                {candidate.access_state === 'BORROWING_REQUIRED' && (candidate.reader_url || candidate.source_url) && (
                  <a
                    href={candidate.reader_url || candidate.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-amber-800 dark:text-amber-200 bg-amber-50 dark:bg-amber-950/50 hover:bg-amber-100 dark:hover:bg-amber-900/60 border border-amber-200 dark:border-amber-800 transition-colors shrink-0 whitespace-nowrap"
                    title="Borrow digital copy via Open Library / Internet Archive"
                  >
                    <ExternalLink className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                    <span>Borrow on {candidate.source_name}</span>
                  </a>
                )}
                {candidate.access_state === 'COMMERCIAL_ACCESS' && candidate.source_url && (
                  <a
                    href={candidate.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 transition-colors shrink-0 whitespace-nowrap"
                    title="Visit official publisher / catalog entry"
                  >
                    <ExternalLink className="w-3.5 h-3.5 text-slate-500" />
                    <span>Official Page</span>
                  </a>
                )}
                {candidate.access_state === 'LOGIN_REQUIRED' && candidate.source_url && (
                  <a
                    href={candidate.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 transition-colors shrink-0 whitespace-nowrap"
                    title="Sign in required to access full text"
                  >
                    <ExternalLink className="w-3.5 h-3.5 text-slate-500" />
                    <span>Sign In on {candidate.source_name}</span>
                  </a>
                )}
                {onFindAlternative && (
                  <button
                    type="button"
                    onClick={() => onFindAlternative(candidate)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-purple-700 dark:text-purple-300 bg-purple-50 dark:bg-purple-950/50 hover:bg-purple-100 dark:hover:bg-purple-900/60 border border-purple-200 dark:border-purple-800 transition-colors shrink-0 whitespace-nowrap"
                    title="Find open-access textbook alternative (OpenStax, Gutenberg)"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" />
                    <span>Find Alternative</span>
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleApprovalClick}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 hover:border-rose-300 transition-colors shrink-0 whitespace-nowrap"
                  title="In-copyright title. Downloading strictly prohibited by policy."
                >
                  <Lock className="w-3 h-3 text-rose-500" />
                  <span>Acquisition Prohibited</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
