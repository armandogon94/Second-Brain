"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import useSWR from "swr";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchWikiPage } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { WikiBacklinks } from "@/components/wiki/WikiBacklinks";
import { WikiSourceReferences } from "@/components/wiki/WikiSourceReferences";
import { WikiMarkdownRenderer } from "@/components/wiki/WikiMarkdownRenderer";

export default function WikiArticlePage() {
  const params = useParams();
  const slug = params.slug as string;

  const { data: page, isLoading, error } = useSWR(
    slug ? `wiki-page-${slug}` : null,
    () => fetchWikiPage(slug)
  );

  if (isLoading) {
    return (
      <>
        <Header title="Wiki" />
        <div className="p-4 sm:p-6 max-w-4xl mx-auto space-y-6">
          <Skeleton className="h-8 w-1/2" />
          <Skeleton className="h-4 w-1/4" />
          <Skeleton className="h-64 w-full" />
        </div>
      </>
    );
  }

  if (error || !page) {
    return (
      <>
        <Header title="Wiki" />
        <div className="p-4 sm:p-6 max-w-4xl mx-auto">
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-16">
              <p className="text-muted-foreground mb-4">Wiki page not found.</p>
              <Link href="/wiki">
                <Button variant="outline">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back to Wiki
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </>
    );
  }

  return (
    <>
      <Header title={page.title} />
      <div className="p-4 sm:p-6 max-w-4xl mx-auto space-y-6">
        {/* Back link */}
        <Link href="/wiki" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Wiki
        </Link>

        {/* Page header */}
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl font-bold">{page.title}</h1>
            {page.is_stale && (
              <Badge variant="secondary">stale</Badge>
            )}
          </div>
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <Badge variant="outline">{page.page_type}</Badge>
            <span>v{page.version}</span>
            <span>Confidence: {Math.round(page.confidence * 100)}%</span>
            <span>Updated {formatDate(page.updated_at)}</span>
          </div>
        </div>

        {/* Markdown content with wikilink conversion */}
        <Card>
          <CardContent className="p-6 prose prose-sm dark:prose-invert max-w-none">
            <WikiMarkdownRenderer content={page.content_markdown} />
          </CardContent>
        </Card>

        {/* Backlinks */}
        {page.backlinks.length > 0 && (
          <WikiBacklinks backlinks={page.backlinks} />
        )}

        {/* Source references */}
        {page.sources.length > 0 && (
          <WikiSourceReferences sources={page.sources} />
        )}
      </div>
    </>
  );
}
