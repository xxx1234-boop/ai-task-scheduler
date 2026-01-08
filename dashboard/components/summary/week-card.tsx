import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { CalendarDays } from 'lucide-react';
import type { WeekBasicSummary } from '@/lib/types';

interface WeekCardProps {
  data: WeekBasicSummary;
}

export function WeekCard({ data }: WeekCardProps) {
  const planned = Number(data.planned_hours) || 0;
  const actual = Number(data.actual_hours) || 0;
  const target = Number(data.target_hours) || 40;
  const progress = target > 0 ? Math.min((actual / target) * 100, 100) : 0;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">This Week</CardTitle>
        <CalendarDays className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">
          {actual.toFixed(1)}h / {target.toFixed(0)}h
        </div>
        <Progress value={progress} className="mt-2" />
        <p className="text-xs text-muted-foreground mt-2">
          {planned.toFixed(1)}h planned
        </p>
      </CardContent>
    </Card>
  );
}
