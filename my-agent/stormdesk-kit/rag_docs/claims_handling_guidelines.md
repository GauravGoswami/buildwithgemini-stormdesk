# Cedar Ridge Insurance Company - Claims Handling Guidelines & SOP

These guidelines establish standard operating procedures for claim intake, triage decisions, peril verification, payout calculations, and Special Investigations Unit (SIU) referrals across all property and casualty claims at Cedar Ridge Insurance Company.

## Section 2 Triage Decisions
When evaluating a newly reported claim, adjusters must categorize the claim into one of three standard triage decisions:
1. **fast_track**: Approved for immediate payout within target timelines without requiring a field or desk inspection, applicable when peril is fully verified and no red flags exist.
2. **inspect**: Designated for mandatory field or desk inspection prior to payment determination, required when physical verification, structural scope evaluation, or roof assessment is necessary.
3. **siu_referral**: Referred to the Special Investigations Unit for fraud and coverage review. Adjusters must never accuse the policyholder or customer of fraud; all communications must maintain strictly neutral, professional, and objective factual language.

## Section 3 Authority Limits
Adjusters must operate within their designated financial authority limits for net payout determinations:
- Standard Adjuster Authority Limit: $25,000 net payout.
- Senior Adjuster Authority Limit: $100,000 net payout.
- Claims Manager Approval: Required for any claim where net payout exceeds $100,000.
An individual adjuster may elect to configure a lower personal authority limit (e.g., $15,000) in their user profile settings, which will be strictly enforced during triage automated checks.

## Section 4 Peril Verification Standard
Every storm-related claim must be corroborated against official weather evidence:
- **Windstorm Peril**: Corroborated when an official NOAA Storm Events report for thunderstorm wind, high wind, or tornado is recorded within 10 miles of the insured property address on the date of loss. Reanalysis weather data (e.g., Open-Meteo) understates convective gusts and must be used solely to confirm that the loss date was the windiest day in a +/- 3-day window.
- **Hail Peril**: Corroborated when an official NOAA hail report is recorded within 25 miles of the property address on the date of loss, or when reanalysis data confirms a hail weather code (e.g., code 96 or 99).

## Section 5 SIU Red Flags
Adjusters must check each claim against the following four specific SIU Red Flags:
1. Policy coverage limits were increased within 60 days prior to the date of loss.
2. The loss was reported more than 30 days after the date of loss.
3. The policyholder has a prior claim for the same peril within the preceding 24 months.
4. The policy incepted within 7 days prior to the loss date AND following a declared catastrophe event.

## Section 6 SIU Referral Rule
An adjuster shall issue an `siu_referral` triage decision ONLY when the claimed peril is NOT corroborated by weather evidence AND at least one SIU Red Flag is present. If the claimed peril is not corroborated but NO red flags are present, the adjuster shall assign a triage decision of `inspect`.

## Section 7 Roof Age
Any homeowners claim involving a roof structure older than 15 years requires a mandatory `inspect` triage decision prior to any payment determination, regardless of peril corroboration.

## Section 8 Documentation
Every triage decision recorded in the system must explicitly document its supporting evidence, including specific NOAA report IDs, measured distances in miles, weather gust metrics, and cited policy clauses.

***
Fictional document for a demo. Not legal advice.
