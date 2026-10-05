import asyncio
import json
import os
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from app.agent import root_agent

async def run_eval_dataset():
    eval_set_path = "tests/eval/stormdesk.evalset.json"
    with open(eval_set_path, "r") as f:
        dataset = json.load(f)
    
    eval_cases = dataset.get("eval_cases", [])
    print(f"Loaded {len(eval_cases)} evaluation cases.")
    
    trace_eval_cases = []
    
    for idx, case in enumerate(eval_cases):
        case_id = case.get("eval_case_id", f"case_{idx+1}")
        prompt_obj = case.get("prompt", {})
        
        if isinstance(prompt_obj, dict):
            parts = prompt_obj.get("parts", [])
            prompt_text = parts[0].get("text", "") if parts else ""
        else:
            prompt_text = str(prompt_obj)
            
        print(f"[{idx+1}/{len(eval_cases)}] Running case {case_id}: '{prompt_text}'")
        
        session_service = InMemorySessionService()
        runner = Runner(
            agent=root_agent,
            session_service=session_service,
            app_name="stormdesk_eval"
        )
        
        session = await session_service.create_session(
            app_name="stormdesk_eval",
            user_id="eval_user"
        )
        
        tool_calls = []
        text_responses = []
        
        user_content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt_text)]
        )
        
        try:
            async for event in runner.run_async(
                user_id="eval_user",
                session_id=session.id,
                new_message=user_content
            ):
                if hasattr(event, "content") and event.content:
                    for part in getattr(event.content, "parts", []):
                        if hasattr(part, "function_call") and part.function_call:
                            tool_calls.append(part.function_call.name)
                        
                        # Extract text
                        txt = getattr(part, "text", None)
                        if txt:
                            text_responses.append(str(txt))
                            
                        # Extract inline_data (e.g. A2UI data blobs)
                        if hasattr(part, "inline_data") and part.inline_data and getattr(part.inline_data, "data", None):
                            data = part.inline_data.data
                            if isinstance(data, bytes):
                                txt_data = data.decode("utf-8", errors="ignore")
                            else:
                                txt_data = str(data)
                            text_responses.append(txt_data)
        except Exception as e:
            print(f"Case {case_id} error: {e}")
            
        turns_data = [
            {
                "events": [
                    {
                        "content": {
                            "parts": [
                                {"function_call": {"name": t}} for t in tool_calls
                            ] + [{"text": txt} for txt in text_responses]
                        }
                    }
                ]
            }
        ]
        
        trace_eval_cases.append({
            "eval_case_id": case_id,
            "agent_data": {
                "turns": turns_data
            }
        })
        print(f"Case {case_id} finished. Tool calls: {tool_calls}, text length: {len(' '.join(text_responses))}")

    trace_file = "artifacts/traces/traces_after.json"
    os.makedirs(os.path.dirname(trace_file), exist_ok=True)
    with open(trace_file, "w") as f:
        json.dump({
            "eval_set_id": "stormdesk_eval_set",
            "eval_cases": trace_eval_cases
        }, f, indent=2)
    print(f"Wrote traces to {trace_file}")

if __name__ == "__main__":
    asyncio.run(run_eval_dataset())
