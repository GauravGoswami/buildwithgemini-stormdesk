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


def triage_queue(
    authority_limit_usd: float = 25000.0,
    flagged_claim_types: list[str] = None,
) -> dict:
    """Triage all new claims in the surge queue in code in a single batch operation.

    Args:
        authority_limit_usd: Adjuster's remembered personal authority limit in USD (default $25,000.00).
        flagged_claim_types: Optional list of claim types the adjuster always wants flagged for inspection (e.g. ['auto']).

    Returns:
        Summary dict containing counts, totals, and per-claim triage results.
    """
    from app.tools.payout import calculate_payout
    from app.tools.weather import check_weather_at_loss, find_storm_reports

    flagged_claim_types = [t.lower() for t in (flagged_claim_types or [])]
    docs = list(db.collection("claims").where(filter=FieldFilter("status", "==", "new")).stream())

    claims_out = []
    total_gross = 0.0
    total_net = 0.0
    counts = {"fast_track": 0, "inspect": 0, "siu_referral": 0}

    for doc in docs:
        c = doc.to_dict()
        cid = c.get("claim_id") or doc.id
        insured = c.get("insured", "Unknown")
        peril = str(c.get("peril") or "").lower()
        ctype = str(c.get("type") or "").lower()
        loss_date_str = c.get("loss_date")
        reported_date_str = c.get("reported_date")
        policy_id = c.get("policy_id")
        lat = c.get("lat")
        lon = c.get("lon")
        roof_age = c.get("roof_age_years", 0)

        pol = get_policy(policy_id) if policy_id else {}

        # Weather & storm report check
        w_res = check_weather_at_loss(lat, lon, loss_date_str) if lat and lon and loss_date_str else {}
        s_res = find_storm_reports(lat, lon, loss_date_str, radius_miles=25) if lat and lon and loss_date_str else {}
        reports = s_res.get("reports", [])

        corroborated = False
        corroboration_detail = ""
        if peril == "wind":
            wind_reports = [r for r in reports if any(k in str(r.get("type", "")).lower() for k in ["wind", "tornado"])]
            near_wind = [r for r in wind_reports if r.get("distance_miles", 999) <= 10.0]
            if near_wind:
                corroborated = True
                r = near_wind[0]
                corroboration_detail = f"{r.get('type')} report within {r.get('distance_miles')} mi ({r.get('location', 'near location')})"
            else:
                corroboration_detail = "No NOAA wind/tornado reports within 10 miles"
        elif peril == "hail":
            hail_code = w_res.get("hail_code", False)
            hail_reports = [r for r in reports if "hail" in str(r.get("type", "")).lower()]
            near_hail = [r for r in hail_reports if r.get("distance_miles", 999) <= 25.0]
            if hail_code or near_hail:
                corroborated = True
                if near_hail:
                    r = near_hail[0]
                    corroboration_detail = f"Hail report within {r.get('distance_miles')} mi ({r.get('location', 'near location')})"
                else:
                    corroboration_detail = "Open-Meteo hail weather code true"
            else:
                corroboration_detail = "No hail reports within 25 miles and hail code false"

        # Red flags
        red_flags = []
        loss_dt = datetime.strptime(loss_date_str, "%Y-%m-%d") if loss_date_str else None
        rep_dt = datetime.strptime(reported_date_str, "%Y-%m-%d") if reported_date_str else None

        if loss_dt and rep_dt and (rep_dt - loss_dt).days > 30:
            red_flags.append(f"Reported {(rep_dt - loss_dt).days} days after loss date (>30d threshold)")

        cov_inc_str = pol.get("coverage_a_increased_on")
        if cov_inc_str and loss_dt:
            cov_inc_dt = datetime.strptime(cov_inc_str, "%Y-%m-%d")
            days_diff = (loss_dt - cov_inc_dt).days
            if 0 <= days_diff <= 60:
                red_flags.append(f"Coverage A increased on {cov_inc_str} ({days_diff} days before loss)")

        eff_str = pol.get("effective")
        if eff_str and loss_dt:
            eff_dt = datetime.strptime(eff_str, "%Y-%m-%d")
            days_before_loss = (loss_dt - eff_dt).days
            cat_dt = datetime.strptime("2024-05-16", "%Y-%m-%d")
            if 0 <= days_before_loss <= 7 and eff_dt >= cat_dt:
                red_flags.append(f"Policy effective {eff_str} ({days_before_loss} days before loss and after 2024-05-16 catastrophe)")

        priors = pol.get("prior_claims") or []
        for pc in priors:
            if str(pc.get("peril", "")).lower() == peril and loss_dt:
                p_date_str = pc.get("date")
                if p_date_str:
                    p_dt = datetime.strptime(p_date_str, "%Y-%m-%d")
                    if 0 <= (loss_dt - p_dt).days <= 730:
                        red_flags.append(f"Prior {peril} claim on {p_date_str} (within 24 months)")

        # Payout
        p_res = calculate_payout(cid)
        gross = float(p_res.get("gross", 0.0))
        net = float(p_res.get("net_payout", 0.0))
        total_gross += gross
        total_net += net

        # Decision
        reasons = []
        if not corroborated and len(red_flags) >= 1:
            decision = "siu_referral"
            reasons.append(f"Peril not corroborated: {corroboration_detail}.")
            reasons.extend(red_flags)
        elif not corroborated or roof_age > 15 or net > authority_limit_usd or ctype in flagged_claim_types:
            decision = "inspect"
            if not corroborated:
                reasons.append(f"Peril not corroborated: {corroboration_detail}.")
            if roof_age > 15:
                reasons.append(f"Roof age {roof_age} years exceeds 15-year threshold.")
            if net > authority_limit_usd:
                reasons.append(f"Net payout ${net:,.2f} exceeds adjuster authority limit (${authority_limit_usd:,.2f}).")
            if ctype in flagged_claim_types:
                reasons.append(f"Claim type '{ctype}' is on adjuster's always-flagged list.")
        else:
            decision = "fast_track"
            reasons.append(f"Peril corroborated ({corroboration_detail}).")
            reasons.append(f"Net payout ${net:,.2f} within authority limit (${authority_limit_usd:,.2f}).")

        counts[decision] = counts.get(decision, 0) + 1

        claims_out.append({
            "claim_id": cid,
            "insured": insured,
            "type": ctype,
            "peril": peril,
            "decision": decision,
            "gross_usd": gross,
            "net_payout_usd": net,
            "corroborated": corroborated,
            "red_flags_count": len(red_flags),
            "red_flags": red_flags,
            "reasons": reasons,
        })

    order = {"siu_referral": 0, "inspect": 1, "fast_track": 2}
    claims_out.sort(key=lambda x: (order.get(x["decision"], 3), x["claim_id"]))

    return {
        "total_claims": len(claims_out),
        "summary": {
            "fast_track": counts["fast_track"],
            "inspect": counts["inspect"],
            "siu_referral": counts["siu_referral"],
            "total_gross_usd": total_gross,
            "total_net_usd": total_net,
        },
        "claims": claims_out,
    }
