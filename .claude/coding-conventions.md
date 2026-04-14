# Coding Conventions

## Python Backend

- **Python version:** 3.12+
- **Async throughout:** Use async/await for all I/O (database, API calls)
- **Type hints:** Required on all function signatures
- **Pydantic models:** For all request/response schemas
- **SQLAlchemy 2.0 style:** Use mapped_column, DeclarativeBase
- **ORM queries:** Use async session, select() expressions, not string-based
- **Logging:** Use standard library logging with JSON format
- **Linting:** ruff (black + isort + flake8 in one)
- **Line length:** 100 characters (ruff default)
- **Naming:** snake_case for functions/variables, PascalCase for classes
- **Error handling:** Raise descriptive HTTPException for API errors, log all errors
- **Testing:** pytest with async support (AsyncClient), factories (factory_boy), mocked APIs
- **Dependencies:** Managed via pyproject.toml (using uv), pinned versions

### Example Python Function

```python
async def get_notes_by_tag(
    tag_id: int,
    session: AsyncSession = Depends(get_db),
) -> list[NoteResponse]:
    """Retrieve all notes assigned to a tag."""
    stmt = select(Note).where(Note.tag_id == tag_id)
    result = await session.execute(stmt)
    notes = result.scalars().all()
    return [NoteResponse.from_orm(n) for n in notes]
```

## TypeScript Frontend

- **TypeScript strict mode:** Enabled (strictNullChecks, noImplicitAny)
- **React Server Components:** Use by default, only client components when needed
- **Client components:** Only for interactivity (search, forms, modals)
- **TailwindCSS:** All styling, no CSS modules
- **Zod:** For runtime form validation (not just TypeScript types)
- **Component structure:** Atomic (button, badge) → Compound (card) → Feature (SearchBar)
- **Props:** Type with interfaces, destructure in params
- **Naming:** camelCase for functions/variables, PascalCase for components
- **Imports:** Use `@/*` path alias, group standard → local → relative
- **Testing:** vitest + React Testing Library, test user interactions not implementation
- **Linting:** ESLint + Prettier (via package.json scripts)

### Example React Component

```typescript
interface SearchBarProps {
  onSearch: (query: string) => Promise<void>;
  placeholder?: string;
}

export function SearchBar({ onSearch, placeholder }: SearchBarProps) {
  const [query, setQuery] = useState('');

  const debouncedSearch = useDebounce(async () => {
    if (query.trim()) await onSearch(query);
  }, 300);

  return (
    <input
      value={query}
      onChange={(e) => {
        setQuery(e.target.value);
        debouncedSearch();
      }}
      placeholder={placeholder}
      className="w-full px-3 py-2 border rounded-md"
    />
  );
}
```

## Code Organization

### Backend Module Structure

```
app/
├── main.py              # FastAPI app, routes, lifespan
├── config.py            # Settings (env vars, defaults)
├── database.py          # Engine, session, dependency
├── models.py            # SQLAlchemy ORM classes
├── schemas.py           # Pydantic request/response
├── api/                 # Route handlers (one per resource)
├── services/            # Business logic (re-usable functions)
└── utils/               # Helpers (logging, tokenization, etc.)
```

### Frontend Module Structure

```
app/
├── layout.tsx           # Root layout, providers
├── page.tsx             # Dashboard
├── [feature]/           # Feature pages (notes, search, etc.)
├── api/                 # Route handlers (if needed)
components/
├── ui/                  # shadcn base components
├── features/            # Feature-specific components
lib/
├── api.ts               # API client wrapper
├── store.ts             # State management (Zustand)
└── utils.ts             # Helpers
```

## Testing Standards

### Backend

- pytest with async support
- Fixtures for setup/teardown
- Mock external APIs (OpenAI, Anthropic, Telegram)
- Test both happy path and error cases
- Use factory_boy for complex object creation
- Aim for >85% coverage

### Frontend

- vitest for unit tests
- React Testing Library for component tests
- Test user interactions, not implementation details
- Mock API calls with MSW or jest.mock()
- Aim for >80% coverage for critical paths
