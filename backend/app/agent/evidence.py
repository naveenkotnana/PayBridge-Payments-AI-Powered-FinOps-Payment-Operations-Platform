"""Evidence validator.

The single most important safety component. It answers: does the collected
evidence actually support a root-cause claim? If not, the workflow returns
INSUFFICIENT EVIDENCE instead of letting the model invent one.

Classification vocabulary, enforced downstream:
  FACT        - a value read directly from the database this run
  EVIDENCE    - a retrieved policy statement or SQL result supporting a claim
  INFERENCE   - a reasoned link between facts, explicitly labelled
  UNCERTAINTY - what is not known and what would resolve it
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class EvidenceBundle:
    facts: Dict[str, Any] = field(default_factory=dict)
    sql_results: List[dict] = field(default_factory=list)
    documents: List[dict] = field(default_factory=list)
    analytics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


# A recommendation may only be generated when enough independent evidence
# streams succeeded. Thresholds are deterministic, not model-decided.
MIN_STREAMS = 2
MIN_DOC_SCORE = 0.05


def validate(bundle: EvidenceBundle) -> dict:
    streams, missing, notes = [], [], []

    has_analytics = False
    if bundle.analytics:
        if bundle.analytics.get("revenue") or bundle.analytics.get("total_attempts") is not None:
            has_analytics = True

    if has_analytics:
        streams.append("ANALYTICS")
    else:
        missing.append("analytics")

    sql_ok = [r for r in bundle.sql_results if r.get("ok") and r.get("row_count", 0) > 0]
    if sql_ok:
        streams.append("SQL")
    else:
        missing.append("sql")

    good_docs = [d for d in bundle.documents
                 if d.get("relevance_score", 0) >= MIN_DOC_SCORE]
    if good_docs:
        streams.append("POLICY")
    else:
        missing.append("policy")
        notes.append("No policy chunk met the relevance floor.")

    # A baseline is required to claim a root cause:
    change = (bundle.analytics or {}).get("change", {})
    has_revenue_baseline = change.get("previous") is not None
    is_payment = bool(bundle.analytics and bundle.analytics.get("total_attempts") is not None)
    has_baseline = has_revenue_baseline or is_payment

    if not has_baseline:
        notes.append("No prior-month baseline; magnitude claims are not supported.")

    sufficient = len(streams) >= MIN_STREAMS and has_baseline

    return {
        "sufficient": sufficient,
        "streams_present": streams,
        "streams_missing": missing,
        "document_count": len(good_docs),
        "sql_result_sets": len(sql_ok),
        "has_baseline": has_baseline,
        "notes": notes,
        "verdict": "EVIDENCE_SUFFICIENT" if sufficient else "INSUFFICIENT_EVIDENCE",
    }


def check_grounding(claim_text: str, bundle: EvidenceBundle) -> dict:
    """Cheap numeric grounding check: every number the model states should be
    traceable to a number we actually computed. Catches fabricated figures."""
    import re
    stated = set(re.findall(r"\d[\d,]*\.?\d*", claim_text or ""))
    known = set()

    def collect(o):
        if isinstance(o, dict):
            for v in o.values():
                collect(v)
        elif isinstance(o, list):
            for v in o:
                collect(v)
        elif isinstance(o, (int, float)):
            known.add(f"{o}")
            known.add(f"{round(float(o), 2)}")

    collect(bundle.analytics)
    for r in bundle.sql_results:
        collect(r.get("rows", []))

    # Strip formatting ($ , %)
    clean_stated = {s.replace(",", "").rstrip("%") for s in stated}
    ungrounded = [s for s in clean_stated if s and s not in known
                  and not s.startswith("0") and float(s) > 1.0] if clean_stated else []

    return {"grounded": len(ungrounded) == 0,
            "ungrounded_tokens": sorted(ungrounded),
            "unsupported_numbers": sorted(ungrounded),
            "stated_count": len(clean_stated), "known_count": len(known)}
