"use client";

import { useRef, useState, useEffect } from "react";
import useSWR from "swr";
import { Network } from "lucide-react";
import { Header } from "@/components/Header";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchWikiGraph } from "@/lib/api";
import { useMediaQuery } from "@/lib/hooks/useMediaQuery";
import { ForceGraph } from "@/components/graph/ForceGraph";
import { MobileGraphFallback } from "@/components/graph/MobileGraphFallback";

export default function GraphPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const isMobile = useMediaQuery("(max-width: 768px)");

  const { data, isLoading } = useSWR("wiki-graph", fetchWikiGraph);

  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: Math.max(400, window.innerHeight - 200),
        });
      }
    };

    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, []);

  return (
    <>
      <Header title="Knowledge Graph" />
      <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-4">
        {/* Stats bar */}
        {data && (
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>{data.nodes.length} pages</span>
            <span>{data.edges.length} connections</span>
          </div>
        )}

        {isLoading ? (
          <Card>
            <CardContent className="p-6">
              <Skeleton className="h-96 w-full" />
            </CardContent>
          </Card>
        ) : !data || data.nodes.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-16">
              <Network className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-2">No graph data yet.</p>
              <p className="text-sm text-muted-foreground">
                Create wiki pages with [[wikilinks]] to build the knowledge graph.
              </p>
            </CardContent>
          </Card>
        ) : isMobile ? (
          <MobileGraphFallback nodes={data.nodes} />
        ) : (
          <Card>
            <CardContent className="p-0 overflow-hidden" ref={containerRef}>
              <ForceGraph
                nodes={data.nodes}
                edges={data.edges}
                width={dimensions.width}
                height={dimensions.height}
              />
            </CardContent>
          </Card>
        )}
      </div>
    </>
  );
}
