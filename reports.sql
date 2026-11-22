-- ============================================================================
-- DevTrace: Intelligent Software Development Provenance System
-- Phase 6: Analytical SQL Reports, Views, Stored Functions & Index Benchmarks
-- ============================================================================
-- 
-- Usage:
--     psql -d devtrace_db -f reports.sql
--
-- Contents:
--     Report 1: Line-Level Code Provenance ("Explain this line")
--     Report 2: Recursive Decision Evolution Lineage (WITH RECURSIVE CTE)
--     Report 3: AI vs. Human Code Contribution Percentage Report
--     Report 4: AI Assistant & Model Effectiveness Breakdown
--     Report 5: Developer Activity & Responsibility Matrix
--     Report 6: Unattributed Code Changes (via View: changes_missing_provenance)
--     Report 7: AI Review Priority List (Untouched AI Code)
--     Report 8: Stored Function Demonstration (get_project_provenance_summary)
--     Report 9: Partial Index Execution Plan Benchmark (EXPLAIN ANALYZE)
-- ============================================================================

\pset null 'NULL'
\echo '========================================================================'
\echo ' DevTrace Analytics & Relational Verification Report'
\echo '========================================================================'

-- ----------------------------------------------------------------------------
-- Report 1: Line-Level Code Provenance ("Explain this line")
-- Traces a specific file and line range back to the commit, prompt, AI tool,
-- model, decision, and explicit architectural reason that caused it.
-- ----------------------------------------------------------------------------
\echo ''
\echo '>>> REPORT 1: Line-Level Code Provenance (db/schema.sql, Line 25)'
\echo ''

SELECT
    cc.file_path,
    cc.line_start || '-' || cc.line_end AS affected_lines,
    cc.origin,
    cc.confidence,
    SUBSTRING(gc.commit_hash, 1, 10) AS commit_hash,
    gc.message AS commit_message,
    ai.tool_name,
    ai.model_name,
    SUBSTRING(ai.prompt, 1, 65) || '...' AS prompt_summary,
    d.title AS decision_title,
    d.reason_text AS architectural_rationale
FROM code_change cc
JOIN git_commit gc ON cc.commit_id = gc.commit_id
LEFT JOIN ai_interaction ai ON cc.interaction_id = ai.interaction_id
LEFT JOIN decision d ON cc.decision_id = d.decision_id
WHERE cc.file_path = 'db/schema.sql'
  AND 25 BETWEEN cc.line_start AND cc.line_end;


-- ----------------------------------------------------------------------------
-- Report 2: Recursive Decision Evolution Lineage (WITH RECURSIVE)
-- Traces architectural decisions replaced over time (e.g. JWT -> Redis sessions).
-- ----------------------------------------------------------------------------
\echo ''
\echo '>>> REPORT 2: Recursive Decision Replacement Lineage'
\echo ''

WITH RECURSIVE decision_lineage AS (
    -- Anchor member: Initial superseded decisions
    SELECT
        d.decision_id,
        d.project_id,
        d.title,
        d.decision_type,
        d.status,
        d.replaced_by_decision_id,
        1 AS generation,
        d.title::text AS lineage_path
    FROM decision d
    WHERE d.replaced_by_decision_id IS NOT NULL

    UNION ALL

    -- Recursive member: Traverse through replacement references
    SELECT
        replacement.decision_id,
        replacement.project_id,
        replacement.title,
        replacement.decision_type,
        replacement.status,
        replacement.replaced_by_decision_id,
        dl.generation + 1,
        dl.lineage_path || ' -> ' || replacement.title
    FROM decision replacement
    JOIN decision_lineage dl ON dl.replaced_by_decision_id = replacement.decision_id
)
SELECT
    generation,
    title AS active_decision,
    status AS current_status,
    lineage_path AS evolution_history
FROM decision_lineage
ORDER BY generation DESC;


-- ----------------------------------------------------------------------------
-- Report 3: AI vs. Human Code Contribution Percentage Report
-- Calculates exact line metrics and percentage of code authored by AI vs human.
-- ----------------------------------------------------------------------------
\echo ''
\echo '>>> REPORT 3: AI vs. Human Code Contribution by File'
\echo ''

SELECT
    p.project_name,
    cc.file_path,
    COUNT(*) AS total_changes,
    SUM(cc.lines_added) AS total_lines_added,
    SUM(CASE WHEN cc.origin IN ('ai_exact', 'ai_inferred') THEN cc.lines_added ELSE 0 END) AS ai_lines_added,
    SUM(CASE WHEN cc.origin = 'human' THEN cc.lines_added ELSE 0 END) AS human_lines_added,
    ROUND(
        100.0 * SUM(CASE WHEN cc.origin IN ('ai_exact', 'ai_inferred') THEN cc.lines_added ELSE 0 END) /
        NULLIF(SUM(cc.lines_added), 0),
        1
    ) AS ai_percentage
FROM code_change cc
JOIN project p ON cc.project_id = p.project_id
GROUP BY p.project_name, cc.file_path
ORDER BY ai_percentage DESC;


-- ----------------------------------------------------------------------------
-- Report 4: AI Assistant & Model Effectiveness Breakdown
-- Measures code volume, interactions, and average provenance confidence per tool.
-- ----------------------------------------------------------------------------
\echo ''
\echo '>>> REPORT 4: AI Tool and Model Productivity Summary'
\echo ''

SELECT
    ai.tool_name,
    ai.model_name,
    COUNT(DISTINCT ai.interaction_id) AS total_interactions,
    COUNT(DISTINCT cc.change_id) AS generated_changes,
    COALESCE(SUM(cc.lines_added), 0) AS total_lines_added,
    ROUND(AVG(cc.confidence)::numeric, 2) AS avg_confidence
FROM ai_interaction ai
LEFT JOIN code_change cc ON ai.interaction_id = cc.interaction_id
GROUP BY ai.tool_name, ai.model_name
ORDER BY total_lines_added DESC;


-- ----------------------------------------------------------------------------
-- Report 5: Developer Activity & Responsibility Matrix
-- Combines project membership with commits, AI usage, and decisions owned.
-- ----------------------------------------------------------------------------
\echo ''
\echo '>>> REPORT 5: Developer Activity & Decision Ownership Matrix'
\echo ''

SELECT
    u.name AS developer_name,
    pm.role AS project_role,
    p.project_name,
    COUNT(DISTINCT gc.commit_id) AS commits_authored,
    COUNT(DISTINCT ai.interaction_id) AS ai_sessions_conducted,
    COUNT(DISTINCT d.decision_id) AS decisions_recorded
FROM project_member pm
JOIN app_user u ON pm.user_id = u.user_id
JOIN project p ON pm.project_id = p.project_id
LEFT JOIN git_commit gc ON pm.project_id = gc.project_id AND pm.user_id = gc.user_id
LEFT JOIN ai_interaction ai ON pm.project_id = ai.project_id AND pm.user_id = ai.user_id
LEFT JOIN decision d ON pm.project_id = d.project_id AND d.interaction_id = ai.interaction_id
GROUP BY u.name, pm.role, p.project_name
ORDER BY commits_authored DESC;


-- ----------------------------------------------------------------------------
-- Report 6: Unattributed Code Changes (Using View: changes_missing_provenance)
-- Identifies technical debt where code lacks both AI telemetry and decision links.
-- ----------------------------------------------------------------------------
\echo ''
\echo '>>> REPORT 6: Unattributed Changes (View: changes_missing_provenance)'
\echo ''

SELECT
    cmp.change_id,
    p.project_name,
    cmp.file_path,
    cmp.origin,
    cmp.changed_at
FROM changes_missing_provenance cmp
JOIN project p ON cmp.project_id = p.project_id;


-- ----------------------------------------------------------------------------
-- Report 7: AI Review Priority List (Untouched AI-Generated Code)
-- AI-written code (ai_exact) that has NEVER been modified by a human developer.
-- ----------------------------------------------------------------------------
\echo ''
\echo '>>> REPORT 7: AI Review Priority List (AI Code Never Edited by Humans)'
\echo ''

SELECT
    cc.change_id,
    p.project_name,
    cc.file_path,
    cc.lines_added,
    cc.line_start || '-' || cc.line_end AS line_range,
    cc.origin,
    cc.changed_at,
    d.title AS linked_decision
FROM code_change cc
JOIN project p ON cc.project_id = p.project_id
LEFT JOIN decision d ON cc.decision_id = d.decision_id
WHERE cc.origin = 'ai_exact'
  AND NOT EXISTS (
      SELECT 1
      FROM code_change human_edit
      WHERE human_edit.file_path = cc.file_path
        AND human_edit.origin = 'human'
        AND human_edit.changed_at > cc.changed_at
  )
ORDER BY cc.changed_at ASC;


-- ----------------------------------------------------------------------------
-- Report 8: Stored Function Demonstration
-- Invokes get_project_provenance_summary(UUID) for CampusCart.
-- ----------------------------------------------------------------------------
\echo ''
\echo '>>> REPORT 8: Project Provenance Summary Stored Function'
\echo ''

SELECT * FROM get_project_provenance_summary('d3b07384-d113-4c92-b0b2-320d9f4c3912'::uuid);


-- ----------------------------------------------------------------------------
-- Report 9: Partial Index Execution Plan Benchmark (EXPLAIN ANALYZE)
-- Demonstrates query optimization using idx_code_change_unattributed.
-- ----------------------------------------------------------------------------
\echo ''
\echo '>>> REPORT 9: Partial Index Execution Plan (idx_code_change_unattributed)'
\echo ''

EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT change_id, project_id, file_path, origin
FROM code_change
WHERE interaction_id IS NULL AND decision_id IS NULL;

\echo ''
\echo '========================================================================'
\echo ' End of DevTrace Analytics & Relational Verification Report'
\echo '========================================================================'
