"""Model access, paths, and hard limits for the Campus Customs agents.

The API key is read from the PORTKEY_API_KEY environment variable at model
construction time. It is never stored in code, prompts, logs, or output files.
A local `.env` file at the project root (copied from `.env.example`) is loaded
if present; variables already set in the shell take precedence.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=False)
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
AUDIT_PATH = PROJECT_ROOT / "output" / "audit_trail.json"

# MCP server: the same entry point and interpreter as .mcp.json.
MCP_SERVER_SCRIPT = PROJECT_ROOT / "mcp_server" / "server.py"
_VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
MCP_PYTHON = str(_VENV_PYTHON if _VENV_PYTHON.exists() else Path(sys.executable))

# The only model any agent may use.
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = os.environ.get("PORTKEY_BASE_URL") or "https://api.portkey.ai/v1"
PORTKEY_PROVIDER = os.environ.get("PORTKEY_PROVIDER") or "openai"

# ---- Hard limits (enforced in code, not only in prompts) -----------------
MAX_DELEGATION_DEPTH = 3        # boss -> specialist -> specialist -> specialist
MAX_DELEGATIONS_PER_RUN = 12    # total delegate_task calls in one run
MAX_STEPS_PER_RUN = 80          # audited steps (tool calls, delegations, agent turns)
MAX_TOOL_FAILURES_PER_RUN = 4   # failed / not-found MCP results before stopping
AGENT_RETRIES = 2               # output-validation retries per agent run

# Shared across the whole run (sub-agents reuse the parent's usage counter).
RUN_USAGE_LIMITS = UsageLimits(
    request_limit=40,
    tool_calls_limit=60,
    total_tokens_limit=250_000,
)


class MissingAPIKeyError(RuntimeError):
    pass


def build_model() -> OpenAIResponsesModel:
    """gpt-6-luna through the Portkey gateway, using the OpenAI Responses API
    (this deployment rejects function tools on /chat/completions)."""
    api_key = os.environ.get("PORTKEY_API_KEY")
    if not api_key:
        raise MissingAPIKeyError("Set the PORTKEY_API_KEY environment variable.")
    headers = {"x-portkey-api-key": api_key}
    if PORTKEY_PROVIDER:
        headers["x-portkey-provider"] = PORTKEY_PROVIDER
    client = AsyncOpenAI(
        api_key="portkey",  # placeholder; Portkey authenticates with the header above
        base_url=PORTKEY_BASE_URL,
        default_headers=headers,
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))
