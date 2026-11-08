
"""
Service-layer operations for AI-interaction persistence.

This module separates database write operations from HTTP request handling.

Responsibilities:
    - Construct AIInteraction ORM objects from validated schema data.
    - Associate each interaction with the server-resolved user identity.
    - Flush changes so database-generated values and constraints are checked.
    - Commit successful writes.
    - Roll back failed transactions before propagating database exceptions.

Authorization is performed by the API route before this service is called.
The database's composite foreign key from (project_id, user_id) to
project membership provides an additional integrity safeguard.
"""

from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.entities import AIInteraction
from app.schemas.interaction import InteractionCreate


def create_interaction(
    db: Session,
    interaction_data: InteractionCreate,
    user_id: UUID,
) -> AIInteraction:
    """
    Persist one AI interaction and return the refreshed ORM object.

    Args:
        db: Active SQLAlchemy session supplied by the database dependency.
        interaction_data: Validated request data from the API layer.
        user_id: UUID of the authenticated development user.

    Returns:
        AIInteraction: The persisted interaction, refreshed from the database.

    Raises:
        SQLAlchemyError: If a database operation fails. The transaction is
            rolled back before the exception is propagated to the API layer.

    Transaction behavior:
        This function owns the transaction for this individual insert.
        It commits on success and rolls back on a SQLAlchemy failure.
        It does not close the session; the request-scoped dependency owns
        session cleanup.
    """

    # The user identity is provided by the server, never by the request body.
    # project_id is retained from the validated request.
    interaction = AIInteraction(
        project_id=interaction_data.project_id,
        user_id=user_id,
        tool_name=interaction_data.tool_name,
        model_name=interaction_data.model_name,
        external_session_ref=interaction_data.external_session_ref,
        prompt=interaction_data.prompt,
        response=interaction_data.response,
    )

    try:
        # Stage the new ORM object in the current session.
        db.add(interaction)

        # Send pending INSERT statements to PostgreSQL before committing.
        # This allows database constraints to reject invalid relationships.
        db.flush()

        # Commit the successful insert as a completed transaction.
        db.commit()

        # Reload generated fields, including the primary key and timestamp.
        db.refresh(interaction)

        return interaction

    except SQLAlchemyError:
        # Do not leave the session in a failed transaction state.
        # The caller can map the original exception to an HTTP response.
        db.rollback()
        raise
