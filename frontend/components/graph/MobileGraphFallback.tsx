"use client";

import { useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { GraphNode } from "@/lib/api";

interface MobileGraphFallbackProps {
  nodes: GraphNode[];
}

const TYPE_ORDER = [
  "concept",
  "person",
  "project",
  "howto",
  "reference",
  "index",
  "log",
];

export function MobileGraphFallback({ nodes }: MobileGraphFallbackProps) {
  const [search, setSearch] = useState("");

  const filtered = nodes.filter(
    (n) =>
      n.title.toLowerCase().includes(search.toLowerCase()) ||
      n.type.toLowerCase().includes(search.toLowerCase())
  );

  // Group by type
  const grouped = TYPE_ORDER.reduce(
    (acc, type) => {
      const items = filtered.filter((n) => n.type === type);
      if (items.length > 0) acc[type] = items;
      return acc;
    },
    {} as Record<string, GraphNode[]>
  );

  return (
    <div className="space-y-4">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search pages..."
          className="h-10 w-full rounded-md border border-input bg-background pl-9 pr-3 py-2 text-sm"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {Object.entries(grouped).map(([type, items]) => (
        <div key={type}>
          <h3 className="text-sm font-medium text-muted-foreground mb-2 capitalize">
            {type} ({items.length})
          </h3>
          <div className="space-y-1">
            {items.map((node) => (
              <Link key={node.slug} href={`/wiki/${node.slug}`}>
                <Card className="hover:shadow-sm transition-shadow cursor-pointer">
                  <CardContent className="p-3 flex items-center justify-between">
                    <span className="text-sm">{node.title}</span>
                    <Badge variant="outline" className="text-[10px]">
                      {node.link_count} links
                    </Badge>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      ))}

      {filtered.length === 0 && (
        <p className="text-sm text-muted-foreground text-center py-8">
          No matching pages found.
        </p>
      )}
    </div>
  );
}
