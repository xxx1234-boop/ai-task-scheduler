'use client';

import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight, Calendar } from 'lucide-react';

interface WeeklyTimelineHeaderProps {
  weekStart: string;
  weekEnd: string;
  onPreviousWeek: () => void;
  onNextWeek: () => void;
  onToday: () => void;
}

export function WeeklyTimelineHeader({
  weekStart,
  weekEnd,
  onPreviousWeek,
  onNextWeek,
  onToday,
}: WeeklyTimelineHeaderProps) {
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('ja-JP', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="flex items-center justify-between py-1 md:py-2 shrink-0">
      <div className="flex items-center gap-1 md:gap-2">
        <Button variant="outline" size="sm" onClick={onPreviousWeek} className="h-7 md:h-8 px-2">
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <Button variant="outline" size="sm" onClick={onToday} className="h-7 md:h-8 px-2">
          <Calendar className="h-4 w-4 md:mr-1" />
          <span className="hidden md:inline">Today</span>
        </Button>
        <Button variant="outline" size="sm" onClick={onNextWeek} className="h-7 md:h-8 px-2">
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
      <div className="text-xs md:text-sm font-medium">
        {formatDate(weekStart)} - {formatDate(weekEnd)}
      </div>
      <div className="hidden md:flex items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <div
            className="w-3 h-3 bg-gray-500 opacity-60 rounded-sm"
            style={{
              backgroundImage: `repeating-linear-gradient(45deg, transparent, transparent 2px, rgba(255,255,255,0.2) 2px, rgba(255,255,255,0.2) 4px)`,
            }}
          />
          <span>Planned</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-gray-500 opacity-90 rounded-sm" />
          <span>Actual</span>
        </div>
      </div>
    </div>
  );
}
