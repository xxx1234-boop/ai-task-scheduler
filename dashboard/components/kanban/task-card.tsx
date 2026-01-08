import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from '@/components/ui/popover';
import { Timer } from 'lucide-react';
import { cn, PRIORITY_COLORS } from '@/lib/utils';
import type { KanbanTask } from '@/lib/types';
import ReactMarkdown from 'react-markdown';

interface TaskCardProps {
  task: KanbanTask;
}

export function TaskCard({ task }: TaskCardProps) {
  const priorityClass = PRIORITY_COLORS[task.priority] || PRIORITY_COLORS['中'];
  const actualHours = Number(task.actual_hours) || 0;
  const estimatedHours =
    task.estimated_hours !== null ? Number(task.estimated_hours) : null;
  const hasBlockers = task.blocked_by && task.blocked_by.length > 0;
  const hasFooter = task.deadline || hasBlockers;
  const hasDescription = task.description && task.description.trim() !== '';

  const cardContent = (
    <Card
      className={cn(
        'overflow-hidden cursor-pointer',
        task.is_timer_running && 'ring-2 ring-green-500'
      )}
      style={{
        borderLeftWidth: '4px',
        borderLeftColor: task.genre_color || '#6b7280',
      }}
    >
      <CardHeader className="p-4 pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle
            className="text-sm font-medium leading-tight truncate flex-1"
            title={task.name}
          >
            {task.name}
          </CardTitle>
          {task.is_timer_running && (
            <Timer className="h-4 w-4 text-green-500 animate-pulse shrink-0" />
          )}
        </div>
        {task.project_name && (
          <CardDescription className="text-xs truncate">
            {task.project_name}
          </CardDescription>
        )}
      </CardHeader>

      <CardContent className="p-4 pt-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1">
            <Badge className={cn('text-xs border', priorityClass)}>
              {task.priority}
            </Badge>
            {task.genre_name && (
              <Badge
                variant="outline"
                className="text-xs"
                style={{ borderColor: task.genre_color || undefined }}
              >
                {task.genre_name}
              </Badge>
            )}
          </div>
          <span className="text-xs text-muted-foreground">
            {actualHours.toFixed(1)}h
            {estimatedHours !== null && ` / ${estimatedHours.toFixed(1)}h`}
          </span>
        </div>
      </CardContent>

      {hasFooter && (
        <CardFooter className="p-4 pt-0 flex-col items-start gap-2">
          {task.deadline && (
            <p className="text-xs text-muted-foreground">
              Due: {new Date(task.deadline).toLocaleDateString('ja-JP')}
            </p>
          )}
          {hasBlockers && (
            <div className="w-full p-2 bg-muted rounded border border-border">
              <p className="text-xs text-foreground font-medium mb-1">
                Blocked by:
              </p>
              {task.blocked_by!.map((blocker, index) => (
                <p
                  key={index}
                  className="text-xs text-muted-foreground truncate"
                >
                  {blocker}
                </p>
              ))}
            </div>
          )}
        </CardFooter>
      )}
    </Card>
  );

  if (!hasDescription) {
    return cardContent;
  }

  return (
    <Popover>
      <PopoverTrigger asChild>{cardContent}</PopoverTrigger>
      <PopoverContent className="w-80 max-h-96 overflow-auto" side="right">
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown>{task.description}</ReactMarkdown>
        </div>
      </PopoverContent>
    </Popover>
  );
}
