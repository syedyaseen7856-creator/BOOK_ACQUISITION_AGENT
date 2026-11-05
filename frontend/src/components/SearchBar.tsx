'use client';

import React, { useState } from 'react';
import {
  Search,
  X,
  SlidersHorizontal,
  Clock,
  Sparkles,
  RotateCcw,
} from 'lucide-react';
import { BookSearchQuery } from '@/types/book';

interface SearchBarProps {
  onSearch: (query: BookSearchQuery) => void;
  isLoading: boolean;
  activeQuery: BookSearchQuery | null;
  onClear: () => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  onSearch,
  isLoading,
  activeQuery,
  onClear,
}) => {
  const [searchTerm, setSearchTerm] = useState(activeQuery?.q || '');
  const [authorFilter, setAuthorFilter] = useState(activeQuery?.author || '');
  const [isbnFilter, setIsbnFilter] = useState(activeQuery?.isbn || '');
  const [editionFilter, setEditionFilter] = useState(activeQuery?.edition || '');
  const [yearFilter, setYearFilter] = useState<string>(
    activeQuery?.year ? String(activeQuery.year) : ''
  );
  const [useMockData, setUseMockData] = useState<boolean>(
    activeQuery?.use_mock_data || false
  );
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Lazy initialize recent searches without cascading renders
  const [recentSearches, setRecentSearches] = useState<string[]>(() => {
    if (typeof window === 'undefined') return [];
    try {
      const saved = localStorage.getItem('syllex_recent_queries');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          return parsed.slice(0, 5);
        }
      }
    } catch {
      // ignore
    }
    return [];
  });

  const saveRecentSearch = (term: string) => {
    if (!term.trim()) return;
    try {
      const updated = [
        term.trim(),
        ...recentSearches.filter((s) => s.toLowerCase() !== term.trim().toLowerCase()),
      ].slice(0, 5);
      setRecentSearches(updated);
      localStorage.setItem('syllex_recent_queries', JSON.stringify(updated));
    } catch {
      // ignore
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = searchTerm.trim();
    if (!trimmed && !authorFilter && !isbnFilter) return;

    if (trimmed) saveRecentSearch(trimmed);

    const query: BookSearchQuery = {
      q: trimmed || undefined,
      author: authorFilter.trim() || undefined,
      isbn: isbnFilter.trim() || undefined,
      edition: editionFilter.trim() || undefined,
      year: yearFilter ? parseInt(yearFilter, 10) : undefined,
      use_mock_data: useMockData,
    };

    onSearch(query);
  };

  const handleClear = () => {
    setSearchTerm('');
    setAuthorFilter('');
    setIsbnFilter('');
    setEditionFilter('');
    setYearFilter('');
    onClear();
  };

  const handleQuickSearch = (term: string) => {
    setSearchTerm(term);
    saveRecentSearch(term);
    onSearch({
      q: term,
      use_mock_data: useMockData,
    });
  };

  const hasAdvancedFilters =
    Boolean(authorFilter || isbnFilter || editionFilter || yearFilter || useMockData);

  return (
    <div className="w-full max-w-4xl mx-auto space-y-3">
      {/* Search Input Box */}
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative flex items-center rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20 transition-all duration-200">
          <div className="pl-4 sm:pl-5 flex items-center pointer-events-none text-slate-400">
            <Search className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
          </div>

          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search academic titles, authors, ISBNs, or subjects..."
            className="w-full py-3.5 sm:py-4 pl-3 sm:pl-4 pr-32 sm:pr-48 md:pr-56 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 bg-transparent text-sm sm:text-base focus:outline-none"
            aria-label="Search book query"
          />

          <div className="absolute right-2 flex items-center gap-1.5 shrink-0">
            {searchTerm && (
              <button
                type="button"
                onClick={handleClear}
                className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                title="Clear input"
                aria-label="Clear search"
              >
                <X className="w-4 h-4" />
              </button>
            )}

            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className={`p-2 rounded-xl border text-xs font-medium transition-colors flex items-center gap-1 ${
                showAdvanced || hasAdvancedFilters
                  ? 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800'
                  : 'bg-slate-50 dark:bg-slate-800/80 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
              title="Toggle Advanced Filters"
              aria-label="Toggle Advanced Filters"
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Filters</span>
            </button>

            <button
              type="submit"
              disabled={isLoading || (!searchTerm.trim() && !authorFilter && !isbnFilter)}
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs sm:text-sm tracking-wide shadow-sm shadow-indigo-600/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150 flex items-center gap-1.5"
            >
              {isLoading ? (
                <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <span>Search</span>
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Advanced Filters Collapsible */}
      {showAdvanced && (
        <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-md space-y-4 animate-fadeIn">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 flex items-center gap-1.5">
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>Advanced Bibliographic Criteria</span>
            </span>
            <button
              type="button"
              onClick={() => {
                setAuthorFilter('');
                setIsbnFilter('');
                setEditionFilter('');
                setYearFilter('');
                setUseMockData(false);
              }}
              className="text-xs text-slate-500 hover:text-indigo-600 dark:hover:text-indigo-400 inline-flex items-center gap-1"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset filters</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
            <div>
              <label className="block text-slate-600 dark:text-slate-400 font-semibold mb-1">
                Author / Editor
              </label>
              <input
                type="text"
                value={authorFilter}
                onChange={(e) => setAuthorFilter(e.target.value)}
                placeholder="e.g. Mary Shelley"
                className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-slate-600 dark:text-slate-400 font-semibold mb-1">
                ISBN-10 or ISBN-13
              </label>
              <input
                type="text"
                value={isbnFilter}
                onChange={(e) => setIsbnFilter(e.target.value)}
                placeholder="e.g. 9780134610993"
                className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 font-mono text-[11px] focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-slate-600 dark:text-slate-400 font-semibold mb-1">
                Publication Year
              </label>
              <input
                type="number"
                value={yearFilter}
                onChange={(e) => setYearFilter(e.target.value)}
                placeholder="e.g. 2020"
                className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-slate-600 dark:text-slate-400 font-semibold mb-1">
                Edition Specification
              </label>
              <input
                type="text"
                value={editionFilter}
                onChange={(e) => setEditionFilter(e.target.value)}
                placeholder="e.g. 3rd ed."
                className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div className="pt-2 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 dark:border-slate-800 text-[11px]">
            <label className="flex items-center gap-2 cursor-pointer text-slate-600 dark:text-slate-400">
              <input
                type="checkbox"
                checked={useMockData}
                onChange={(e) => setUseMockData(e.target.checked)}
                className="rounded text-indigo-600 focus:ring-indigo-500 bg-slate-50 dark:bg-slate-800 border-slate-300 dark:border-slate-700"
              />
              <span>Include offline test catalog (Deterministic offline dataset)</span>
            </label>
            <span className="text-slate-400">
              Applies exact match scoring with subtitle &amp; author surname decay
            </span>
          </div>
        </div>
      )}

      {/* Recent Queries bar */}
      {recentSearches.length > 0 && !activeQuery && (
        <div className="flex items-center gap-2 text-xs overflow-x-auto py-1">
          <span className="text-slate-500 dark:text-slate-400 flex items-center gap-1 shrink-0">
            <Clock className="w-3.5 h-3.5" /> Recent:
          </span>
          <div className="flex items-center gap-1.5 flex-wrap">
            {recentSearches.map((term, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleQuickSearch(term)}
                className="px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:border-indigo-400 dark:hover:border-indigo-600 transition-colors truncate max-w-[200px]"
              >
                {term}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
