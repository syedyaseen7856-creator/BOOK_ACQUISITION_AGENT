'use client';

import React, { useState } from 'react';
import {
  Sparkles,
  ArrowUpDown,
  AlertCircle,
  BookMarked,
  LayoutGrid,
  List,
  Filter,
  CheckCircle2,
  X,
  Compass,
  ArrowRight,
} from 'lucide-react';
import { SearchBar } from './SearchBar';
import { ProviderStatusPills } from './ProviderStatusPills';
import { BookCard } from './BookCard';
import {
  BookCandidate,
  BookSearchQuery,
  ProviderStatus,
} from '@/types/book';

type SortOption = 'SCORE_DESC' | 'YEAR_DESC' | 'TITLE_ASC';
type ScoreFilter = 'ALL' | 'STRONG_ONLY' | 'PLAUSIBLE_PLUS';
type LicenseFilter = 'ALL' | 'PERMITTED_ONLY' | 'NOT_ELIGIBLE';

interface DiscoveryViewProps {
  candidates: BookCandidate[];
  relatedPublications?: BookCandidate[];
  providerStatuses: ProviderStatus[];
  isLoading: boolean;
  error: string | null;
  hasSearched: boolean;
  activeQuery: BookSearchQuery | null;
  onSearch: (query: BookSearchQuery) => void;
  onClear: () => void;
  onViewDetails: (candidate: BookCandidate) => void;
  onReadOnline: (candidate: BookCandidate) => void;
  onApprove: (candidate: BookCandidate) => void;
  onFindAlternative: (candidate: BookCandidate) => void;
}

export function DiscoveryView({
  candidates,
  relatedPublications = [],
  providerStatuses,
  isLoading,
  error,
  hasSearched,
  activeQuery,
  onSearch,
  onClear,
  onViewDetails,
  onReadOnline,
  onApprove,
  onFindAlternative,
}: DiscoveryViewProps) {
  const [sortBy, setSortBy] = useState<SortOption>('SCORE_DESC');
  const [scoreFilter, setScoreFilter] = useState<ScoreFilter>('ALL');
  const [licenseFilter, setLicenseFilter] = useState<LicenseFilter>('ALL');
  const [selectedProvider, setSelectedProvider] = useState<string>('ALL');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Extract unique providers from results
  const availableProviders = Array.from(
    new Set(candidates.map((c) => c.source_name))
  );

  // Apply filters
  const filteredCandidates = candidates.filter((c) => {
    // Score filter
    if (scoreFilter === 'STRONG_ONLY') {
      if ((c.confidence?.total_score || 0) < 90) return false;
    } else if (scoreFilter === 'PLAUSIBLE_PLUS') {
      if ((c.confidence?.total_score || 0) < 75) return false;
    }

    // License filter
    if (licenseFilter === 'PERMITTED_ONLY') {
      if (c.licensing?.status !== 'VERIFIED_FOR_PERMITTED_DOWNLOAD') return false;
    } else if (licenseFilter === 'NOT_ELIGIBLE') {
      if (c.licensing?.status !== 'NOT_ELIGIBLE' && c.licensing?.status !== 'COMMERCIAL_RESTRICTED')
        return false;
    }

    // Provider filter
    if (selectedProvider !== 'ALL') {
      if (c.source_name !== selectedProvider) return false;
    }

    return true;
  });

  // Sort candidates
  const sortedCandidates = [...filteredCandidates].sort((a, b) => {
    if (sortBy === 'SCORE_DESC') {
      const scoreA = a.confidence?.total_score || 0;
      const scoreB = b.confidence?.total_score || 0;
      return scoreB - scoreA;
    }
    if (sortBy === 'YEAR_DESC') {
      const yearA = a.published_year || 0;
      const yearB = b.published_year || 0;
      return yearB - yearA;
    }
    if (sortBy === 'TITLE_ASC') {
      return a.title.localeCompare(b.title);
    }
    return 0;
  });

  return (
    <div className="w-full space-y-6 animate-fadeIn">
      {/* Search Header Banner */}
      <div className="text-center w-full max-w-4xl mx-auto space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Multi-Source Bibliographic Discovery Engine</span>
        </div>
        <h2 className="text-2xl sm:text-4xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight">
          Academic Book Discovery &amp; <span className="text-indigo-600 dark:text-indigo-400">Legal Access</span>
        </h2>
        <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">
          Search Google Books, Open Library, Project Gutenberg, and OpenStax. Preview candidates, verify
          independent licensing evidence, and manage authorized acquisitions.
        </p>
      </div>

      {/* Main Search Bar */}
      <SearchBar
        onSearch={onSearch}
        isLoading={isLoading}
        activeQuery={activeQuery}
        onClear={onClear}
      />

      {/* Provider Status Indicators */}
      {providerStatuses.length > 0 && (
        <div className="w-full max-w-4xl mx-auto">
          <ProviderStatusPills statuses={providerStatuses} />
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="w-full max-w-4xl mx-auto p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0" />
          <p className="flex-1 font-medium">{error}</p>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800 animate-pulse">
            <div className="h-5 w-48 bg-slate-200 dark:bg-slate-800 rounded" />
            <div className="h-5 w-24 bg-slate-200 dark:bg-slate-800 rounded" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3, 4].map((n) => (
              <div
                key={n}
                className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 animate-pulse flex gap-4"
              >
                <div className="w-24 h-36 bg-slate-200 dark:bg-slate-800 rounded-xl shrink-0" />
                <div className="flex-1 space-y-3">
                  <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-3/4" />
                  <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded w-1/2" />
                  <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded w-full" />
                  <div className="h-8 bg-slate-200 dark:bg-slate-800 rounded w-1/3 mt-4" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Search Results / Controls / Empty States */}
      {!isLoading && hasSearched && (
        <div className="space-y-5">
          {/* Controls Bar: Results Count, Filters & Sorters */}
          <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <span>Discovered Candidates ({sortedCandidates.length})</span>
                {candidates.length !== sortedCandidates.length && (
                  <span className="text-xs font-normal text-slate-500">
                    (filtered from {candidates.length})
                  </span>
                )}
              </h3>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Ranked using explainable 0–100 match point calculation with hard mismatch caps
              </p>
            </div>

            {/* Filter & Sort Controls */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              {/* Score Filter */}
              <div className="flex items-center gap-1">
                <span className="text-slate-500 dark:text-slate-400 text-[11px]">Score:</span>
                <select
                  value={scoreFilter}
                  onChange={(e) => setScoreFilter(e.target.value as ScoreFilter)}
                  className="px-2.5 py-1.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
                >
                  <option value="ALL">All Scores</option>
                  <option value="STRONG_ONLY">Strong Match (90+ pts)</option>
                  <option value="PLAUSIBLE_PLUS">Plausible+ (75+ pts)</option>
                </select>
              </div>

              {/* License Filter */}
              <div className="flex items-center gap-1">
                <span className="text-slate-500 dark:text-slate-400 text-[11px]">License:</span>
                <select
                  value={licenseFilter}
                  onChange={(e) => setLicenseFilter(e.target.value as LicenseFilter)}
                  className="px-2.5 py-1.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
                >
                  <option value="ALL">All Licenses</option>
                  <option value="PERMITTED_ONLY">Download Permitted</option>
                  <option value="NOT_ELIGIBLE">Commercial / Prohibited</option>
                </select>
              </div>

              {/* Provider Filter */}
              {availableProviders.length > 1 && (
                <div className="flex items-center gap-1">
                  <span className="text-slate-500 dark:text-slate-400 text-[11px]">Source:</span>
                  <select
                    value={selectedProvider}
                    onChange={(e) => setSelectedProvider(e.target.value)}
                    className="px-2.5 py-1.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
                  >
                    <option value="ALL">All Sources</option>
                    {availableProviders.map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Sort By */}
              <div className="flex items-center gap-1">
                <span className="text-slate-500 dark:text-slate-400 text-[11px]">Sort:</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as SortOption)}
                  className="px-2.5 py-1.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
                >
                  <option value="SCORE_DESC">Confidence Score (High to Low)</option>
                  <option value="YEAR_DESC">Publication Year (Newest)</option>
                  <option value="TITLE_ASC">Title (A-Z)</option>
                </select>
              </div>

              {/* Grid / List View Toggle */}
              <div className="flex items-center border border-slate-200 dark:border-slate-700 rounded-xl p-0.5 bg-slate-50 dark:bg-slate-800">
                <button
                  type="button"
                  onClick={() => setViewMode('grid')}
                  className={`p-1.5 rounded-lg transition-colors ${
                    viewMode === 'grid'
                      ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-xs'
                      : 'text-slate-400 hover:text-slate-600'
                  }`}
                  aria-label="Grid View"
                  title="Grid View"
                >
                  <LayoutGrid className="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('list')}
                  className={`p-1.5 rounded-lg transition-colors ${
                    viewMode === 'list'
                      ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-xs'
                      : 'text-slate-400 hover:text-slate-600'
                  }`}
                  aria-label="List View"
                  title="List View"
                >
                  <List className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>

          {/* Results Display */}
          {sortedCandidates.length === 0 ? (
            <div className="p-12 text-center rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
              <BookMarked className="w-12 h-12 mx-auto text-slate-400" />
              <h4 className="text-base font-bold text-slate-800 dark:text-slate-200">
                No Candidates Match the Current Filters
              </h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                Try resetting your score or licensing filters, or execute a broader query without strict
                field constraints.
              </p>
              <button
                onClick={() => {
                  setScoreFilter('ALL');
                  setLicenseFilter('ALL');
                  setSelectedProvider('ALL');
                }}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800 hover:bg-indigo-100"
              >
                Reset All Filters
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              <div
                className={
                  viewMode === 'grid'
                    ? 'grid grid-cols-1 xl:grid-cols-2 gap-4 w-full min-w-0'
                    : 'space-y-4 w-full min-w-0'
                }
              >
                {sortedCandidates.map((cand) => (
                  <BookCard
                    key={cand.candidate_id}
                    candidate={cand}
                    onViewDetails={onViewDetails}
                    onReadOnline={onReadOnline}
                    onApprove={onApprove}
                    onFindAlternative={onFindAlternative}
                  />
                ))}
              </div>

              {/* Separate Section: Related Publications & Critical Context */}
              {relatedPublications && relatedPublications.length > 0 && (
                <div className="pt-6 border-t border-slate-200 dark:border-slate-800 space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                        <span>Related Publications &amp; Critical Context ({relatedPublications.length})</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 font-semibold">
                          Biographies &amp; Secondary Works
                        </span>
                      </h4>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400">
                        Works about the author, biographies, or critical studies separated from primary editions
                      </p>
                    </div>
                  </div>
                  <div
                    className={
                      viewMode === 'grid'
                        ? 'grid grid-cols-1 xl:grid-cols-2 gap-4 w-full min-w-0'
                        : 'space-y-4 w-full min-w-0'
                    }
                  >
                    {relatedPublications.map((cand) => (
                      <BookCard
                        key={cand.candidate_id}
                        candidate={cand}
                        onViewDetails={onViewDetails}
                        onReadOnline={onReadOnline}
                        onApprove={onApprove}
                        onFindAlternative={onFindAlternative}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Initial Empty State (Before searching) */}
      {!isLoading && !hasSearched && (
        <div className="w-full max-w-4xl mx-auto p-8 sm:p-12 text-center rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <div className="w-12 h-12 rounded-2xl bg-indigo-50 dark:bg-indigo-950/50 flex items-center justify-center text-indigo-600 dark:text-indigo-400 mx-auto">
            <Compass className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200">
              Ready for Academic Discovery
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Enter a title, author, ISBN, or subject above to aggregate records across authorized
              academic providers with legal licensing analysis.
            </p>
          </div>
          <div className="pt-2 flex flex-wrap items-center justify-center gap-2 text-xs">
            <span className="text-slate-400">Quick suggestions:</span>
            <button
              onClick={() => onSearch({ title: 'Frankenstein', author: 'Mary Shelley' })}
              className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors font-medium"
            >
              Frankenstein
            </button>
            <button
              onClick={() => onSearch({ title: 'Operating Systems: Three Easy Pieces' })}
              className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors font-medium"
            >
              Operating Systems (OSTEP)
            </button>
            <button
              onClick={() => onSearch({ title: 'Artificial Intelligence: A Modern Approach' })}
              className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors font-medium"
            >
              AI: A Modern Approach
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
