"""Wiki compilation endpoints — trigger, status, history."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import CompilationLog
from app.schemas import CompilationLogResponse, CompileRequest
from app.services.wiki_compilation_service import compile_wiki

router = APIRouter()


async def run_compilation(
    db: AsyncSession, *, user_id: int, model: str, force: bool, source_ids: list[int] | None
) -> None:
    """Background task wrapper for compilation."""
    await compile_wiki(
        db, user_id=user_id, model=model, force=force, source_ids=source_ids
    )


@router.post("", status_code=202)
async def trigger_compile(
    req: CompileRequest,
    db: AsyncSession = Depends(get_db),
):
    """Start a wiki compilation run."""
    # Create initial log entry
    log = CompilationLog(
        user_id=1,
        action="compile",
        status="running",
    )
    db.add(log)
    await db.flush()
    log_id = log.id

    # Run compilation (in foreground for tests, background in prod)
    await run_compilation(
        db,
        user_id=1,
        model=req.model,
        force=req.force,
        source_ids=req.source_ids,
    )

    # Refresh log status
    result = await db.execute(
        select(CompilationLog).where(CompilationLog.id == log_id)
    )
    log = result.scalar_one()

    return {"log_id": log_id, "status": log.status}


@router.get("/history")
async def compile_history(db: AsyncSession = Depends(get_db)):
    """Get compilation run history."""
    result = await db.execute(
        select(CompilationLog)
        .where(CompilationLog.user_id == 1)
        .order_by(CompilationLog.started_at.desc())
        .limit(50)
    )
    logs = result.scalars().all()
    return [CompilationLogResponse.model_validate(l) for l in logs]


@router.get("/{log_id}", response_model=CompilationLogResponse)
async def compile_status(log_id: int, db: AsyncSession = Depends(get_db)):
    """Check status of a compilation run."""
    result = await db.execute(
        select(CompilationLog).where(
            CompilationLog.id == log_id, CompilationLog.user_id == 1
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Compilation log not found")
    return CompilationLogResponse.model_validate(log)
