import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Repeat, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ContextSwitches } from '@/lib/types';

interface ContextSwitchesCardProps {
  data: ContextSwitches;
}

export function ContextSwitchesCard({ data }: ContextSwitchesCardProps) {
  const TrendIcon = {
    increasing: TrendingUp,
    decreasing: TrendingDown,
    stable: Minus,
  }[data.trend];

  const trendColor = {
    increasing: 'text-red-500',
    decreasing: 'text-green-500',
    stable: 'text-muted-foreground',
  }[data.trend];

  const trendLabel = {
    increasing: 'Increasing',
    decreasing: 'Decreasing',
    stable: 'Stable',
  }[data.trend];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Context Switches</CardTitle>
        <Repeat className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">
          {Number(data.average_per_day).toFixed(1)}
        </div>
        <p className="text-xs text-muted-foreground">per day average</p>
        <div className={cn('flex items-center gap-1 mt-2', trendColor)}>
          <TrendIcon className="h-4 w-4" />
          <span className="text-xs">{trendLabel}</span>
        </div>
      </CardContent>
    </Card>
  );
}
