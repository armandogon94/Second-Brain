from datetime import datetime

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
