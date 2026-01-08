'use client';

import { useState, useCallback } from 'react';
import { WeeklyTimeline, WeeklyTimelineHeader } from '@/components/timeline';
import { useWeeklyTimeline } from '@/hooks/use-weekly-timeline';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { RefreshCw, Loader2 } from 'lucide-react';
import { ModeToggle } from '@/components/mode-toggle';
import { AccentSelector } from '@/components/accent-selector';
import { SidebarTrigger } from '@/components/ui/sidebar';
import { Separator } from '@/components/ui/separator';

export default function WeeklyPage() {
  const [weekStart, setWeekStart] = useState<string | undefined>(undefined);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const { data, error, isLoading, refresh } = useWeeklyTimeline({
    weekStart,
    autoRefresh,
  });

  const handlePreviousWeek = useCallback(() => {
    if (data) {
      const prev = new Date(data.week_start);
      prev.setDate(prev.getDate() - 7);
      setWeekStart(prev.toISOString().split('T')[0]);
    }
  }, [data]);

  const handleNextWeek = useCallback(() => {
    if (data) {
      const next = new Date(data.week_start);
      next.setDate(next.getDate() + 7);
      setWeekStart(next.toISOString().split('T')[0]);
    }
  }, [data]);

  const handleToday = useCallback(() => {
    setWeekStart(undefined); // Reset to current week
  }, []);

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <header className="border-b bg-card/50 px-3 md:px-4 py-2 md:py-3 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-2 h-4" />
            <h1 className="text-lg md:text-xl font-bold">Weekly Timeline</h1>
          </div>
          <div className="flex items-center gap-2 md:gap-4">
            <div className="hidden md:flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Auto-refresh</span>
              <Switch checked={autoRefresh} onCheckedChange={setAutoRefresh} />
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={refresh}
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              <span className="hidden md:inline ml-2">Refresh</span>
            </Button>
            <div className="flex items-center gap-2 border-l pl-2 md:pl-4">
              <AccentSelector />
              <ModeToggle />
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 p-3 md:p-4 flex flex-col min-h-0 overflow-hidden">
        {data && (
          <WeeklyTimelineHeader
            weekStart={data.week_start}
            weekEnd={data.week_end}
            onPreviousWeek={handlePreviousWeek}
            onNextWeek={handleNextWeek}
            onToday={handleToday}
          />
        )}
        <div className="flex-1 mt-2 md:mt-3 min-h-0">
          <WeeklyTimeline data={data} isLoading={isLoading} error={error} />
        </div>
      </main>
    </div>
  );
}
