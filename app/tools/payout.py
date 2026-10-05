"""Tool for calculating insurance claim payouts based on policy terms."""

from app.tools.claims import get_claim, get_policy


def calculate_payout(claim_id: str) -> dict:
    """Calculate the payout for a claim based on policy rules.

    Args:
        claim_id: Unique claim identifier (e.g. 'CLM-1003').

    Returns:
        Dict with keys: gross, deductible, depreciation, net_payout, notes.
    """
    claim = get_claim(claim_id)
    if not claim or "error" in claim:
        return {
            "error": f"Claim '{claim_id}' not found.",
            "gross": 0.0,
            "deductible": 0.0,
            "depreciation": 0.0,
            "net_payout": 0.0,
            "notes": f"Claim '{claim_id}' not found.",
        }

    policy_id = claim.get("policy_id")
    policy = get_policy(policy_id) if policy_id else {}
    if not policy or "error" in policy:
        return {
            "error": f"Policy '{policy_id}' not found for claim '{claim_id}'.",
            "gross": 0.0,
            "deductible": 0.0,
            "depreciation": 0.0,
            "net_payout": 0.0,
            "notes": f"Policy '{policy_id}' not found.",
        }

    policy_type = (policy.get("type") or claim.get("type") or "").upper()
    estimate_usd = float(claim.get("estimate_usd", 0.0))

    if policy_type in ("HO3", "HOME"):
        peril = (claim.get("peril") or "").lower()
        coverage_a_limit = float(policy.get("coverage_a_limit", 0.0))
        wind_hail_deductible_pct = float(policy.get("wind_hail_deductible_pct", 0.0))

        if peril in ("wind", "hail"):
            deductible = (wind_hail_deductible_pct / 100.0) * coverage_a_limit
        else:
            deductible = float(policy.get("flat_deductible_usd") or 0.0)

        roof_acv_endorsement = bool(policy.get("roof_acv_endorsement", False))
        roof_age_years = float(claim.get("roof_age_years", 0.0))
        roof_portion_usd = float(claim.get("roof_portion_usd", 0.0))

        if roof_acv_endorsement and roof_age_years > 15:
            depreciation = roof_portion_usd * min(0.8, roof_age_years / 25.0)
        else:
            depreciation = 0.0

        gross = estimate_usd
        net_payout = max(0.0, min(estimate_usd - depreciation - deductible, coverage_a_limit))
        notes = (
            f"HO3 payout for {peril} peril. Coverage A Limit: ${coverage_a_limit:,.2f}, "
            f"Deductible: ${deductible:,.2f}, Depreciation: ${depreciation:,.2f}."
        )

    elif policy_type in ("AUTO_COMP", "AUTO"):
        vehicle_acv_usd = float(policy.get("vehicle_acv_usd", 0.0))
        flat_deductible_usd = float(policy.get("flat_deductible_usd", 0.0))

        gross = estimate_usd
        deductible = flat_deductible_usd
        depreciation = 0.0
        net_payout = max(0.0, min(estimate_usd, vehicle_acv_usd) - flat_deductible_usd)
        notes = (
            f"AUTO_COMP payout. Estimate: ${estimate_usd:,.2f}, Vehicle ACV: ${vehicle_acv_usd:,.2f}, "
            f"Deductible: ${flat_deductible_usd:,.2f}."
        )

    else:
        return {
            "error": f"Unsupported policy type '{policy_type}' for claim '{claim_id}'.",
            "gross": 0.0,
            "deductible": 0.0,
            "depreciation": 0.0,
            "net_payout": 0.0,
            "notes": f"Unsupported policy type '{policy_type}'.",
        }

    return {
        "gross": gross,
        "deductible": deductible,
        "depreciation": depreciation,
        "net_payout": net_payout,
        "notes": notes,
    }
