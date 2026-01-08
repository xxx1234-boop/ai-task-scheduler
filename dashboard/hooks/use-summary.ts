'use client';

import useSWR from 'swr';
import type { SummaryResponse, StatsResponse, WeeklyResponse } from '@/lib/types';

const fetcher = async <T>(url: string): Promise<T> => {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error('Failed to fetch data');
  }
  return res.json();
};

interface UseSummaryOptions {
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function useSummary({
  autoRefresh = true,
  refreshInterval = 60000,
}: UseSummaryOptions = {}) {
  const summaryResult = useSWR<SummaryResponse>(
    '/api/summary',
    fetcher,
    {
      refreshInterval: autoRefresh ? refreshInterval : 0,
      revalidateOnFocus: false,
    }
  );

  const statsResult = useSWR<StatsResponse>(
    '/api/stats?period=week',
    fetcher,
    {
      refreshInterval: autoRefresh ? refreshInterval : 0,
      revalidateOnFocus: false,
    }
  );

  const weeklyResult = useSWR<WeeklyResponse>(
    '/api/weekly',
    fetcher,
    {
      refreshInterval: autoRefresh ? refreshInterval : 0,
      revalidateOnFocus: false,
    }
  );

  const isLoading =
    summaryResult.isLoading || statsResult.isLoading || weeklyResult.isLoading;
  const error =
    summaryResult.error || statsResult.error || weeklyResult.error;

  const refresh = () => {
    summaryResult.mutate();
    statsResult.mutate();
    weeklyResult.mutate();
  };

  return {
    summary: summaryResult.data,
    stats: statsResult.data,
    weekly: weeklyResult.data,
    isLoading,
    error,
    refresh,
  };
}
