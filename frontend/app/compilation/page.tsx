"use client";

import { useState } from "react";
import useSWR, { mutate } from "swr";
import {
  Cpu,
  Play,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  triggerCompile,
  fetchCompileHistory,
  wikiLint,
  type CompilationLog,
  type LintResult,
} from "@/lib/api";
import { formatDate } from "@/lib/utils";

const STATUS_ICONS: Record<string, typeof CheckCircle> = {
  success: CheckCircle,
  failed: XCircle,
  running: RefreshCw,
  pending: Clock,
};

const STATUS_COLORS: Record<string, string> = {
  success: "text-green-600",
  failed: "text-red-600",
  running: "text-blue-600",
  pending: "text-yellow-600",
};

export default function CompilationPage() {
  const [isCompiling, setIsCompiling] = useState(false);
  const [compileModel, setCompileModel] = useState("haiku");

  const { data: history, isLoading: historyLoading } = useSWR(
    "compile-history",
    fetchCompileHistory,
    { refreshInterval: isCompiling ? 3000 : 0 }
  );

  const { data: lintResult, isLoading: lintLoading } = useSWR<LintResult>(
    "wiki-lint",
    wikiLint
  );

  const handleCompile = async () => {
    setIsCompiling(true);
    try {
      await triggerCompile({ model: compileModel });
      mutate("compile-history");
      mutate("wiki-lint");
    } finally {
      setIsCompiling(false);
    }
  };

  return (
    <>
      <Header title="Compilation" />
      <div className="p-4 sm:p-6 max-w-5xl mx-auto space-y-6">
        {/* Compile action */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="h-5 w-5" />
              Run Compilation
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3 flex-wrap">
              <select
                className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={compileModel}
                onChange={(e) => setCompileModel(e.target.value)}
              >
                <option value="haiku">Haiku (faster, cheaper)</option>
                <option value="sonnet">Sonnet (better quality)</option>
              </select>
              <Button
                onClick={handleCompile}
                disabled={isCompiling}
                className="gap-2"
              >
                {isCompiling ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                {isCompiling ? "Compiling..." : "Run Compilation"}
              </Button>
            </div>
            <p className="text-sm text-muted-foreground mt-3">
              Compiles unprocessed notes, bookmarks, and PDFs into wiki pages.
            </p>
          </CardContent>
        </Card>

        {/* Health check */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <AlertTriangle className="h-4 w-4" />
              Health Check
            </CardTitle>
          </CardHeader>
          <CardContent>
            {lintLoading ? (
              <Skeleton className="h-20 w-full" />
            ) : lintResult ? (
              <div className="space-y-3">
                <div className="flex gap-4 text-sm">
                  <span>
                    Pages: <strong>{lintResult.stats.total_pages || 0}</strong>
                  </span>
                  <span>
                    Links: <strong>{lintResult.stats.total_links || 0}</strong>
                  </span>
                  <span>
                    Orphans: <strong>{lintResult.stats.orphan_count || 0}</strong>
                  </span>
                  <span>
                    Stale: <strong>{lintResult.stats.stale_count || 0}</strong>
                  </span>
                </div>
                {lintResult.issues.length > 0 && (
                  <div className="space-y-1">
                    {lintResult.issues.slice(0, 10).map((issue, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-2 text-sm text-muted-foreground"
                      >
                        <Badge
                          variant="outline"
                          className="text-[10px] shrink-0"
                        >
                          {issue.type}
                        </Badge>
                        <span className="truncate">{issue.message}</span>
                      </div>
                    ))}
                  </div>
                )}
                {lintResult.issues.length === 0 && (
                  <p className="text-sm text-green-600">
                    No issues found.
                  </p>
                )}
              </div>
            ) : null}
          </CardContent>
        </Card>

        {/* Compilation history */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Compilation History
            </CardTitle>
          </CardHeader>
          <CardContent>
            {historyLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : !history || history.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                No compilation runs yet.
              </p>
            ) : (
              <div className="space-y-3">
                {history.map((log: CompilationLog) => {
                  const Icon = STATUS_ICONS[log.status] || Clock;
                  const color = STATUS_COLORS[log.status] || "";

                  return (
                    <div
                      key={log.id}
                      className="flex items-center gap-3 p-3 rounded-lg border text-sm"
                    >
                      <Icon className={`h-4 w-4 shrink-0 ${color}`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{log.action}</span>
                          <Badge variant="outline" className="text-[10px]">
                            {log.status}
                          </Badge>
                        </div>
                        <span className="text-muted-foreground text-xs">
                          {log.sources_processed} sources, {log.pages_created}{" "}
                          created, {log.pages_updated} updated
                        </span>
                      </div>
                      <span className="text-xs text-muted-foreground shrink-0">
                        {formatDate(log.started_at)}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
