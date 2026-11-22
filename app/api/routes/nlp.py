"""
app/api/routes/nlp.py

FastAPI routes for on-demand NLP candidate extraction and provenance classification.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.schemas.nlp import (
    CandidateDecisionResponse,
    ExtractionResponse,
    NLPExtractCandidatesRequest,
)
from nlp.llm_engine import LLMUnavailable
from nlp.pipeline import extract_decisions


router = APIRouter(prefix="/nlp", tags=["NLP Studio"])


class SingleTurnNLPExtractRequest(BaseModel):
    """Backwards compatibility for single-turn extraction."""

    prompt: str = Field(..., min_length=1)
    response: str = Field(..., min_length=1)
    project_id: UUID | None = None


@router.post(
    "/extract-candidates",
    response_model=ExtractionResponse,
    summary="Extract proposed candidate decisions from a multi-turn conversation",
)
def extract_candidates(request: NLPExtractCandidatesRequest) -> ExtractionResponse:
    """
    Execute NLP candidate extraction across a multi-turn developer and AI chat transcript.
    Supports rules, llm, or auto engines. Returns 503 if engine=llm and Ollama is unreachable.
    """
    turns = [(t.prompt, t.response) for t in request.turns]

    try:
        result = extract_decisions(
            turns=turns,
            engine=request.engine,
            project_id=request.project_id,
        )
        return ExtractionResponse.model_validate(result)

    except LLMUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Local LLM service is unavailable: {exc}",
        ) from exc


@router.post(
    "/extract-candidate",
    response_model=CandidateDecisionResponse | None,
    summary="Directly extract candidate decision from raw prompt and response (single turn)",
)
def extract_candidate_single(request: SingleTurnNLPExtractRequest) -> CandidateDecisionResponse | None:
    """Backwards-compatible endpoint for single prompt/response pair."""
    result = extract_decisions(
        turns=[(request.prompt, request.response)],
        engine="rules",
        project_id=request.project_id,
    )
    if not result.candidates:
        return None
    return CandidateDecisionResponse.model_validate(result.candidates[0])
