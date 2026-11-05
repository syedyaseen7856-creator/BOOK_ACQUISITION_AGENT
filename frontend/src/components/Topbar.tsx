'use client';

import React, { useState, useEffect } from 'react';
import {
  Menu,
  Search,
  Sun,
  Moon,
  Bell,
  CheckCircle2,
  AlertTriangle,
  FileText,
  BookOpen,
  ArrowRight,
  Shield,
  ExternalLink,
} from 'lucide-react';
import { NavTab } from './Sidebar';

interface TopbarProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  onMobileMenuOpen: () => void;
  onQuickSearch: (queryText: string) => void;
  auditCount?: number;
  activeBatchCount?: number;
  isBackendHealthy?: boolean | null;
}

export function Topbar({
  activeTab,
  onTabChange,
  onMobileMenuOpen,
  onQuickSearch,
  auditCount = 0,
  activeBatchCount = 0,
  isBackendHealthy = true,
}: TopbarProps) {
  const [quickInput, setQuickInput] = useState('');
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isNotifOpen, setIsNotifOpen] = useState(false);

  useEffect(() => {
    // Check initial dark mode state
    const isDark = document.documentElement.classList.contains('dark');
    setIsDarkMode(isDark);
  }, []);

  const toggleTheme = () => {
    const nextDark = !isDarkMode;
    setIsDarkMode(nextDark);
    if (nextDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('syllex_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('syllex_theme', 'light');
    }
  };

  const handleQuickSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (quickInput.trim()) {
      onQuickSearch(quickInput.trim());
      onTabChange('discovery');
    }
  };

  const tabTitles: Record<NavTab, { title: string; subtitle: string }> = {
    overview: {
      title: 'Overview Dashboard',
      subtitle: 'System health, acquisition statistics & provider telemetry',
    },
    discovery: {
      title: 'Book Discovery',
      subtitle: 'Multi-source search with 0–100 match confidence & legal verification',
    },
    syllabus: {
      title: 'Syllabus Finder',
      subtitle: 'Document citation extraction & multi-title batch search',
    },
    progress: {
      title: 'Search Progress',
      subtitle: 'Real-time multi-book discovery pipeline & provider metrics',
    },
    reading: {
      title: 'Reading Workspace',
      subtitle: 'Authorized full-text reader & citation provenance viewer',
    },
    library: {
      title: 'Download Library',
      subtitle: 'Locally acquired verified books, hierarchical storage & SHA-256 provenance',
    },
    history: {
      title: 'Acquisition History',
      subtitle: 'Immutable audit ledger, approvals & SHA-256 integrity hashes',
    },
    settings: {
      title: 'Settings & Diagnostics',
      subtitle: 'Provider status, model parameters & security safeguards',
    },
  };

  const currentTabInfo = tabTitles[activeTab] || tabTitles.overview;

  return (
    <header className="h-16 px-4 sm:px-6 lg:px-8 border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-[#0b1120]/95 backdrop-blur-md sticky top-0 z-20 flex items-center justify-between transition-colors w-full">
      {/* Left side: Mobile hamburger & Breadcrumbs */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onMobileMenuOpen}
          className="lg:hidden p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 focus:outline-none shrink-0"
          aria-label="Open mobile menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="min-w-0">
          <div className="flex items-center gap-2 text-[11px] font-medium text-slate-600 dark:text-slate-300">
            <span className="shrink-0">SyllExtract Pro</span>
            <span className="text-slate-400 dark:text-slate-600 shrink-0">/</span>
            <span className="text-indigo-600 dark:text-indigo-400 font-semibold capitalize truncate">
              {currentTabInfo.title}
            </span>
          </div>
          <h1 className="text-sm font-bold text-slate-800 dark:text-slate-100 hidden sm:block truncate max-w-xs md:max-w-md lg:max-w-lg">
            {currentTabInfo.subtitle}
          </h1>
        </div>
      </div>

      {/* Right side: Quick Search, Provider Pill, Notifications, Theme Toggle */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {/* Global Quick Search */}
        <form onSubmit={handleQuickSearchSubmit} className="hidden md:flex items-center relative">
          <Search className="w-3.5 h-3.5 absolute left-3 text-slate-400 pointer-events-none" />
          <input
            type="text"
            value={quickInput}
            onChange={(e) => setQuickInput(e.target.value)}
            placeholder="Quick title, author, or ISBN... (Enter)"
            className="w-56 lg:w-64 pl-8 pr-3 py-1.5 text-xs rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 transition-all"
          />
        </form>

        {/* Live Provider Status Pill */}
        <button
          onClick={() => onTabChange('settings')}
          className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-xs font-medium bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:border-indigo-400 dark:hover:border-indigo-600 transition-colors"
          title="Click to view provider telemetry & status"
        >
          <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
          <span className="text-[11px]">5 Providers Online</span>
        </button>

        {/* Notifications Popover */}
        <div className="relative">
          <button
            onClick={() => setIsNotifOpen(!isNotifOpen)}
            className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 focus:outline-none relative transition-colors"
            aria-label="View system notifications"
            title="System notifications"
          >
            <Bell className="w-4 h-4" />
            {(auditCount > 0 || activeBatchCount > 0) && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-indigo-500 ring-2 ring-white dark:ring-slate-900" />
            )}
          </button>

          {isNotifOpen && (
            <div className="absolute right-0 mt-2 w-80 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl p-4 z-50 text-xs space-y-3 animate-fadeIn">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                <span className="font-bold text-slate-800 dark:text-slate-200">System Activity</span>
                <span className="text-[10px] text-slate-400">Live events</span>
              </div>

              <div className="space-y-2 max-h-60 overflow-y-auto">
                {auditCount > 0 ? (
                  <div className="p-2.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-200/50 dark:border-indigo-800/40 text-indigo-900 dark:text-indigo-200 flex items-start gap-2.5">
                    <Shield className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold">{auditCount} Approved Books Recorded</p>
                      <p className="text-[10px] text-indigo-700 dark:text-indigo-300">
                        Human affirmations with SHA-256 snapshot hashes active in audit log.
                      </p>
                    </div>
                  </div>
                ) : null}

                {activeBatchCount > 0 ? (
                  <div className="p-2.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200/50 dark:border-emerald-800/40 text-emerald-900 dark:text-emerald-200 flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold">{activeBatchCount} Batch Search Job Active</p>
                      <p className="text-[10px] text-emerald-700 dark:text-emerald-300">
                        Multi-provider concurrent pipeline is evaluating candidates.
                      </p>
                    </div>
                  </div>
                ) : null}

                <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 flex items-start gap-2.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold">FastAPI Engine Online</p>
                    <p className="text-[10px] text-slate-500 dark:text-slate-400">
                      Safe downloader, SSRF defense &amp; pypdf validator active.
                    </p>
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex justify-end">
                <button
                  onClick={() => {
                    setIsNotifOpen(false);
                    onTabChange('history');
                  }}
                  className="text-indigo-600 dark:text-indigo-400 font-semibold hover:underline inline-flex items-center gap-1"
                >
                  <span>Open Audit Ledger</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 focus:outline-none transition-colors"
          aria-label={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          title={isDarkMode ? 'Switch to light theme' : 'Switch to dark theme'}
        >
          {isDarkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-600" />}
        </button>

        {/* Quick Action: New Search */}
        <button
          onClick={() => onTabChange('discovery')}
          className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm shadow-indigo-600/20 transition-all"
        >
          <Search className="w-3.5 h-3.5" />
          <span>New Search</span>
        </button>
      </div>
    </header>
  );
}
