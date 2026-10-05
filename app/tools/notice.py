"""Claim status notice graphic generator and explainer video tools."""

import os
from datetime import datetime, timezone

from google import genai
from google.genai import types
from google.cloud import storage
from google.adk.tools import ToolContext

from app.tools.claims import get_claim
from app.tools.payout import calculate_payout

MEDIA_BUCKET = os.environ.get("MEDIA_BUCKET", "stormdesk-media-8c3b70")


async def generate_claim_notice(
    claim_id: str,
    status_message: str = "",
    tool_context: ToolContext = None,
) -> str:
    """Generate a clean customer-facing claim status graphic notice.

    Args:
        claim_id: Unique claim identifier (e.g. 'CLM-1001').
        status_message: Optional status message. If empty, auto-generated based on claim status in Firestore.
        tool_context: ToolContext for saving session artifacts.

    Returns:
        Public HTTPS URL of the uploaded claim notice graphic.
    """
    claim = get_claim(claim_id)
    claim_status = (claim.get("status") or "new").lower() if isinstance(claim, dict) else "new"

    highlighted_step = "Received"

    if not status_message or not status_message.strip():
        # Retrieve payout_usd from triage dict if present, otherwise call calculate_payout
        payout_usd = None
        if isinstance(claim, dict) and "triage" in claim and isinstance(claim.get("triage"), dict):
            payout_usd = claim["triage"].get("payout_usd")

        if payout_usd is None:
            payout_res = calculate_payout(claim_id)
            payout_usd = payout_res.get("net_payout", 0.0)

        payout_formatted = f"{payout_usd:,.2f}" if payout_usd % 1 != 0 else f"{int(payout_usd):,}"

        if claim_status == "fast_track":
            highlighted_step = "Assessed"
            status_message = f"Approved: your payment of ${payout_formatted} is being processed within 72 hours."
        elif claim_status == "inspect":
            highlighted_step = "Assessed"
            status_message = "An adjuster will contact you to schedule an inspection."
        elif claim_status == "siu_referral":
            highlighted_step = "Received"
            status_message = "Your claim is under review. We'll contact you if we need anything else."
        else:  # 'new' or default
            highlighted_step = "Received"
            status_message = "We've received your claim and are reviewing it."
    else:
        if claim_status in ("fast_track", "inspect"):
            highlighted_step = "Assessed"
        elif claim_status == "paid":
            highlighted_step = "Paid"

    # Select icon type based on claim/policy type
    policy_type = (claim.get("type") or "").lower() if isinstance(claim, dict) else ""
    icon_type = "car" if "auto" in policy_type else "house"

    client = genai.Client(vertexai=True, location="global")
    prompt = (
        f"A clean customer-facing status graphic for Cedar Ridge Insurance (fictional) for claim ID {claim_id}.\n"
        f"Design elements:\n"
        f"- A simple {icon_type} icon\n"
        f"- A 3-step progress bar (Received, Assessed, Paid) with the '{highlighted_step}' step visually highlighted\n"
        f"- Claim ID '{claim_id}'\n"
        f"- Large readable status message text: '{status_message}'\n"
        f"- Color palette: flat illustration, navy #0B2545 and teal #13B5A6 on a clean white background\n"
        f"- No people, no real logos."
    )

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    part = response.candidates[0].content.parts[0]
    image_bytes = part.inline_data.data
    mime_type = part.inline_data.mime_type or "image/png"

    # 1. Save artifact for Playground Artifacts panel
    filename = f"{claim_id}_notice.png"
    if tool_context and hasattr(tool_context, "save_artifact"):
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload same bytes to MEDIA_BUCKET at notices/<claim_id>-<timestamp>.png
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    blob_name = f"notices/{claim_id}-{timestamp}.png"

    storage_client = storage.Client()
    bucket = storage_client.bucket(MEDIA_BUCKET)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    return blob.public_url


async def generate_claim_explainer_video(
    claim_id: str,
    tool_context: ToolContext = None,
) -> str:
    """Generate a 6-second calm animated explainer video of the claim's next steps.

    Args:
        claim_id: Unique claim identifier (e.g. 'CLM-1001').
        tool_context: ToolContext for saving session artifacts.

    Returns:
        Public HTTPS URL of the uploaded claim explainer video in MEDIA_BUCKET.
    """
    claim = get_claim(claim_id)
    policy_type = (claim.get("type") or "").lower() if isinstance(claim, dict) else ""
    icon_type = "car" if "auto" in policy_type else "house"

    client = genai.Client(vertexai=True, location="global")
    prompt = (
        f"A 6-second calm animated explainer video of next steps for claim {claim_id}.\n"
        f"Design elements:\n"
        f"- Flat illustration style, navy #0B2545 and teal #13B5A6 colors on a clean white background\n"
        f"- Simple {icon_type} icon showing claim review and progress steps\n"
        f"- Calm smooth motion illustrating next steps for the policyholder\n"
        f"- No people, no real logos."
    )

    res = client.interactions.create(
        model="gemini-omni-flash-preview",
        input=[{"type": "text", "text": prompt}],
        response_modalities=["text", "video"],
    )

    video_bytes = None
    if hasattr(res, "output_video") and res.output_video and getattr(res.output_video, "data", None):
        video_bytes = res.output_video.data

    if not video_bytes and hasattr(res, "outputs"):
        for output in getattr(res, "outputs", []):
            if getattr(output, "type", None) == "video" and hasattr(output, "data"):
                video_bytes = output.data
                break

    if not video_bytes:
        raise RuntimeError("Failed to generate video: no video bytes returned from model.")

    mime_type = "video/mp4"

    # 1. Save artifact for Playground Artifacts panel
    filename = f"{claim_id}_explainer.mp4"
    if tool_context and hasattr(tool_context, "save_artifact"):
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload same bytes to MEDIA_BUCKET at videos/<claim_id>-<timestamp>.mp4
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    blob_name = f"videos/{claim_id}-{timestamp}.mp4"

    storage_client = storage.Client()
    bucket = storage_client.bucket(MEDIA_BUCKET)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    return blob.public_url
