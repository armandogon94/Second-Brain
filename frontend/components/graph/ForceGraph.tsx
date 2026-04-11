"use client";

import { useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import type { GraphNode, GraphEdge } from "@/lib/api";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

const TYPE_COLORS: Record<string, string> = {
  concept: "#3b82f6",
  person: "#22c55e",
  project: "#a855f7",
  howto: "#f97316",
  reference: "#6b7280",
  index: "#eab308",
  log: "#ef4444",
};

interface ForceGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  width: number;
  height: number;
}

export function ForceGraph({ nodes, edges, width, height }: ForceGraphProps) {
  const router = useRouter();
  const fgRef = useRef<any>(null);

  const graphData = {
    nodes: nodes.map((n) => ({
      id: n.id,
      name: n.title,
      slug: n.slug,
      type: n.type,
      val: Math.max(2, n.link_count + 1),
    })),
    links: edges.map((e) => ({
      source: e.source,
      target: e.target,
      label: e.label,
    })),
  };

  const handleNodeClick = useCallback(
    (node: any) => {
      if (node.slug) {
        router.push(`/wiki/${node.slug}`);
      }
    },
    [router]
  );

  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = node.name;
      const fontSize = 12 / globalScale;
      const radius = Math.max(4, (node.val || 1) * 2);
      const color = TYPE_COLORS[node.type] || TYPE_COLORS.concept;

      // Draw circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
      ctx.fillStyle = color;
      ctx.fill();

      // Draw label
      ctx.font = `${fontSize}px Sans-Serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillStyle = "#888";
      ctx.fillText(label, node.x, node.y + radius + 2);
    },
    []
  );

  return (
    <ForceGraph2D
      ref={fgRef}
      graphData={graphData}
      width={width}
      height={height}
      nodeCanvasObject={nodeCanvasObject}
      onNodeClick={handleNodeClick}
      nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
        const radius = Math.max(4, (node.val || 1) * 2);
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius + 4, 0, 2 * Math.PI, false);
        ctx.fillStyle = color;
        ctx.fill();
      }}
      linkColor={() => "rgba(100,100,100,0.3)"}
      linkWidth={1}
      cooldownTime={2000}
    />
  );
}
