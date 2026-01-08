import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { CheckCircle } from 'lucide-react';
import type { CompletionRate } from '@/lib/types';

interface CompletionCardProps {
  data: CompletionRate;
}

export function CompletionCard({ data }: CompletionCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Completion Rate</CardTitle>
        <CheckCircle className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{data.percentage}%</div>
        <Progress value={data.percentage} className="mt-2" />
        <p className="text-xs text-muted-foreground mt-2">
          {data.tasks_completed} / {data.tasks_total} tasks
        </p>
      </CardContent>
    </Card>
  );
}
