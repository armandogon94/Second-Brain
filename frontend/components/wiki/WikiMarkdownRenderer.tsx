"use client";

import Link from "next/link";
import { convertWikilinks } from "@/lib/wiki-utils";

interface WikiMarkdownRendererProps {
  content: string;
}

export function WikiMarkdownRenderer({ content }: WikiMarkdownRendererProps) {
  // Convert [[wikilinks]] to markdown links, then render
  const converted = convertWikilinks(content);

  // Split by lines and render with basic markdown support
  const lines = converted.split("\n");

  return (
    <div className="wiki-content space-y-2">
      {lines.map((line, i) => {
        // Headers
        if (line.startsWith("### ")) {
          return <h3 key={i} className="text-lg font-semibold mt-4 mb-2">{line.slice(4)}</h3>;
        }
        if (line.startsWith("## ")) {
          return <h2 key={i} className="text-xl font-semibold mt-6 mb-2">{line.slice(3)}</h2>;
        }
        if (line.startsWith("# ")) {
          return <h1 key={i} className="text-2xl font-bold mt-6 mb-3">{line.slice(2)}</h1>;
        }

        // List items
        if (line.startsWith("- ")) {
          return (
            <li key={i} className="ml-4 list-disc">
              <LineContent text={line.slice(2)} />
            </li>
          );
        }

        // Empty lines
        if (line.trim() === "") {
          return <br key={i} />;
        }

        // Regular paragraph
        return (
          <p key={i}>
            <LineContent text={line} />
          </p>
        );
      })}
    </div>
  );
}

function LineContent({ text }: { text: string }) {
  // Parse markdown links: [text](/wiki/slug)
  const parts = text.split(/(\[[^\]]+\]\([^)]+\))/g);

  return (
    <>
      {parts.map((part, i) => {
        const linkMatch = part.match(/\[([^\]]+)\]\(([^)]+)\)/);
        if (linkMatch) {
          const [, linkText, href] = linkMatch;
          if (href.startsWith("/wiki/")) {
            return (
              <Link
                key={i}
                href={href}
                className="text-primary underline hover:text-primary/80"
              >
                {linkText}
              </Link>
            );
          }
          return (
            <a key={i} href={href} className="text-primary underline" target="_blank" rel="noopener noreferrer">
              {linkText}
            </a>
          );
        }

        // Bold
        const boldParts = part.split(/(\*\*[^*]+\*\*)/g);
        return boldParts.map((bp, j) => {
          if (bp.startsWith("**") && bp.endsWith("**")) {
            return <strong key={`${i}-${j}`}>{bp.slice(2, -2)}</strong>;
          }
          return <span key={`${i}-${j}`}>{bp}</span>;
        });
      })}
    </>
  );
}
