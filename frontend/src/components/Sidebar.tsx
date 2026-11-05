'use client';

import React from 'react';
import {
  LayoutDashboard,
  Search,
  GraduationCap,
  Activity,
  BookOpen,
  ShieldCheck,
  Settings,
  ChevronLeft,
  ChevronRight,
  Library,
  Radio,
  X,
  FolderDown,
} from 'lucide-react';

export type NavTab =
  | 'overview'
  | 'discovery'
  | 'syllabus'
  | 'progress'
  | 'reading'
  | 'library'
  | 'history'
  | 'settings';

interface SidebarProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  isMobileOpen: boolean;
  onMobileClose: () => void;
  auditCount?: number;
  activeBatchCount?: number;
  isBackendHealthy?: boolean | null;
}

export function Sidebar({
  activeTab,
  onTabChange,
  isCollapsed,
  onToggleCollapse,
  isMobileOpen,
  onMobileClose,
  auditCount = 0,
  activeBatchCount = 0,
  isBackendHealthy = true,
}: SidebarProps) {
  const navItems = [
    {
      id: 'overview' as NavTab,
      label: 'Overview',
      icon: LayoutDashboard,
      badge: null,
      description: 'System dashboard & metrics',
    },
    {
      id: 'discovery' as NavTab,
      label: 'Book Discovery',
      icon: Search,
      badge: null,
      description: 'Multi-source candidate search',
    },
    {
      id: 'syllabus' as NavTab,
      label: 'Syllabus Finder',
      icon: GraduationCap,
      badge: null,
      description: 'Upload & parse course reading lists',
    },
    {
      id: 'progress' as NavTab,
      label: 'Search Progress',
      icon: Activity,
      badge: activeBatchCount > 0 ? `${activeBatchCount} active` : null,
      badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
      description: 'Live batch search pipeline',
    },
    {
      id: 'reading' as NavTab,
      label: 'Reading Workspace',
      icon: BookOpen,
      badge: null,
      description: 'Authorized full-text reader',
    },
    {
      id: 'library' as NavTab,
      label: 'Download Library',
      icon: FolderDown,
      badge: null,
      description: 'Verified acquired books & storage',
    },
    {
      id: 'history' as NavTab,
      label: 'Acquisition History',
      icon: ShieldCheck,
      badge: auditCount > 0 ? `${auditCount}` : null,
      badgeColor: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
      description: 'Audited legal approval ledger',
    },
    {
      id: 'settings' as NavTab,
      label: 'Settings & System',
      icon: Settings,
      badge: null,
      description: 'Provider status & configuration',
    },
  ];

  const handleNavClick = (tab: NavTab) => {
    onTabChange(tab);
    if (isMobileOpen) {
      onMobileClose();
    }
  };

  const sidebarContent = (
    <div className="h-full w-full flex flex-col justify-between bg-[#0b1329] dark:bg-[#070d1e] text-slate-300 border-r border-slate-800 select-none overflow-x-hidden">
      {/* Brand Header */}
      <div>
        <div className="h-16 px-4 flex items-center justify-between border-b border-slate-800/80">
          <div
            onClick={() => handleNavClick('overview')}
            className="flex items-center gap-3 cursor-pointer group"
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center text-white shadow-md shadow-indigo-900/30 shrink-0 group-hover:scale-105 transition-transform">
              <Library className="w-5 h-5" />
            </div>
            {!isCollapsed && (
              <div className="overflow-hidden transition-all duration-200">
                <div className="flex items-center gap-1.5">
                  <span className="font-bold text-slate-100 text-sm tracking-tight">SyllExtract</span>
                  <span className="text-[10px] font-extrabold uppercase px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    Pro
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 truncate">Book Acquisition Agent</p>
              </div>
            )}
          </div>

          {/* Mobile close button */}
          <button
            onClick={onMobileClose}
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800"
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation list */}
        <nav className="p-3 space-y-1 overflow-y-auto max-h-[calc(100vh-230px)]">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleNavClick(item.id)}
                title={isCollapsed ? item.label : undefined}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all group relative ${
                  isActive
                    ? 'bg-indigo-600/15 text-indigo-300 font-semibold shadow-inner border border-indigo-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                {isActive && (
                  <span className="absolute left-0 top-2 bottom-2 w-1 bg-indigo-500 rounded-r-full" />
                )}
                <Icon
                  className={`w-4 h-4 shrink-0 transition-transform ${
                    isActive ? 'text-indigo-400 scale-110' : 'text-slate-400 group-hover:text-slate-200'
                  }`}
                />
                {!isCollapsed && (
                  <div className="flex-1 flex items-center justify-between text-left truncate">
                    <span className="truncate">{item.label}</span>
                    {item.badge && (
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded-full border font-semibold ${
                          item.badgeColor || 'bg-slate-800 text-slate-300 border-slate-700'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </div>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer / User Profile & System Status */}
      <div className="p-3 border-t border-slate-800/80 space-y-2">
        {/* Backend health status badge */}
        <div
          className={`flex items-center gap-2.5 px-3 py-2 rounded-xl text-[11px] ${
            isBackendHealthy
              ? 'bg-emerald-950/30 border border-emerald-800/40 text-emerald-300'
              : 'bg-rose-950/30 border border-rose-800/40 text-rose-300'
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${
              isBackendHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'
            }`}
          />
          {!isCollapsed && (
            <div className="truncate flex-1">
              <span className="font-medium">
                {isBackendHealthy ? 'API Engine Active' : 'API Engine Offline'}
              </span>
              <p className="text-[10px] text-slate-400">Port 8000 (FastAPI)</p>
            </div>
          )}
        </div>

        {/* User Card */}
        <div className="flex items-center gap-2.5 px-2.5 py-2 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
            AL
          </div>
          {!isCollapsed && (
            <div className="truncate flex-1">
              <p className="text-xs font-semibold text-slate-200 truncate">Academic Librarian</p>
              <p className="text-[10px] text-slate-400 truncate">Acquisition &amp; Audit</p>
            </div>
          )}
        </div>

        {/* Desktop Collapse Toggle */}
        <button
          onClick={onToggleCollapse}
          className="hidden lg:flex w-full items-center justify-center p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 text-xs transition-colors"
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <div className="flex items-center gap-2">
              <ChevronLeft className="w-4 h-4" />
              <span className="text-[11px]">Collapse Sidebar</span>
            </div>
          )}
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        className={`hidden lg:flex flex-col shrink-0 sticky top-0 h-screen z-30 transition-[width] duration-300 ease-in-out ${
          isCollapsed ? 'w-[72px]' : 'w-[260px]'
        }`}
      >
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Backdrop */}
      {isMobileOpen && (
        <div
          onClick={onMobileClose}
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-40 lg:hidden"
          aria-hidden="true"
        />
      )}

      {/* Mobile Sidebar Drawer */}
      <aside
        className={`fixed top-0 bottom-0 left-0 w-[260px] z-50 lg:hidden transform transition-transform duration-300 ease-in-out ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {sidebarContent}
      </aside>
    </>
  );
}
