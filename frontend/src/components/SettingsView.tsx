'use client';

import React, { useState, useEffect } from 'react';
import {
  Settings,
  Database,
  Cpu,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Sun,
  Moon,
  Trash2,
  HardDrive,
  Lock,
  Globe,
  Clock,
  Sparkles,
} from 'lucide-react';
import { getSystemStatus, getProvidersStatus, SystemStatusInfo } from '@/lib/api';

export function SettingsView() {
  const [systemStatus, setSystemStatus] = useState<SystemStatusInfo | null>(null);
  const [providers, setProviders] = useState<Array<{ name: string; status: string; type: string }>>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [cacheCleared, setCacheCleared] = useState(false);

  useEffect(() => {
    const isDark = document.documentElement.classList.contains('dark');
    setTheme(isDark ? 'dark' : 'light');

    async function loadData() {
      try {
        const [statusData, providerData] = await Promise.allSettled([
          getSystemStatus(),
          getProvidersStatus(),
        ]);
        if (statusData.status === 'fulfilled') setSystemStatus(statusData.value);
        if (providerData.status === 'fulfilled') setProviders(providerData.value.providers);
      } catch {
        // ignore
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  const handleThemeChange = (newTheme: 'light' | 'dark') => {
    setTheme(newTheme);
    if (newTheme === 'dark') {
      document.documentElement.classList.add('dark');
      localStorage.setItem('syllex_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('syllex_theme', 'light');
    }
  };

  const handleClearCache = () => {
    localStorage.removeItem('syllex_recent_queries');
    setCacheCleared(true);
    setTimeout(() => setCacheCleared(false), 2500);
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto animate-fadeIn">
      {/* Header Banner */}
      <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            <h2 className="text-xl font-extrabold text-slate-900 dark:text-slate-100">
              System Settings &amp; Diagnostics
            </h2>
            <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
              Active v0.2.0
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Engine configuration, security policies, provider health checks, and interface preferences.
          </p>
        </div>
      </div>

      {/* Grid: Diagnostics and Security Policies */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Core Engine Status */}
        <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-100 dark:border-slate-800">
            <Cpu className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              FastAPI Engine &amp; Database
            </h3>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Service Name</span>
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {systemStatus?.app_name || 'SyllExtract Book Acquisition Agent'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Engine Environment</span>
              <span className="font-mono text-emerald-600 dark:text-emerald-400 font-semibold uppercase">
                {systemStatus?.environment || 'development'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">SQLite Database</span>
              <span className="flex items-center gap-1.5 font-semibold text-slate-800 dark:text-slate-200">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                <span>data/book_agent.db (Connected)</span>
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Gemini Flash AI Integration</span>
              <span className="flex items-center gap-1.5 font-semibold text-slate-800 dark:text-slate-200">
                {systemStatus?.gemini_flash_configured ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                    <span>{systemStatus.gemini_model} (Active)</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
                    <span>Deterministic Heuristic Fallback (Active)</span>
                  </>
                )}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Human Approval Expiration</span>
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {systemStatus?.approval_expiry_hours || 24} Hours
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Max Download File Size</span>
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {systemStatus?.max_file_size_mb || 50} MB
              </span>
            </div>
          </div>
        </div>

        {/* Security & SSRF Safeguards */}
        <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-100 dark:border-slate-800">
            <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              Security Safeguards &amp; SSRF Rules
            </h3>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">SSRF Defense</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Blocked Local/Private IP
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">PDF Signature Verification</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> pypdf Header &amp; Non-encrypted
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Cryptographic Integrity</span>
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                SHA-256 Hashing &amp; Duplicate Filter
              </span>
            </div>
            <div className="space-y-1 pt-1">
              <span className="text-slate-500 text-[11px] font-semibold">Allowed Domain Whitelist:</span>
              <div className="flex flex-wrap gap-1">
                {(systemStatus?.allowed_domains || [
                  'gutenberg.org',
                  'archive.org',
                  'openlibrary.org',
                  'doabooks.org',
                  'wisc.edu',
                ]).map((domain, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-mono text-[10px] border border-slate-200 dark:border-slate-700"
                  >
                    {domain}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Provider Telemetry Matrix */}
      <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              Connected Repository Providers
            </h3>
          </div>
          <span className="text-xs text-slate-500">Live API Endpoints</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {providers.map((p, i) => (
            <div
              key={i}
              className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1.5"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-slate-900 dark:text-slate-100">{p.name}</span>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    p.status === 'ONLINE'
                      ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                      : 'bg-amber-50 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800'
                  }`}
                >
                  {p.status}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">{p.type}</p>
            </div>
          ))}
        </div>
      </div>

      {/* User Preferences & Theme */}
      <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
          Interface &amp; Local Storage Preferences
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          {/* Theme Selector */}
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-2">
            <span className="font-semibold text-slate-800 dark:text-slate-200">Color Appearance</span>
            <p className="text-[11px] text-slate-500">
              Select your visual preference. Light workspace or modern dark slate.
            </p>
            <div className="flex items-center gap-2 pt-1">
              <button
                onClick={() => handleThemeChange('light')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border font-semibold ${
                  theme === 'light'
                    ? 'bg-white text-indigo-600 border-indigo-500 shadow-xs'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 border-slate-200 dark:border-slate-700'
                }`}
              >
                <Sun className="w-3.5 h-3.5" />
                <span>Light Workspace</span>
              </button>
              <button
                onClick={() => handleThemeChange('dark')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border font-semibold ${
                  theme === 'dark'
                    ? 'bg-slate-900 text-indigo-400 border-indigo-500 shadow-xs'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 border-slate-200 dark:border-slate-700'
                }`}
              >
                <Moon className="w-3.5 h-3.5" />
                <span>Dark Slate</span>
              </button>
            </div>
          </div>

          {/* Local Storage Cache */}
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-2">
            <span className="font-semibold text-slate-800 dark:text-slate-200">
              Clear Client Storage Cache
            </span>
            <p className="text-[11px] text-slate-500">
              Removes saved recent queries from local browser storage without affecting the database.
            </p>
            <div className="pt-1">
              <button
                onClick={handleClearCache}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white dark:bg-slate-800 hover:bg-rose-50 dark:hover:bg-rose-950/30 text-rose-600 dark:text-rose-400 border border-slate-200 dark:border-slate-700 transition-colors font-semibold"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>{cacheCleared ? 'Storage Cleared!' : 'Clear Recent Queries'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
