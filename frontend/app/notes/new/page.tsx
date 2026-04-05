"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { toast } from "sonner";
import { Save, X as XIcon } from "lucide-react";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { createNote } from "@/lib/api";

const MDEditor = dynamic(() => import("@uiw/react-md-editor"), { ssr: false });

export default function NewNotePage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  const addTag = () => {
    const tag = tagInput.trim().toLowerCase();
    if (tag && !tags.includes(tag)) {
      setTags([...tags, tag]);
    }
    setTagInput("");
  };

  const removeTag = (tagToRemove: string) => {
    setTags(tags.filter((t) => t !== tagToRemove));
  };

  const handleTagKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag();
    }
  };

  const handleSave = async () => {
    if (!title.trim()) {
      toast.error("Please enter a title");
      return;
    }

    setSaving(true);
    try {
      await createNote({ title: title.trim(), content, tags });
      toast.success("Note created successfully");
      router.push("/notes");
    } catch (err) {
      toast.error("Failed to create note");
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Header title="New Note" />
      <div className="p-4 sm:p-6 space-y-6 max-w-4xl mx-auto">
        {/* Title */}
        <Input
          placeholder="Note title..."
          className="text-lg font-semibold h-12"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          autoFocus
        />

        {/* Tags */}
        <div className="space-y-2">
          <div className="flex gap-2">
            <Input
              placeholder="Add tags (press Enter)"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleTagKeyDown}
              className="max-w-xs"
            />
            <Button variant="outline" size="sm" onClick={addTag}>
              Add
            </Button>
          </div>
          {tags.length > 0 && (
            <div className="flex gap-1.5 flex-wrap">
              {tags.map((tag) => (
                <Badge
                  key={tag}
                  variant="secondary"
                  className="cursor-pointer gap-1"
                  onClick={() => removeTag(tag)}
                >
                  {tag}
                  <XIcon className="h-3 w-3" />
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* Markdown editor */}
        <div data-color-mode="auto">
          <MDEditor
            value={content}
            onChange={(val) => setContent(val || "")}
            height={400}
            preview="edit"
          />
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <Button onClick={handleSave} disabled={saving} className="gap-2">
            <Save className="h-4 w-4" />
            {saving ? "Saving..." : "Save Note"}
          </Button>
          <Button variant="outline" onClick={() => router.push("/notes")}>
            Cancel
          </Button>
        </div>
      </div>
    </>
  );
}
