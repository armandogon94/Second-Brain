"use client";

import { useState, useRef } from "react";
import useSWR, { mutate } from "swr";
import { toast } from "sonner";
import {
  Upload,
  File,
  Trash2,
  ChevronDown,
  ChevronRight,
  FileText,
} from "lucide-react";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchPdfs, uploadPdf, deletePdf, type Pdf } from "@/lib/api";
import { formatDate, formatFileSize } from "@/lib/utils";

export default function PdfsPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const { data: pdfs, isLoading } = useSWR("pdfs", fetchPdfs);

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];

    if (file.type !== "application/pdf") {
      toast.error("Please upload a PDF file");
      return;
    }

    setUploading(true);
    try {
      await uploadPdf(file);
      toast.success("PDF uploaded successfully");
      mutate("pdfs");
    } catch (err) {
      toast.error("Failed to upload PDF");
      console.error(err);
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this PDF?")) return;
    try {
      await deletePdf(id);
      toast.success("PDF deleted");
      mutate("pdfs");
    } catch (err) {
      toast.error("Failed to delete PDF");
      console.error(err);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleUpload(e.dataTransfer.files);
  };

  return (
    <>
      <Header title="PDFs" />
      <div className="p-4 sm:p-6 space-y-6 max-w-4xl mx-auto">
        {/* Upload zone */}
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragOver
              ? "border-primary bg-primary/5"
              : "border-muted-foreground/25 hover:border-muted-foreground/50"
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <Upload className="h-10 w-10 mx-auto mb-3 text-muted-foreground" />
          <p className="text-sm text-muted-foreground mb-3">
            Drag and drop a PDF here, or click to browse
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            className="hidden"
            onChange={(e) => handleUpload(e.target.files)}
          />
          <Button
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? "Uploading..." : "Choose File"}
          </Button>
        </div>

        {/* PDF list */}
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="pt-4">
                  <Skeleton className="h-5 w-3/4 mb-2" />
                  <Skeleton className="h-3 w-1/3" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : !pdfs || pdfs.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-16">
              <File className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                No PDFs uploaded yet. Upload your first PDF above.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {pdfs.map((pdf: Pdf) => (
              <Card key={pdf.id} className="group">
                <CardContent className="pt-4">
                  <div className="flex items-start gap-3">
                    <FileText className="h-5 w-5 mt-0.5 text-red-500 shrink-0" />

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-sm font-medium truncate">
                          {pdf.filename}
                        </h3>
                      </div>

                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span>{pdf.page_count} pages</span>
                        <span>&middot;</span>
                        <span>{formatFileSize(pdf.file_size)}</span>
                        <span>&middot;</span>
                        <span>{formatDate(pdf.created_at)}</span>
                      </div>

                      {/* Expandable extracted text */}
                      <button
                        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mt-2 transition-colors"
                        onClick={() =>
                          setExpandedId(
                            expandedId === pdf.id ? null : pdf.id
                          )
                        }
                      >
                        {expandedId === pdf.id ? (
                          <ChevronDown className="h-3 w-3" />
                        ) : (
                          <ChevronRight className="h-3 w-3" />
                        )}
                        {expandedId === pdf.id
                          ? "Hide extracted text"
                          : "Show extracted text"}
                      </button>

                      {expandedId === pdf.id && pdf.extracted_text && (
                        <div className="mt-2 p-3 rounded bg-muted text-xs whitespace-pre-wrap max-h-64 overflow-y-auto">
                          {pdf.extracted_text}
                        </div>
                      )}
                    </div>

                    <Button
                      variant="ghost"
                      size="icon"
                      className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => handleDelete(pdf.id)}
                    >
                      <Trash2 className="h-4 w-4 text-muted-foreground" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
