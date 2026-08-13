import asyncio
import logging
import json
import os
from typing import Optional
from core.message_broker import (
    claim_next_event,
    mark_event_completed,
    mark_event_failed,
    mark_event_poison,
)
from core.agent import JarvisAgent

logger = logging.getLogger("JARVIS_ORCHESTRATOR")

MAX_CONCURRENT_AGENTS = 3
_semaphore: Optional[asyncio.Semaphore] = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT_AGENTS)
    return _semaphore


def _resolve_prompt_path(target_agent: str) -> Optional[str]:
    """Find role prompt under core/prompts/ (including nested business/)."""
    base = os.path.join(os.getcwd(), "core", "prompts")
    direct = os.path.join(base, f"{target_agent}.md")
    if os.path.exists(direct):
        return direct
    for root, _dirs, files in os.walk(base):
        if f"{target_agent}.md" in files:
            return os.path.join(root, f"{target_agent}.md")
    return None


def _square_context(limit: int = 8000) -> str:
    square_path = os.path.join("workspace", "square.md")
    if not os.path.exists(square_path):
        return ""
    try:
        with open(square_path, "r", encoding="utf-8") as f:
            return f.read()[-limit:]
    except Exception:
        return ""


async def _run_claimed_event(event_id: int, event_type: str, target_agent: str, payload_str: str):
    sem = _get_semaphore()
    async with sem:
        try:
            try:
                payload = json.loads(payload_str) if payload_str else {}
            except json.JSONDecodeError as e:
                mark_event_poison(event_id, f"Invalid JSON payload: {e}")
                return

            if not isinstance(payload, dict):
                mark_event_poison(event_id, "Payload is not a JSON object")
                return

            logger.info(f"📬 Orchestrator claimed event {event_id}: [{event_type}] for '{target_agent}'")

            agent = JarvisAgent(role=target_agent)
            prompt_path = _resolve_prompt_path(target_agent)
            if prompt_path:
                with open(prompt_path, "r", encoding="utf-8") as f:
                    agent.brain.system_instruction = f.read()

            square_context = _square_context()
            msg = f"""
🔔 [SYSTEM EVENT TRIGGERED: {event_type}]
Event ID: {event_id}
You have received a new background event from the Message Broker.

[🌐 THE INTERNAL SQUARE FEED (Team Activity & Awareness)]:
{square_context if square_context else "No recent activity."}

[STRUCTURED PAYLOAD]:
{json.dumps(payload, indent=2, ensure_ascii=False)}

[CRITICAL INSTRUCTIONS]:
1. Prefer structured fields (product, chat_id, image_path, min_amount, etc.) over free-text.
2. Execute your designated task for this event_type only.
3. If the overarching workflow is NOT done, use `publish_event` to pass the baton to the logical next agent.
4. If you are the CEO and the event is "WORKFLOW_COMPLETED", use `report_to_sir` to report to the Sir.
5. For jammer events NEVER generate VIP invites. For VIP events NEVER record jammer orders.
"""
            result = await agent.chat(msg, user_id=999999)
            # Treat hard system/API failures as retryable
            if isinstance(result, str) and result.startswith("API အခက်အခဲ"):
                mark_event_failed(event_id, result, retry=True)
                return
            if isinstance(result, str) and result.startswith("System Error:"):
                mark_event_failed(event_id, result, retry=True)
                return

            mark_event_completed(event_id)
            logger.info(f"✅ Event {event_id} completed")

        except Exception as e:
            logger.error(f"Event {event_id} failed: {e}")
            mark_event_failed(event_id, str(e), retry=True)


async def start_orchestrator():
    """
    Claim-based event dispatcher with bounded concurrency.
    Events are only COMPLETED after the agent finishes successfully.
    """
    logger.info("🎼 Orchestrator (Claim Dispatcher) Started in Background...")

    while True:
        try:
            claimed = claim_next_event()
            if not claimed:
                await asyncio.sleep(2)
                continue

            event_id, event_type, target_agent, payload_str = claimed

            if not target_agent:
                mark_event_poison(event_id, "Missing target_agent")
                continue

            # Fire supervised task — completion/failure handled inside
            asyncio.create_task(
                _run_claimed_event(event_id, event_type, target_agent, payload_str),
                name=f"event-{event_id}",
            )
            # Small yield so we can claim more up to semaphore capacity
            await asyncio.sleep(0.05)

        except Exception as e:
            logger.error(f"Orchestrator Loop Error: {e}")
            await asyncio.sleep(2)
