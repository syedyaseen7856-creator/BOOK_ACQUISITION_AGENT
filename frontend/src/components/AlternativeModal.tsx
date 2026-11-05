'use client';

import React, { useState, useEffect } from 'react';
import {
  X,
  Sparkles,
  BookOpen,
  AlertCircle,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import { BookCandidate, AlternativeBookResponse } from '@/types/book';
import { getAlternativeBooks } from '@/lib/api';

interface AlternativeModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidate: BookCandidate | null;
  onSelectAlternative: (candidate: BookCandidate) => void;
}

export const AlternativeModal: React.FC<AlternativeModalProps> = ({
  isOpen,
  onClose,
  candidate,
  onSelectAlternative,
}) => {
  const [data, setData] = useState<AlternativeBookResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !candidate) return;
    let active = true;
    getAlternativeBooks(candidate.candidate_id)
      .then((resp) => {
        if (active) {
          setData(resp);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : 'Failed to search alternatives.');
          setData(null);
        }
      });
    return () => {
      active = false;
    };
  }, [isOpen, candidate]);

  const isLoading = isOpen && candidate && !data && !error;

  if (!isOpen || !candidate) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-3xl rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-800/50">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-purple-50 dark:bg-purple-950/50 border border-purple-200 dark:border-purple-800 flex items-center justify-center text-purple-600 dark:text-purple-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Open-Access Academic Alternatives
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Legitimate open textbooks &amp; public domain editions covering the same syllabus topics
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Area */}
        <div className="p-6 overflow-y-auto space-y-5">
          {/* Original Book Summary */}
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 flex items-start justify-between gap-4">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Prescribed Reference Book
              </span>
              <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 mt-0.5">{candidate.title}</h4>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {candidate.authors?.join(', ')} • {candidate.publisher}
              </p>
            </div>
            <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-rose-50 dark:bg-rose-950/50 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800 shrink-0">
              Commercial Copyright
            </span>
          </div>

          {/* Loading / Results */}
          {isLoading ? (
            <div className="p-12 text-center space-y-3">
              <RefreshCw className="w-8 h-8 mx-auto text-purple-600 dark:text-purple-400 animate-spin" />
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                Searching OpenStax, DOAB, and Open Library for verified open textbooks...
              </p>
            </div>
          ) : error ? (
            <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs">
              {error}
            </div>
          ) : data?.alternatives.length === 0 ? (
            <div className="p-8 text-center text-slate-500 space-y-2">
              <AlertCircle className="w-8 h-8 mx-auto text-slate-400" />
              <p className="text-xs font-semibold">No verified open textbook alternative found for this title.</p>
            </div>
          ) : (
            <div className="space-y-4">
              <h5 className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Recommended Authorized Alternatives ({data?.alternatives.length})
              </h5>

              {data?.alternatives.map((alt, idx) => {
                const c = alt.candidate;
                return (
                  <div
                    key={idx}
                    className="p-4 rounded-2xl bg-white dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 hover:border-purple-300 dark:hover:border-purple-700 transition-colors space-y-3 shadow-xs"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">{c.title}</h4>
                          <span
                            className={`px-2 py-0.5 text-[10px] font-bold rounded-full ${
                              alt.category === 'EXACT_OPEN_ACCESS'
                                ? 'bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                                : alt.category === 'OPEN_TEXTBOOK_ALTERNATIVE'
                                ? 'bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800'
                                : 'bg-purple-50 dark:bg-purple-950 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800'
                            }`}
                          >
                            {alt.category.replace(/_/g, ' ')}
                          </span>
                          <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-600">
                            {c.source_name}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                          {c.authors?.join(', ')} • {c.publisher} • {c.published_year || 'Recent edition'}
                        </p>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          onClick={() => {
                            onClose();
                            onSelectAlternative(c);
                          }}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white transition-all shadow-sm active:scale-95"
                        >
                          <BookOpen className="w-3.5 h-3.5" />
                          <span>Open in Workspace</span>
                        </button>
                      </div>
                    </div>

                    <p className="text-xs text-purple-800 dark:text-purple-200 bg-purple-50 dark:bg-purple-950/40 p-2.5 rounded-xl border border-purple-200 dark:border-purple-900/40">
                      💡 <strong>Why this alternative:</strong> {alt.relevance_explanation}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
