"use client";

import Link from "next/link";
import useSWR from "swr";
import { FileText, Upload, Link2, Bookmark, File } from "lucide-react";
import { Header } from "@/components/Header";
import { SearchBar } from "@/components/SearchBar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchNotes, fetchBookmarks, type Note, type Bookmark as BookmarkType } from "@/lib/api";
import { formatDate, truncate } from "@/lib/utils";

function RecentItemCard({
  type,
  title,
  preview,
  date,
  tags,
  href,
}: {
  type: "note" | "bookmark";
  title: string;
  preview: string;
  date: string;
  tags: string[];
  href: string;
}) {
  const Icon = type === "note" ? FileText : Bookmark;

  return (
    <Link href={href}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
        <CardHeader className="pb-2">
          <div className="flex items-start gap-2">
            <Icon className="h-4 w-4 mt-1 text-muted-foreground shrink-0" />
            <CardTitle className="text-sm font-medium leading-tight">
              {truncate(title, 60)}
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground mb-3 line-clamp-2">
            {truncate(preview, 100)}
          </p>
          <div className="flex items-center justify-between">
            <div className="flex gap-1 flex-wrap">
              {tags.slice(0, 3).map((tag) => (
                <Badge key={tag} variant="secondary" className="text-[10px] px-1.5 py-0">
                  {tag}
                </Badge>
              ))}
            </div>
            <span className="text-[10px] text-muted-foreground">{formatDate(date)}</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

export default function DashboardPage() {
  const { data: notesData, isLoading: notesLoading } = useSWR(
    "dashboard-notes",
    () => fetchNotes({ limit: 3 })
  );
  const { data: bookmarksData, isLoading: bookmarksLoading } = useSWR(
    "dashboard-bookmarks",
    () => fetchBookmarks({ limit: 3 })
  );

  const isLoading = notesLoading || bookmarksLoading;

  const recentItems: Array<{
    type: "note" | "bookmark";
    title: string;
    preview: string;
    date: string;
    tags: string[];
    href: string;
  }> = [];

  if (notesData?.items) {
    notesData.items.forEach((note: Note) => {
      recentItems.push({
        type: "note",
        title: note.title,
        preview: note.content,
        date: note.created_at,
        tags: note.tags,
        href: `/notes/${note.id}`,
      });
    });
  }

  if (bookmarksData?.items) {
    bookmarksData.items.forEach((bm: BookmarkType) => {
      recentItems.push({
        type: "bookmark",
        title: bm.title,
        preview: bm.description,
        date: bm.created_at,
        tags: bm.tags,
        href: `/bookmarks`,
      });
    });
  }

  // Sort by date descending
  recentItems.sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
  );

  return (
    <>
      <Header title="Dashboard" />
      <div className="p-4 sm:p-6 space-y-8 max-w-5xl mx-auto">
        {/* Welcome */}
        <div className="space-y-2">
          <h2 className="text-3xl font-bold tracking-tight">
            Welcome to your Second Brain
          </h2>
          <p className="text-muted-foreground">
            Search, organize, and connect your knowledge.
          </p>
        </div>

        {/* Search */}
        <SearchBar className="max-w-2xl" />

        {/* Quick actions */}
        <div className="flex flex-wrap gap-3">
          <Link href="/notes/new">
            <Button className="gap-2">
              <FileText className="h-4 w-4" />
              Add Note
            </Button>
          </Link>
          <Link href="/pdfs">
            <Button variant="outline" className="gap-2">
              <Upload className="h-4 w-4" />
              Upload PDF
            </Button>
          </Link>
          <Link href="/bookmarks">
            <Button variant="outline" className="gap-2">
              <Link2 className="h-4 w-4" />
              Paste URL
            </Button>
          </Link>
        </div>

        {/* Recent items */}
        <div>
          <h3 className="text-lg font-semibold mb-4">Recent Items</h3>
          {isLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Card key={i}>
                  <CardHeader className="pb-2">
                    <Skeleton className="h-4 w-3/4" />
                  </CardHeader>
                  <CardContent>
                    <Skeleton className="h-3 w-full mb-2" />
                    <Skeleton className="h-3 w-2/3" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : recentItems.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                <File className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">
                  No items yet. Start by adding a note, uploading a PDF, or
                  saving a bookmark.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {recentItems.slice(0, 6).map((item, i) => (
                <RecentItemCard key={i} {...item} />
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
