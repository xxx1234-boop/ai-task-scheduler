'use client';

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { PieChart } from 'lucide-react';
import type { TimeDistribution } from '@/lib/types';
import { cn } from '@/lib/utils';

interface DistributionChartProps {
  data: TimeDistribution;
}

const COLORS = [
  'bg-blue-500',
  'bg-green-500',
  'bg-yellow-500',
  'bg-purple-500',
  'bg-pink-500',
  'bg-orange-500',
  'bg-cyan-500',
  'bg-red-500',
];

export function DistributionChart({ data }: DistributionChartProps) {
  return (
    <Card className="col-span-full lg:col-span-2">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base font-medium">Time Distribution</CardTitle>
        <PieChart className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="text-sm font-medium mb-3">By Genre</h4>
            <div className="space-y-2">
              {data.by_genre.map((item, index) => (
                <div key={item.name} className="flex items-center gap-2">
                  <div
                    className={cn(
                      'w-3 h-3 rounded-sm',
                      COLORS[index % COLORS.length]
                    )}
                  />
                  <span className="text-sm flex-1 truncate">{item.name}</span>
                  <span className="text-sm text-muted-foreground">
                    {Number(item.hours).toFixed(1)}h ({item.percentage}%)
                  </span>
                </div>
              ))}
              {data.by_genre.length === 0 && (
                <p className="text-sm text-muted-foreground">No data</p>
              )}
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium mb-3">By Project</h4>
            <div className="space-y-2">
              {data.by_project.map((item, index) => (
                <div key={item.name} className="flex items-center gap-2">
                  <div
                    className={cn(
                      'w-3 h-3 rounded-sm',
                      COLORS[index % COLORS.length]
                    )}
                  />
                  <span className="text-sm flex-1 truncate">{item.name}</span>
                  <span className="text-sm text-muted-foreground">
                    {Number(item.hours).toFixed(1)}h ({item.percentage}%)
                  </span>
                </div>
              ))}
              {data.by_project.length === 0 && (
                <p className="text-sm text-muted-foreground">No data</p>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
