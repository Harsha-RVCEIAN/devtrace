"""
DevTrace ORM entity models.

This module re-exports all SQLAlchemy entities defined in app.models.entities,
ensuring they are registered with Base.metadata whenever app.models is imported.
"""

from app.models.entities import (
    AIInteraction,
    Alternative,
    CodeChange,
    Decision,
    Evidence,
    GitCommit,
    Project,
    ProjectMember,
    User,
)

__all__ = [
    "AIInteraction",
    "Alternative",
    "CodeChange",
    "Decision",
    "Evidence",
    "GitCommit",
    "Project",
    "ProjectMember",
    "User",
]
