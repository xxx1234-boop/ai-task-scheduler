'use client';

import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { RefreshCw, Loader2 } from 'lucide-react';
import { ModeToggle } from '@/components/mode-toggle';
import { AccentSelector } from '@/components/accent-selector';
import { SidebarTrigger } from '@/components/ui/sidebar';
import { Separator } from '@/components/ui/separator';

interface SummaryHeaderProps {
  autoRefresh: boolean;
  onAutoRefreshChange: (checked: boolean) => void;
  onRefresh: () => void;
  isLoading: boolean;
}

export function SummaryHeader({
  autoRefresh,
  onAutoRefreshChange,
  onRefresh,
  isLoading,
}: SummaryHeaderProps) {
  return (
    <header className="border-b bg-card/50 px-3 md:px-4 py-2 md:py-3 shrink-0">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-2 h-4" />
          <h1 className="text-lg md:text-xl font-bold">Summary</h1>
        </div>
        <div className="flex items-center gap-2 md:gap-4">
          <div className="hidden md:flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Auto-refresh</span>
            <Switch checked={autoRefresh} onCheckedChange={onAutoRefreshChange} />
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            <span className="hidden md:inline ml-2">Refresh</span>
          </Button>
          <div className="flex items-center gap-2 border-l pl-2 md:pl-4">
            <AccentSelector />
            <ModeToggle />
          </div>
        </div>
      </div>
    </header>
  );
}
