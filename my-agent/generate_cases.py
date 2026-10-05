import os
import json

eval_dir = "/config/.gemini/antigravity/scratch/build-with-gemini/my-agent/tests/eval"
os.makedirs(eval_dir, exist_ok=True)

test_config = {
  "criteria": {
    "tool_trajectory_avg_score": {
      "threshold": 1.0,
      "matchType": 2
    },
    "response_match_score": 0.8
  }
}

with open(os.path.join(eval_dir, "test_config.json"), "w") as f:
    json.dump(test_config, f, indent=2)

eval_cases = [
    {
        "eval_case_id": "case_1_CLM-1003",
        "prompt": {
            "role": "user",
            "parts": [{"text": "Triage CLM-1003"}]
        },
        "rubrics": [
            {
                "rubric_id": "r1",
                "rubric_content": {"text_property": "The response classifies CLM-1003 as fast_track with net payout of $5,600, without recording a decision."},
                "description": "Check decision fast_track and payout $5,600 for CLM-1003",
                "type": "FINAL_RESPONSE_QUALITY"
            }
        ]
    },
    {
        "eval_case_id": "case_2_CLM-1042",
        "prompt": {
            "role": "user",
            "parts": [{"text": "Triage CLM-1042"}]
        },
        "rubrics": [
            {
                "rubric_id": "r2",
                "rubric_content": {"text_property": "The response identifies siu_referral for CLM-1042, mentioning hail not corroborated and at least one red flag."},
                "description": "Check siu_referral, uncorroborated hail and red flag for CLM-1042",
                "type": "FINAL_RESPONSE_QUALITY"
            }
        ]
    },
    {
        "eval_case_id": "case_3_CLM-1057",
        "prompt": {
            "role": "user",
            "parts": [{"text": "Triage CLM-1057"}]
        },
        "rubrics": [
            {
                "rubric_id": "r3",
                "rubric_content": {"text_property": "The response identifies siu_referral for CLM-1057, mentioning no storm reports on May 20 and recent policy start."},
                "description": "Check siu_referral, no storm reports on May 20, recent policy start for CLM-1057",
                "type": "FINAL_RESPONSE_QUALITY"
            }
        ]
    },
    {
        "eval_case_id": "case_4_CLM-1015",
        "prompt": {
            "role": "user",
            "parts": [{"text": "Triage CLM-1015"}]
        },
        "rubrics": [
            {
                "rubric_id": "r4",
                "rubric_content": {"text_property": "The response classifies CLM-1015 as inspect, mentioning roof age and $5,400 net payout."},
                "description": "Check inspect, roof age, $5,400 for CLM-1015",
                "type": "FINAL_RESPONSE_QUALITY"
            }
        ]
    },
    {
        "eval_case_id": "case_5_CLM-1005",
        "prompt": {
            "role": "user",
            "parts": [{"text": "Triage CLM-1005"}]
        },
        "rubrics": [
            {
                "rubric_id": "r5",
                "rubric_content": {"text_property": "The response classifies CLM-1005 as inspect, mentioning authority limit and $44,300 payout."},
                "description": "Check inspect, authority limit, $44,300 for CLM-1005",
                "type": "FINAL_RESPONSE_QUALITY"
            }
        ]
    },
    {
        "eval_case_id": "case_6_CLM-2009",
        "prompt": {
            "role": "user",
            "parts": [{"text": "Triage CLM-2009"}]
        },
        "rubrics": [
            {
                "rubric_id": "r6",
                "rubric_content": {"text_property": "The response classifies CLM-2009 as inspect, noting hail not corroborated, no red flags, and not SIU."},
                "description": "Check inspect, hail uncorroborated, no red flags, not SIU for CLM-2009",
                "type": "FINAL_RESPONSE_QUALITY"
            }
        ]
    },
    {
        "eval_case_id": "case_7_CLM-1003_deductible",
        "prompt": {
            "role": "user",
            "parts": [{"text": "What is the wind and hail deductible on CLM-1003's policy?"}]
        },
        "rubrics": [
            {
                "rubric_id": "r7",
                "rubric_content": {"text_property": "The response identifies the wind and hail deductible as 1% of Coverage A ($2,800)."},
                "description": "Check 1% Coverage A ($2,800) deductible for CLM-1003",
                "type": "FINAL_RESPONSE_QUALITY"
            }
        ]
    },
    {
        "eval_case_id": "case_8_CLM-1001",
        "prompt": {
            "role": "user",
            "parts": [{"text": "Triage CLM-1001"}]
        },
        "rubrics": [
            {
                "rubric_id": "r8",
                "rubric_content": {"text_property": "The response classifies CLM-1001 as fast_track with $11,400 net payout without recording a decision."},
                "description": "Check fast_track and $11,400 payout for CLM-1001",
                "type": "FINAL_RESPONSE_QUALITY"
            }
        ]
    }
]

eval_set = {
    "eval_set_id": "stormdesk_eval_set",
    "name": "StormDesk Evaluation Set",
    "description": "8 test cases for StormDesk agent",
    "eval_cases": eval_cases
}

dataset_path = os.path.join(eval_dir, "stormdesk.evalset.json")
with open(dataset_path, "w") as f:
    json.dump(eval_set, f, indent=2)

print(f"Generated {dataset_path}")
