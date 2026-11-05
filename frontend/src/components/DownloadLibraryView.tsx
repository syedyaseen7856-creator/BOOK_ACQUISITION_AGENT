'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  FolderDown,
  BookOpen,
  Download,
  Trash2,
  Search,
  CheckCircle2,
  FileText,
  Calendar,
  HardDrive,
  Sparkles,
  ExternalLink,
  Layers,
  GraduationCap,
  ShieldCheck,
  RefreshCw,
  Copy,
  Check,
} from 'lucide-react';
import { DownloadLibraryItem, BookCandidate } from '@/types/book';
import { getDownloadLibrary, deleteDownloadLibraryItem } from '@/lib/api';

interface DownloadLibraryViewProps {
  onOpenReader?: (candidate: BookCandidate) => void;
}

export const DownloadLibraryView: React.FC<DownloadLibraryViewProps> = ({ onOpenReader }) => {
  const [items, setItems] = useState<DownloadLibraryItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [filterSource, setFilterSource] = useState<'ALL' | 'SYLLABUS' | 'INDIVIDUAL'>('ALL');
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchLibrary = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await getDownloadLibrary();
      setItems(resp.items || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load download library.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLibrary();
  }, []);

  const handleDelete = async (jobId: string, title: string) => {
    if (!window.confirm(`Are you sure you want to delete '${title}' from your local library?`)) {
      return;
    }
    setDeletingId(jobId);
    try {
      await deleteDownloadLibraryItem(jobId);
      setItems((prev) => prev.filter((it) => it.job_id !== jobId));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to delete file.');
    } finally {
      setDeletingId(null);
    }
  };

  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const filteredItems = useMemo(() => {
    let list = items;

    if (filterSource === 'SYLLABUS') {
      list = list.filter((it) => Boolean(it.syllabus_name));
    } else if (filterSource === 'INDIVIDUAL') {
      list = list.filter((it) => !it.syllabus_name);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        (it) =>
          it.title.toLowerCase().includes(q) ||
          it.authors.some((a) => a.toLowerCase().includes(q)) ||
          (it.subject && it.subject.toLowerCase().includes(q)) ||
          (it.provider && it.provider.toLowerCase().includes(q))
      );
    }

    return list;
  }, [items, filterSource, searchQuery]);

  const totalBytes = useMemo(
    () => items.reduce((acc, it) => acc + (it.file_size_bytes || 0), 0),
    [items]
  );

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  const handleReadInApp = (item: DownloadLibraryItem) => {
    if (onOpenReader) {
      const streamUrl = `/api/downloads/library/${encodeURIComponent(item.job_id)}/stream`;
      const cand: BookCandidate = {
        candidate_id: item.candidate_id || item.job_id,
        title: item.title,
        alternate_titles: [],
        authors: item.authors,
        publisher: item.publisher,
        edition: item.edition,
        isbns: [],
        categories: item.subject ? [item.subject] : [],
        source_name: item.provider,
        source_url: streamUrl,
        reader_url: streamUrl,
        can_embed: true,
        reader_type: 'EMBEDDED_PDF',
        access_type: 'FULL_TEXT',
        format: item.format,
        licensing: {
          status: 'VERIFIED_FOR_PERMITTED_DOWNLOAD',
          license_name: 'Verified Local Copy',
          rights_statement: 'Authorized educational reference acquisition',
          source_url: streamUrl,
          evidence_details: ['SHA-256 hash verified', 'PDF structure validated by pypdf'],
          verified_at: item.downloaded_at,
          intended_use: 'educational_reference_acquisition',
          is_legally_downloadable: true,
        },
        missing_or_conflicting_metadata: [],
        is_approximate_suggestion: false,
        is_demo_data: false,
      };
      onOpenReader(cand);
    } else {
      window.open(`/api/downloads/library/${encodeURIComponent(item.job_id)}/stream`, '_blank');
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn max-w-6xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 mb-2">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Centralized Storage &amp; Integrity Provenance</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight">
            Download <span className="text-emerald-600 dark:text-emerald-400">Library</span>
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Locally acquired and verified digital books organized hierarchically by syllabus course or individual search.
          </p>
        </div>

        <button
          onClick={fetchLibrary}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 transition-colors shadow-xs self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
            <FolderDown className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Acquired Volumes
            </span>
            <p className="text-xl font-extrabold text-slate-900 dark:text-slate-100">
              {items.length} Books
            </p>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
            <HardDrive className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Storage Utilized
            </span>
            <p className="text-xl font-extrabold text-slate-900 dark:text-slate-100">
              {formatBytes(totalBytes)}
            </p>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-purple-50 dark:bg-purple-950/50 border border-purple-200 dark:border-purple-800 flex items-center justify-center text-purple-600 dark:text-purple-400">
            <GraduationCap className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Syllabus Curricula
            </span>
            <p className="text-xl font-extrabold text-slate-900 dark:text-slate-100">
              {items.filter((it) => it.syllabus_name).length} Books
            </p>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <button
            onClick={() => setFilterSource('ALL')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-colors ${
              filterSource === 'ALL'
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900'
            }`}
          >
            All Downloads ({items.length})
          </button>
          <button
            onClick={() => setFilterSource('SYLLABUS')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-colors ${
              filterSource === 'SYLLABUS'
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900'
            }`}
          >
            Syllabus Books ({items.filter((it) => it.syllabus_name).length})
          </button>
          <button
            onClick={() => setFilterSource('INDIVIDUAL')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-colors ${
              filterSource === 'INDIVIDUAL'
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900'
            }`}
          >
            Individual Searches ({items.filter((it) => !it.syllabus_name).length})
          </button>
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by title, author, or subject..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-emerald-500"
          />
        </div>
      </div>

      {/* Library Items List */}
      {isLoading ? (
        <div className="p-12 text-center rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-500 text-xs">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-500" />
          <span>Loading verified files from local library...</span>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="p-12 text-center rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-500 space-y-3 shadow-sm">
          <FolderDown className="w-12 h-12 mx-auto text-emerald-500/50" />
          <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
            No Downloaded Books in Library
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
            Authorized PDF or EPUB books acquired from Syllabus Finder or Book Discovery will automatically
            appear here with cryptographic SHA-256 integrity verification.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredItems.map((item) => (
            <div
              key={item.id}
              className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm hover:border-emerald-300 dark:hover:border-emerald-800 transition-all flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
            >
              <div className="space-y-2 flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="text-base font-bold text-slate-900 dark:text-slate-100 break-words">
                    {item.title}
                  </h4>
                  <span className="px-2 py-0.5 text-[10px] font-mono font-bold rounded-md bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 uppercase shrink-0">
                    .{item.format}
                  </span>
                  <span className="px-2 py-0.5 text-[10px] font-semibold rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 shrink-0">
                    {item.provider}
                  </span>
                  <span className="px-2 py-0.5 text-[10px] font-semibold rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 shrink-0">
                    {formatBytes(item.file_size_bytes)}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
                  {item.authors && item.authors.length > 0 && (
                    <span>
                      By <strong className="text-slate-700 dark:text-slate-200">{item.authors.join(', ')}</strong>
                    </span>
                  )}
                  {item.edition && <span>• {item.edition}</span>}
                  {item.publisher && <span>• {item.publisher}</span>}
                </div>

                {/* Storage Path & Context Hierarchy */}
                <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px] text-slate-500 dark:text-slate-400">
                  {item.syllabus_name ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 font-mono">
                      <GraduationCap className="w-3 h-3" />
                      <span>
                        {item.syllabus_name} / {item.semester || 'General'} / {item.subject || 'Reference'}
                      </span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-mono">
                      <span>downloads/Individual_Books</span>
                    </span>
                  )}

                  <div className="inline-flex items-center gap-1 font-mono text-[10px] text-slate-400">
                    <span>SHA: {item.file_hash.substring(0, 10)}...</span>
                    <button
                      onClick={() => handleCopyHash(item.file_hash)}
                      className="hover:text-emerald-500"
                      title="Copy full SHA-256 hash"
                    >
                      {copiedHash === item.file_hash ? (
                        <Check className="w-3 h-3 text-emerald-500" />
                      ) : (
                        <Copy className="w-3 h-3" />
                      )}
                    </button>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
                <button
                  onClick={() => handleReadInApp(item)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs transition-all active:scale-95"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  <span>Read in App</span>
                </button>

                <a
                  href={`/api/downloads/library/${encodeURIComponent(item.job_id)}/stream?download=true`}
                  download
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 transition-colors shadow-xs"
                >
                  <Download className="w-3.5 h-3.5 text-slate-500" />
                  <span>Save File</span>
                </a>

                <button
                  onClick={() => handleDelete(item.job_id, item.title)}
                  disabled={deletingId === item.job_id}
                  className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-xl transition-colors disabled:opacity-50"
                  title="Delete from library"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

