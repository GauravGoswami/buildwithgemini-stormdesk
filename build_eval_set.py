import os
import json
import asyncio
from google.adk.evaluation.eval_set import EvalSet
from google.adk.evaluation.eval_case import EvalCase, SessionInput, Invocation, InvocationEvent, IntermediateData, Rubric
from google.adk.evaluation.eval_config import EvalConfig
from google.adk.evaluation import AgentEvaluator

os.makedirs("tests/eval", exist_ok=True)
os.makedirs("eval_results", exist_ok=True)

test_config = {
  "criteria": {
    "tool_trajectory_avg_score": {
      "threshold": 1.0,
      "matchType": 2
    },
    "response_match_score": 0.8
  }
}

with open("tests/eval/test_config.json", "w") as f:
    json.dump(test_config, f, indent=2)

eval_cases = [
    # Case 1: Triage CLM-1003
    EvalCase(
        eval_id="case_1_CLM-1003",
        conversation=[
            Invocation(
                user_content=InvocationEvent(author="user", content={"parts": [{"text": "Triage CLM-1003"}]}),
                final_response=InvocationEvent(author="agent", content={"parts": [{"text": "CLM-1003 triaged as fast_track with net payout $5,600."}]}),
                intermediate_data=IntermediateData(
                    tool_uses=[
                        {"name": "find_storm_reports"},
                        {"name": "calculate_payout"}
                    ]
                ),
                rubrics=[
                    Rubric(
                        rubric_id="r1",
                        rubric_content={"text_property": "The response classifies CLM-1003 as fast_track and calculates net payout of $5,600, without recording a decision."},
                        description="Check decision fast_track and payout $5,600 for CLM-1003",
                        type="FINAL_RESPONSE_QUALITY"
                    )
                ]
            )
        ]
    ),
    # Case 2: Triage CLM-1042
    EvalCase(
        eval_id="case_2_CLM-1042",
        conversation=[
            Invocation(
                user_content=InvocationEvent(author="user", content={"parts": [{"text": "Triage CLM-1042"}]}),
                final_response=InvocationEvent(author="agent", content={"parts": [{"text": "CLM-1042 triaged as siu_referral because hail is not corroborated and red flags were detected."}]}),
                intermediate_data=IntermediateData(
                    tool_uses=[
                        {"name": "find_storm_reports"}
                    ]
                ),
                rubrics=[
                    Rubric(
                        rubric_id="r2",
                        rubric_content={"text_property": "The response identifies siu_referral for CLM-1042 and mentions hail not corroborated and at least one red flag."},
                        description="Check siu_referral, uncorroborated hail and red flags for CLM-1042",
                        type="FINAL_RESPONSE_QUALITY"
                    )
                ]
            )
        ]
    ),
    # Case 3: Triage CLM-1057
    EvalCase(
        eval_id="case_3_CLM-1057",
        conversation=[
            Invocation(
                user_content=InvocationEvent(author="user", content={"parts": [{"text": "Triage CLM-1057"}]}),
                final_response=InvocationEvent(author="agent", content={"parts": [{"text": "CLM-1057 triaged as siu_referral due to no storm reports on 20 May and recent policy inception."}]}),
                intermediate_data=IntermediateData(
                    tool_uses=[
                        {"name": "find_storm_reports"}
                    ]
                ),
                rubrics=[
                    Rubric(
                        rubric_id="r3",
                        rubric_content={"text_property": "The response identifies siu_referral for CLM-1057, mentioning no storm reports on May 20 and recent policy start."},
                        description="Check siu_referral, no storm reports on 20 May, recent policy start for CLM-1057",
                        type="FINAL_RESPONSE_QUALITY"
                    )
                ]
            )
        ]
    ),
    # Case 4: Triage CLM-1015
    EvalCase(
        eval_id="case_4_CLM-1015",
        conversation=[
            Invocation(
                user_content=InvocationEvent(author="user", content={"parts": [{"text": "Triage CLM-1015"}]}),
                final_response=InvocationEvent(author="agent", content={"parts": [{"text": "CLM-1015 triaged as inspect due to roof age, with estimated payout $5,400."}]}),
                intermediate_data=IntermediateData(
                    tool_uses=[
                        {"name": "calculate_payout"}
                    ]
                ),
                rubrics=[
                    Rubric(
                        rubric_id="r4",
                        rubric_content={"text_property": "The response classifies CLM-1015 as inspect, mentioning roof age and $5,400 net payout."},
                        description="Check inspect, roof age, and $5,400 for CLM-1015",
                        type="FINAL_RESPONSE_QUALITY"
                    )
                ]
            )
        ]
    ),
    # Case 5: Triage CLM-1005
    EvalCase(
        eval_id="case_5_CLM-1005",
        conversation=[
            Invocation(
                user_content=InvocationEvent(author="user", content={"parts": [{"text": "Triage CLM-1005"}]}),
                final_response=InvocationEvent(author="agent", content={"parts": [{"text": "CLM-1005 triaged as inspect because payout $44,300 exceeds authority limit."}]}),
                intermediate_data=IntermediateData(
                    tool_uses=[
                        {"name": "calculate_payout"}
                    ]
                ),
                rubrics=[
                    Rubric(
                        rubric_id="r5",
                        rubric_content={"text_property": "The response classifies CLM-1005 as inspect, mentioning authority limit and $44,300 payout."},
                        description="Check inspect, authority limit, and $44,300 for CLM-1005",
                        type="FINAL_RESPONSE_QUALITY"
                    )
                ]
            )
        ]
    ),
    # Case 6: Triage CLM-2009
    EvalCase(
        eval_id="case_6_CLM-2009",
        conversation=[
            Invocation(
                user_content=InvocationEvent(author="user", content={"parts": [{"text": "Triage CLM-2009"}]}),
                final_response=InvocationEvent(author="agent", content={"parts": [{"text": "CLM-2009 triaged as inspect because hail is not corroborated, but there are no red flags so it is not SIU."}]}),
                intermediate_data=IntermediateData(
                    tool_uses=[
                        {"name": "find_storm_reports"}
                    ]
                ),
                rubrics=[
                    Rubric(
                        rubric_id="r6",
                        rubric_content={"text_property": "The response classifies CLM-2009 as inspect, noting hail not corroborated, no red flags, and not SIU."},
                        description="Check inspect, hail uncorroborated, no red flags, not SIU for CLM-2009",
                        type="FINAL_RESPONSE_QUALITY"
                    )
                ]
            )
        ]
    ),
    # Case 7: Deductible query
    EvalCase(
        eval_id="case_7_CLM-1003_deductible",
        conversation=[
            Invocation(
                user_content=InvocationEvent(author="user", content={"parts": [{"text": "What is the wind and hail deductible on CLM-1003's policy?"}]}),
                final_response=InvocationEvent(author="agent", content={"parts": [{"text": "The wind and hail deductible for CLM-1003 is 1% of Coverage A ($2,800)."}]}),
                intermediate_data=IntermediateData(
                    tool_uses=[
                        {"name": "search_policy_docs"}
                    ]
                ),
                rubrics=[
                    Rubric(
                        rubric_id="r7",
                        rubric_content={"text_property": "The response identifies the wind and hail deductible as 1% of Coverage A ($2,800)."},
                        description="Check 1% Coverage A deductible ($2,800) for CLM-1003",
                        type="FINAL_RESPONSE_QUALITY"
                    )
                ]
            )
        ]
    ),
    # Case 8: Triage CLM-1001
    EvalCase(
        eval_id="case_8_CLM-1001",
        conversation=[
            Invocation(
                user_content=InvocationEvent(author="user", content={"parts": [{"text": "Triage CLM-1001"}]}),
                final_response=InvocationEvent(author="agent", content={"parts": [{"text": "CLM-1001 triaged as fast_track with net payout $11,400."}]}),
                intermediate_data=IntermediateData(
                    tool_uses=[
                        {"name": "find_storm_reports"},
                        {"name": "calculate_payout"}
                    ]
                ),
                rubrics=[
                    Rubric(
                        rubric_id="r8",
                        rubric_content={"text_property": "The response classifies CLM-1001 as fast_track with $11,400 net payout without recording a decision."},
                        description="Check fast_track and $11,400 payout for CLM-1001",
                        type="FINAL_RESPONSE_QUALITY"
                    )
                ]
            )
        ]
    )
]

eval_set = EvalSet(
    eval_set_id="stormdesk_eval_set",
    name="StormDesk Evaluation Set",
    description="8 test cases for StormDesk agent triage and policy query logic",
    eval_cases=eval_cases
)

eval_set_path = "tests/eval/stormdesk.evalset.json"
with open(eval_set_path, "w") as f:
    f.write(eval_set.model_dump_json(by_alias=True, indent=2))

print(f"Saved eval set to {eval_set_path}")
