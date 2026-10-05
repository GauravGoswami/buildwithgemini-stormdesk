"""Claims management tools backed by Firestore."""

from datetime import datetime, timezone
from google.cloud.firestore_v1.base_query import FieldFilter
from app.db import db


def get_claim(claim_id: str) -> dict:
    """Retrieve details for a specific claim document by claim ID.

    Args:
        claim_id: Unique claim identifier (e.g. 'CLM-1001').

    Returns:
        The claim document as a dictionary, or error dict if missing.
    """
    doc_ref = db.collection("claims").document(claim_id)
    doc = doc_ref.get()
    if not doc.exists:
        return {"error": f"Claim '{claim_id}' not found."}
    return doc.to_dict()


def list_claims(status: str = "new") -> list[dict]:
    """List up to 20 claims filtered by status.

    Args:
        status: Claim status filter (default 'new'). Pass 'all' for all statuses.

    Returns:
        List of claim dicts containing claim_id, insured, type, peril,
        loss_date, zip, estimate_usd, status.
    """
    query = db.collection("claims")
    if status and status.lower() != "all":
        query = query.where(filter=FieldFilter("status", "==", status))

    docs = query.limit(20).stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        results.append({
            "claim_id": data.get("claim_id"),
            "insured": data.get("insured"),
            "type": data.get("type"),
            "peril": data.get("peril"),
            "loss_date": data.get("loss_date"),
            "zip": data.get("zip"),
            "estimate_usd": data.get("estimate_usd"),
            "status": data.get("status"),
        })
    return results


def get_policy(policy_id: str) -> dict:
    """Retrieve details for an insurance policy document by policy ID.

    Args:
        policy_id: Unique policy identifier (e.g. 'POL-1001').

    Returns:
        The policy document as a dictionary, or error dict if missing.
    """
    doc_ref = db.collection("policies").document(policy_id)
    doc = doc_ref.get()
    if not doc.exists:
        return {"error": f"Policy '{policy_id}' not found."}
    return doc.to_dict()


def record_decision(
    claim_id: str,
    decision: str,
    reasons: list[str],
    payout_usd: float,
) -> dict:
    """Record a triage decision for a claim in Firestore.

    Args:
        claim_id: Unique claim identifier (e.g. 'CLM-1001').
        decision: Triage decision ('fast_track', 'inspect', or 'siu_referral').
        reasons: List of reasoning statements supporting the decision.
        payout_usd: Calculated payout in USD.

    Returns:
        The updated claim document as a dictionary.
    """
    doc_ref = db.collection("claims").document(claim_id)
    doc = doc_ref.get()
    if not doc.exists:
        return {"error": f"Claim '{claim_id}' not found."}

    decided_at = datetime.now(timezone.utc).isoformat()
    update_data = {
        "status": decision,
        "triage": {
            "reasons": reasons,
            "payout_usd": payout_usd,
            "decided_at": decided_at,
        },
    }
    doc_ref.update(update_data)
    updated_doc = doc_ref.get()
    return updated_doc.to_dict()
