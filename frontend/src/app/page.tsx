'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Layers } from 'lucide-react';
import { Sidebar, NavTab } from '@/components/Sidebar';
import { Topbar } from '@/components/Topbar';
import { OverviewView } from '@/components/OverviewView';
import { DiscoveryView } from '@/components/DiscoveryView';
import { SyllabusView } from '@/components/SyllabusView';
import { BatchProgressView } from '@/components/BatchProgressView';
import { ReadingWorkspaceView } from '@/components/ReadingWorkspaceView';
import { DownloadLibraryView } from '@/components/DownloadLibraryView';
import { AcquisitionHistoryView } from '@/components/AcquisitionHistoryView';
import { SettingsView } from '@/components/SettingsView';
import { BookDetailsModal } from '@/components/BookDetailsModal';
import { ReaderModal } from '@/components/ReaderModal';
import { ApprovalModal } from '@/components/ApprovalModal';
import { AlternativeModal } from '@/components/AlternativeModal';
import { AuditDrawer } from '@/components/AuditDrawer';
import {
  BookCandidate,
  BookSearchQuery,
  SearchResponse,
  ProviderStatus,
} from '@/types/book';
import { searchBooks, getHealth, getApprovals } from '@/lib/api';

export default function Home() {
  const [activeTab, setActiveTab] = useState<NavTab>('overview');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState<boolean>(false);

  // Single Search State
  const [query, setQuery] = useState<BookSearchQuery | null>(null);
  const [candidates, setCandidates] = useState<BookCandidate[]>([]);
  const [relatedPublications, setRelatedPublications] = useState<BookCandidate[]>([]);
  const [providerStatuses, setProviderStatuses] = useState<ProviderStatus[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState<boolean>(false);

  // Active Batch State
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);

  // Modals state
  const [selectedCandidate, setSelectedCandidate] = useState<BookCandidate | null>(null);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [isReaderOpen, setIsReaderOpen] = useState(false);
  const [isApprovalOpen, setIsApprovalOpen] = useState(false);
  const [isAuditOpen, setIsAuditOpen] = useState(false);
  const [isAlternativeOpen, setIsAlternativeOpen] = useState(false);

  // System & ledger counters
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);
  const [auditCount, setAuditCount] = useState<number>(0);

  const loadAuditCount = useCallback(async () => {
    try {
      const records = await getApprovals();
      setAuditCount(records.length);
    } catch {
      // ignore
    }
  }, []);

  // Check health and count on mount
  useEffect(() => {
    let active = true;
    getHealth()
      .then((res) => {
        if (active) setIsBackendHealthy(res.status === 'healthy');
      })
      .catch(() => {
        if (active) setIsBackendHealthy(false);
      });

    getApprovals()
      .then((records) => {
        if (active) setAuditCount(records.length);
      })
      .catch(() => {
        // ignore
      });

    return () => {
      active = false;
    };
  }, []);

  const handleSearch = async (searchQuery: BookSearchQuery) => {
    setIsLoading(true);
    setError(null);
    setQuery(searchQuery);

    try {
      const resp: SearchResponse = await searchBooks(searchQuery);
      setCandidates(resp.candidates || []);
      setRelatedPublications(resp.related_publications || []);
      setProviderStatuses(resp.provider_statuses || []);
      setHasSearched(true);
      if (resp.candidates?.length > 0 && !selectedCandidate) {
        setSelectedCandidate(resp.candidates[0]);
      }
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : 'Discovery search failed across bibliographic providers.'
      );
      setCandidates([]);
      setProviderStatuses([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickSearch = (queryText: string) => {
    const q: BookSearchQuery = { title: queryText };
    handleSearch(q);
    setActiveTab('discovery');
  };

  const handleOpenDetails = (cand: BookCandidate) => {
    setSelectedCandidate(cand);
    setIsDetailsOpen(true);
  };

  const handleOpenReader = (cand: BookCandidate) => {
    setSelectedCandidate(cand);
    setActiveTab('reading');
  };

  const handleOpenApproval = (cand: BookCandidate) => {
    setSelectedCandidate(cand);
    setIsApprovalOpen(true);
  };

  const handleOpenAlternative = (cand: BookCandidate) => {
    setSelectedCandidate(cand);
    setIsAlternativeOpen(true);
  };

  const handleApprovalSuccess = () => {
    setIsApprovalOpen(false);
    loadAuditCount();
  };

  const handleStartBatchFromSyllabus = (batchId: string) => {
    setActiveBatchId(batchId);
    setActiveTab('progress');
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0b1120] text-slate-900 dark:text-slate-100 flex font-sans transition-colors duration-150">
      {/* Collapsible Left Navigation Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
        isMobileOpen={isMobileNavOpen}
        onMobileClose={() => setIsMobileNavOpen(false)}
        auditCount={auditCount}
        activeBatchCount={activeBatchId ? 1 : 0}
        isBackendHealthy={isBackendHealthy}
      />

      {/* Main Workspace Frame */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen overflow-x-hidden">
        {/* Sticky Topbar with Search, Stats & Actions */}
        <Topbar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onMobileMenuOpen={() => setIsMobileNavOpen(true)}
          onQuickSearch={handleQuickSearch}
          auditCount={auditCount}
          activeBatchCount={activeBatchId ? 1 : 0}
          isBackendHealthy={isBackendHealthy}
        />

        {/* Dynamic Viewport Container */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-fadeIn">
          {/* 1. System Overview Dashboard */}
          {activeTab === 'overview' && (
            <OverviewView
              onTabChange={setActiveTab}
              onExecuteSearch={(q) => {
                handleSearch(q);
                setActiveTab('discovery');
              }}
            />
          )}

          {/* 2. Book Discovery (Multi-source Search & Filtering) */}
          {activeTab === 'discovery' && (
            <DiscoveryView
              candidates={candidates}
              relatedPublications={relatedPublications}
              providerStatuses={providerStatuses}
              isLoading={isLoading}
              error={error}
              hasSearched={hasSearched}
              activeQuery={query}
              onSearch={handleSearch}
              onClear={() => {
                setQuery(null);
                setCandidates([]);
                setRelatedPublications([]);
                setHasSearched(false);
              }}
              onViewDetails={handleOpenDetails}
              onReadOnline={handleOpenReader}
              onApprove={handleOpenApproval}
              onFindAlternative={handleOpenAlternative}
            />
          )}

          {/* 3. Syllabus Book Finder */}
          {activeTab === 'syllabus' && (
            <SyllabusView onStartBatch={handleStartBatchFromSyllabus} />
          )}

          {/* 4. Live Batch Search Progress */}
          {activeTab === 'progress' && (
            <div>
              {activeBatchId ? (
                <BatchProgressView
                  batchId={activeBatchId}
                  onOpenReader={handleOpenReader}
                  onOpenDetails={handleOpenDetails}
                  onOpenAlternative={handleOpenAlternative}
                />
              ) : (
                <div className="p-12 text-center rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 space-y-4 max-w-xl mx-auto shadow-sm">
                  <Layers className="w-12 h-12 mx-auto text-indigo-500 dark:text-indigo-400" />
                  <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                    No Active Batch Search Running
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Upload a course syllabus document in PDF or DOCX format to parse citations and launch bounded parallel searches.
                  </p>
                  <button
                    onClick={() => setActiveTab('syllabus')}
                    className="px-5 py-2.5 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm shadow-indigo-600/20 transition-all active:scale-95"
                  >
                    Go to Syllabus Book Finder
                  </button>
                </div>
              )}
            </div>
          )}

          {/* 5. Reading Workspace (Authorized View) */}
          {activeTab === 'reading' && (
            <ReadingWorkspaceView
              candidate={selectedCandidate}
              candidatesList={candidates}
              onBackToSyllabus={() =>
                setActiveTab(activeBatchId ? 'progress' : 'discovery')
              }
              onOpenDownloadApproval={handleOpenApproval}
              onFindAlternative={handleOpenAlternative}
            />
          )}

          {/* 6. Download Library (Local Acquired Storage) */}
          {activeTab === 'library' && (
            <DownloadLibraryView onOpenReader={handleOpenReader} />
          )}

          {/* 7. Legal Acquisition History Ledger */}
          {activeTab === 'history' && <AcquisitionHistoryView />}

          {/* 8. Settings & Architecture Diagnostics */}
          {activeTab === 'settings' && <SettingsView />}
        </main>
      </div>

      {/* Global Interactive Modals & Drawers */}
      {selectedCandidate && (
        <BookDetailsModal
          isOpen={isDetailsOpen}
          onClose={() => setIsDetailsOpen(false)}
          candidate={selectedCandidate}
          onReadOnline={handleOpenReader}
          onRequestDownload={handleOpenApproval}
        />
      )}

      {selectedCandidate && (
        <ReaderModal
          isOpen={isReaderOpen}
          onClose={() => setIsReaderOpen(false)}
          candidate={selectedCandidate}
        />
      )}

      {selectedCandidate && (
        <ApprovalModal
          isOpen={isApprovalOpen}
          onClose={() => setIsApprovalOpen(false)}
          candidate={selectedCandidate}
          onApprovalComplete={handleApprovalSuccess}
        />
      )}

      {selectedCandidate && (
        <AlternativeModal
          isOpen={isAlternativeOpen}
          onClose={() => setIsAlternativeOpen(false)}
          candidate={selectedCandidate}
          onSelectAlternative={(alt) => {
            setSelectedCandidate(alt);
            setActiveTab('reading');
          }}
        />
      )}

      <AuditDrawer
        isOpen={isAuditOpen}
        onClose={() => setIsAuditOpen(false)}
        onRefresh={loadAuditCount}
      />
    </div>
  );
}
