from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id
from app.db.session import get_db
from app.eval.loader import list_datasets, load_dataset
from app.eval.runner import evaluate_cases
from app.models.eval import EvalDataset, EvalRun
from app.rag.pipeline import RagPipeline
from app.schemas.eval import EvalRunRead, EvalRunRequest, EvalRunResponse

router = APIRouter(prefix="/eval", tags=["eval"])


@router.get("/datasets")
def datasets() -> dict[str, list[str]]:
    """列出内置评测集。"""
    return {"datasets": list_datasets()}


@router.get("/runs", response_model=list[EvalRunRead])
def list_eval_runs(
    limit: int = 10,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> list[EvalRunRead]:
    """列出最近的评测记录。"""
    stmt = (
        select(EvalRun, EvalDataset.name)
        .join(EvalDataset, EvalRun.dataset_id == EvalDataset.id)
        .where(EvalDataset.tenant_id == tenant_id)
        .order_by(EvalRun.created_at.desc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [
        EvalRunRead(
            id=run.id,
            dataset_name=dataset_name,
            hit_rate=run.recall_at_5,
            mrr=run.mrr,
            metrics=run.metrics,
            created_at=run.created_at,
        )
        for run, dataset_name in rows
    ]


@router.post("/runs", response_model=EvalRunResponse)
def run_eval(
    payload: EvalRunRequest,
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
) -> EvalRunResponse:
    """运行内置评测集并返回指标。"""
    try:
        cases = load_dataset(payload.dataset_name)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    pipeline = RagPipeline(db=db, tenant_id=tenant_id)
    metrics = evaluate_cases(
        cases=cases,
        retrieve_fn=pipeline.retrieve,
        answer_fn=lambda question, chunks: pipeline.answer_from_chunks(question, chunks).answer,
        top_k=payload.top_k,
    )

    dataset = db.execute(
        select(EvalDataset).where(
            EvalDataset.tenant_id == tenant_id,
            EvalDataset.name == payload.dataset_name,
        )
    ).scalar_one_or_none()
    if dataset is None:
        dataset = EvalDataset(
            tenant_id=tenant_id,
            name=payload.dataset_name,
            description="内置 RAG 评测集",
        )
        db.add(dataset)
        db.flush()

    summary_metrics = {
        "hit_rate": float(metrics["hit_rate"]),
        "mrr": float(metrics["mrr"]),
        "avg_answer_keyword_coverage": float(metrics["avg_answer_keyword_coverage"]),
        "cases": float(metrics["cases"]),
    }
    db.add(
        EvalRun(
            dataset_id=dataset.id,
            recall_at_5=float(metrics["hit_rate"]),
            mrr=float(metrics["mrr"]),
            metrics={"summary": summary_metrics, "results": metrics["results"]},
        )
    )
    db.commit()

    return EvalRunResponse(
        status="ok",
        message=f"完成 {metrics['cases']} 条评测",
        metrics=summary_metrics,
        results=metrics["results"],
    )
