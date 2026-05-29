"""Anthropic client + tool-use loop for the WhatsApp owner bot (S5 Feature 1).

Same configuration discipline as the other external clients: `is_configured()`
gates everything and there are no module-level SDK side effects, so importing
this in dev/CI without a key is harmless.

`run_conversation` runs the standard Anthropic tool-use loop:
    1. Send the owner's message + the available tools to Claude (Sonnet 4.6).
    2. If Claude asks to use tools, execute each via the injected `dispatch`
       (which is closed over the authenticated tenant_id — Claude never picks
       the tenant) and feed the results back.
    3. Repeat until Claude returns a final natural-language answer, or we hit
       the iteration cap (a cost/runaway guard).

The model and key come from settings. Callers MUST check `is_configured()`
first; calling unconfigured raises (it's a programming error, not a runtime
condition we degrade on).
"""

from collections.abc import Callable
from typing import Any, cast

import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)

# A WhatsApp reply is short; cap output so a runaway generation can't balloon
# cost or latency.
MAX_TOKENS = 1024
# Hard ceiling on tool round-trips per message. Each iteration is one Claude
# call; 4 is plenty for "look up X then maybe Y then answer".
MAX_ITERATIONS = 4

# Dispatch executes a tool by name with Claude's input and returns a string to
# hand back as the tool result. The tenant scope is baked into the closure.
DispatchFn = Callable[[str, dict[str, Any]], str]


def is_configured() -> bool:
    return bool(get_settings().anthropic_api_key)


def run_conversation(
    *,
    system: str,
    user_text: str,
    tools: list[dict[str, Any]],
    dispatch: DispatchFn,
    max_iterations: int = MAX_ITERATIONS,
) -> str:
    """Run the tool-use loop and return Claude's final text answer.

    Raises RuntimeError if called without configuration (caller must gate on
    `is_configured()`). Tool execution errors are caught per-tool and returned
    to Claude as an error tool_result so it can recover or explain, rather than
    crashing the whole reply.
    """
    if not is_configured():
        raise RuntimeError("anthropic_client.run_conversation called unconfigured")

    from anthropic import Anthropic

    settings = get_settings()
    client = Anthropic(api_key=settings.anthropic_api_key)
    model = settings.anthropic_model

    messages: list[dict[str, Any]] = [{"role": "user", "content": user_text}]

    for _ in range(max_iterations):
        # The SDK types tools/messages with strict TypedDicts but accepts plain
        # dicts at runtime (same tolerance we rely on for resend). Cast to Any
        # so we keep one dict shape without chasing SDK type-stub churn.
        resp = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system,
            tools=cast(Any, tools),
            messages=cast(Any, messages),
        )

        if getattr(resp, "stop_reason", None) != "tool_use":
            return _extract_text(resp)

        # Claude wants to call one or more tools. Echo its turn back, then run
        # each tool and append the results in a single user turn.
        messages.append({"role": "assistant", "content": _blocks_to_dicts(resp.content)})
        tool_results: list[dict[str, Any]] = []
        for block in resp.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            name = getattr(block, "name", "")
            tool_input = getattr(block, "input", {}) or {}
            try:
                result = dispatch(name, dict(tool_input))
            except Exception as exc:  # surface to Claude, not a crash
                log.warning("bot_tool_failed", tool=name, error=str(exc))
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": getattr(block, "id", ""),
                        "content": "Error running this tool. Tell the user it's unavailable.",
                        "is_error": True,
                    }
                )
                continue
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": getattr(block, "id", ""),
                    "content": result,
                }
            )
        messages.append({"role": "user", "content": tool_results})

    # Hit the iteration cap without a final answer — degrade gracefully.
    log.warning("bot_tool_loop_exhausted", iterations=max_iterations)
    return "Sorry, I couldn't put that together right now. Try asking a simpler question."


def _extract_text(resp: Any) -> str:
    """Concatenate text blocks from a final (non-tool) response."""
    parts: list[str] = []
    for block in getattr(resp, "content", []) or []:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", ""))
    return "\n".join(p for p in parts if p).strip()


def _blocks_to_dicts(content: Any) -> list[dict[str, Any]]:
    """Convert SDK content blocks back into the plain-dict shape the messages
    API accepts on the next turn. We only need text and tool_use blocks."""
    out: list[dict[str, Any]] = []
    for block in content or []:
        btype = getattr(block, "type", None)
        if btype == "text":
            out.append({"type": "text", "text": getattr(block, "text", "")})
        elif btype == "tool_use":
            out.append(
                {
                    "type": "tool_use",
                    "id": getattr(block, "id", ""),
                    "name": getattr(block, "name", ""),
                    "input": getattr(block, "input", {}) or {},
                }
            )
    return out
