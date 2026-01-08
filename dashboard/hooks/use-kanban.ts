'use client';

import useSWR from 'swr';
import type { KanbanResponse } from '@/lib/types';

const fetcher = async (url: string): Promise<KanbanResponse> => {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error('Failed to fetch kanban data');
  }
  return res.json();
};

export function useKanban(autoRefresh: boolean = true) {
  const { data, error, isLoading, mutate } = useSWR<KanbanResponse>(
    '/api/kanban',
    fetcher,
    {
      refreshInterval: autoRefresh ? 30000 : 0,
      revalidateOnFocus: false,
    }
  );

  const totalCount = data
    ? data.counts.todo + data.counts.doing + data.counts.waiting + data.counts.done
    : 0;

  return {
    data,
    error,
    isLoading,
    totalCount,
    refresh: () => mutate(),
  };
}
