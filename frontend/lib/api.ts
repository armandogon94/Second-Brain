const BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8110") + "/api/v1";

async function request<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers: Record<string, string> = {};

  if (body && !(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(url, {
    method,
    headers,
    body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const errorBody = await res.text().catch(() => "Unknown error");
    throw new Error(`API ${method} ${path} failed (${res.status}): ${errorBody}`);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
  delete: <T>(path: string) => request<T>("DELETE", path),
};

// ---- Types ----

export interface Note {
  id: string;
  title: string;
  content: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface Bookmark {
  id: string;
  url: string;
  title: string;
  description: string;
  tags: string[];
  is_read: boolean;
  created_at: string;
}

export interface Pdf {
  id: string;
  filename: string;
  page_count: number;
  file_size: number;
  extracted_text: string;
  created_at: string;
}

export interface Tag {
  id: string;
  name: string;
  color: string;
  item_count: number;
}

export interface SearchResult {
  answer: string;
  sources: SearchSource[];
}

export interface SearchSource {
  id: string;
  content: string;
  source_type: string;
  title: string;
  score: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}

export interface Settings {
  llm_model: string;
  theme: string;
}

// ---- Notes ----

export function fetchNotes(params?: {
  page?: number;
  per_page?: number;
  tag?: string;
  limit?: number;
}) {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.per_page) query.set("per_page", String(params.per_page));
  if (params?.tag) query.set("tag", params.tag);
  if (params?.limit) query.set("limit", String(params.limit));
  const qs = query.toString();
  return api.get<PaginatedResponse<Note>>(`/notes${qs ? `?${qs}` : ""}`);
}

export function fetchNote(id: string) {
  return api.get<Note>(`/notes/${id}`);
}

export function createNote(data: { title: string; content: string; tags?: string[] }) {
  return api.post<Note>("/notes", data);
}

export function updateNote(
  id: string,
  data: { title?: string; content?: string; tags?: string[] }
) {
  return api.put<Note>(`/notes/${id}`, data);
}

export function deleteNote(id: string) {
  return api.delete(`/notes/${id}`);
}

// ---- Bookmarks ----

export function fetchBookmarks(params?: {
  page?: number;
  per_page?: number;
  is_read?: boolean;
  limit?: number;
}) {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.per_page) query.set("per_page", String(params.per_page));
  if (params?.is_read !== undefined) query.set("is_read", String(params.is_read));
  if (params?.limit) query.set("limit", String(params.limit));
  const qs = query.toString();
  return api.get<PaginatedResponse<Bookmark>>(`/bookmarks${qs ? `?${qs}` : ""}`);
}

export function createBookmark(data: { url: string; tags?: string[] }) {
  return api.post<Bookmark>("/bookmarks", data);
}

export function updateBookmark(id: string, data: { is_read?: boolean; tags?: string[] }) {
  return api.put<Bookmark>(`/bookmarks/${id}`, data);
}

export function deleteBookmark(id: string) {
  return api.delete(`/bookmarks/${id}`);
}

// ---- PDFs ----

export function fetchPdfs() {
  return api.get<Pdf[]>("/pdfs");
}

export function uploadPdf(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return api.post<Pdf>("/pdfs", formData);
}

export function deletePdf(id: string) {
  return api.delete(`/pdfs/${id}`);
}

// ---- Search ----

export function search(query: string, model?: string) {
  return api.post<SearchResult>("/search", { query, model });
}

export function rawSearch(query: string) {
  return api.post<SearchSource[]>("/search/raw", { query });
}

// ---- Tags ----

export function fetchTags() {
  return api.get<Tag[]>("/tags");
}

export function createTag(data: { name: string; color: string }) {
  return api.post<Tag>("/tags", data);
}

export function deleteTag(id: string) {
  return api.delete(`/tags/${id}`);
}

// ---- Settings ----

export function fetchSettings() {
  return api.get<Settings>("/settings");
}

export function updateSettings(data: Partial<Settings>) {
  return api.put<Settings>("/settings", data);
}
