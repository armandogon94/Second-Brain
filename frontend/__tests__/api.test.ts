import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Set env before import
process.env.NEXT_PUBLIC_API_URL = "http://localhost:8110";

import { api, fetchNotes, createNote, fetchTags, search } from "@/lib/api";

describe("API Client", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("makes GET requests correctly", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ data: "test" }),
    });

    const result = await api.get("/test");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8110/api/v1/test",
      expect.objectContaining({ method: "GET" })
    );
    expect(result).toEqual({ data: "test" });
  });

  it("makes POST requests with JSON body", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ id: 1 }),
    });

    await api.post("/notes", { content: "test" });
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8110/api/v1/notes",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ content: "test" }),
      })
    );
  });

  it("handles 204 No Content", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
    });

    const result = await api.delete("/notes/1");
    expect(result).toBeUndefined();
  });

  it("throws on error responses", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      text: () => Promise.resolve("Not Found"),
    });

    await expect(api.get("/notes/999")).rejects.toThrow("API GET /notes/999 failed (404)");
  });
});

describe("fetchNotes", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("fetches notes with default params", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ items: [], total: 0 }),
    });

    await fetchNotes();
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8110/api/v1/notes",
      expect.any(Object)
    );
  });

  it("includes tag filter in query", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ items: [], total: 0 }),
    });

    await fetchNotes({ tag: "python" });
    const url = mockFetch.mock.calls[0][0];
    expect(url).toContain("tag=python");
  });
});

describe("createNote", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("sends note data correctly", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: () => Promise.resolve({ id: 1, content: "test" }),
    });

    await createNote({ title: "Test", content: "test content" });
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8110/api/v1/notes",
      expect.objectContaining({ method: "POST" })
    );
  });
});

describe("fetchTags", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("fetches tags", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve([
          { id: "1", name: "python", color: "#3572A5", item_count: 5 },
        ]),
    });

    const tags = await fetchTags();
    expect(tags).toHaveLength(1);
    expect(tags[0].name).toBe("python");
  });
});

describe("search", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("sends search query", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          answer: "Test answer",
          sources: [],
        }),
    });

    const result = await search("what is pgvector?");
    expect(result.answer).toBe("Test answer");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8110/api/v1/search",
      expect.objectContaining({ method: "POST" })
    );
  });
});
