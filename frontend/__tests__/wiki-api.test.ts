import { describe, it, expect, vi, beforeEach } from "vitest";

const mockFetch = vi.fn();
global.fetch = mockFetch;

process.env.NEXT_PUBLIC_API_URL = "http://localhost:8110";

import {
  fetchWikiPages,
  fetchWikiPage,
  createWikiPage,
  updateWikiPage,
  deleteWikiPage,
  fetchWikiGraph,
  triggerCompile,
  fetchCompileStatus,
  fetchCompileHistory,
  wikiLint,
  wikiQuery,
} from "@/lib/api";

describe("Wiki API functions", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("fetchWikiPages sends GET to /wiki/pages", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ pages: [], total: 0 }),
    });

    const result = await fetchWikiPages();
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8110/api/v1/wiki/pages",
      expect.objectContaining({ method: "GET" })
    );
    expect(result.pages).toEqual([]);
  });

  it("fetchWikiPages includes type filter in query", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ pages: [], total: 0 }),
    });

    await fetchWikiPages({ page_type: "concept" });
    const url = mockFetch.mock.calls[0][0];
    expect(url).toContain("page_type=concept");
  });

  it("fetchWikiPages includes search in query", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ pages: [], total: 0 }),
    });

    await fetchWikiPages({ search: "python" });
    const url = mockFetch.mock.calls[0][0];
    expect(url).toContain("search=python");
  });

  it("fetchWikiPage sends GET to /wiki/pages/{slug}", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          id: 1,
          slug: "machine-learning",
          title: "Machine Learning",
        }),
    });

    const result = await fetchWikiPage("machine-learning");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8110/api/v1/wiki/pages/machine-learning",
      expect.objectContaining({ method: "GET" })
    );
    expect(result.slug).toBe("machine-learning");
  });

  it("createWikiPage sends POST to /wiki/pages", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: () =>
        Promise.resolve({ id: 1, slug: "test", title: "Test" }),
    });

    await createWikiPage({
      title: "Test",
      content_markdown: "# Test\nContent",
    });
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8110/api/v1/wiki/pages",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("deleteWikiPage sends DELETE to /wiki/pages/{slug}", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
    });

    await deleteWikiPage("test-page");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8110/api/v1/wiki/pages/test-page",
      expect.objectContaining({ method: "DELETE" })
    );
  });

  it("fetchWikiGraph sends GET to /wiki/graph", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ nodes: [], edges: [] }),
    });

    const result = await fetchWikiGraph();
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8110/api/v1/wiki/graph",
      expect.objectContaining({ method: "GET" })
    );
    expect(result.nodes).toEqual([]);
  });

  it("triggerCompile sends POST to /wiki/compile", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 202,
      json: () => Promise.resolve({ log_id: 1, status: "running" }),
    });

    const result = await triggerCompile({ model: "haiku" });
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8110/api/v1/wiki/compile",
      expect.objectContaining({ method: "POST" })
    );
    expect(result.log_id).toBe(1);
  });

  it("wikiQuery sends POST to /wiki/query", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({ answer: "Test answer", wiki_page: null }),
    });

    const result = await wikiQuery("machine learning");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8110/api/v1/wiki/query",
      expect.objectContaining({ method: "POST" })
    );
    expect(result.answer).toBe("Test answer");
  });
});
