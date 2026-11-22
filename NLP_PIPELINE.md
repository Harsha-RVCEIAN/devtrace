# DevTrace: End-to-End NLP Candidate Decision Extraction Pipeline

This document provides a comprehensive architectural and algorithmic explanation of how the DevTrace Natural Language Processing (NLP) pipeline extracts engineering decisions, evaluated alternatives, causal justifications, and verbatim evidence from developer-AI development transcripts.

---

## 1. System Goal & Core DBMS Invariant

### The Problem
During modern software development with AI assistants (e.g. Claude Code, Antigravity, Cursor, ChatGPT), critical architectural choices, trade-offs, and rationale are discussed informally across multi-turn dialogues:
- *"Which auth approach should we use? JWT or Redis sessions?"*
- *"ok i feel like session based auth is the best here"*
- *"Definitely! it has a simpler lifecycle and safer browser storage."*

Without automated extraction, this architectural context is lost forever, resulting in untracked decisions and code changes missing causal provenance.

### The Non-Negotiable DBMS Invariant
> **Strict Proposed Staging:** Machine learning and NLP extractors are treated as **untrusted proposers**. Extracted decisions are **always staged** with `status='proposed'`. They are never auto-inserted into the authoritative PostgreSQL `DECISION` table without human developer review and authorization.

---

## 2. High-Level Architecture Diagram

```
Multi-Turn Dialogue Turns: [ (Prompt 1, Response 1), (Prompt 2, Response 2), ... ]
                                     │
                                     ▼
                   ┌───────────────────────────────────┐
                   │   Stage 1: Transcript Builder     │  (nlp/transcript.py)
                   │   • Strips code fences (```)      │
                   │   • Global 0-based sentence IDs   │
                   │   • Retains choice conjunctions   │
                   └─────────────────┬─────────────────┘
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         ▼                                                       ▼
┌─────────────────────────────────┐             ┌─────────────────────────────────┐
│ Stage 2A: Option Sets Discovery │             │ Stage 2B: Status Mentions Scan  │
│ (nlp/alternative_extractor.py)  │             │ (nlp/alternative_extractor.py)  │
│ • Question disjunctions (A or B)│             │ • "instead of X" ➔ rejected     │
│ • Option lists ("A, B, and C")  │             │ • "considered Y" ➔ considered   │
│ • Bulleted candidate blocks     │             │ • "ruled out Z"  ➔ rejected     │
└────────────────┬────────────────┘             └────────────────┬────────────────┘
                 │                                               │
                 └───────────────────────┬───────────────────────┘
                                         ▼
                   ┌───────────────────────────────────┐
                   │ Stage 3: Decision Statements      │  (nlp/decision_extractor.py)
                   │ • Pattern matcher (commit/pref)   │
                   │ • Speaker authority hierarchy     │
                   │ • Ordinal & anaphoric resolution  │
                   └─────────────────┬─────────────────┘
                                     │
                                     ▼
                   ┌───────────────────────────────────┐
                   │ Stage 4: Causal Rationale Engine  │  (nlp/rationale_extractor.py)
                   │ • 1. Inline decision connectives  │
                   │ • 2. Nearby justifications        │
                   │ • 3. Hedged language check        │
                   └─────────────────┬─────────────────┘
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         ▼                                                       ▼
┌─────────────────────────────────┐             ┌─────────────────────────────────┐
│ Stage 5: Rule Engine (Default)  │             │ Stage 6: LLM Engine (Optional)  │
│ (nlp/rule_engine.py)            │             │ (nlp/llm_engine.py)             │
│ • Single forward cluster walk   │             │ • Local Ollama (llama3:latest)  │
│ • Authority conflict override   │             │ • Strict JSON schema output     │
│ • Auto-reject unchosen options  │             │ • Python validates all IDs/alts │
└────────────────┬────────────────┘             └────────────────┬────────────────┘
                 │                                               │
                 └───────────────────────┬───────────────────────┘
                                         ▼
                   ┌───────────────────────────────────┐
                   │ Final ExtractionResult            │
                   │ • CandidateDecisions (status=prop)│
                   │ • Evaluated Alternative pills     │
                   │ • Verbatim cited Evidence quotes  │
                   └───────────────────────────────────┘
```

---

## 3. Step-by-Step Pipeline Mechanics

### Stage 1: Ingestion & Transcript Normalization (`nlp/transcript.py`)
Converts raw UI prompt/response pairs into a structured, flat stream of `Sentence` objects.

```python
@dataclass(frozen=True)
class Sentence:
    id: int               # Global position across entire conversation (0, 1, 2...)
    turn: int             # 1-based turn number matching UI
    speaker: Literal["developer", "assistant"]
    text: str             # Verbatim sentence string
    is_question: bool     # True if sentence ends with or contains '?'
    is_bullet: bool       # True if line originated as a markdown bullet
    message_index: int    # 0-based index of the message
```

#### Key Rules:
1. **Code Block Stripping:** Fenced code blocks (` ```...``` `) are removed. Code syntax must never pollute dialogue decision extraction.
2. **Disjunctive Preservation:** Standard sentence tokenizers split on `?`. Our regex lookahead refuses to split when followed by `or`, `and`, or `vs`:
   ```regex
   (?<=[.!?])\s+(?!(?:or|and|vs\.?|versus)\b)
   ```
   *Result:* `"how do we secure our website? JWT? or redis session based auth, or mutual TLS?"` stays intact as a single choice menu.

---

### Stage 2: Dual Option Extraction (`nlp/alternative_extractor.py`)
Human communication introduces options in two fundamentally different ways:
1. **Option Sets (`OptionSet`)**: The speaker enumerates the menu of candidate choices.
   - *Questions:* `"which database? postgres or mongo?"`
   - *Declarations:* `"options are PostgreSQL, MySQL and MongoDB"`, `"between A and B"`.
   - *Bulleted Blocks:* Lines following an intro word like `options:`, `alternatives:`, `considered:`.
2. **Status Mentions (`StatusMention`)**: The speaker evaluates individual options:
   - *Rejected:* `"instead of MongoDB"`, `"chose PostgreSQL over MySQL"`, `"ruled out MongoDB"`, `"X is overkill"`.
   - *Considered:* `"we also considered MySQL"`, `"another option is SQLite"`.

#### Token Normalization & Fuzzy Option Matching (`nlp/text_utils.py`)
Options are compared using weighted semantic token sets:
- **Aliases:** `postgres` &rarr; `postgresql`, `mongo` &rarr; `mongodb`, `k8s` &rarr; `kubernetes`.
- **Generic Words:** Common architectural glue words (`auth`, `database`, `based`, `server`, `storage`) carry low weight (`0.25`).
- **Scoring:** `shared_weight / min_weight`. Two phrases are considered the same option if score &ge; `0.6`. Sharing only generic words (`auth`) returns `0.0`.

---

### Stage 3: Decision Statement Detection & Authority Hierarchy (`nlp/decision_extractor.py`)
Statements expressing a choice are scanned and classified using a strict speaker authority table:

| Statement Kind | Speaker | Authority Rank | Confidence | Triggers |
| :--- | :--- | :---: | :---: | :--- |
| **Developer Commit** | Developer | **3** | **0.90** | `"let's use X"`, `"we decided on X"`, `"X it is"`, `"replace A with B"` |
| **Developer Acceptance** | Developer | **3** | **0.85** | Short agreement (`"ok"`, `"agreed"`, `"fair"`, `"sounds good"`) accepting an assistant recommendation |
| **Assistant Commit** | Assistant | **2** | **0.85** | `"We decided on X"`, `"We chose X"` |
| **Developer Preference** | Developer | **2** | **0.80** | `"i feel like X is the best"`, `"i think X is better"`, `"i prefer X"` |
| **Assistant Recommendation**| Assistant | **1** | **0.65** | `"I recommend X"`, `"you should use X"`, `"Use X"` (after choice question) |
| **Developer Tentative** | Developer | **1** | **0.50** | `"i was thinking X"`, `"maybe X"` |

#### Essential Filtering & Reference Resolution Rules:
- **Negative Rule:** A question is **never** treated as a decision.
- **Ordinal Resolution:** Phrases like `"the former"`, `"the latter"`, `"the first one"`, `"option 2"` automatically resolve to the corresponding index in the active `OptionSet`.
- **Anaphoric Resolution:** Pronouns like `"it"`, `"that"`, `"your suggestion"` resolve to the choice of the preceding assistant recommendation.

---

### Stage 4: Causal Rationale Extraction (`nlp/rationale_extractor.py`)
Justifications are resolved using a 4-tier confidence ladder:

```
┌────────────────────────────────────────────────────────────────────────┐
│ Tier 1: Inline Causal Connective (EXPLICIT, 0.95)                      │
│ - "We chose PostgreSQL because native composite foreign keys..."       │
│ - Triggers: because, since, so that, in order to, due to, or colon (:) │
├────────────────────────────────────────────────────────────────────────┤
│ Tier 2: Nearby Justification Sentence (EXPLICIT, 0.80)                 │
│ - Search up to 3 sentences forward (skipping filler like "Definitely!")│
│   or 1 sentence backward in the same message.                          │
│ - Triggers: "it/this has/provides/is simpler...", "we need/want..."    │
├────────────────────────────────────────────────────────────────────────┤
│ Tier 3: Hedged Wording (INFERRED, 0.60)                                │
│ - Statements using: might, may, probably, likely, perhaps, presumably. │
├────────────────────────────────────────────────────────────────────────┤
│ Tier 4: No Rationale Identified (UNKNOWN, 0.0)                         │
│ - Never synthesizes, guesses, or hallucinates missing justification.   │
└────────────────────────────────────────────────────────────────────────┘
```

---

### Stage 5: Rule Engine Forward Walk & Resolution (`nlp/rule_engine.py`)
The engine iterates forward through all statements:
1. **Decision Clustering:** Statements referencing the same `OptionSet` or matching option tokens are grouped into a single decision draft.
2. **Authority Conflict Override:**
   - If a later statement has `authority >= draft.authority`, the new choice replaces the earlier choice. The old choice is automatically converted into a `rejected` alternative.
   - If a later statement has lower authority, it is recorded as a `considered` alternative.
3. **Implicit Rejection of Unchosen Menu Options:**
   - Any option from the active `OptionSet` that was not selected is automatically marked as `rejected`, with the option-set sentence cited as evidence.
4. **Context Evidence Attachment:**
   - The nearest developer question asked prior to the decision is attached as `role="context"` evidence.
5. **Decision Type Classification:**
   - Scored against domain terminology with tie-breaking precedence:
     `security > architecture > infrastructure > refactor > implementation`.

---

### Stage 6: Optional LLM Engine (`nlp/llm_engine.py`)
For complex or unconventional phrasing, the system can delegate extraction to a local LLM (e.g. `llama3:latest` via Ollama at `http://localhost:11434`):
- Connects using Python standard library `urllib` (no external SDK dependencies).
- Forces JSON schema compliance:
  ```json
  {
    "decisions": [
      {
        "chosen_option": "string",
        "decision_type": "string",
        "decision_sentence_ids": [1],
        "rationale_sentence_ids": [2],
        "alternatives": [
          {"option": "string", "status": "selected|rejected|considered", "sentence_id": 0}
        ]
      }
    ]
  }
  ```
- **Treated as an Untrusted Proposer:**
  - Python checks every cited sentence ID against the transcript.
  - Drops decisions if the chosen option appears nowhere in the transcript.
  - Drops decisions if all cited decision sentences are questions.
  - Re-evaluates cited rationale sentences using deterministic Python scoring.
- **Engine Modes:**
  - `rules`: Deterministic default (1ms execution, fully offline, $0 cost).
  - `llm`: Strict LLM execution (returns HTTP 503 if Ollama is unreachable).
  - `auto`: Tries LLM first; if unavailable, falls back to Rule Engine with a warning banner.

---

## 4. API Endpoints

### `POST /nlp/extract-candidates`
Multi-turn extraction endpoint accepting an array of dialogue turns.

#### Request Body
```json
{
  "turns": [
    {
      "prompt": "how do we secure our website? JWT? or redis session based auth, or mutual TLS?\nok i feel like session based auth is the best here",
      "response": "Definitely! it has a simpler lifecycle and safer browser storage. creating the files now..."
    }
  ],
  "engine": "rules",
  "project_id": "d3b07384-d113-4c92-b0b2-320d9f4c3912"
}
```

#### Response Body
```json
{
  "engine_used": "rules",
  "candidates": [
    {
      "title": "Adopt Redis Session Based Auth",
      "description": "Redis Session Based Auth was selected over JWT, Mutual TLS. (Context: \"how do we secure our website? JWT? or redis session based auth, or mutual TLS?\")",
      "decision_type": "security",
      "chosen_option": "Redis Session Based Auth",
      "confidence": 0.8,
      "reason_text": "it has a simpler lifecycle and safer browser storage.",
      "reason_source_type": "EXPLICIT",
      "reason_confidence": 0.8,
      "status": "proposed",
      "alternatives": [
        {
          "description": "Redis Session Based Auth",
          "selection_status": "selected",
          "evidence": {
            "role": "decision",
            "turn": 1,
            "speaker": "developer",
            "quote": "ok i feel like session based auth is the best here",
            "sentence_id": 2
          }
        },
        {
          "description": "JWT",
          "selection_status": "rejected",
          "evidence": {
            "role": "alternative",
            "turn": 1,
            "speaker": "developer",
            "quote": "how do we secure our website? JWT? or redis session based auth, or mutual TLS?",
            "sentence_id": 0
          }
        },
        {
          "description": "Mutual TLS",
          "selection_status": "rejected",
          "evidence": {
            "role": "alternative",
            "turn": 1,
            "speaker": "developer",
            "quote": "how do we secure our website? JWT? or redis session based auth, or mutual TLS?",
            "sentence_id": 0
          }
        }
      ],
      "evidence": [
        {
          "role": "context",
          "turn": 1,
          "speaker": "developer",
          "quote": "how do we secure our website? JWT? or redis session based auth, or mutual TLS?",
          "sentence_id": 0
        },
        {
          "role": "decision",
          "turn": 1,
          "speaker": "developer",
          "quote": "ok i feel like session based auth is the best here",
          "sentence_id": 2
        },
        {
          "role": "rationale",
          "turn": 1,
          "speaker": "assistant",
          "quote": "it has a simpler lifecycle and safer browser storage.",
          "sentence_id": 4
        }
      ]
    }
  ],
  "warnings": []
}
```

---

## 5. Test Suite & Verification Matrix

The pipeline is verified by 48 automated test cases in `pytest`:

| Test Module | Coverage | Status |
| :--- | :--- | :---: |
| `tests/unit/test_transcript_nlp.py` | Conversational questions, multi-turn acceptance, bullet selection, replacement lineage, negative controls | **PASSED** |
| `tests/unit/test_extractors.py` | Rationale confidence ladder, alternative extraction, provenance classifier integration | **PASSED** |
| `tests/unit/test_llm_engine.py` | Schema validation, hallucination dropping, question filtering, network timeout handling | **PASSED** |
| `tests/integration/test_candidate_endpoint.py` | FastAPI endpoint integration, project membership authorization, empty non-decision turns | **PASSED** |
