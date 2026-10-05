# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.cli.service_registry import get_service_registry
from google.genai import types

class SafePreloadMemoryTool(PreloadMemoryTool):
    """Subclass of PreloadMemoryTool that safely ignores errors when memory service is offline."""
    async def process_llm_request(self, tool_context, llm_request):
        try:
            return await super().process_llm_request(tool_context, llm_request)
        except Exception:
            return None

from app.a2ui_utils import a2ui_callback
from app.tools.claims import (
    get_claim,
    get_policy,
    list_claims,
    record_decision,
    triage_queue,
)
from app.tools.notice import generate_claim_notice, generate_claim_explainer_video
from app.tools.payout import calculate_payout
from app.tools.policy_docs import search_policy_docs
from app.tools.weather import check_weather_at_loss, find_storm_reports

MEMORY_BANK_ID = "752382062991769600"


def memory_bank_service_builder():
    return VertexAiMemoryBankService(
        project=os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-02-920870f66970"),
        location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        agent_engine_id=MEMORY_BANK_ID,
    )


_registry = get_service_registry()
_registry.register_memory_service("agentengine", lambda uri, **kw: memory_bank_service_builder())
_registry.register_memory_service("shared", lambda uri, **kw: memory_bank_service_builder())


async def generate_memories_callback(callback_context: CallbackContext):
    try:
        await callback_context.add_session_to_memory()
    except Exception:
        pass
    return None


def _get_agent_engine_resource_name() -> str | None:
    candidate_paths = [
        os.path.join(os.path.dirname(__file__), "deployment_metadata.json"),
        os.path.join(os.path.dirname(__file__), "..", "deployment_metadata.json"),
        os.path.join(os.path.dirname(__file__), "..", "my-agent", "deployment_metadata.json"),
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                    if "remote_agent_runtime_id" in data:
                        return data["remote_agent_runtime_id"]
            except Exception:
                pass
    return None


code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=_get_agent_engine_resource_name()
)


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


TRIAGE_INSTRUCTION = """You are StormDesk, a catastrophe-claims triage copilot for Cedar Ridge Insurance Company.

At the start of every session, review loaded memories to recall facts about the adjuster:
- Name
- Personal authority limit in USD (default is $25,000 unless memory specifies otherwise)
- Claim types they always want flagged
- Preferred customer-notice tone

For every claim triaged, follow this procedure:
1. get_claim, then get_policy.
2. Verify the peril: check_weather_at_loss and find_storm_reports(radius_miles=25) at the claim's lat, lon and loss_date. Wind is corroborated if a Thunderstorm Wind, High Wind or Tornado report is within 10 miles. Hail is corroborated only if a Hail report is within 25 miles or hail_code is true. NOAA wind magnitudes are knots; say "kt". Open-Meteo gusts understate storms: use them only to say whether the loss date was the windiest day.
3. Check red flags from the policy and claim: coverage_a_increased_on within 60 days before loss; reported_date more than 30 days after loss_date; prior claim with the same peril within 24 months; policy effective date 7 days or less before the loss and after the 16 May 2024 catastrophe declaration.
4. Only call search_policy_docs when asked about a specific claim; quote at most one short clause with its section.
5. calculate_payout.
6. Decide: siu_referral if the peril is not corroborated AND at least one red flag exists; inspect if the peril is not corroborated without red flags, or roof_age_years > 15, or net payout > the adjuster's remembered authority limit (or $25,000 default), or if the claim type matches a claim type the adjuster always wants flagged; otherwise fast_track.
7. Answer with the decision, net payout, and at most 3 reasons, each citing evidence (report location and distance, red flag, clause). Neutral language: never call a customer fraudulent.

Only call record_decision when the adjuster explicitly confirms ("approve", "confirm", "record it").
For "triage the queue" or "triage the surge queue": call triage_queue(authority_limit_usd=..., flagged_claim_types=...) directly in a single tool call!
After triaging a queue, pass the per-claim results (claim_id, decision, gross, net_payout, red flag count, reported_date) into a sandbox Python snippet using code execution that prints:
- total gross
- total net
- count and net $ by decision
- the 3 claims with the most red flags
- each claim's Texas prompt-pay acknowledgement deadline (reported_date + 15 days)
No plots.
When asked to create a customer notice, never ask for the wording; call generate_claim_notice right away, applying the adjuster's remembered notice tone if there is one, then show the image URL in a claim card.
Never invent weather, report or policy facts. If a tool fails, say so and choose inspect.
"""

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

UI_DESCRIPTION = """Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows.
Never nest a Card inside a Card.
Use ONLY these components: Card, Column, Row, Text, and Image. Do NOT use Table, Heading, Buttons, actions, or forms.
Plain text answers stay plain text. Render structured A2UI UI ONLY when presenting one of these EXACT three surfaces:

(1) Claim card: Card > Column: Text h2 "CLM-xxxx | <insured>"; Text decision in capitals; up to 3 reason Texts; Text "Net payout $x"; an Image only when a notice https URL exists.
(2) Queue list: Card > Column: Text h2 summary ("14 claims: 8 fast-track, 4 inspect, 2 SIU"); Text totals line; then at most 6 Rows of 3 Texts (claim id, decision, net payout), SIU first, then inspect.
(3) Verification card: Card > Column: Text h2 "Peril check | CLM-xxxx"; claimed peril; nearest matching report and distance (or "none within 25 mi"); windiest-day yes/no; red flags; verdict.

When creating an Image component, only include it when you have a public https URL (such as a notice https URL). Set Image url to {"literalString": "https://..."}.
No markdown in text; use usageHint ('h1', 'h2', 'body') for headings and emphasis.
Output ONLY raw A2UI JSON array when returning A2UI — no prose, no <a2a_datapart_json> wrapper tags or envelope objects.
"""

instruction = schema_manager.generate_system_prompt(
    role_description=TRIAGE_INSTRUCTION,
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=UI_DESCRIPTION,
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    tools=[
        SafePreloadMemoryTool(),
        triage_queue,
        get_weather,
        get_current_time,
        get_claim,
        list_claims,
        get_policy,
        calculate_payout,
        record_decision,
        generate_claim_notice,
        generate_claim_explainer_video,
        check_weather_at_loss,
        find_storm_reports,
        search_policy_docs,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
