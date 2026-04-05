"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import useSWR from "swr";
import Highlighter from "react-highlight-words";
import { Sparkles, FileText } from "lucide-react";
import { Header } from "@/components/Header";
import { SearchBar } from "@/components/SearchBar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { search, type SearchResult } from "@/lib/api";
import { truncate } from "@/lib/utils";

function SearchContent() {
  const searchParams = useSearchParams();
  const query = searchParams.get("q") || "";
  const [model, setModel] = useState<string>("haiku");

  const { data, isLoading, error } = useSWR<SearchResult>(
    query ? `search-${query}-${model}` : null,
    () => search(query, model)
  );

  const searchWords = query.split(/\s+/).filter(Boolean);

  return (
    <>
      <Header title="Search" />
      <div className="p-4 sm:p-6 space-y-6 max-w-4xl mx-auto">
        <SearchBar defaultValue={query} autoFocus className="max-w-2xl" />

        {/* Model toggle */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Model:</span>
          <Button
            variant={model === "haiku" ? "default" : "outline"}
            size="sm"
            onClick={() => setModel("haiku")}
          >
            Haiku
          </Button>
          <Button
            variant={model === "sonnet" ? "default" : "outline"}
            size="sm"
            onClick={() => setModel("sonnet")}
          >
            Sonnet
          </Button>
        </div>

        {!query && (
          <div className="text-center py-16 text-muted-foreground">
            <Sparkles className="h-12 w-12 mx-auto mb-4" />
            <p>Enter a query to search your knowledge base with AI.</p>
          </div>
        )}

        {isLoading && (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <Skeleton className="h-5 w-32" />
              </CardHeader>
              <CardContent className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </CardContent>
            </Card>
            {Array.from({ length: 3 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="pt-4">
                  <Skeleton className="h-4 w-full mb-2" />
                  <Skeleton className="h-4 w-2/3" />
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {error && (
          <Card className="border-destructive">
            <CardContent className="pt-6">
              <p className="text-destructive">
                Search failed. Make sure the backend is running.
              </p>
            </CardContent>
          </Card>
        )}

        {data && (
          <div className="space-y-6">
            {/* AI Answer */}
            <Card className="border-primary/20 bg-primary/5">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <Sparkles className="h-4 w-4" />
                  AI Answer
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
                  {data.answer}
                </div>
              </CardContent>
            </Card>

            {/* Sources */}
            {data.sources && data.sources.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wide">
                  Sources ({data.sources.length})
                </h3>
                <div className="space-y-3">
                  {data.sources.map((source, i) => (
                    <Card key={i}>
                      <CardContent className="pt-4">
                        <div className="flex items-center gap-2 mb-2">
                          <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                          <span className="text-sm font-medium">
                            {source.title || "Untitled"}
                          </span>
                          <Badge variant="secondary" className="text-[10px]">
                            {source.source_type}
                          </Badge>
                          <span className="text-[10px] text-muted-foreground ml-auto">
                            Score: {(source.score * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          <Highlighter
                            searchWords={searchWords}
                            autoEscape
                            textToHighlight={truncate(source.content, 300)}
                            highlightClassName="bg-yellow-200 dark:bg-yellow-800 rounded px-0.5"
                          />
                        </p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="p-6">
          <Skeleton className="h-10 w-full max-w-2xl" />
        </div>
      }
    >
      <SearchContent />
    </Suspense>
  );
}
