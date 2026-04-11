from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


# --- Tags ---
class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")


class TagResponse(BaseModel):
    id: int
    name: str
    color: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TagWithCount(TagResponse):
    count: int = 0


# --- Notes ---
class NoteCreate(BaseModel):
    content: str = Field(min_length=1)
    markdown_content: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: str = "web_ui"


class NoteUpdate(BaseModel):
    content: str | None = None
    markdown_content: str | None = None


class NoteResponse(BaseModel):
    id: int
    content: str
    markdown_content: str | None
    created_at: datetime
    updated_at: datetime
    source: str
    is_archived: bool
    tags: list[TagResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class NoteListResponse(BaseModel):
    notes: list[NoteResponse]
    total: int


# --- Bookmarks ---
class BookmarkCreate(BaseModel):
    url: HttpUrl
    tags: list[str] = Field(default_factory=list)


class BookmarkUpdate(BaseModel):
    is_read: bool | None = None
    tags: list[str] | None = None


class BookmarkResponse(BaseModel):
    id: int
    original_url: str
    title: str | None
    scraped_content: str | None
    source_domain: str | None
    captured_at: datetime
    is_read: bool
    is_archived: bool
    tags: list[TagResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class BookmarkListResponse(BaseModel):
    bookmarks: list[BookmarkResponse]
    total: int


# --- PDFs ---
class PdfResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    extracted_text: str | None
    page_count: int | None
    file_size: int | None
    uploaded_at: datetime
    is_archived: bool
    tags: list[TagResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PdfListResponse(BaseModel):
    pdfs: list[PdfResponse]
    total: int


# --- Search ---
class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=50)
    llm_model: str = "haiku"


class SearchSource(BaseModel):
    source_type: str
    source_id: int
    title: str | None
    content_preview: str
    score: float
    chunk_id: int


class SearchResponse(BaseModel):
    answer: str
    sources: list[SearchSource]
    usage: dict = Field(default_factory=dict)


class RawSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=50)
    include_scores: bool = False


class RawSearchResponse(BaseModel):
    chunks: list[SearchSource]
    total: int


# --- Settings ---
class SettingsResponse(BaseModel):
    llm_preference: str
    settings: dict

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    llm_preference: str | None = Field(None, pattern=r"^(haiku|sonnet)$")


# --- Tags assignment ---
class TagAssignRequest(BaseModel):
    tag_ids: list[int] = Field(min_length=1)


# --- Wiki ---
WIKI_PAGE_TYPES = Literal[
    "concept", "person", "project", "howto", "reference", "index", "log"
]


class WikiPageCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content_markdown: str = Field(min_length=1)
    page_type: WIKI_PAGE_TYPES = "concept"
    frontmatter: dict = Field(default_factory=dict)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class WikiPageUpdate(BaseModel):
    title: str | None = None
    content_markdown: str | None = None
    page_type: WIKI_PAGE_TYPES | None = None
    frontmatter: dict | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    is_published: bool | None = None
    is_stale: bool | None = None


class WikiLinkRef(BaseModel):
    slug: str
    title: str
    page_type: str

    model_config = {"from_attributes": True}


class WikiSourceRef(BaseModel):
    source_type: str
    source_id: int
    source_hash: str | None = None

    model_config = {"from_attributes": True}


class WikiPageResponse(BaseModel):
    id: int
    slug: str
    title: str
    page_type: str
    content_markdown: str
    frontmatter: dict = Field(default_factory=dict)
    confidence: float
    is_stale: bool
    version: int
    compiled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    backlinks: list[WikiLinkRef] = Field(default_factory=list)
    sources: list[WikiSourceRef] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class WikiPageListResponse(BaseModel):
    pages: list[WikiPageResponse]
    total: int


class CompileRequest(BaseModel):
    source_ids: list[int] | None = None
    force: bool = False
    model: Literal["haiku", "sonnet"] = "haiku"


class CompilationLogResponse(BaseModel):
    id: int
    action: str
    status: str
    sources_processed: int
    pages_created: int
    pages_updated: int
    token_usage: dict = Field(default_factory=dict)
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    details: dict = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class GraphNode(BaseModel):
    id: int
    slug: str
    title: str
    type: str
    link_count: int = 0


class GraphEdge(BaseModel):
    source: int
    target: int
    label: str = ""


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class LintIssue(BaseModel):
    type: str
    slug: str | None = None
    message: str


class LintResponse(BaseModel):
    issues: list[LintIssue]
    stats: dict = Field(default_factory=dict)


class WikiQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    mode: Literal["wiki_first", "search_first", "hybrid"] = "wiki_first"
    limit: int = Field(default=10, ge=1, le=50)
    llm_model: str = "haiku"


class WikiQueryResponse(BaseModel):
    answer: str
    wiki_page: WikiPageResponse | None = None
    sources: list[SearchSource] = Field(default_factory=list)
    usage: dict = Field(default_factory=dict)
