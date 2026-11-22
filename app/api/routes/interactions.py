
"""
FastAPI routes for recording AI interactions.

Endpoint:
    POST /interactions

Request flow:
    1. Resolve the database session.
    2. Resolve the current user through the existing X-User-ID dependency.
    3. Validate the request body using InteractionCreate.
    4. Check that the user belongs to the requested project.
    5. Persist the interaction through the service layer.
    6. Return the persisted record using InteractionResponse.

Authorization:
    Project membership is checked before an interaction is inserted.
    A non-member receives 404 so the endpoint does not disclose whether
    a project exists but belongs to somebody else.

The database composite foreign key on (project_id, user_id) provides
additional integrity enforcement if membership changes or a conflicting
write occurs between application-level validation and insertion.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.dependencies import CurrentUser, DatabaseSession
from app.models.entities import AIInteraction, ProjectMember
from app.schemas.decision import (
    CandidateAlternativeResponse,
    CandidateDecisionResponse,
)
from app.schemas.interaction import (
    InteractionCreate,
    InteractionResponse,
)
from app.services.interaction_service import create_interaction
from nlp.decision_extractor import extract_candidate_decision


router = APIRouter(
    prefix="/interactions",
    tags=["AI Interactions"],
)


@router.post(
    "",
    response_model=InteractionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an AI interaction",
    response_description="The persisted AI interaction",
)
def ingest_interaction(
    interaction_data: InteractionCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> InteractionResponse:
    """
    Create an AI-interaction record for a project the current user belongs to.

    Args:
        interaction_data: Validated project, tool, model, prompt, and response
            data supplied by the client.
        db: Request-scoped SQLAlchemy session.
        current_user: User resolved by the existing authentication dependency.

    Returns:
        InteractionResponse: The persisted record, including its generated
        interaction UUID and database creation timestamp.

    Raises:
        HTTPException 404: The current user is not a member of the requested
            project, or the project/user relationship cannot be established.
        HTTPException 409: A database integrity constraint rejects the insert.
        HTTPException 500: An unexpected database operation fails.
    """

    # Verify the exact project/user membership pair. Checking project existence
    # alone would not be sufficient: a valid project may belong to another user.
    membership_statement = select(ProjectMember).where(
        ProjectMember.project_id == interaction_data.project_id,
        ProjectMember.user_id == current_user.user_id,
    )

    membership = db.scalar(membership_statement)

    if membership is None:
        # Do not reveal whether a non-member's requested project exists.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    try:
        # The service derives user_id from the resolved user object.
        # The client cannot impersonate another user through the JSON body.
        interaction = create_interaction(
            db=db,
            interaction_data=interaction_data,
            user_id=current_user.user_id,
        )

        return InteractionResponse.model_validate(interaction)

    except IntegrityError as exc:
        # A database constraint may reject the write, for example if the
        # membership relationship becomes invalid before the INSERT commits.
        # Avoid exposing SQL or database internals in the HTTP response.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The interaction conflicts with a database constraint.",
        ) from exc

    except SQLAlchemyError as exc:
        # The service has already rolled back failed SQLAlchemy transactions.
        # Return a generic error instead of leaking connection details.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The interaction could not be saved.",
        ) from exc


@router.post(
    "/{interaction_id}/extract-candidates",
    response_model=CandidateDecisionResponse | None,
    summary="Extract candidate decisions from an AI interaction using NLP",
)
def extract_candidates_from_interaction(
    interaction_id: UUID,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> CandidateDecisionResponse | None:
    """
    Scan an interaction transcript to detect engineering choices, rationale,
    and alternatives, returning a proposed candidate decision for human review.
    """
    interaction = db.get(AIInteraction, interaction_id)
    if interaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interaction not found.",
        )

    # Require project membership
    membership = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == interaction.project_id,
            ProjectMember.user_id == current_user.user_id,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interaction not found.",
        )

    candidate = extract_candidate_decision(
        prompt=interaction.prompt,
        response=interaction.response,
        project_id=interaction.project_id,
        interaction_id=interaction.interaction_id,
    )
    if candidate is None:
        return None

    return CandidateDecisionResponse(
        title=candidate.title,
        description=candidate.description,
        decision_type=candidate.decision_type,
        status=candidate.status,
        reason_text=candidate.reason_text,
        reason_source_type=candidate.reason_source_type,
        reason_confidence=candidate.reason_confidence,
        alternatives=[
            CandidateAlternativeResponse(
                description=a.description,
                selection_status=a.selection_status,
            )
            for a in candidate.alternatives
        ],
        project_id=candidate.project_id,
        interaction_id=candidate.interaction_id,
    )

