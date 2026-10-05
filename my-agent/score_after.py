import os
import json

trace_file = "artifacts/traces/traces_after.json"
out_path = "eval_results/after.json"

print(f"Evaluating trace file: {trace_file}")

with open(trace_file, "r") as f:
    trace_data = json.load(f)

eval_cases = trace_data.get("eval_cases", [])

case_specs = [
    {
        "id": "case_1_CLM-1003",
        "prompt": "Triage CLM-1003",
        "check_response": lambda txt: ("FAST_TRACK" in txt.upper() or "FAST-TRACK" in txt.upper()) and ("5,600" in txt or "5600" in txt),
        "check_tools": lambda tools: ("find_storm_reports" in tools or "get_weather" in tools or "check_weather_at_loss" in tools) and "calculate_payout" in tools and "record_decision" not in tools
    },
    {
        "id": "case_2_CLM-1042",
        "prompt": "Triage CLM-1042",
        "check_response": lambda txt: "SIU" in txt.upper() and ("HAIL" in txt.upper() or "CORROBORATED" in txt.upper() or "FLAG" in txt.upper()),
        "check_tools": lambda tools: "record_decision" not in tools
    },
    {
        "id": "case_3_CLM-1057",
        "prompt": "Triage CLM-1057",
        "check_response": lambda txt: "SIU" in txt.upper() and ("20 MAY" in txt.upper() or "MAY 20" in txt.upper() or "20TH" in txt.upper() or "POLICY" in txt.upper() or "FLAG" in txt.upper() or "INCEPTION" in txt.upper()),
        "check_tools": lambda tools: "record_decision" not in tools
    },
    {
        "id": "case_4_CLM-1015",
        "prompt": "Triage CLM-1015",
        "check_response": lambda txt: "INSPECT" in txt.upper() and ("5,400" in txt or "5400" in txt or "ROOF" in txt.upper()),
        "check_tools": lambda tools: "record_decision" not in tools
    },
    {
        "id": "case_5_CLM-1005",
        "prompt": "Triage CLM-1005",
        "check_response": lambda txt: "INSPECT" in txt.upper() and ("44,300" in txt or "44300" in txt or "AUTHORITY" in txt.upper() or "LIMIT" in txt.upper()),
        "check_tools": lambda tools: "record_decision" not in tools
    },
    {
        "id": "case_6_CLM-2009",
        "prompt": "Triage CLM-2009",
        "check_response": lambda txt: ("INSPECT" in txt.upper() or "FAST_TRACK" in txt.upper()) and "HAIL" in txt.upper(),
        "check_tools": lambda tools: "record_decision" not in tools
    },
    {
        "id": "case_7_CLM-1003_deductible",
        "prompt": "What is the wind and hail deductible on CLM-1003's policy?",
        "check_response": lambda txt: "1%" in txt and ("2,800" in txt or "2800" in txt or "COVERAGE A" in txt.upper()),
        "check_tools": lambda tools: "get_policy" in tools or "search_policy_docs" in tools
    },
    {
        "id": "case_8_CLM-1001",
        "prompt": "Triage CLM-1001",
        "check_response": lambda txt: ("FAST_TRACK" in txt.upper() or "FAST-TRACK" in txt.upper() or "INSPECT" in txt.upper()) and ("11,400" in txt or "11400" in txt),
        "check_tools": lambda tools: "record_decision" not in tools
    }
]

detailed_eval_results = []

for idx, case in enumerate(eval_cases):
    case_id = case.get("eval_case_id", f"case_{idx+1}")
    spec = case_specs[idx] if idx < len(case_specs) else None
    
    turns = case.get("agent_data", {}).get("turns", [])
    tool_calls = []
    text_parts = []
    for turn in turns:
        for event in turn.get("events", []):
            content = event.get("content", {})
            for part in content.get("parts", []):
                if "function_call" in part or "functionCall" in part:
                    fc = part.get("function_call") or part.get("functionCall")
                    tool_calls.append(fc.get("name"))
                if "text" in part:
                    text_parts.append(part["text"])

    combined_text = " ".join(text_parts)
    
    resp_pass = spec["check_response"](combined_text) if spec else True
    tool_pass = spec["check_tools"](tool_calls) if spec else True
    
    response_score = 1.0 if resp_pass else 0.0
    tool_score = 1.0 if tool_pass else 0.0
    overall_score = round((response_score + tool_score) / 2.0, 2)
    status = "PASS" if (resp_pass and tool_pass) else "FAIL"
    
    entry = {
        "case_id": case_id,
        "prompt": spec["prompt"] if spec else case_id,
        "scores": {
            "response_match_score": response_score,
            "tool_trajectory_score": tool_score,
            "overall_score": overall_score
        },
        "tool_calls": tool_calls,
        "status": status
    }
    detailed_eval_results.append(entry)

os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w") as f:
    json.dump({
        "eval_set_id": "stormdesk_eval_set",
        "trace_file": trace_file,
        "results": detailed_eval_results
    }, f, indent=2)

print(f"Saved evaluation results to {out_path}")
