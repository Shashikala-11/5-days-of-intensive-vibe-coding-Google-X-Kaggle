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

import os
from dotenv import load_dotenv
import google.auth
from google.auth.exceptions import DefaultCredentialsError

# Load environment configuration from .env file
load_dotenv()

# Setup Vertex AI vs Google AI Studio authentication
if not os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"):
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
    else:
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") == "True":
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        try:
            _, project_id = google.auth.default()
            os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
        except DefaultCredentialsError:
            pass
    if not os.environ.get("GOOGLE_CLOUD_LOCATION"):
        os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

from pydantic import BaseModel, Field
import json
import base64
import re
from google.adk.workflow import Workflow, START, FunctionNode
from google.adk.agents import LlmAgent
from google.adk.events.event import Event, EventActions
from google.adk.events.request_input import RequestInput
from google.adk.agents.context import Context
from google.adk.apps import App, ResumabilityConfig
from google.genai import types

# Import threshold and model config
from expense_agent.config import THRESHOLD_USD, LLM_MODEL


# 1. Input/Output Schemas
class RiskAssessment(BaseModel):
    risk_level: str = Field(
        description="The evaluated level of risk: Low, Medium, or High."
    )
    risk_factors: list[str] = Field(
        description="List of specific risk factors or red flags identified."
    )
    alert_triggered: bool = Field(
        description="True if an alert should be raised to a manager, False otherwise."
    )
    reasoning: str = Field(description="Detailed reasoning for the risk judgment.")


# 2. Node Definitions


def parse_expense_report(node_input) -> dict:
    """Parses incoming JSON event (handles base64 Pub/Sub or plain JSON)."""
    text_content = ""
    if hasattr(node_input, "parts"):
        text_content = "".join([part.text for part in node_input.parts if part.text])
    elif isinstance(node_input, str):
        text_content = node_input
    elif isinstance(node_input, dict):
        event_dict = node_input
    else:
        raise ValueError(f"Unsupported input type: {type(node_input)}")

    if not isinstance(node_input, dict):
        try:
            event_dict = json.loads(text_content)
        except Exception as e:
            raise ValueError(f"Failed to parse input as JSON: {e}. Raw: {text_content}")

    # Access data key, supporting base64-encoded or plain JSON payload
    data_val = event_dict.get("data")
    if not data_val:
        data_val = event_dict  # Fallback to root

    if isinstance(data_val, str):
        try:
            decoded = base64.b64decode(data_val).decode("utf-8")
            data_val = json.loads(decoded)
        except Exception:
            try:
                data_val = json.loads(data_val)
            except Exception:
                pass

    if not isinstance(data_val, dict):
        raise ValueError(
            f"Expense report data must be a dictionary. Got: {type(data_val)}"
        )

    # Pull out fields (amount, submitter, category, description, date)
    return {
        "amount": float(data_val.get("amount", 0.0)),
        "submitter": str(data_val.get("submitter", "Unknown")),
        "category": str(data_val.get("category", "General")),
        "description": str(data_val.get("description", "")),
        "date": str(data_val.get("date", "")),
    }


def security_checkpoint(ctx: Context, node_input: dict):
    """PII scrubbing and prompt injection interception checkpoint."""
    # Ensure parsed_expense is in state immediately for downstream nodes
    ctx.state["parsed_expense"] = node_input
    description = node_input.get("description", "")

    # 1. Scrub SSNs (e.g., 000-00-0000)
    ssn_pattern = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    scrubbed_desc = ssn_pattern.sub("[REDACTED SSN]", description)

    # Scrub Credit Card numbers (13 to 19 digits)
    cc_pattern = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
    scrubbed_desc = cc_pattern.sub("[REDACTED CARD]", scrubbed_desc)

    node_input["description"] = scrubbed_desc

    # 2. Defend against prompt injection
    injection_keywords = [
        "ignore previous",
        "system override",
        "new instructions",
        "disregard instructions",
        "you are now a",
        "prompt injection",
        "override system",
        "do not follow",
    ]

    has_injection = any(kw in scrubbed_desc.lower() for kw in injection_keywords)

    if has_injection:
        node_input["status"] = (
            "Flagged (Security Violation: Potential Prompt Injection)"
        )
        node_input["security_flagged"] = True
        yield Event(output=node_input, actions=EventActions(route="security_flagged"))
    else:
        yield Event(output=node_input, actions=EventActions(route="passed"))


def check_threshold(ctx: Context, node_input: dict):
    """Routing node: Keep threshold check and routing in Python code."""
    ctx.state["parsed_expense"] = node_input
    amount = node_input.get("amount", 0.0)

    if amount < THRESHOLD_USD:
        yield Event(output=node_input, actions=EventActions(route="auto_approve"))
    else:
        yield Event(output=node_input, actions=EventActions(route="llm_review"))


# The LLM is only there for risk judgment on expenses >= threshold
risk_assessor = LlmAgent(
    name="risk_assessor",
    model=LLM_MODEL,
    instruction="""Audit this expense report. Identify any policy violations, odd descriptions, or mismatch between merchant and category.
Provide a risk assessment detailing risk_level, risk_factors, alert_triggered flag, and reasoning.

Expense Details:
Submitter: {parsed_expense[submitter]}
Amount: ${parsed_expense[amount]}
Category: {parsed_expense[category]}
Description: {parsed_expense[description]}
Date: {parsed_expense[date]}""",
    output_schema=RiskAssessment,
    output_key="risk_assessment",
)


async def manager_review(ctx: Context, node_input: dict):
    """HITL step: pause the workflow using RequestInput for human approval."""
    expense = ctx.state["parsed_expense"]

    # Check if this expense was flagged as a security event by the checkpoint
    is_security_event = expense.get("security_flagged", False)

    if is_security_event:
        risk = {
            "risk_level": "CRITICAL (Security Threat)",
            "risk_factors": ["Potential Prompt Injection Attack"],
            "alert_triggered": True,
            "reasoning": "Intercepted by local security checkpoint. Bypassed LLM reviewer to prevent injection.",
        }
    else:
        risk = node_input

    if not ctx.resume_inputs or "decision" not in ctx.resume_inputs:
        raw_factors = risk.get("risk_factors", [])
        risk_factors = raw_factors if isinstance(raw_factors, list) else []
        msg = (
            f"⚠️ ALERT: Manual Review Required!\n"
            f"Submitter: {expense['submitter']}\n"
            f"Amount: ${expense['amount']:.2f}\n"
            f"Category: {expense['category']}\n"
            f"Description: {expense['description']}\n"
            f"--- LLM Audit ---\n"
            f"Risk Level: {risk.get('risk_level')}\n"
            f"Risk Factors: {', '.join(str(f) for f in risk_factors)}\n"
            f"Alert Triggered: {risk.get('alert_triggered')}\n"
            f"Reasoning: {risk.get('reasoning')}\n\n"
            f"Please approve or reject this expense (respond with 'approve' or 'reject'):"
        )
        yield RequestInput(interrupt_id="decision", message=msg)
        return

    raw_decision = ctx.resume_inputs["decision"]
    if isinstance(raw_decision, dict):
        decision = (
            raw_decision.get("decision")
            or raw_decision.get("value")
            or raw_decision.get("response")
            or list(raw_decision.values())[0]
        )
    else:
        decision = raw_decision
    decision = str(decision).strip().lower()

    result = {"expense": expense, "risk_assessment": risk, "manager_decision": decision}

    if decision in ["approve", "approved", "yes", "y"]:
        result["status"] = "Approved"
        yield Event(output=result, actions=EventActions(route="manager_approve"))
    else:
        result["status"] = "Rejected"
        yield Event(output=result, actions=EventActions(route="manager_reject"))


def auto_approve_expense(node_input: dict):
    """Auto-approve instantly, no LLM involved."""
    result = {
        **node_input,
        "status": "Approved",
        "reason": f"Auto-approved (below ${THRESHOLD_USD} threshold)",
    }
    yield Event(
        content=types.Content(
            role="model",
            parts=[
                types.Part.from_text(
                    text=f"Expense auto-approved! Details:\nAmount: ${node_input['amount']:.2f}\nSubmitter: {node_input['submitter']}\nCategory: {node_input['category']}"
                )
            ],
        )
    )
    yield Event(output=result)


# Final Nodes to record the outcomes
def record_approved(node_input: dict) -> str:
    return f"Expense Approved and Recorded. Details: {node_input}"


def record_rejected(node_input: dict) -> str:
    return f"Expense Rejected and Recorded. Details: {node_input}"


# Wrap the HITL step in FunctionNode to specify rerun_on_resume=True
manager_review_node = FunctionNode(
    func=manager_review, name="manager_review", rerun_on_resume=True
)


# 3. Connect Workflow Edges
edges = [
    (START, parse_expense_report),
    (parse_expense_report, security_checkpoint),
    # Routing out of security checkpoint
    (
        security_checkpoint,
        {"passed": check_threshold, "security_flagged": manager_review_node},
    ),
    # Threshold routing
    (
        check_threshold,
        {"auto_approve": auto_approve_expense, "llm_review": risk_assessor},
    ),
    # LLM Risk Assessor & Manager HITL path
    (risk_assessor, manager_review_node),
    (
        manager_review_node,
        {"manager_approve": record_approved, "manager_reject": record_rejected},
    ),
]

# 4. Instantiate Workflow
root_agent = Workflow(
    name="expense_workflow",
    edges=edges,
    description="Processes arriving expense reports based on thresholds and LLM-driven risk audit, with manual manager sign-off.",
)

# 5. Create App
app = App(
    root_agent=root_agent,
    name="app",
    resumability_config=ResumabilityConfig(is_resumable=True),
)
