import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Calendar } from 'lucide-react';
import type { TodayBasicSummary } from '@/lib/types';

interface TodayCardProps {
  data: TodayBasicSummary;
}

export function TodayCard({ data }: TodayCardProps) {
  const planned = Number(data.planned_hours) || 0;
  const actual = Number(data.actual_hours) || 0;
  const progress = planned > 0 ? Math.min((actual / planned) * 100, 100) : 0;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Today</CardTitle>
        <Calendar className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">
          {actual.toFixed(1)}h / {planned.toFixed(1)}h
        </div>
        <Progress value={progress} className="mt-2" />
        <p className="text-xs text-muted-foreground mt-2">
          {data.tasks_scheduled} tasks scheduled
        </p>
      </CardContent>
    </Card>
  );
}
