import asyncio
import logging
import json
import os
from core.message_broker import get_pending_events, mark_event_completed
from core.agent import JarvisAgent

logger = logging.getLogger("JARVIS_ORCHESTRATOR")

async def start_orchestrator():
    """
    The True OpenClaw Supervisor: 
    Message Broker ကို ၂ စက္ကန့် တစ်ခါ စောင့်ကြည့်ပြီး Agent များကို နောက်ကွယ်မှ နှိုးပေးမည်။
    """
    logger.info("🎼 Orchestrator (Event Dispatcher) Started in Background...")
    
    while True:
        try:
            # 1. Broker ထဲက မလုပ်ရသေးတဲ့ အလုပ်တွေကို ဆွဲထုတ်မယ်
            pending_events = get_pending_events()
            
            for row in pending_events:
                event_id, event_type, target_agent, payload_str = row
                
                # 🛑 THE FIX: NoneType Error Loop ကို ဖြတ်တောက်ရှင်းလင်းခြင်း
                if not target_agent:
                    logger.warning(f"⚠️ Event {event_id} has no target_agent (NoneType). Clearing it to prevent infinite loops.")
                    mark_event_completed(event_id)
                    continue

                payload = json.loads(payload_str)
                logger.info(f"📬 Orchestrator picked up event: [{event_type}] for Agent '{target_agent.upper()}'")
                
                # 2. အလုပ်ကို ယူပြီးကြောင်း 'COMPLETED' လို့ ချက်ချင်း မှတ်လိုက်မယ်
                mark_event_completed(event_id)
                
                # 3. သက်ဆိုင်ရာ Agent ကို အသက်သွင်းမယ်
                agent = JarvisAgent(role=target_agent)
                prompt_path = os.path.join(os.getcwd(), 'core', 'prompts', f'{target_agent}.md')
                if os.path.exists(prompt_path):
                    with open(prompt_path, 'r', encoding='utf-8') as f:
                        agent.brain.system_instruction = f.read()

                # 👁️ THE AWARENESS FIX: Worker တွေကို The Square (Master Plan) ဖတ်ခွင့်ပေးလိုက်ခြင်း
                square_path = os.path.join("workspace", "square.md")
                square_context = ""
                if os.path.exists(square_path):
                    with open(square_path, "r", encoding="utf-8") as f:
                        square_context = f.read()[-8000:]

                # 4. Agent ကို ခိုင်းမယ့် Message ပုံစံထုတ်မယ်
                msg = f"""
🔔 [SYSTEM EVENT TRIGGERED: {event_type}]
You have received a new background event from the Message Broker.

[🌐 THE INTERNAL SQUARE FEED (Team Activity & Awareness)]:
{square_context if square_context else "No recent activity."}

[PAYLOAD DATA & END-GOAL]:
{json.dumps(payload, indent=2, ensure_ascii=False)}

[CRITICAL INSTRUCTIONS]:
1. Read the payload data and the Square Feed to understand the overarching END-GOAL.
2. Execute your designated task.
3. If the overarching workflow is NOT done, use `publish_event` to pass the baton to the logical next agent.
4. If you are the CEO and the event is "WORKFLOW_COMPLETED", use `report_to_sir` to report to the Sir.
"""
                # 5. 🚀 Fire and Forget
                asyncio.create_task(agent.chat(msg, user_id=999999))
                
        except Exception as e:
            logger.error(f"Orchestrator Loop Error: {e}")
            
        # အမြဲတမ်း ပတ်မနေအောင် ၂ စက္ကန့် နားမယ် (CPU မစားအောင်)
        await asyncio.sleep(2)