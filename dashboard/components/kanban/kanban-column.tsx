import { Badge } from '@/components/ui/badge';
import { TaskCard } from './task-card';
import { cn, COLUMN_COLORS, COLUMN_TITLES } from '@/lib/utils';
import type { KanbanTask, ColumnKey } from '@/lib/types';

interface KanbanColumnProps {
  columnKey: ColumnKey;
  tasks: KanbanTask[];
  count: number;
}

export function KanbanColumn({ columnKey, tasks, count }: KanbanColumnProps) {
  const colors = COLUMN_COLORS[columnKey];
  const title = COLUMN_TITLES[columnKey];

  return (
    <div className="flex flex-col min-w-0">
      {/* Column Header */}
      <div className="flex items-center gap-2 mb-3">
        <Badge className={cn('text-sm px-3 py-1 border-0', colors.badge)}>
          <span className={cn('w-2 h-2 rounded-full mr-2', colors.badgeDot)} />
          {title}
        </Badge>
        <span className={cn('text-sm font-medium', colors.countText)}>
          {count}
        </span>
      </div>

      {/* Task List Container */}
      <div className={cn('rounded-lg p-3 flex-1', colors.background)}>
        <div className="space-y-2">
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} />
          ))}
          {tasks.length === 0 && (
            <p className="text-xs text-muted-foreground text-center py-4">
              No tasks
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
