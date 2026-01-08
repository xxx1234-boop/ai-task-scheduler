import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { UrgentSummary } from '@/lib/types';

interface UrgentCardProps {
  data: UrgentSummary;
}

export function UrgentCard({ data }: UrgentCardProps) {
  const hasUrgent = data.overdue_tasks > 0 || data.blocked_tasks > 0;

  return (
    <Card className={cn(hasUrgent && 'border-destructive')}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Urgent</CardTitle>
        <AlertTriangle
          className={cn(
            'h-4 w-4',
            hasUrgent ? 'text-destructive' : 'text-muted-foreground'
          )}
        />
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2">
          <Badge
            variant={data.overdue_tasks > 0 ? 'destructive' : 'secondary'}
            className="text-xs"
          >
            {data.overdue_tasks} overdue
          </Badge>
          <Badge variant="secondary" className="text-xs">
            {data.due_this_week} due this week
          </Badge>
          <Badge
            variant={data.blocked_tasks > 0 ? 'destructive' : 'secondary'}
            className="text-xs"
          >
            {data.blocked_tasks} blocked
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}
