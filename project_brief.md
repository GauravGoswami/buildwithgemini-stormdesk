# My agent: StormDesk
One-liner: A catastrophe-claims triage copilot that helps insurance adjusters at Cedar Ridge Insurance (a fictional insurer) clear the post-storm claim surge, with a catalog of claims, policies and NOAA storm reports.

## Business Problem
After a major storm, an insurer receives thousands of claims in 48 hours. Adjusters triage by hand (look up the policy, check whether the storm actually hit that address, apply the wind/hail deductible, decide fast-track vs inspect vs fraud referral). Backlogs breach Texas prompt-pay deadlines (Insurance Code ch. 542) and the surge is when opportunistic fraud slips through. StormDesk triages a claim, or a whole surge queue, in seconds with cited evidence.

## Demo Event
The real 16 May 2024 Houston derecho (Harris County, TX). Weather and storm-report data are real; the insurer, policyholders and claims are fictional.

## Tool Coverage
- **Memory**: Per adjuster: name, authority limit in USD (default $25,000), claim types they always want flagged (e.g. roofs older than N years), customer-notice tone.
- **Tools**:
  - `get_claim`: Look up detailed claim record.
  - `list_claims`: Retrieve surge queue or filtered list of claims.
  - `get_policy`: Fetch policy details and coverage limits.
  - `record_decision`: Writes decision back to Firestore (only after the adjuster confirms).
  - `calculate_payout`: Deterministic calculation (1% of Coverage A wind/hail deductible for homeowners, flat deductible for auto, roof ACV depreciation when the roof ACV endorsement applies and roof age > 15).
  - `check_weather_at_loss`: Live Open-Meteo historical archive API (free, no key: daily max gust, precipitation, weather code, and whether the loss date was the windiest day in a +/-3 day window).
  - `find_storm_reports`: NOAA Storm Events reports stored in Firestore (within a radius of the claim, nearest first).
  - `search_policy_docs`: Vertex AI RAG Engine over policy wording, claims-handling guidelines, cat-event SOP and a Texas prompt-pay summary (exposed as a plain function tool).
- **Catalog/UI**: 14 claims from the derecho surge (12 homeowners, 2 auto comprehensive), 14 policies, ~33 real NOAA storm reports. A2UI renders a claim card, a compact queue list (no tables: rows of text, max 6 rows) and a peril-verification card.
- **Image gen**: Customer-facing claim status notice graphic (progress bar Received > Assessed > Paid, flat navy/teal style), uploaded to a public Cloud Storage bucket so A2UI cards can show it.
- **Sandbox**: Queue analytics after a surge triage: total gross exposure, total net payout, count and $ by decision, top claims by fraud risk, prompt-pay acknowledgement deadlines (15 days after reported date).

## Triage Procedure (Core Logic)
1. `get_claim`, `get_policy`.
2. **Verify peril**: Wind is supported if a NOAA wind or tornado report is within 10 miles on the loss date (Open-Meteo reanalysis gusts understate convective storms, so use it only to confirm the loss date was the windiest day of the week). Hail is supported only if a NOAA hail report is within 25 miles or Open-Meteo weather code is 96/99.
3. **Check coverage**: Use `search_policy_docs` and quote the clause and section relied on.
4. **Calculate payout**: Run `calculate_payout`.
5. **Decide**:
   - `siu_referral`: If the peril is unsupported AND there is at least one red flag (coverage increased < 60 days before loss, reported > 30 days after loss, prior same-peril claim < 24 months, policy incepted <= 7 days before the loss after a declared cat event).
   - `inspect`: If the peril is unsupported without red flags, or roof age > 15, or net payout exceeds the adjuster's authority limit.
   - `fast_track`: Otherwise.
6. **Give decision**: State decision with at most 3 reasons, each citing evidence (report location and distance, gust, clause).

## Headline Demo Moments
- **(a) "Triage the surge queue"**: 8 fast-track, 4 inspect, 2 SIU, with cited evidence and queue summary.
- **(b) "Why is CLM-1042 flagged?"**: Hail claimed, but the nearest NOAA hail report that day was ~69 miles away (the derecho was wind-driven), plus 3 red flags.
- **(c) CLM-1057 claims wind on 20 May on a policy bought 17 May**: No storm reports that day.
- **(d) Memory**: The adjuster sets a $15,000 limit once and later session checks apply $15,000 instead of $25,000.

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch: Vertex AI RAG grounding, code sandbox for queue analytics, live Open-Meteo API, ADK evaluation (8-case evalset, baseline vs improved score), Omni video explainer for the customer, Cloud Trace.
