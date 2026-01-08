'use client';

import { useMemo } from 'react';
import { TimelineBlock } from './timeline-block';
import { cn } from '@/lib/utils';
import type { WeeklyTimelineDay } from '@/lib/types';

interface TimelineGridProps {
  days: WeeklyTimelineDay[];
  startHour: number;
  endHour: number;
}

export function TimelineGrid({ days, startHour, endHour }: TimelineGridProps) {
  const hours = useMemo(() => {
    const result = [];
    for (let h = startHour; h < endHour; h++) {
      result.push(h);
    }
    return result;
  }, [startHour, endHour]);

  const totalHours = hours.length;

  return (
    <div className="flex flex-col h-full overflow-hidden border rounded-lg bg-card">
      {/* Day Headers */}
      <div className="flex border-b bg-card z-20 shrink-0">
        {/* Time column spacer */}
        <div className="w-10 md:w-14 shrink-0 border-r bg-muted/30" />

        {/* Day columns */}
        {days.map((day) => (
          <div
            key={day.date}
            className={cn(
              'flex-1 min-w-0 border-r last:border-r-0 py-1 md:py-2 text-center',
              day.is_today && 'bg-accent/10'
            )}
          >
            <div className="text-[10px] md:text-xs text-muted-foreground">
              {day.day_of_week}
            </div>
            <div
              className={cn(
                'text-xs md:text-sm font-medium',
                day.is_today && 'text-accent-foreground'
              )}
            >
              {new Date(day.date).getDate()}
            </div>
          </div>
        ))}
      </div>

      {/* Time Grid - flex-1 to use remaining height */}
      <div className="flex flex-1 min-h-0">
        {/* Time labels column */}
        <div className="w-10 md:w-14 shrink-0 border-r relative bg-muted/30">
          {hours.map((hour, index) => (
            <div
              key={hour}
              className="absolute w-full text-[9px] md:text-xs text-muted-foreground text-right pr-1 md:pr-2"
              style={{
                top: `${(index / totalHours) * 100}%`,
                transform: 'translateY(-50%)',
              }}
            >
              {hour}
            </div>
          ))}
        </div>

        {/* Day columns with blocks */}
        {days.map((day) => (
          <div
            key={day.date}
            className={cn(
              'flex-1 min-w-0 border-r last:border-r-0 relative',
              day.is_today && 'bg-accent/5'
            )}
          >
            {/* Hour grid lines */}
            {hours.map((_, index) => (
              <div
                key={index}
                className="absolute w-full border-t border-border/50"
                style={{ top: `${(index / totalHours) * 100}%` }}
              />
            ))}

            {/* Planned blocks (left half) */}
            <div className="absolute inset-y-0 left-0 w-1/2 pr-px">
              {day.planned.map((block, index) => (
                <TimelineBlock
                  key={`planned-${index}`}
                  block={block}
                  startHour={startHour}
                  totalHours={totalHours}
                  type="planned"
                />
              ))}
            </div>

            {/* Actual blocks (right half) */}
            <div className="absolute inset-y-0 right-0 w-1/2 pl-px">
              {day.actual.map((block, index) => (
                <TimelineBlock
                  key={`actual-${index}`}
                  block={block}
                  startHour={startHour}
                  totalHours={totalHours}
                  type="actual"
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
