'use client';

import { KanbanColumn } from './kanban-column';
import { Loader2 } from 'lucide-react';
import type { KanbanResponse, ColumnKey } from '@/lib/types';

interface KanbanBoardProps {
  data: KanbanResponse | undefined;
  isLoading: boolean;
  error: Error | undefined;
}

const COLUMN_ORDER: ColumnKey[] = ['todo', 'doing', 'waiting', 'done'];

export function KanbanBoard({ data, isLoading, error }: KanbanBoardProps) {
  return (
    <div className="relative">
      {/* Loading Overlay */}
      {isLoading && !data && (
        <div className="fixed inset-0 bg-background/80 flex items-center justify-center z-10">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Loading...</span>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
          <p className="text-sm text-red-400">
            Failed to load kanban data: {error.message}
          </p>
        </div>
      )}

      {/* Kanban Columns */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 pb-4">
        {COLUMN_ORDER.map((columnKey) => (
          <KanbanColumn
            key={columnKey}
            columnKey={columnKey}
            tasks={data?.columns[columnKey] || []}
            count={data?.counts[columnKey] || 0}
          />
        ))}
      </div>
    </div>
  );
}
