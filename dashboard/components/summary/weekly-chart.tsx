'use client';

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { BarChart3 } from 'lucide-react';
import type { DailyData } from '@/lib/types';

interface WeeklyChartProps {
  data: DailyData[];
}

export function WeeklyChart({ data }: WeeklyChartProps) {
  const maxHours = Math.max(
    ...data.flatMap((d) => [Number(d.planned_hours), Number(d.actual_hours)]),
    8
  );

  return (
    <Card className="col-span-full lg:col-span-2">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base font-medium">Weekly Hours</CardTitle>
        <BarChart3 className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="flex items-end justify-between gap-2 h-48">
          {data.map((day) => {
            const planned = Number(day.planned_hours) || 0;
            const actual = Number(day.actual_hours) || 0;
            const plannedHeight = (planned / maxHours) * 100;
            const actualHeight = (actual / maxHours) * 100;

            return (
              <div
                key={day.date}
                className="flex-1 flex flex-col items-center gap-1"
              >
                <div className="w-full flex items-end justify-center gap-1 h-40">
                  <div
                    className="w-3 bg-muted rounded-t transition-all"
                    style={{ height: `${plannedHeight}%` }}
                    title={`Planned: ${planned.toFixed(1)}h`}
                  />
                  <div
                    className="w-3 bg-primary rounded-t transition-all"
                    style={{ height: `${actualHeight}%` }}
                    title={`Actual: ${actual.toFixed(1)}h`}
                  />
                </div>
                <span className="text-xs text-muted-foreground">{day.day}</span>
              </div>
            );
          })}
        </div>
        <div className="flex justify-center gap-4 mt-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-muted rounded" />
            <span className="text-xs text-muted-foreground">Planned</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-primary rounded" />
            <span className="text-xs text-muted-foreground">Actual</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
