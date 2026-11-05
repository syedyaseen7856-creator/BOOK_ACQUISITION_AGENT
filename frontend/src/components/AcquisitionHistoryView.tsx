'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  History,
  Download,
  ShieldCheck,
  Search,
  Copy,
  Check,
  RefreshCw,
  ExternalLink,
  Filter,
  FileCheck,
  Lock,
} from 'lucide-react';
import { AcquisitionHistoryItem } from '@/types/book';
import { getAcquisitionHistory } from '@/lib/api';

export const AcquisitionHistoryView: React.FC = () => {
  const [records, setRecords] = useState<AcquisitionHistoryItem[]>([]);
  const [recordType, setRecordType] = useState<string>('');
  const [status, setStatus] = useState<string>('');
  const [searchFilter, setSearchFilter] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  const handleRefresh = useCallback(async () => {
    setIsLoading(true);
    try {
      const resp = await getAcquisitionHistory(recordType || undefined, status || undefined);
      setRecords(resp.records);
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  }, [recordType, status]);

  useEffect(() => {
    let active = true;
    getAcquisitionHistory(recordType || undefined, status || undefined)
      .then((resp) => {
        if (active) {
          setRecords(resp.records);
          setIsLoading(false);
        }
      })
      .catch(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [recordType, status]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(text);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const filteredRecords = records.filter((r) => {
    if (!searchFilter.trim()) return true;
    const q = searchFilter.toLowerCase();
    return (
      r.title.toLowerCase().includes(q) ||
      (r.author && r.author.toLowerCase().includes(q)) ||
      r.source.toLowerCase().includes(q) ||
      (r.file_hash && r.file_hash.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto animate-fadeIn">
      {/* Header Banner */}
      <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            <h2 className="text-xl font-extrabold text-slate-900 dark:text-slate-100">
              Acquisition &amp; Audit History
            </h2>
            <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
              {records.length} Records
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Tamper-evident persistent log of all real searches, human licensing approvals, and SHA-256 validated downloads.
          </p>
        </div>

        <button
          onClick={handleRefresh}
          disabled={isLoading}
          className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 transition-colors self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-indigo-600' : ''}`} />
          <span>Refresh Ledger</span>
        </button>
      </div>

      {/* Filter Tabs & Search */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs shadow-sm">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-slate-500 font-semibold mr-1 flex items-center gap-1 text-[11px]">
            <Filter className="w-3 h-3" /> Type:
          </span>
          {[
            ['', 'All Records'],
            ['DOWNLOAD', 'Downloads'],
            ['APPROVAL', 'Approvals'],
            ['SEARCH', 'Searches'],
          ].map(([val, label]) => (
            <button
              key={val}
              onClick={() => setRecordType(val)}
              className={`px-3 py-1 rounded-xl text-xs font-medium transition-colors ${
                recordType === val
                  ? 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 font-bold'
                  : 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 border border-slate-200 dark:border-slate-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400 pointer-events-none" />
            <input
              type="text"
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              placeholder="Filter by title, hash..."
              className="pl-7 pr-3 py-1 text-xs rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="px-2.5 py-1 text-xs rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Statuses</option>
            <option value="COMPLETED">Completed</option>
            <option value="ACTIVE">Active Approval</option>
            <option value="EXPIRED">Expired</option>
            <option value="FAILED">Failed</option>
          </select>
        </div>
      </div>

      {/* History Table */}
      <div className="rounded-3xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
        {filteredRecords.length === 0 ? (
          <div className="p-12 text-center text-slate-500 space-y-2">
            <History className="w-10 h-10 mx-auto text-slate-400" />
            <p className="text-sm font-semibold">No audit records found matching the criteria.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800 uppercase tracking-wider font-semibold">
                <tr>
                  <th className="py-3 px-4">Event Type</th>
                  <th className="py-3 px-4">Book Title &amp; Details</th>
                  <th className="py-3 px-4">Source / Target</th>
                  <th className="py-3 px-4">SHA-256 Hash</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                {filteredRecords.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors">
                    {/* Event Type */}
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md font-bold text-[11px] ${
                          r.record_type === 'DOWNLOAD'
                            ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                            : r.record_type === 'APPROVAL'
                            ? 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800'
                            : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
                        }`}
                      >
                        {r.record_type === 'DOWNLOAD' && <Download className="w-3 h-3" />}
                        {r.record_type === 'APPROVAL' && <ShieldCheck className="w-3 h-3" />}
                        {r.record_type === 'SEARCH' && <Search className="w-3 h-3" />}
                        <span>{r.record_type}</span>
                      </span>
                    </td>

                    {/* Title & Author */}
                    <td className="py-3 px-4 max-w-xs truncate">
                      <p className="font-bold text-slate-900 dark:text-slate-100 truncate">{r.title}</p>
                      {r.author && <p className="text-[11px] text-slate-500 truncate">{r.author}</p>}
                    </td>

                    {/* Source */}
                    <td className="py-3 px-4 max-w-xs truncate text-[11px] text-slate-500">
                      {r.source.startsWith('http') ? (
                        <a
                          href={r.source}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 truncate"
                        >
                          <span className="truncate">{new URL(r.source).hostname}</span>
                          <ExternalLink className="w-3 h-3 shrink-0" />
                        </a>
                      ) : (
                        <span>{r.source}</span>
                      )}
                    </td>

                    {/* SHA-256 Hash */}
                    <td className="py-3 px-4 whitespace-nowrap">
                      {r.file_hash ? (
                        <button
                          onClick={() => copyToClipboard(r.file_hash!)}
                          className="flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-indigo-400 font-mono text-[10px] text-indigo-600 dark:text-indigo-400"
                          title="Click to copy full cryptographic SHA-256 hash"
                        >
                          <span>{r.file_hash.substring(0, 10)}...</span>
                          {copiedHash === r.file_hash ? (
                            <Check className="w-3 h-3 text-emerald-600" />
                          ) : (
                            <Copy className="w-3 h-3 text-slate-400" />
                          )}
                        </button>
                      ) : (
                        <span className="text-slate-400 font-mono">—</span>
                      )}
                    </td>

                    {/* Status */}
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-0.5 text-[10px] font-bold rounded-full ${
                          r.status === 'COMPLETED' || r.status === 'ACTIVE'
                            ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                            : r.status === 'EXPIRED'
                            ? 'bg-slate-100 dark:bg-slate-800 text-slate-500 border border-slate-200 dark:border-slate-700'
                            : 'bg-rose-50 dark:bg-rose-950/50 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
                        }`}
                      >
                        {r.status}
                      </span>
                    </td>

                    {/* Timestamp */}
                    <td className="py-3 px-4 whitespace-nowrap text-[11px] text-slate-500 font-mono">
                      {new Date(r.timestamp).toLocaleDateString()} {new Date(r.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
