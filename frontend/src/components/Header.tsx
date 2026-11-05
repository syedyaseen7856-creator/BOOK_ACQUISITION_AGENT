'use client';

import React, { useEffect, useState } from 'react';
import {
  BookOpen,
  Search,
  FileText,
  ListOrdered,
  BookCheck,
  History,
  Sun,
  Moon,
  ShieldCheck,
} from 'lucide-react';

export type NavTab = 'discovery' | 'syllabus' | 'batch' | 'reading' | 'history';

interface HeaderProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  auditCount: number;
  batchCount?: number;
  syllabusCount?: number;
  isBackendHealthy: boolean | null;
  onOpenAudit?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onTabChange,
  auditCount,
  batchCount = 0,
  syllabusCount = 0,
  isBackendHealthy,
  onOpenAudit,
}) => {
  const [isDarkMode, setIsDarkMode] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const isDark = document.documentElement.classList.contains('dark');
      setIsDarkMode(isDark);
    }
  }, []);

  const toggleTheme = () => {
    if (typeof window !== 'undefined') {
      if (isDarkMode) {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('syllex_theme', 'light');
        setIsDarkMode(false);
      } else {
        document.documentElement.classList.add('dark');
        localStorage.setItem('syllex_theme', 'dark');
        setIsDarkMode(true);
      }
    }
  };

  return (
    <header className="sticky top-0 z-30 w-full border-b border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Brand */}
        <div
          onClick={() => onTabChange('discovery')}
          className="flex items-center gap-3 cursor-pointer shrink-0"
        >
          <div className="h-10 w-10 rounded-2xl bg-indigo-600 text-white shadow-md shadow-indigo-600/25 flex items-center justify-center">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-base sm:text-lg text-slate-900 dark:text-slate-100 tracking-tight">
                SyllExtract <span className="text-indigo-600 dark:text-indigo-400 font-extrabold">Acquisition Pro</span>
              </span>
              <span className="px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase rounded-full bg-indigo-50 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                PRO v3.2
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 hidden lg:block">
              Compliant Digital Library Discovery &amp; Legal Access Agent
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 sm:gap-2 overflow-x-auto py-1">
          <button
            onClick={() => onTabChange('discovery')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all whitespace-nowrap ${
              activeTab === 'discovery'
                ? 'bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60'
            }`}
          >
            <Search className="w-3.5 h-3.5" />
            <span>Book Discovery</span>
          </button>

          <button
            onClick={() => onTabChange('syllabus')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all whitespace-nowrap ${
              activeTab === 'syllabus'
                ? 'bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Syllabus Finder</span>
            {syllabusCount > 0 && (
              <span className="px-1.5 py-0.2 text-[10px] rounded-full bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 font-bold">
                {syllabusCount}
              </span>
            )}
          </button>

          <button
            onClick={() => onTabChange('batch')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all whitespace-nowrap ${
              activeTab === 'batch'
                ? 'bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60'
            }`}
          >
            <ListOrdered className="w-3.5 h-3.5" />
            <span>Search Progress</span>
            {batchCount > 0 && (
              <span className="px-1.5 py-0.2 text-[10px] rounded-full bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 font-bold">
                {batchCount}
              </span>
            )}
          </button>

          <button
            onClick={() => onTabChange('reading')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all whitespace-nowrap ${
              activeTab === 'reading'
                ? 'bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60'
            }`}
          >
            <BookCheck className="w-3.5 h-3.5" />
            <span>Reading Workspace</span>
          </button>

          <button
            onClick={() => onTabChange('history')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all whitespace-nowrap ${
              activeTab === 'history'
                ? 'bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Acquisition</span> History
            {auditCount > 0 && (
              <span className="px-1.5 py-0.2 text-[10px] rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 font-bold border border-emerald-200 dark:border-emerald-800">
                {auditCount}
              </span>
            )}
          </button>
        </nav>

        {/* Right side controls */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0">
          {/* Quick Audit Drawer trigger */}
          {onOpenAudit && (
            <button
              onClick={onOpenAudit}
              title="Open Compliance & Audit Ledger"
              className="p-2 rounded-xl text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors flex items-center gap-1.5 text-xs font-semibold"
            >
              <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span className="hidden xl:inline">Audit Ledger</span>
            </button>
          )}

          {/* Theme Toggle Button */}
          <button
            onClick={toggleTheme}
            aria-label="Toggle Dark / Light Mode"
            title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            className="p-2 rounded-xl text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 transition-colors"
          >
            {isDarkMode ? (
              <Sun className="w-4 h-4 text-amber-400" />
            ) : (
              <Moon className="w-4 h-4 text-slate-600" />
            )}
          </button>

          {/* Backend Status indicator */}
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border bg-slate-50 dark:bg-slate-800/60 border-slate-200 dark:border-slate-700"
            title="Backend Service Status"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isBackendHealthy === true
                  ? 'bg-emerald-500 animate-pulse'
                  : isBackendHealthy === false
                  ? 'bg-rose-500'
                  : 'bg-amber-400'
              }`}
            />
            <span className="text-slate-600 dark:text-slate-300 hidden md:inline text-[11px] font-medium">
              {isBackendHealthy === true
                ? 'Online'
                : isBackendHealthy === false
                ? 'Offline'
                : 'Connecting'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
