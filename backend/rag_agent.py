"""OpsPilot AI & RAG Agent — Root Entrypoint.

This module provides direct access to the autonomous 10-node LangGraph
investigation state machine and the Standard Operating Procedure (SOP) RAG index.

Usage:
    # 1. Search Payment SOPs directly:
    python rag_agent.py --search "SBI switch degradation"

    # 2. Run an autonomous investigation on an open alert:
    python rag_agent.py --investigate

    # 3. Import in your code:
    from rag_agent import run_investigation, search_sops
"""
import argparse
import sys
from pathlib import Path

# Fix Windows console encoding for UTF-8 compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agent.tools.rag_tool import retrieve  # noqa: E402
from app.agent.workflow import run_investigation as _run_investigation  # noqa: E402
from app.db.base import SessionLocal  # noqa: E402
from app.models import Alert  # noqa: E402


def search_sops(query: str, top_k: int = 3, role: str = "ANALYST") -> dict:
    """Search payment standard operating procedures (SOPs) using local RAG."""
    return retrieve(query=query, k=top_k, role=role)


def run_investigation(alert_id: str = None, question: str = None, user_id: str = "usr_admin_001") -> dict:
    """Execute the deterministic 10-node LangGraph investigation workflow."""
    db = SessionLocal()
    try:
        if not alert_id:
            first_alert = db.query(Alert).first()
            if not first_alert:
                return {"ok": False, "error": "No open alerts found in database. Run ingestion or simulation first."}
            alert_id = first_alert.alert_id

        return _run_investigation(db=db, alert_id=alert_id, user_id=user_id, role="ADMIN", question=question)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="OpsPilot AI Agent & RAG Copilot CLI")
    parser.add_argument("--search", "-s", type=str, help="Search payment SOPs via local RAG")
    parser.add_argument("--investigate", "-i", action="store_true", help="Run 10-node investigation on the latest alert")
    parser.add_argument("--alert-id", "-a", type=str, help="Specific alert ID to investigate")
    parser.add_argument("--question", "-q", type=str, help="Custom investigation question")

    args = parser.parse_args()

    if args.search:
        print(f"\n[RAG] Searching Payment SOP Knowledge Base for: '{args.search}'")
        res = search_sops(args.search)
        if res.get("ok"):
            print(f"[*] Found {res.get('count', 0)} relevant policy chunks:\n")
            for i, doc in enumerate(res.get("documents", []), start=1):
                print(f"[{i}] {doc.get('citation')}")
                print(f"    Relevance Score: {doc.get('relevance_score', 0):.4f}")
                print(f"    Excerpt: {doc.get('chunk', '')[:160]}...\n")
        else:
            print(f"[!] Search failed: {res.get('error')}")

    elif args.investigate or args.alert_id:
        print("\n[AI Agent] Initiating LangGraph 10-Node Investigation State Machine...")
        res = run_investigation(alert_id=args.alert_id, question=args.question)
        print("=" * 64)
        print(f"Workflow ID       : {res.get('workflow_id')}")
        print(f"Alert ID          : {res.get('alert_id')}")
        print(f"Approval Required : {res.get('approval_required')}")
        print(f"Approval Status   : {res.get('approval_status')}")
        print(f"Evidence Verdict  : {res.get('evidence', {}).get('verdict')}")
        print("-" * 64)
        rec = res.get("recommendation", {})
        print(f"Summary           : {rec.get('what_happened')}")
        print(f"Citations         : {rec.get('citations')}")
        print(f"Action Proposed   : {rec.get('recommended_action')}")
        print("=" * 64)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
