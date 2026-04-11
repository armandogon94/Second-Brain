"use client";

import Link from "next/link";
import { FileText, Bookmark, File } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { WikiSourceRef } from "@/lib/api";

const SOURCE_ICONS: Record<string, typeof FileText> = {
  note: FileText,
  bookmark: Bookmark,
  pdf: File,
};

const SOURCE_LINKS: Record<string, (id: number) => string> = {
  note: (id) => `/notes/${id}`,
  bookmark: (id) => `/bookmarks/${id}`,
  pdf: (id) => `/pdfs/${id}`,
};

interface WikiSourceReferencesProps {
  sources: WikiSourceRef[];
}

export function WikiSourceReferences({ sources }: WikiSourceReferencesProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">
          Sources ({sources.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {sources.map((source, i) => {
            const Icon = SOURCE_ICONS[source.source_type] || FileText;
            const href = SOURCE_LINKS[source.source_type]?.(source.source_id);

            return (
              <li key={i}>
                {href ? (
                  <Link
                    href={href}
                    className="flex items-center gap-2 text-sm hover:text-primary transition-colors"
                  >
                    <Icon className="h-3 w-3 shrink-0" />
                    <span>
                      {source.source_type} #{source.source_id}
                    </span>
                  </Link>
                ) : (
                  <span className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Icon className="h-3 w-3 shrink-0" />
                    {source.source_type} #{source.source_id}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}
