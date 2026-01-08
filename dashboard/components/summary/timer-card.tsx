import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Timer } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { TimerInfo } from '@/lib/types';

interface TimerCardProps {
  data: TimerInfo;
}

export function TimerCard({ data }: TimerCardProps) {
  const formatTime = (minutes: number): string => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };

  return (
    <Card className={cn(data.is_running && 'ring-2 ring-green-500')}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Timer</CardTitle>
        <Timer
          className={cn(
            'h-4 w-4',
            data.is_running
              ? 'text-green-500 animate-pulse'
              : 'text-muted-foreground'
          )}
        />
      </CardHeader>
      <CardContent>
        {data.is_running ? (
          <>
            <div className="text-2xl font-bold text-green-500">
              {data.elapsed_minutes !== null
                ? formatTime(data.elapsed_minutes)
                : '0m'}
            </div>
            <p
              className="text-xs text-muted-foreground mt-2 truncate"
              title={data.task_name || ''}
            >
              {data.task_name || 'Unknown task'}
            </p>
          </>
        ) : (
          <>
            <div className="text-2xl font-bold text-muted-foreground">
              Stopped
            </div>
            <p className="text-xs text-muted-foreground mt-2">No active timer</p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
