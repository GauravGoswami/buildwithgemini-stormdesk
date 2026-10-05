"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.
"""

import base64
import json
import os
import re
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    FilePart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    TextPart,
    TransportProtocol,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

RESOURCE = os.environ["AGENT_ENGINE_RESOURCE_NAME"]
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"

_A2UI_MIME = "application/json+a2ui"

_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


_contexts: dict[str, str] = {}
_card: AgentCard | None = None


async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        card = AgentCard(**resp.json())
        card.url = A2A_BASE
        _card = card
    return _card


def _parse_a2ui_payload(obj) -> dict | None:
    if isinstance(obj, dict):
        if "surfaceUpdate" in obj or "beginRendering" in obj:
            return {"kind": "a2ui", "data": obj}
        if "data" in obj and isinstance(obj["data"], dict):
            return _parse_a2ui_payload(obj["data"])
    return None


def _extract_parts_from_part(p) -> list[dict]:
    out = []
    root = getattr(p, "root", p)

    # 1. TextPart
    if isinstance(root, TextPart) and getattr(root, "text", None):
        text = root.text
        if "Cannot add session to memory" in text:
            return out

        # Handle markdown ```json ... ``` containing A2UI surface updates
        if "```json" in text:
            m = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if m:
                try:
                    payload = json.loads(m.group(1).strip())
                    if isinstance(payload, list) and len(payload) > 0 and isinstance(payload[0], dict) and "surfaceId" in payload[0]:
                        out.append({"kind": "a2ui", "data": {"surfaceUpdate": payload}})
                        clean = re.sub(r"```json\s*.*?\s*```", "", text, flags=re.DOTALL).strip()
                        if clean:
                            out.append({"kind": "text", "text": clean})
                        return out
                except Exception:
                    pass

        # Handle <a2ui-json> tags
        if "<a2ui-json>" in text:
            m = re.search(r"<a2ui-json>(.*?)</a2ui-json>", text, re.DOTALL)
            if m:
                try:
                    payload = json.loads(m.group(1).strip())
                    out.append({"kind": "a2ui", "data": {"surfaceUpdate": payload}})
                except Exception:
                    pass
            # Extract any remaining non-tag text
            clean = re.sub(r"<a2ui-json>.*?</a2ui-json>", "", text, flags=re.DOTALL).strip()
            if clean:
                out.append({"kind": "text", "text": clean})
        # Handle <a2a_datapart_json> tags
        elif "<a2a_datapart_json>" in text:
            m = re.search(r"<a2a_datapart_json>(.*?)</a2a_datapart_json>", text, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(1).strip())
                    res = _parse_a2ui_payload(parsed)
                    if res:
                        out.append(res)
                except Exception:
                    pass
            clean = re.sub(r"<a2a_datapart_json>.*?</a2a_datapart_json>", "", text, flags=re.DOTALL).strip()
            if clean:
                out.append({"kind": "text", "text": clean})
        else:
            out.append({"kind": "text", "text": text})

    # 2. DataPart
    elif getattr(root, "data", None) is not None:
        data = root.data
        if isinstance(data, dict):
            meta = getattr(root, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if mime == _A2UI_MIME or "surfaceUpdate" in data or "beginRendering" in data:
                out.append({"kind": "a2ui", "data": data})
            elif "text" in data:
                out.append({"kind": "text", "text": str(data["text"])})

    # 3. FilePart
    elif isinstance(root, FilePart):
        f = getattr(root, "file", None)
        if f:
            raw = getattr(f, "bytes", None) or getattr(f, "bytes_b64", None)
            if raw:
                try:
                    decoded = (
                        base64.b64decode(raw).decode("utf-8", errors="ignore")
                        if isinstance(raw, str)
                        else raw.decode("utf-8", errors="ignore")
                    )
                    if "<a2a_datapart_json>" in decoded:
                        m = re.search(r"<a2a_datapart_json>(.*?)</a2a_datapart_json>", decoded, re.DOTALL)
                        if m:
                            parsed = json.loads(m.group(1).strip())
                            res = _parse_a2ui_payload(parsed)
                            if res:
                                out.append(res)
                    elif "<a2ui-json>" in decoded:
                        m = re.search(r"<a2ui-json>(.*?)</a2ui-json>", decoded, re.DOTALL)
                        if m:
                            payload = json.loads(m.group(1).strip())
                            out.append({"kind": "a2ui", "data": {"surfaceUpdate": payload}})
                except Exception:
                    pass
            uri = getattr(f, "uri", None)
            if uri and uri.startswith("http"):
                out.append({"kind": "text", "text": uri})

    return out


def _extract_message(msg) -> list[dict]:
    out = []
    if msg is None:
        return out
    role = getattr(msg, "role", None)
    if role and "user" in str(role).lower():
        return out
    for p in getattr(msg, "parts", None) or []:
        out.extend(_extract_parts_from_part(p))
    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=180) as client:
        card = await _get_card(client)
        factory = ClientFactory(
            ClientConfig(
                supported_transports=[
                    TransportProtocol.jsonrpc,
                    TransportProtocol.http_json,
                ],
                httpx_client=client,
            )
        )
        a2a_client = factory.create(card)

        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.user,
            parts=[Part(root=TextPart(text=message))],
            context_id=_contexts.get(user_id),
        )

        last_task = None
        async for event in a2a_client.send_message(msg):
            if not isinstance(event, tuple):
                continue
            task, update = event
            if task is not None:
                last_task = task
                if getattr(task, "context_id", None):
                    _contexts[user_id] = task.context_id

            if update:
                # Extract from TaskArtifactUpdateEvent
                if isinstance(update, TaskArtifactUpdateEvent) and getattr(update, "artifact", None):
                    for p in getattr(update.artifact, "parts", []):
                        parts.extend(_extract_parts_from_part(p))
                # Extract from TaskStatusUpdateEvent
                st = getattr(update, "status", None)
                if st and getattr(st, "message", None):
                    parts.extend(_extract_message(st.message))

        # Check task history and status message
        if last_task:
            if getattr(last_task, "history", None):
                for m in last_task.history:
                    parts.extend(_extract_message(m))
            st = getattr(last_task, "status", None)
            if st and getattr(st, "message", None):
                parts.extend(_extract_message(st.message))

    # Deduplicate parts while preserving order
    deduped = []
    seen = set()
    for p in parts:
        s = json.dumps(p, sort_keys=True)
        if s not in seen:
            seen.add(s)
            deduped.append(p)

    if not deduped:
        deduped = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": deduped})


STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
