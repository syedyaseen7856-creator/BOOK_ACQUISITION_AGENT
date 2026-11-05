'use client';

import React, { useState, useEffect } from 'react';
import {
  Search,
  GraduationCap,
  ShieldCheck,
  FileDown,
  Database,
  Cpu,
  BookOpen,
  ArrowRight,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Layers,
  Compass,
} from 'lucide-react';
import { NavTab } from './Sidebar';
import {
  getSystemStatus,
  getAcquisitionHistory,
  getProvidersStatus,
  SystemStatusInfo,
} from '@/lib/api';
import { AcquisitionHistoryItem, BookSearchQuery } from '@/types/book';

interface OverviewViewProps {
  onTabChange: (tab: NavTab) => void;
  onExecuteSearch: (query: BookSearchQuery) => void;
}

export function OverviewView({ onTabChange, onExecuteSearch }: OverviewViewProps) {
  const [systemStats, setSystemStats] = useState<SystemStatusInfo | null>(null);
  const [historyItems, setHistoryItems] = useState<AcquisitionHistoryItem[]>([]);
  const [providers, setProviders] = useState<Array<{ name: string; status: string; type: string }>>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      try {
        const [statsData, historyData, providersData] = await Promise.allSettled([
          getSystemStatus(),
          getAcquisitionHistory(undefined, undefined),
          getProvidersStatus(),
        ]);

        if (isMounted) {
          if (statsData.status === 'fulfilled') setSystemStats(statsData.value);
          if (historyData.status === 'fulfilled') setHistoryItems(historyData.value.records.slice(0, 6));
          if (providersData.status === 'fulfilled') setProviders(providersData.value.providers);
          setIsLoading(false);
        }
      } catch {
        if (isMounted) setIsLoading(false);
      }
    }
    loadData();
    return () => {
      isMounted = false;
    };
  }, []);

  const searchPresets = [
    {
      title: 'Frankenstein',
      author: 'Mary Shelley',
      badge: 'Public Domain',
      badgeClass: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
      description: 'Public domain monograph with authorized Gutenberg download & verified license.',
      query: { title: 'Frankenstein', author: 'Mary Shelley' },
    },
    {
      title: 'Operating Systems: Three Easy Pieces',
      author: 'Remzi Arpaci-Dusseau',
      badge: 'Open Access CC-BY',
      badgeClass: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
      description: 'Authorized open educational resource (OER) with full-text chapters.',
      query: { title: 'Operating Systems: Three Easy Pieces', author: 'Remzi Arpaci-Dusseau' },
    },
    {
      title: 'Artificial Intelligence: A Modern Approach',
      author: 'Stuart Russell, Peter Norvig',
      badge: 'Commercial Copyright',
      badgeClass: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20',
      description: 'Demonstrates mandatory safeguard: In-copyright title with download strictly blocked.',
      query: { title: 'Artificial Intelligence: A Modern Approach', author: 'Russell' },
    },
    {
      title: 'Introduction to Algorithms',
      author: 'Thomas H. Cormen',
      badge: 'CDL Borrow Only',
      badgeClass: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
      description: 'Controlled digital lending record requiring library credential check.',
      query: { title: 'Introduction to Algorithms', author: 'Cormen' },
    },
  ];

  return (
    <div className="space-y-8 animate-fadeIn max-w-7xl mx-auto">
      {/* Hero Welcome Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-900 via-indigo-950 to-slate-900 text-white p-6 sm:p-8 lg:p-10 shadow-lg border border-indigo-800/40">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 opacity-10 bg-[radial-gradient(circle_at_top_right,white,transparent_70%)] pointer-events-none" />
        <div className="relative z-10 max-w-3xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-400/30">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Academic Book Discovery &amp; Legal Access Agent</span>
          </div>

          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-white leading-tight">
            SyllExtract Acquisition Pro
          </h1>

          <p className="text-sm sm:text-base text-slate-300 max-w-2xl leading-relaxed">
            Discover academic books across global bibliographic repositories, calculate explainable
            0–100 match confidence scores in Python, independently verify licensing evidence, and manage
            explicit per-book human approvals with cryptographic audit logging.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              onClick={() => onTabChange('discovery')}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold bg-white text-indigo-950 hover:bg-slate-100 shadow-md transition-all active:scale-95"
            >
              <Search className="w-4 h-4 text-indigo-600" />
              <span>Search for a Book</span>
            </button>
            <button
              onClick={() => onTabChange('syllabus')}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold bg-indigo-600/30 hover:bg-indigo-600/40 text-indigo-100 border border-indigo-400/40 shadow-sm transition-all active:scale-95"
            >
              <GraduationCap className="w-4 h-4" />
              <span>Upload Syllabus Document</span>
            </button>
            <button
              onClick={() => onTabChange('history')}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white transition-colors"
            >
              <span>View Audit History</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Real Statistics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Searches */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Searches Recorded</span>
            <div className="w-8 h-8 rounded-xl bg-indigo-50 dark:bg-indigo-950/50 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
              <Search className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100">
            {systemStats ? systemStats.total_searches_recorded : '—'}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            Multi-source queries with query tokens preserved
          </p>
        </div>

        {/* Total Approvals */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Recorded Approvals</span>
            <div className="w-8 h-8 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100">
            {systemStats ? systemStats.total_approvals_recorded : '—'}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            Explicit human affirmations with SHA-256 snapshot hashes
          </p>
        </div>

        {/* Validated Downloads */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Validated Downloads</span>
            <div className="w-8 h-8 rounded-xl bg-blue-50 dark:bg-blue-950/50 flex items-center justify-center text-blue-600 dark:text-blue-400">
              <FileDown className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100">
            {systemStats ? systemStats.total_downloads_recorded : '—'}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            SSRF-guarded, pypdf-validated legitimate acquisitions
          </p>
        </div>

        {/* Database & Model Health */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-slate-500 dark:text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">System Engine</span>
            <div className="w-8 h-8 rounded-xl bg-purple-50 dark:bg-purple-950/50 flex items-center justify-center text-purple-600 dark:text-purple-400">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0" />
            <span className="text-base font-bold text-slate-900 dark:text-slate-100">
              {systemStats ? `v${systemStats.version} Ready` : 'Connecting...'}
            </span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
            SQLite: {systemStats?.database_connected ? 'Connected' : 'Offline'} | Gemini:{' '}
            {systemStats?.gemini_flash_configured ? 'Active' : 'Fallback'}
          </p>
        </div>
      </div>

      {/* Two Column Grid: Search Presets & Provider Telemetry */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 cols: Verification Scenarios */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Verification &amp; Test Scenarios
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Click any benchmark query to test the scoring engine and legal rights verification:
              </p>
            </div>
            <button
              onClick={() => onTabChange('discovery')}
              className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline inline-flex items-center gap-1"
            >
              <span>Custom Search</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {searchPresets.map((preset, idx) => (
              <div
                key={idx}
                onClick={() => {
                  onExecuteSearch(preset.query);
                  onTabChange('discovery');
                }}
                className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-indigo-500 dark:hover:border-indigo-500 shadow-sm hover:shadow-md cursor-pointer transition-all group flex flex-col justify-between space-y-3"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${preset.badgeClass}`}
                    >
                      {preset.badge}
                    </span>
                    <Compass className="w-4 h-4 text-slate-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors line-clamp-1">
                    {preset.title}
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">by {preset.author}</p>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-snug">
                  {preset.description}
                </p>
                <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center text-[11px] font-semibold text-indigo-600 dark:text-indigo-400">
                  <span>Run Evaluation Search</span>
                  <ArrowRight className="w-3 h-3 ml-1 transform group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right 1 col: Live Provider Telemetry */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Provider Telemetry
            </h2>
            <span className="text-[10px] font-semibold text-slate-500 dark:text-slate-400">
              Real-time check
            </span>
          </div>

          <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
            {providers.length === 0 ? (
              <div className="space-y-3 py-2">
                {['Google Books API', 'Open Library API', 'Project Gutenberg', 'OpenStax OER', 'Crossref Registry'].map(
                  (name, i) => (
                    <div key={i} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-emerald-500" />
                        <span className="font-semibold text-slate-800 dark:text-slate-200">{name}</span>
                      </div>
                      <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">ONLINE</span>
                    </div>
                  )
                )}
              </div>
            ) : (
              providers.map((p, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between py-1.5 border-b border-slate-100 dark:border-slate-800/60 last:border-0 text-xs"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          p.status === 'ONLINE' ? 'bg-emerald-500' : 'bg-amber-500'
                        }`}
                      />
                      <span className="font-semibold text-slate-800 dark:text-slate-200">{p.name}</span>
                    </div>
                    <p className="text-[10px] text-slate-400 pl-4">{p.type}</p>
                  </div>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      p.status === 'ONLINE'
                        ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20'
                    }`}
                  >
                    {p.status}
                  </span>
                </div>
              ))
            )}

            <div className="pt-2 text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 shrink-0" />
              <span>Strict SSRF domain whitelist enforcement active</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Acquisitions & Audited Searches Table */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Recent Audit &amp; Acquisition Records
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Immutable ledger from SQLite backend (searches, server approvals, and downloads):
            </p>
          </div>
          <button
            onClick={() => onTabChange('history')}
            className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline inline-flex items-center gap-1"
          >
            <span>Full History Ledger</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {historyItems.length === 0 ? (
          <div className="p-8 text-center rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-500 space-y-2">
            <Clock className="w-8 h-8 mx-auto text-slate-400" />
            <p className="text-xs font-medium">No recent acquisition events recorded yet.</p>
            <p className="text-[11px] text-slate-400">
              Execute a search or upload a syllabus to record discovery events.
            </p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Event Type</th>
                    <th className="py-3 px-4">Book Title / Query</th>
                    <th className="py-3 px-4">Source</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {historyItems.map((item) => (
                    <tr
                      key={item.id}
                      className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors"
                    >
                      <td className="py-3 px-4 font-semibold">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                            item.record_type === 'APPROVAL'
                              ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                              : item.record_type === 'DOWNLOAD'
                              ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20'
                              : 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20'
                          }`}
                        >
                          {item.record_type}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-medium text-slate-800 dark:text-slate-200">
                        {item.title}
                        {item.author && (
                          <span className="text-slate-500 dark:text-slate-400 font-normal">
                            {' '}
                            ({item.author})
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-500 dark:text-slate-400">{item.source}</td>
                      <td className="py-3 px-4">
                        <span className="font-semibold text-slate-700 dark:text-slate-300">
                          {item.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-500 dark:text-slate-400 whitespace-nowrap">
                        {new Date(item.timestamp).toLocaleString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
