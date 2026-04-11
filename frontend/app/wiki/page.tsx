"use client";

import { useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { BookOpen, Search, ChevronLeft, ChevronRight } from "lucide-react";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchWikiPages } from "@/lib/api";
import { formatDate } from "@/lib/utils";

const PAGE_TYPES = [
  "concept",
  "person",
  "project",
  "howto",
  "reference",
  "index",
  "log",
];

const TYPE_COLORS: Record<string, string> = {
  concept: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  person: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  project: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
  howto: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  reference: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200",
  index: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  log: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
};

export default function WikiPage() {
  const [page, setPage] = useState(0);
  const [selectedType, setSelectedType] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const perPage = 20;

  const { data, isLoading } = useSWR(
    `wiki-${page}-${perPage}-${selectedType}-${searchQuery}`,
    () =>
      fetchWikiPages({
        skip: page * perPage,
        limit: perPage,
        page_type: selectedType || undefined,
        search: searchQuery || undefined,
      })
  );

  const totalPages = data ? Math.ceil(data.total / perPage) : 1;

  return (
    <>
      <Header title="Wiki" />
      <div className="p-4 sm:p-6 space-y-6 max-w-5xl mx-auto">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3 justify-between">
          <div className="flex items-center gap-3 flex-wrap">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search wiki..."
                className="h-10 rounded-md border border-input bg-background pl-9 pr-3 py-2 text-sm w-56"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setPage(0);
                }}
              />
            </div>

            {/* Type filter */}
            <select
              className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={selectedType}
              onChange={(e) => {
                setSelectedType(e.target.value);
                setPage(0);
              }}
            >
              <option value="">All types</option>
              {PAGE_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          {data && (
            <span className="text-sm text-muted-foreground">
              {data.total} page{data.total !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        {/* Wiki pages list */}
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="p-4">
                  <Skeleton className="h-5 w-1/3 mb-2" />
                  <Skeleton className="h-3 w-2/3" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : data?.pages.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-16">
              <BookOpen className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-2">No wiki pages yet.</p>
              <p className="text-sm text-muted-foreground">
                Run a compilation to generate pages from your notes and
                bookmarks.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {data?.pages.map((wikiPage) => (
              <Link key={wikiPage.slug} href={`/wiki/${wikiPage.slug}`}>
                <Card className="hover:shadow-md transition-shadow cursor-pointer">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-medium truncate">
                            {wikiPage.title}
                          </h3>
                          {wikiPage.is_stale && (
                            <Badge variant="secondary" className="text-[10px] shrink-0">
                              stale
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {wikiPage.content_markdown.slice(0, 200)}
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-1 shrink-0">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full ${
                            TYPE_COLORS[wikiPage.page_type] || TYPE_COLORS.concept
                          }`}
                        >
                          {wikiPage.page_type}
                        </span>
                        <span className="text-[10px] text-muted-foreground">
                          {formatDate(wikiPage.updated_at)}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 0}
              onClick={() => setPage((p) => p - 1)}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm text-muted-foreground px-2">
              Page {page + 1} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page + 1 >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
    </>
  );
}
