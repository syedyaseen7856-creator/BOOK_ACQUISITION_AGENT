'use client';

import React, { useEffect, useState, useCallback } from 'react';
import {
  X,
  History,
  ExternalLink,
  Calendar,
  FileCheck,
  RotateCw,
  AlertCircle,
} from 'lucide-react';
import { ApprovalRecord } from '@/types/book';
import { getApprovals } from '@/lib/api';

interface AuditDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onRefresh: () => void;
}

export const AuditDrawer: React.FC<AuditDrawerProps> = ({
  isOpen,
  onClose,
  onRefresh,
}) => {
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAuditHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const records = await getApprovals();
      setApprovals(records);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load audit history');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    let active = true;

    getApprovals()
      .then((records) => {
        if (active) {
          setApprovals(records);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : 'Failed to load audit history');
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-950/80 backdrop-blur-xs flex justify-end animate-in fade-in duration-150">
      <div className="relative w-full max-w-xl bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col h-full animate-in slide-in-from-right duration-200">
        {/* Drawer Header */}
        <div className="px-6 py-4 border-b border-slate-800 bg-slate-950/80 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-cyan-950/80 text-cyan-400 border border-cyan-800/60">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">
                Persistent Audit Ledger
              </h2>
              <p className="text-xs text-slate-400">
                Verifiable acquisition history &amp; cryptographic hashes
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                loadAuditHistory();
                onRefresh();
              }}
              className="p-2 text-slate-400 hover:text-cyan-400 hover:bg-slate-800 rounded-lg transition-colors"
              title="Refresh ledger"
            >
              <RotateCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Drawer Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 text-xs text-slate-300">
          {loading && approvals.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-500 space-y-3">
              <RotateCw className="w-6 h-6 animate-spin text-cyan-400" />
              <span>Querying audit ledger database...</span>
            </div>
          ) : error ? (
            <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 flex items-start gap-2.5">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          ) : approvals.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center space-y-3">
              <div className="w-14 h-14 rounded-2xl bg-slate-950 border border-slate-800 flex items-center justify-center text-slate-600">
                <FileCheck className="w-7 h-7" />
              </div>
              <h3 className="text-sm font-semibold text-slate-300">
                No Acquisition Approvals Recorded Yet
              </h3>
              <p className="text-xs text-slate-500 max-w-xs">
                When you explicitly approve an eligible book candidate for download, the cryptographic
                hash, licensing evidence, and provenance will be immutably recorded here.
              </p>
            </div>
          ) : (
            approvals.map((rec) => (
              <div
                key={rec.approval_id}
                className="p-4 rounded-xl bg-slate-950/80 border border-slate-800/90 space-y-3 shadow-md"
              >
                <div className="flex justify-between items-start gap-2">
                  <div>
                    <h3 className="text-sm font-bold text-slate-100">
                      {rec.book_title}
                    </h3>
                    <p className="text-slate-400 text-[11px]">
                      {rec.book_authors?.join(', ') || 'Unknown Author'}
                    </p>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                      rec.licensing_status === 'VERIFIED_FOR_PERMITTED_DOWNLOAD'
                        ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                        : 'bg-slate-800 text-slate-300 border-slate-700'
                    }`}
                  >
                    {rec.licensing_status}
                  </span>
                </div>

                <div className="space-y-1 font-mono text-[11px] text-slate-400 bg-slate-900/90 p-2.5 rounded-lg border border-slate-800">
                  <div className="flex justify-between items-center text-[10px] text-slate-500 font-sans pb-1 border-b border-slate-800">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {new Date(rec.approved_at).toLocaleString()}
                    </span>
                    <span>Approval ID: {rec.approval_id.slice(0, 8)}...</span>
                  </div>

                  <div className="pt-1 truncate">
                    <span className="text-slate-500 font-sans text-[10px] block">
                      Metadata Snapshot SHA-256:
                    </span>
                    <span className="text-cyan-400 text-[10px] select-all">
                      {rec.snapshot_hash}
                    </span>
                  </div>

                  {rec.file_hash && (
                    <div className="truncate">
                      <span className="text-slate-500 font-sans text-[10px] block">
                        Acquired File SHA-256:
                      </span>
                      <span className="text-emerald-400 text-[10px] select-all">
                        {rec.file_hash}
                      </span>
                    </div>
                  )}

                  {rec.file_size_bytes && (
                    <div className="text-[10px] text-slate-400 font-sans">
                      Verified Payload: {(rec.file_size_bytes / 1024).toFixed(1)} KB
                    </div>
                  )}
                </div>

                {rec.user_note && (
                  <p className="text-[11px] text-slate-400 italic">
                    Note: &ldquo;{rec.user_note}&rdquo;
                  </p>
                )}

                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
                  <a
                    href={rec.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-slate-400 hover:text-cyan-400 transition-colors"
                  >
                    <ExternalLink className="w-3 h-3" />
                    <span>View Repository Source</span>
                  </a>
                  <span className="text-emerald-400 font-medium">Recorded</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
