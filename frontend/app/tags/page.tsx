"use client";

import { useState } from "react";
import useSWR, { mutate } from "swr";
import { toast } from "sonner";
import { Plus, Trash2, Tag } from "lucide-react";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchTags, createTag, deleteTag, type Tag as TagType } from "@/lib/api";

const PRESET_COLORS = [
  "#ef4444",
  "#f97316",
  "#eab308",
  "#22c55e",
  "#06b6d4",
  "#3b82f6",
  "#8b5cf6",
  "#ec4899",
  "#6b7280",
];

export default function TagsPage() {
  const [name, setName] = useState("");
  const [color, setColor] = useState(PRESET_COLORS[5]);
  const [creating, setCreating] = useState(false);

  const { data: tags, isLoading } = useSWR("tags", fetchTags);

  const handleCreate = async () => {
    if (!name.trim()) {
      toast.error("Please enter a tag name");
      return;
    }

    setCreating(true);
    try {
      await createTag({ name: name.trim().toLowerCase(), color });
      toast.success("Tag created");
      setName("");
      mutate("tags");
    } catch (err) {
      toast.error("Failed to create tag");
      console.error(err);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this tag?")) return;
    try {
      await deleteTag(id);
      toast.success("Tag deleted");
      mutate("tags");
    } catch (err) {
      toast.error("Failed to delete tag");
      console.error(err);
    }
  };

  return (
    <>
      <Header title="Tags" />
      <div className="p-4 sm:p-6 space-y-6 max-w-3xl mx-auto">
        {/* Create tag form */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Create New Tag</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-3">
              <Input
                placeholder="Tag name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                className="max-w-xs"
              />
              <Button
                onClick={handleCreate}
                disabled={creating}
                className="gap-2"
              >
                <Plus className="h-4 w-4" />
                {creating ? "Creating..." : "Create"}
              </Button>
            </div>

            {/* Color picker */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Color:</span>
              <div className="flex gap-1.5">
                {PRESET_COLORS.map((c) => (
                  <button
                    key={c}
                    className={`h-6 w-6 rounded-full border-2 transition-transform ${
                      color === c
                        ? "border-foreground scale-110"
                        : "border-transparent hover:scale-105"
                    }`}
                    style={{ backgroundColor: c }}
                    onClick={() => setColor(c)}
                  />
                ))}
              </div>
              <Input
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="w-10 h-8 p-0.5 cursor-pointer"
              />
            </div>
          </CardContent>
        </Card>

        {/* Tags table */}
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : !tags || tags.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-16">
              <Tag className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                No tags yet. Create your first tag above.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="text-left text-xs font-medium text-muted-foreground px-4 py-3">
                    Color
                  </th>
                  <th className="text-left text-xs font-medium text-muted-foreground px-4 py-3">
                    Name
                  </th>
                  <th className="text-left text-xs font-medium text-muted-foreground px-4 py-3">
                    Items
                  </th>
                  <th className="text-right text-xs font-medium text-muted-foreground px-4 py-3">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {tags.map((tag: TagType) => (
                  <tr key={tag.id} className="border-b last:border-0">
                    <td className="px-4 py-3">
                      <div
                        className="h-5 w-5 rounded-full"
                        style={{ backgroundColor: tag.color || "#6b7280" }}
                      />
                    </td>
                    <td className="px-4 py-3 text-sm font-medium">
                      {tag.name}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {tag.item_count}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDelete(tag.id)}
                      >
                        <Trash2 className="h-4 w-4 text-muted-foreground" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
