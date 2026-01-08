'use client';

import useSWR from 'swr';
import type { WeeklyTimelineResponse } from '@/lib/types';

const fetcher = async (url: string): Promise<WeeklyTimelineResponse> => {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error('Failed to fetch weekly timeline data');
  }
  return res.json();
};

interface UseWeeklyTimelineOptions {
  weekStart?: string;  // ISO date string for week start
  startHour?: number;
  endHour?: number;
  autoRefresh?: boolean;
}

export function useWeeklyTimeline({
  weekStart,
  startHour = 6,
  endHour = 24,
  autoRefresh = true,
}: UseWeeklyTimelineOptions = {}) {
  // Build query string
  const params = new URLSearchParams();
  if (weekStart) params.set('week_start', weekStart);
  if (startHour !== 6) params.set('start_hour', String(startHour));
  if (endHour !== 24) params.set('end_hour', String(endHour));

  const queryString = params.toString();
  const url = `/api/weekly-timeline${queryString ? `?${queryString}` : ''}`;

  const { data, error, isLoading, mutate } = useSWR<WeeklyTimelineResponse>(
    url,
    fetcher,
    {
      refreshInterval: autoRefresh ? 60000 : 0,  // 1 minute refresh
      revalidateOnFocus: false,
    }
  );

  return {
    data,
    error,
    isLoading,
    refresh: () => mutate(),
  };
}
