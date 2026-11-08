
# DevTrace Database Schema and Normalization

## 1. Database overview

DevTrace uses PostgreSQL to store software-development provenance. The database records users, projects, memberships, AI interactions, engineering decisions, alternatives, evidence, Git commits, and code changes.

The schema consists of nine relations:

1. `app_user`
2. `project`
3. `project_member`
4. `ai_interaction`
5. `decision`
6. `alternative`
7. `evidence`
8. `git_commit`
9. `code_change`

## 2. First Normal Form (1NF)

A relation satisfies 1NF when each attribute contains an atomic value and repeating groups are not stored within a single field.

In DevTrace, alternatives are stored as separate rows in the `alternative` relation instead of being stored as comma-separated values in a decision record.

This makes individual alternatives easier to retrieve, update, and compare.

## 3. Second Normal Form (2NF)

A relation satisfies 2NF when it satisfies 1NF and every non-key attribute depends on the whole candidate key, not merely part of a composite key.

The `project_member` relation uses the composite primary key:

`(project_id, user_id)`

Attributes such as `role` and `joined_at` describe the membership of a particular user in a particular project. They depend on the combination of project and user, rather than on only one part of the key.

The remaining relations use single-column primary keys, so partial dependency on part of their primary key does not arise.

## 4. Third Normal Form (3NF)

A relation satisfies 3NF when it satisfies 2NF and non-key attributes do not depend transitively on a key through another non-key attribute.

DevTrace separates user, project, and membership information into `app_user`, `project`, and `project_member` rather than duplicating these facts across interaction and change records.

For example, programming-language information should not be redundantly stored in `code_change` when it can be derived from a file path. Similarly, user profile details should not be copied into every AI interaction.

This separation reduces insertion, update, and deletion anomalies.

## 5. Keys and integrity constraints

- Primary keys uniquely identify records.
- `project_member` uses the composite primary key `(project_id, user_id)`.
- Foreign keys enforce relationships between related records.
- Composite foreign keys enforce same-project integrity for linked records where defined by the schema.
- Check constraints restrict valid values, including decision status, provenance origin, confidence, and line counts.
- Nullable provenance links allow a code change to exist when its originating interaction, decision, or commit is unknown.
- Referential integrity rules help preserve historical provenance rather than silently deleting linked records.

## 6. Provenance principle

Missing provenance must remain explicitly unknown. The system must not invent an AI interaction, engineering decision, or rationale merely because a code change occurred near an AI interaction in time.

## 7. Maintenance note

Keep this document synchronized with `app/models/entities.py` and the applied Alembic migrations whenever the database schema changes.
