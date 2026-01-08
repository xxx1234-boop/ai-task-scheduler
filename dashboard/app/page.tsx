'use client';

import { useState } from 'react';
import { Header } from '@/components/header';
import { KanbanBoard } from '@/components/kanban/kanban-board';
import { useKanban } from '@/hooks/use-kanban';

export default function Home() {
  const [autoRefresh, setAutoRefresh] = useState(true);
  const { data, error, isLoading, totalCount, refresh } = useKanban(autoRefresh);

  return (
    <div className="min-h-screen">
      <Header
        totalCount={totalCount}
        autoRefresh={autoRefresh}
        onAutoRefreshChange={setAutoRefresh}
        onRefresh={refresh}
        isLoading={isLoading}
      />
      <main className="p-6">
        <KanbanBoard data={data} isLoading={isLoading} error={error} />
      </main>
    </div>
  );
}
