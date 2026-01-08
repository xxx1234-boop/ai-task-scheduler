import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Target } from 'lucide-react';
import type { EstimationAccuracy } from '@/lib/types';

interface EstimationCardProps {
  data: EstimationAccuracy;
}

export function EstimationCard({ data }: EstimationCardProps) {
  const averageRatio = data.average_ratio ? Number(data.average_ratio) : null;

  const getAccuracyLabel = (
    ratio: number
  ): { text: string; color: string } => {
    if (ratio >= 0.9 && ratio <= 1.1)
      return { text: 'Excellent', color: 'text-green-500' };
    if (ratio >= 0.7 && ratio <= 1.3)
      return { text: 'Good', color: 'text-yellow-500' };
    return { text: 'Needs improvement', color: 'text-red-500' };
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Estimation Accuracy</CardTitle>
        <Target className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {averageRatio !== null ? (
          <>
            <div className="text-2xl font-bold">
              {(averageRatio * 100).toFixed(0)}%
            </div>
            <p className={`text-xs mt-1 ${getAccuracyLabel(averageRatio).color}`}>
              {getAccuracyLabel(averageRatio).text}
            </p>
            {data.by_genre.length > 0 && (
              <div className="mt-3 space-y-1">
                {data.by_genre.slice(0, 3).map((genre) => (
                  <div key={genre.name} className="flex justify-between text-xs">
                    <span className="text-muted-foreground truncate">
                      {genre.name}
                    </span>
                    <span>{(Number(genre.ratio) * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          <div className="text-muted-foreground text-sm">No data</div>
        )}
      </CardContent>
    </Card>
  );
}
