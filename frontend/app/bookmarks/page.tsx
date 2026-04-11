"use client";

import { useState } from "react";
import useSWR, { mutate } from "swr";
import { toast } from "sonner";
import {
  Plus,
  Bookmark,
  ExternalLink,
  Check,
  Circle,
  Trash2,
  X as XIcon,
} from "lucide-react";
import { Header } from "@/components/Header";
import { Pagination } from "@/components/Pagination";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  fetchBookmarks,
  createBookmark,
  updateBookmark,
  deleteBookmark,
  fetchTags,
  type Bookmark as BookmarkType,
  type Tag,
} from "@/lib/api";
import { formatDate, getDomain } from "@/lib/utils";

export default function BookmarksPage() {
  const [showAddForm, setShowAddForm] = useState(false);
  const [url, setUrl] = useState("");
  const [filter, setFilter] = useState<"all" | "unread" | "read">("all");
  const [adding, setAdding] = useState(false);
  const [page, setPage] = useState(0);
  const [selectedTag, setSelectedTag] = useState("");
  const perPage = 20;

  const fetchParams: Record<string, unknown> = {
    page: page + 1,
    per_page: perPage,
  };
  if (filter !== "all") fetchParams.is_read = filter === "read";
  if (selectedTag) fetchParams.tag = selectedTag;

  const { data, isLoading } = useSWR(
    `bookmarks-${filter}-${page}-${selectedTag}`,
    () => fetchBookmarks(fetchParams as any)
  );

  const { data: tags } = useSWR("tags", fetchTags);

  const totalPages = data ? Math.ceil(data.total / perPage) : 1;

  const handleAdd = async () => {
    if (!url.trim()) {
      toast.error("Please enter a URL");
      return;
    }

    setAdding(true);
    try {
      await createBookmark({ url: url.trim() });
      toast.success("Bookmark added");
      setUrl("");
      setShowAddForm(false);
      mutate(`bookmarks-${filter}`);
    } catch (err) {
      toast.error("Failed to add bookmark");
      console.error(err);
    } finally {
      setAdding(false);
    }
  };

  const handleToggleRead = async (bookmark: BookmarkType) => {
    try {
      await updateBookmark(bookmark.id, { is_read: !bookmark.is_read });
      mutate(`bookmarks-${filter}`);
    } catch (err) {
      toast.error("Failed to update bookmark");
      console.error(err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this bookmark?")) return;
    try {
      await deleteBookmark(id);
      toast.success("Bookmark deleted");
      mutate(`bookmarks-${filter}`);
    } catch (err) {
      toast.error("Failed to delete bookmark");
      console.error(err);
    }
  };

  return (
    <>
      <Header title="Bookmarks" />
      <div className="p-4 sm:p-6 space-y-6 max-w-4xl mx-auto">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3 justify-between">
          <div className="flex items-center gap-3 flex-wrap">
            <Button
              className="gap-2"
              onClick={() => setShowAddForm(!showAddForm)}
            >
              <Plus className="h-4 w-4" />
              Add Bookmark
            </Button>

            <select
              className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={selectedTag}
              onChange={(e) => {
                setSelectedTag(e.target.value);
                setPage(0);
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

          <div className="flex gap-1">
            {(["all", "unread", "read"] as const).map((f) => (
              <Button
                key={f}
                variant={filter === f ? "default" : "outline"}
                size="sm"
                onClick={() => {
                  setFilter(f);
                  setPage(0);
                }}
                className="capitalize"
              >
                {f}
              </Button>
            ))}
          </div>
        </div>

        {/* Add form */}
        {showAddForm && (
          <Card>
            <CardContent className="pt-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Paste URL here..."
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAdd()}
                  autoFocus
                />
                <Button onClick={handleAdd} disabled={adding}>
                  {adding ? "Adding..." : "Save"}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowAddForm(false)}
                >
                  <XIcon className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Bookmarks list */}
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="pt-4">
                  <Skeleton className="h-5 w-3/4 mb-2" />
                  <Skeleton className="h-3 w-1/2" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : data?.items.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-16">
              <Bookmark className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-4">No bookmarks yet.</p>
              <Button onClick={() => setShowAddForm(true)}>
                Add your first bookmark
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {data?.items.map((bookmark) => (
              <Card key={bookmark.id} className="group">
                <CardContent className="pt-4">
                  <div className="flex items-start gap-3">
                    {/* Read toggle */}
                    <button
                      onClick={() => handleToggleRead(bookmark)}
                      className="mt-0.5 shrink-0"
                      title={bookmark.is_read ? "Mark as unread" : "Mark as read"}
                    >
                      {bookmark.is_read ? (
                        <Check className="h-5 w-5 text-green-500" />
                      ) : (
                        <Circle className="h-5 w-5 text-muted-foreground" />
                      )}
                    </button>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-sm font-medium truncate">
                          {bookmark.title || bookmark.url}
                        </h3>
                        <a
                          href={bookmark.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="shrink-0"
                        >
                          <ExternalLink className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground" />
                        </a>
                      </div>

                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{getDomain(bookmark.url)}</span>
                        <span>&middot;</span>
                        <span>{formatDate(bookmark.created_at)}</span>
                      </div>

                      {bookmark.description && (
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                          {bookmark.description}
                        </p>
                      )}

                      {bookmark.tags.length > 0 && (
                        <div className="flex gap-1 mt-2 flex-wrap">
                          {bookmark.tags.map((tag) => (
                            <Badge
                              key={tag}
                              variant="secondary"
                              className="text-[10px] px-1.5 py-0"
                            >
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Delete */}
                    <Button
                      variant="ghost"
                      size="icon"
                      className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => handleDelete(bookmark.id)}
                    >
                      <Trash2 className="h-4 w-4 text-muted-foreground" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
      </div>
    </>
  );
}
