"use client";

import { useState } from "react";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";

const BASE_URL =
  (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8110") + "/api/v1";

export function ObsidianExportButton() {
  const [downloading, setDownloading] = useState(false);

  const handleExport = async () => {
    setDownloading(true);
    try {
      const res = await fetch(`${BASE_URL}/wiki/export`);
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "wiki-export.zip";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <Button
      variant="outline"
      size="sm"
      className="gap-2"
      onClick={handleExport}
      disabled={downloading}
    >
      <Download className="h-4 w-4" />
      {downloading ? "Exporting..." : "Export to Obsidian"}
    </Button>
  );
}
