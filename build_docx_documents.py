import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from pathlib import Path

# Clean, simple student styling (Black & White / Charcoal)
COLOR_TEXT = RGBColor(0, 0, 0)
COLOR_MUTED = RGBColor(80, 80, 80)

def set_cell_background(cell, hex_color="FFFFFF"):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_padding(cell, top=80, bottom=80, left=100, right=100):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def add_clean_heading_1(doc, text):
    h = doc.add_paragraph()
    h.paragraph_format.space_before = Pt(14)
    h.paragraph_format.space_after = Pt(4)
    run = h.add_run(text)
    run.font.name = "Arial"
    run.font.size = Pt(13)
    run.font.bold = True
    return h

def add_clean_heading_2(doc, text):
    h = doc.add_paragraph()
    h.paragraph_format.space_before = Pt(10)
    h.paragraph_format.space_after = Pt(2)
    run = h.add_run(text)
    run.font.name = "Arial"
    run.font.size = Pt(11)
    run.font.bold = True
    return h

def format_table_header(row, titles):
    for i, t in enumerate(titles):
        c = row.cells[i]
        set_cell_background(c, "E5E5E5")  # Classic academic light gray
        set_cell_padding(c, top=100, bottom=100, left=100, right=100)
        p = c.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(t)
        r.font.name = "Arial"
        r.font.size = Pt(9.5)
        r.font.bold = True

def populate_table_rows(table, rows_data):
    for r_idx, r_data in enumerate(rows_data):
        row = table.rows[r_idx + 1]
        for c_idx, val in enumerate(r_data):
            c = row.cells[c_idx]
            set_cell_background(c, "FFFFFF")
            set_cell_padding(c, top=60, bottom=60, left=100, right=100)
            p = c.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(str(val))
            r.font.name = "Arial"
            r.font.size = Pt(9)

# =============================================================================
# DOCUMENT 1: NORMALIZATION & DECOMPOSITION (CONCISE & TEXTBOOK-ACCURATE)
# =============================================================================
print("Building compact, human-style Normalization Docx...")
doc1 = Document()

for s in doc1.sections:
    s.top_margin = Inches(0.8)
    s.bottom_margin = Inches(0.8)
    s.left_margin = Inches(0.8)
    s.right_margin = Inches(0.8)

# Title
t = doc1.add_paragraph()
t.paragraph_format.space_before = Pt(0)
t.paragraph_format.space_after = Pt(2)
r_t = t.add_run("Relational Database Normalization: DevTrace System")
r_t.font.name = "Arial"
r_t.font.size = Pt(16)
r_t.font.bold = True

sub = doc1.add_paragraph()
sub.paragraph_format.space_after = Pt(10)
r_sub = sub.add_run("DBMS Lab Project Report — Step-by-Step Functional Dependency Decomposition (1NF → 2NF → 3NF)")
r_sub.font.name = "Arial"
r_sub.font.size = Pt(10)
r_sub.font.color.rgb = COLOR_MUTED

# 1. Unnormalized Schema (UNF)
add_clean_heading_1(doc1, "1. Unnormalized Form (UNF)")
p = doc1.add_paragraph(
    "Initially, all software development provenance data is recorded in a single unnormalized relation containing multi-valued repeating groups:"
)
p.paragraph_format.space_after = Pt(3)

code_p = doc1.add_paragraph()
code_p.paragraph_format.space_after = Pt(6)
r_code = code_p.add_run(
    "DEV_SESSION_UNF ( project_id, project_name, repo_url, user_id, user_name, user_email,\n"
    "                 member_role, joined_at, interaction_id, tool_name, prompt, response,\n"
    "                 decision_id, decision_title, status, reason_text,\n"
    "                 { alternative_id, alt_description, selection_status },\n"
    "                 { evidence_id, evidence_type, source_reference },\n"
    "                 commit_hash, commit_message, commit_time,\n"
    "                 { file_path, change_type, origin, lines_added, lines_deleted } )"
)
r_code.font.name = "Courier New"
r_code.font.size = Pt(8.5)

# 2. Conversion to 1NF
add_clean_heading_1(doc1, "2. First Normal Form (1NF)")
p = doc1.add_paragraph(
    "To achieve 1NF, we remove repeating groups ({alternatives}, {evidence}, {code_changes}) so that all attributes are atomic scalar values:"
)
p.paragraph_format.space_after = Pt(4)

tbl_1nf = doc1.add_table(rows=5, cols=3)
tbl_1nf.alignment = WD_TABLE_ALIGNMENT.CENTER
format_table_header(tbl_1nf.rows[0], ["1NF Relation", "Key", "Non-Key Attributes"])
populate_table_rows(tbl_1nf, [
    ["DEV_PROJECT_ASSIGNMENT", "{ project_id, user_id }", "hours_logged, project_name, repo_url, user_name, user_email"],
    ["DECISION_AI_CONTEXT", "{ decision_id }", "project_id, title, decision_type, interaction_id, tool_name, prompt, response"],
    ["ALTERNATIVE_1NF", "{ decision_id, alternative_id }", "alt_description, selection_status"],
    ["COMMIT_CHANGESET_1NF", "{ project_id, commit_hash, file_path }", "change_type, origin, lines_added, lines_deleted, commit_message"]
])
doc1.add_paragraph().paragraph_format.space_after = Pt(6)

# 3. Conversion to 2NF (Partial Dependencies)
add_clean_heading_1(doc1, "3. Second Normal Form (2NF): Removal of Partial Dependencies")
p = doc1.add_paragraph(
    "A relation is in 2NF if it is in 1NF and no non-prime attribute is partially dependent on any candidate key.\n"
    "Consider DEV_PROJECT_ASSIGNMENT with composite candidate key: Prime = { project_id, user_id }."
)
p.paragraph_format.space_after = Pt(4)

p_fds = doc1.add_paragraph()
p_fds.paragraph_format.space_after = Pt(4)
r_fds = p_fds.add_run(
    "• FD1 (Full FD):             { project_id, user_id } → hours_logged\n"
    "• FD2 (Partial Dependency):   project_id → { project_name, repo_url }        (depends only on part of PK)\n"
    "• FD3 (Partial Dependency):   user_id → { user_name, user_email }            (depends only on part of PK)"
)
r_fds.font.name = "Courier New"
r_fds.font.size = Pt(9)

# Embed Textbook Diagram 1
img1 = Path("/home/adithya/scratch/DBMS_Lab/docs/images/figure_1_2nf_normalization.png")
if img1.exists():
    doc1.add_picture(str(img1), width=Inches(6.2))
    cap = doc1.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_cap = cap.add_run("Figure 1: Normalizing DEV_PROJECT_ASSIGNMENT into 2NF relations by decomposing partial dependencies.")
    r_cap.font.name = "Arial"
    r_cap.font.size = Pt(8.5)
    r_cap.font.italic = True
    cap.paragraph_format.space_after = Pt(4)

p = doc1.add_paragraph("Decomposition into 2NF Relations:")
p.paragraph_format.space_after = Pt(3)

tbl_2nf = doc1.add_table(rows=4, cols=3)
tbl_2nf.alignment = WD_TABLE_ALIGNMENT.CENTER
format_table_header(tbl_2nf.rows[0], ["Relation", "Primary Key", "Attributes & Foreign Keys"])
populate_table_rows(tbl_2nf, [
    ["R1: PROJECT_MEMBER", "{ project_id, user_id }", "hours_logged (Full dependency on composite key)"],
    ["R2: PROJECT", "project_id", "project_name, repo_url (FD2 isolated)"],
    ["R3: APP_USER", "user_id", "user_name, user_email (FD3 isolated)"]
])
doc1.add_paragraph().paragraph_format.space_after = Pt(6)

# 4. Conversion to 3NF (Transitive Dependencies)
add_clean_heading_1(doc1, "4. Third Normal Form (3NF): Removal of Transitive Dependencies")
p = doc1.add_paragraph(
    "A relation is in 3NF if it is in 2NF and no non-prime attribute is transitively dependent on the primary key.\n"
    "Consider DECISION_AI_CONTEXT with primary key: Prime = { decision_id }."
)
p.paragraph_format.space_after = Pt(4)

p_3fds = doc1.add_paragraph()
p_3fds.paragraph_format.space_after = Pt(4)
r_3fds = p_3fds.add_run(
    "• FD1:                       decision_id → { project_id, title, decision_type, interaction_id }\n"
    "• FD2 (Transitive):          interaction_id → { tool_name, prompt, response }\n\n"
    "Transitive Chain: decision_id → interaction_id → { tool_name, prompt, response }\n"
    "Since interaction_id is not a candidate key and tool_name/prompt are non-prime attributes, this violates 3NF."
)
r_3fds.font.name = "Courier New"
r_3fds.font.size = Pt(9)

# Embed Textbook Diagram 2
img2 = Path("/home/adithya/scratch/DBMS_Lab/docs/images/figure_2_3nf_normalization.png")
if img2.exists():
    doc1.add_picture(str(img2), width=Inches(6.2))
    cap = doc1.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_cap = cap.add_run("Figure 2: Normalizing DECISION_AI_CONTEXT into 3NF relations by isolating transitive determinant.")
    r_cap.font.name = "Arial"
    r_cap.font.size = Pt(8.5)
    r_cap.font.italic = True
    cap.paragraph_format.space_after = Pt(4)

p = doc1.add_paragraph("Decomposition into 3NF Relations:")
p.paragraph_format.space_after = Pt(3)

tbl_3nf = doc1.add_table(rows=3, cols=3)
tbl_3nf.alignment = WD_TABLE_ALIGNMENT.CENTER
format_table_header(tbl_3nf.rows[0], ["Relation", "Primary Key", "Attributes & Foreign Keys"])
populate_table_rows(tbl_3nf, [
    ["ED1: DECISION", "decision_id", "project_id (FK), title, decision_type, interaction_id (FK)"],
    ["ED2: AI_INTERACTION", "interaction_id", "project_id (FK), tool_name, prompt, response (interaction_id is now PK)"]
])
doc1.add_paragraph().paragraph_format.space_after = Pt(6)

# 5. Summary of Final 9 Relations in 3NF / BCNF
add_clean_heading_1(doc1, "5. Summary of Final 9 Database Relations (in 3NF / BCNF)")
p = doc1.add_paragraph("The resulting 9 tables implemented in the PostgreSQL database:")
p.paragraph_format.space_after = Pt(3)

tbl_final = doc1.add_table(rows=10, cols=4)
tbl_final.alignment = WD_TABLE_ALIGNMENT.CENTER
format_table_header(tbl_final.rows[0], ["Table", "Primary Key", "Foreign Keys", "Normal Form"])
populate_table_rows(tbl_final, [
    ["app_user", "user_id", "None (email is Unique)", "3NF / BCNF"],
    ["project", "project_id", "None", "3NF / BCNF"],
    ["project_member", "{ project_id, user_id }", "project_id → project, user_id → app_user", "3NF / BCNF"],
    ["ai_interaction", "interaction_id", "(project_id, user_id) → project_member", "3NF / BCNF"],
    ["decision", "decision_id", "project_id → project, (project_id, interaction_id) → ai_interaction", "3NF / BCNF"],
    ["alternative", "alternative_id", "decision_id → decision", "3NF / BCNF"],
    ["evidence", "evidence_id", "decision_id → decision", "3NF / BCNF"],
    ["git_commit", "commit_id", "(project_id, user_id) → project_member", "3NF / BCNF"],
    ["code_change", "change_id", "(project_id, commit_id), (project_id, interaction_id), (project_id, decision_id)", "3NF / BCNF"]
])
doc1.add_paragraph().paragraph_format.space_after = Pt(4)

p_proof = doc1.add_paragraph(
    "Note on Lossless Join: For each decomposed pair (R1, R2), (R1 ∩ R2) forms a superkey of R1 or R2, "
    "guaranteeing lossless join equivalence (R1 ⨝ R2 ≡ R) with zero spurious tuples."
)
p_proof.runs[0].font.size = Pt(8.5)
p_proof.runs[0].font.italic = True

doc1_path = Path("/home/adithya/scratch/DBMS_Lab/docs/DevTrace_Relational_Normalization_and_Decomposition.docx")
doc1.save(doc1_path)
print(f"Compact docx saved: {doc1_path}")


# =============================================================================
# DOCUMENT 2: FORM DESIGN, SECURITY & VALIDATION (CONCISE & FOCUSED)
# =============================================================================
print("Building compact Form Design, Security & Validation Docx...")
doc2 = Document()

for s in doc2.sections:
    s.top_margin = Inches(0.8)
    s.bottom_margin = Inches(0.8)
    s.left_margin = Inches(0.8)
    s.right_margin = Inches(0.8)

# Title
t2 = doc2.add_paragraph()
t2.paragraph_format.space_before = Pt(0)
t2.paragraph_format.space_after = Pt(2)
r_t2 = t2.add_run("Form Design, Input Validation, and Database Security")
r_t2.font.name = "Arial"
r_t2.font.size = Pt(16)
r_t2.font.bold = True

sub2 = doc2.add_paragraph()
sub2.paragraph_format.space_after = Pt(10)
r_sub2 = sub2.add_run("DBMS Lab Project Report — UI Form Specifications, Pydantic Schema Validation & PostgreSQL Constraints")
r_sub2.font.name = "Arial"
r_sub2.font.size = Pt(10)
r_sub2.font.color.rgb = COLOR_MUTED

# 1. Validation Architecture
add_clean_heading_1(doc2, "1. Input Validation Architecture")
p = doc2.add_paragraph(
    "Validation is enforced across three sequential levels before data is written to PostgreSQL:\n"
    "1. Client-Side (Forms): Basic HTML5 types, required flags, and length limits.\n"
    "2. Application Layer (FastAPI + Pydantic v2): Strict data coercion, whitespace trimming, and rejection of unexpected fields (extra='forbid').\n"
    "3. Database Layer (PostgreSQL 16): Primary keys, CHECK constraints, composite foreign keys, and transaction rollbacks."
)
p.paragraph_format.space_after = Pt(6)

# 2. Form Specifications Table
add_clean_heading_1(doc2, "2. Form Field Specifications & Validation Rules")
p = doc2.add_paragraph("Summary of all forms implemented in DevTrace with their validation rules and database constraints:")
p.paragraph_format.space_after = Pt(4)

tbl_forms = doc2.add_table(rows=9, cols=5)
tbl_forms.alignment = WD_TABLE_ALIGNMENT.CENTER
format_table_header(tbl_forms.rows[0], ["Form / Endpoint", "Key Input Fields", "HTML5 Input Type", "Pydantic Schema Validation", "PostgreSQL Engine Constraint"])
populate_table_rows(tbl_forms, [
    ["1. User Registration\nPOST /users", "name\nemail", "text\nemail", "name: 1-120 chars, stripped\nemail: normalized lowercase, exactly 1 '@'", "NOT NULL\nUNIQUE (email)"],
    ["2. Project Creation\nPOST /projects", "project_name\ndescription\nrepo_url", "text\ntextarea\nurl", "name: non-blank, 1-200 chars\nrepo_url: HttpUrl or None", "project_name NOT NULL\nAtomic membership insert"],
    ["3. AI Interaction\nPOST /interactions", "project_id\ntool_name\nprompt\nresponse", "select (UUID)\ntext\ntextarea\ntextarea", "tool_name: 1-120 chars\nprompt/response: min_length=1", "Composite FK:\n(project_id, user_id) → project_member"],
    ["4. Decision Formulation\nPOST /projects/{id}/decisions", "title\ntype\nstatus\nreason_source\nconfidence", "text\ntext\nselect\nselect\nnumber", "status: proposed/active/replaced/rejected\nsource: EXPLICIT/INFERRED/UNKNOWN\nconfidence: 0.0 to 1.0", "CHECK (status IN (...))\nCHECK (source IN (...))\nCHECK (confidence >= 0 AND <= 1)"],
    ["5. Decision Alternative\nPOST /decisions/{id}/alternatives", "description\nselection_status", "textarea\nselect", "description: 1-10000 chars\nstatus: selected/rejected/considered", "description NOT NULL\nCHECK (status IN (...))"],
    ["6. Evidence Attachment\nPOST /decisions/{id}/evidence", "evidence_type\nsource_reference", "text\ntext", "type: 1-80 chars\nsource_ref: 1-2000 chars", "NOT NULL\nCaptured_at default now()"],
    ["7. Commit Ingestion\nPOST /commits", "commit_hash\nmessage\ncommit_time\nchanges (list)", "text (hex)\ntextarea\ndatetime\ntable list", "commit_hash: 7-64 hex verification\nlines_added/deleted: int >= 0", "UNIQUE(project_id, commit_hash)\nCHECK (lines_added >= 0)\nComposite FK on changes"],
    ["8. Provenance Linkage\nPATCH /changes/{id}", "interaction_id\ndecision_id\norigin\nconfidence", "select (UUID)\nselect (UUID)\nselect\nnumber", "origin: ai_exact/ai_inferred/human\nsame-project verification in service", "CHECK (origin IN (...))\nComposite FKs for project isolation"]
])
doc2.add_paragraph().paragraph_format.space_after = Pt(6)

# 3. Security Implementation Details
add_clean_heading_1(doc2, "3. Security Controls & Threat Mitigations")

sec_points = [
    ("Mass Assignment Prevention (extra='forbid')", "Every Pydantic request schema specifies extra='forbid'. Clients cannot submit unauthorized fields such as user_id, project_id, or role to elevate privileges. Unrecognized fields immediately trigger HTTP 422."),
    ("SQL Injection Immunity", "All database operations use SQLAlchemy 2.0 type-safe expressions (select(), where()). Positional parameters ($1, $2) are bound by the psycopg driver. No user input is ever concatenated into raw SQL strings."),
    ("Broken Object-Level Authorization (404 Concealment)", "Every project-scoped endpoint checks membership via _require_project_membership(). If a user attempts to access a project or decision they do not belong to, the API returns HTTP 404 Not Found rather than 403 Forbidden to prevent UUID probing."),
    ("Cross-Project Isolation via Composite Foreign Keys", "Code changes cannot reference commits, interactions, or decisions from a different project because code_change uses composite foreign keys (project_id, commit_id), (project_id, interaction_id), and (project_id, decision_id)."),
    ("Audit History Preservation (ON DELETE RESTRICT)", "All foreign keys use ON DELETE RESTRICT instead of CASCADE. Deleting a user or project that contains audit history is blocked by the PostgreSQL engine."),
    ("Transaction Atomicity (ACID)", "Multi-row writes (such as committing a git commit and 20 file changes) are executed within an explicit database transaction (db.flush() -> db.commit()). Any constraint failure triggers db.rollback(), leaving no partial or orphaned data.")
]

for stitle, sdesc in sec_points:
    bp = doc2.add_paragraph(style='List Bullet')
    bp.paragraph_format.space_after = Pt(3)
    r_bt = bp.add_run(f"{stitle}: ")
    r_bt.bold = True
    bp.add_run(sdesc)

doc2_path = Path("/home/adithya/scratch/DBMS_Lab/docs/DevTrace_Form_Design_Security_and_Validation.docx")
doc2.save(doc2_path)
print(f"Compact docx saved: {doc2_path}")

print("Both compact Word documents updated successfully!")
