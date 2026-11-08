
"""
DevTrace User API Routes
========================

Purpose
-------
Provides the HTTP endpoint for registering application users. It validates
incoming registration data, checks for an existing email address, persists
a new User entity, and returns the created user through UserResponse.

Registration Flow
-----------------
1. FastAPI validates the request against UserCreate.
2. The route checks whether the normalized email is already registered.
3. The route creates a User with the default developer role.
4. The database enforces the unique email constraint.
5. The transaction is committed and the generated user fields are returned.

Data Integrity and Transactions
-------------------------------
The preliminary email lookup gives clients a clear conflict response when
an address already exists. It is not sufficient by itself to prevent
concurrent duplicate registrations, so the database unique constraint
remains the final authority.

If an insert fails, the session is rolled back before an HTTP error is
returned. This keeps the session from remaining in a failed transaction.

Security Considerations
-----------------------
This endpoint is a basic development registration flow. It does not verify
email ownership, create credentials, issue tokens, or establish a secure
authenticated session. It assigns the developer role on the server rather
than trusting a role supplied by the client.

A production registration flow should include appropriate abuse prevention,
email verification, and a separate secure authentication mechanism.

Dependencies
------------
- app.db.session.get_db: request-scoped database session.
- app.models.entities.User: SQLAlchemy user entity.
- app.schemas.user: validated registration and response schemas.
- SQLAlchemy exceptions: database-integrity and persistence error handling.

This module does not create projects or assign project memberships.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import User
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])

# FastAPI creates and cleans up the request-scoped session through get_db.
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    user_data: UserCreate,
    db: DatabaseSession,
) -> User:
    """
    Register a new developer account.

    The request schema normalizes and validates the supplied name and email.
    The endpoint assigns the default developer role itself; the client cannot
    choose a role through UserCreate.

    Args:
        user_data: Validated registration details.
        db: Request-scoped SQLAlchemy session.

    Returns:
        The persisted User entity, serialized using UserResponse.

    Raises:
        HTTPException: HTTP 409 if the email is already registered or a
            concurrent registration violates the database unique constraint.
            HTTP 500 is returned for an unexpected database failure.

    Transaction Behaviour:
        The user insert is committed only after it succeeds. Database
        failures trigger a rollback before the error is translated into
        an HTTP response.
    """
    # Perform an early lookup so an ordinary duplicate registration receives
    # a clear response instead of relying on a database exception.
    existing_user = db.scalar(
        select(User).where(User.email == user_data.email)
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    # Assign the role on the server. Never trust a public registration
    # payload to grant itself an elevated role.
    user = User(
        name=user_data.name,
        email=user_data.email,
        role="developer",
    )

    try:
        db.add(user)

        # Commit persists the new row and allows database-generated values
        # to be made available for the response.
        db.commit()

        # Refresh the entity so server-generated values, such as created_at,
        # are loaded before FastAPI serializes the response.
        db.refresh(user)

        return user

    except IntegrityError as exc:
        # A concurrent request may have inserted the same email after the
        # preliminary lookup. The unique database constraint catches that
        # race; rollback is required before the session can be reused.
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        ) from exc

    except SQLAlchemyError as exc:
        # Roll back any failed database transaction before returning a
        # generic server error without exposing internal database details.
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while registering the user.",
        ) from exc
