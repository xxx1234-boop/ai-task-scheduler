'use client';

import { TimelineGrid } from './timeline-grid';
import { Loader2 } from 'lucide-react';
import type { WeeklyTimelineResponse } from '@/lib/types';

interface WeeklyTimelineProps {
  data: WeeklyTimelineResponse | undefined;
  isLoading: boolean;
  error: Error | undefined;
}

export function WeeklyTimeline({
  data,
  isLoading,
  error,
}: WeeklyTimelineProps) {
  return (
    <div className="relative h-full flex flex-col">
      {/* Loading Overlay */}
      {isLoading && !data && (
        <div className="absolute inset-0 bg-background/80 flex items-center justify-center z-10">
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
            Failed to load timeline: {error.message}
          </p>
        </div>
      )}

      {/* Timeline Content */}
      {data && (
        <div className="flex-1 min-h-0">
          <TimelineGrid
            days={data.days}
            startHour={data.start_hour}
            endHour={data.end_hour}
          />
        </div>
      )}
    </div>
  );
}
