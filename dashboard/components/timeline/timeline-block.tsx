'use client';

import { useMemo } from 'react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { TimelineBlock as TimelineBlockType } from '@/lib/types';

interface TimelineBlockProps {
  block: TimelineBlockType;
  startHour: number;
  totalHours: number;
  type: 'planned' | 'actual';
}

function timeToMinutes(time: string): number {
  const [hours, minutes] = time.split(':').map(Number);
  return hours * 60 + minutes;
}

export function TimelineBlock({
  block,
  startHour,
  totalHours,
  type,
}: TimelineBlockProps) {
  const { topPercent, heightPercent } = useMemo(() => {
    const startMinutes = timeToMinutes(block.start);
    const endMinutes = timeToMinutes(block.end);
    const dayStartMinutes = startHour * 60;
    const totalMinutes = totalHours * 60;

    const topMinutes = Math.max(0, startMinutes - dayStartMinutes);
    const durationMinutes = Math.max(15, endMinutes - startMinutes); // min 15 min

    return {
      topPercent: (topMinutes / totalMinutes) * 100,
      heightPercent: (durationMinutes / totalMinutes) * 100,
    };
  }, [block.start, block.end, startHour, totalHours]);

  const backgroundColor = block.genre_color || '#6b7280';
  const isPlanned = type === 'planned';

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              'absolute left-0 right-0 mx-0.5 rounded-sm overflow-hidden cursor-pointer',
              'hover:ring-2 hover:ring-white/50 transition-all',
              isPlanned ? 'opacity-60' : 'opacity-90'
            )}
            style={{
              top: `${topPercent}%`,
              height: `${heightPercent}%`,
              minHeight: '16px',
              backgroundColor,
              backgroundImage: isPlanned
                ? `repeating-linear-gradient(
                    45deg,
                    transparent,
                    transparent 4px,
                    rgba(255,255,255,0.1) 4px,
                    rgba(255,255,255,0.1) 8px
                  )`
                : undefined,
            }}
          >
            <div className="px-1 py-0.5 text-white text-[10px] md:text-xs truncate font-medium drop-shadow-sm">
              {block.task_name}
            </div>
          </div>
        </TooltipTrigger>
        <TooltipContent side="right" className="max-w-[200px]">
          <div className="space-y-1">
            <p className="font-medium">{block.task_name}</p>
            <p className="text-xs text-muted-foreground">
              {block.start} - {block.end}
            </p>
            <p className="text-xs">{isPlanned ? 'Planned' : 'Actual'}</p>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
