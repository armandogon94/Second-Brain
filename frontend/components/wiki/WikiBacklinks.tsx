"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { WikiLinkRef } from "@/lib/api";

interface WikiBacklinksProps {
  backlinks: WikiLinkRef[];
}

export function WikiBacklinks({ backlinks }: WikiBacklinksProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">
          Backlinks ({backlinks.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {backlinks.map((link) => (
            <li key={link.slug}>
              <Link
                href={`/wiki/${link.slug}`}
                className="flex items-center gap-2 text-sm hover:text-primary transition-colors"
              >
                <ArrowUpRight className="h-3 w-3 shrink-0" />
                <span>{link.title}</span>
                <Badge variant="outline" className="text-[10px] ml-auto">
                  {link.page_type}
                </Badge>
              </Link>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
