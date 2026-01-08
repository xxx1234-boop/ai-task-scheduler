'use client';

import { useState } from 'react';
import { useSummary } from '@/hooks/use-summary';
import {
  SummaryHeader,
  SummarySkeleton,
  TodayCard,
  WeekCard,
  TimerCard,
  UrgentCard,
  WeeklyChart,
  DistributionChart,
  EstimationCard,
  CompletionCard,
  ContextSwitchesCard,
} from '@/components/summary';

export default function SummaryPage() {
  const [autoRefresh, setAutoRefresh] = useState(true);
  const { summary, stats, weekly, isLoading, error, refresh } = useSummary({
    autoRefresh,
  });

  return (
    <div className="min-h-screen flex flex-col">
      <SummaryHeader
        autoRefresh={autoRefresh}
        onAutoRefreshChange={setAutoRefresh}
        onRefresh={refresh}
        isLoading={isLoading}
      />

      <main className="flex-1 p-4 md:p-6">
        {error && (
          <div className="mb-4 p-4 bg-destructive/10 border border-destructive/30 rounded-lg">
            <p className="text-sm text-destructive">
              Failed to load data: {error.message}
            </p>
          </div>
        )}

        {isLoading && !summary && !stats && !weekly && <SummarySkeleton />}

        {(summary || stats || weekly) && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {summary && (
              <>
                <TodayCard data={summary.today} />
                <WeekCard data={summary.this_week} />
                <TimerCard data={summary.timer} />
                <UrgentCard data={summary.urgent} />
              </>
            )}

            {weekly && <WeeklyChart data={weekly.daily} />}
            {stats && <DistributionChart data={stats.time_distribution} />}

            {stats && (
              <>
                <EstimationCard data={stats.estimation_accuracy} />
                <CompletionCard data={stats.completion_rate} />
                <ContextSwitchesCard data={stats.context_switches} />
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
