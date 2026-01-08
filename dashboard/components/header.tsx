'use client';

import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { RefreshCw, Loader2 } from 'lucide-react';
import { ModeToggle } from '@/components/mode-toggle';
import { AccentSelector } from '@/components/accent-selector';
import { SidebarTrigger } from '@/components/ui/sidebar';
import { Separator } from '@/components/ui/separator';

interface HeaderProps {
  totalCount: number;
  autoRefresh: boolean;
  onAutoRefreshChange: (checked: boolean) => void;
  onRefresh: () => void;
  isLoading: boolean;
}

export function Header({
  totalCount,
  autoRefresh,
  onAutoRefreshChange,
  onRefresh,
  isLoading,
}: HeaderProps) {
  return (
    <header className="border-b bg-card/50 px-4 py-4">
      <div className="flex items-center justify-between">
        {/* Left: Sidebar Trigger + Title */}
        <div className="flex items-center gap-2">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-2 h-4" />
          <h1 className="text-xl font-bold">Research Time Tracker</h1>
          <Badge variant="secondary" className="text-xs">
            {totalCount} tasks
          </Badge>
        </div>

        {/* Right: Controls */}
        <div className="flex items-center gap-4">
          {/* Auto-refresh toggle */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Auto-refresh</span>
            <Switch checked={autoRefresh} onCheckedChange={onAutoRefreshChange} />
          </div>

          {/* Manual refresh button */}
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
            <span className="ml-2">Refresh</span>
          </Button>

          {/* Theme controls */}
          <div className="flex items-center gap-2 border-l pl-4">
            <AccentSelector />
            <ModeToggle />
          </div>
        </div>
      </div>
    </header>
  );
}
