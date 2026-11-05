'use client';

import React from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, ShieldAlert } from 'lucide-react';
import { ProviderStatus } from '@/types/book';

interface ProviderStatusPillsProps {
  statuses: ProviderStatus[];
}

export const ProviderStatusPills: React.FC<ProviderStatusPillsProps> = ({ statuses }) => {
  if (!statuses || statuses.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <span className="text-slate-500 dark:text-slate-400 font-semibold text-[11px] uppercase tracking-wider">
        Discovery Sources:
      </span>
      {statuses.map((ps, idx) => {
        let badgeColor =
          'bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300';
        let Icon = CheckCircle2;

        if (ps.status === 'SUCCESS') {
          badgeColor =
            'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300';
          Icon = CheckCircle2;
        } else if (ps.status === 'RATE_LIMITED') {
          badgeColor =
            'bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-300';
          Icon = AlertTriangle;
        } else if (ps.status === 'NO_RESULTS') {
          badgeColor =
            'bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400';
          Icon = AlertCircle;
        } else {
          badgeColor =
            'bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300';
          Icon = ShieldAlert;
        }

        return (
          <div
            key={idx}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium shadow-xs ${badgeColor}`}
            title={ps.message || `${ps.provider_name}: ${ps.status} (${ps.results_count} records)`}
          >
            <Icon className="w-3 h-3 shrink-0" />
            <span className="font-semibold">{ps.provider_name}</span>
            <span className="opacity-80">
              {ps.status === 'SUCCESS' ? `(${ps.results_count})` : ps.status}
            </span>
          </div>
        );
      })}
    </div>
  );
};
