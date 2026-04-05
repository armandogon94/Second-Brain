"use client";

import { useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { Plus, FileText, ChevronLeft, ChevronRight } from "lucide-react";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchNotes, fetchTags, type Tag } from "@/lib/api";
import { formatDate, truncate } from "@/lib/utils";

export default function NotesPage() {
  const [page, setPage] = useState(1);
  const [selectedTag, setSelectedTag] = useState<string>("");
  const perPage = 12;

  const { data, isLoading } = useSWR(
    `notes-${page}-${perPage}-${selectedTag}`,
    () => fetchNotes({ page, per_page: perPage, tag: selectedTag || undefined })
  );

  const { data: tags } = useSWR("tags", fetchTags);

  const totalPages = data ? Math.ceil(data.total / perPage) : 1;

  return (
    <>
      <Header title="Notes" />
      <div className="p-4 sm:p-6 space-y-6 max-w-5xl mx-auto">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3 justify-between">
          <div className="flex items-center gap-3 flex-wrap">
            <Link href="/notes/new">
              <Button className="gap-2">
                <Plus className="h-4 w-4" />
                New Note
              </Button>
            </Link>

            {/* Tag filter */}
            <select
              className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={selectedTag}
              onChange={(e) => {
                setSelectedTag(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All tags</option>
              {tags?.map((tag: Tag) => (
                <option key={tag.id} value={tag.name}>
                  {tag.name}
                </option>
              ))}
            </select>
          </div>

          {data && (
            <span className="text-sm text-muted-foreground">
              {data.total} note{data.total !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        {/* Notes grid */}
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-5 w-3/4" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-3 w-full mb-2" />
                  <Skeleton className="h-3 w-2/3" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : data?.items.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-16">
              <FileText className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-4">No notes yet.</p>
              <Link href="/notes/new">
                <Button>Create your first note</Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {data?.items.map((note) => (
              <Link key={note.id} href={`/notes/${note.id}`}>
                <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium">
                      {truncate(note.title, 50)}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-muted-foreground mb-3 line-clamp-3">
                      {truncate(note.content, 120)}
                    </p>
                    <div className="flex items-center justify-between">
                      <div className="flex gap-1 flex-wrap">
                        {note.tags.slice(0, 3).map((tag) => (
                          <Badge
                            key={tag}
                            variant="secondary"
                            className="text-[10px] px-1.5 py-0"
                          >
                            {tag}
                          </Badge>
                        ))}
                      </div>
                      <span className="text-[10px] text-muted-foreground">
                        {formatDate(note.created_at)}
                      </span>
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
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm text-muted-foreground px-2">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
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
