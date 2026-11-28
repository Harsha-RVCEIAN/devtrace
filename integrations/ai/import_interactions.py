"""
integrations/ai/import_interactions.py

CLI tool to import an exported AI conversation file (JSON, ChatGPT conversations.json,
or Markdown/text transcript) into DevTrace via POST /interactions/ingest.
"""

import argparse
from pathlib import Path
from uuid import UUID

import httpx

from integrations.ai.adapters.transcript_parser import parse_transcript


def main() -> None:
    parser = argparse.ArgumentParser(description="Import an AI chat transcript into DevTrace.")
    parser.add_argument("--file", required=True, help="Path to .json, .md, or .txt chat export")
    parser.add_argument("--project-id", type=UUID, required=True, help="Target DevTrace project UUID")
    parser.add_argument("--user-id", type=UUID, required=True, help="DevTrace user UUID (X-User-ID)")
    parser.add_argument("--tool", default="AI Chat", help="AI tool name (e.g. ChatGPT, Claude)")
    parser.add_argument("--model", default=None, help="Optional model name")
    parser.add_argument("--engine", default="rules", choices=["rules", "llm", "auto"])
    parser.add_argument("--commit-id", type=UUID, default=None, help="Optional commit UUID to auto-link")
    parser.add_argument("--api-url", default="http://localhost:8001/interactions/ingest")
    args = parser.parse_args()

    raw_text = Path(args.file).read_text(encoding="utf-8")
    parsed = parse_transcript(raw_text, tool_name=args.tool, model_name=args.model)

    body = {
        "project_id": str(args.project_id),
        "tool_name": parsed.tool_name,
        "model_name": parsed.model_name,
        "external_session_ref": parsed.external_session_ref,
        "engine": args.engine,
        "turns": [{"prompt": p, "response": r} for p, r in parsed.turns],
        "commit_id": str(args.commit_id) if args.commit_id else None,
        "auto_link": True,
    }

    with httpx.Client(timeout=60.0) as client:
        res = client.post(
            args.api_url,
            json=body,
            headers={"X-User-ID": str(args.user_id)},
        )
        res.raise_for_status()
        data = res.json()

    print(
        f"Ingested interaction {data['interaction_id']} ({data['turns_count']} turns, "
        f"engine={data['engine_used']}): staged {len(data['staged_decisions'])} decision(s), "
        f"auto-linked {len(data['auto_linked_changes'])} file change(s)."
    )


if __name__ == "__main__":
    main()
