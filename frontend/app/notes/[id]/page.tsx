"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import dynamic from "next/dynamic";
import useSWR from "swr";
import { toast } from "sonner";
import { Save, Trash2, X as XIcon } from "lucide-react";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchNote, updateNote, deleteNote } from "@/lib/api";

const MDEditor = dynamic(() => import("@uiw/react-md-editor"), { ssr: false });

export default function NoteEditorPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;

  const { data: note, isLoading } = useSWR(
    id ? `note-${id}` : null,
    () => fetchNote(id)
  );

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (note) {
      setTitle(note.title);
      setContent(note.content);
      setTags(note.tags || []);
    }
  }, [note]);

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
      await updateNote(id, { title: title.trim(), content, tags });
      toast.success("Note updated successfully");
    } catch (err) {
      toast.error("Failed to update note");
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this note?")) return;

    setDeleting(true);
    try {
      await deleteNote(id);
      toast.success("Note deleted");
      router.push("/notes");
    } catch (err) {
      toast.error("Failed to delete note");
      console.error(err);
    } finally {
      setDeleting(false);
    }
  };

  if (isLoading) {
    return (
      <>
        <Header title="Edit Note" />
        <div className="p-4 sm:p-6 space-y-6 max-w-4xl mx-auto">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-[400px] w-full" />
        </div>
      </>
    );
  }

  return (
    <>
      <Header title="Edit Note" />
      <div className="p-4 sm:p-6 space-y-6 max-w-4xl mx-auto">
        {/* Title */}
        <Input
          placeholder="Note title..."
          className="text-lg font-semibold h-12"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
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
          />
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <Button onClick={handleSave} disabled={saving} className="gap-2">
            <Save className="h-4 w-4" />
            {saving ? "Saving..." : "Save"}
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={deleting}
            className="gap-2"
          >
            <Trash2 className="h-4 w-4" />
            {deleting ? "Deleting..." : "Delete"}
          </Button>
          <Button variant="outline" onClick={() => router.push("/notes")}>
            Back
          </Button>
        </div>
      </div>
    </>
  );
}
