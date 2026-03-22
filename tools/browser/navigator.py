import logging
from typing import Dict, List
from google.genai import types

from tools.base import BaseTool
from tools.browser.session import BrowserManager

logger = logging.getLogger("JARVIS_NAVIGATOR")

class NavigatorTool(BaseTool):
    """
    Advanced Browser Navigation Tool.
    Allows Jarvis to interact with websites dynamically (Click, Type, Read).
    """
    name = "browser_navigate"
    description = "Navigate and interact with websites dynamically. Use this to login to social media, click buttons, type messages, or read specific elements."

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "action": types.Schema(
                type=types.Type.STRING,
                enum=["goto", "click", "type", "read", "press"],
                description="Action: 'goto' (open url), 'click' (click element), 'type' (type text), 'read' (extract text), 'press' (press keyboard key)."
            ),
            "url": types.Schema(
                type=types.Type.STRING,
                description="The URL to visit (Required for 'goto')."
            ),
            "selector": types.Schema(
                type=types.Type.STRING,
                description="CSS or XPath selector of the element (Required for 'click', 'type', 'read')."
            ),
            "text": types.Schema(
                type=types.Type.STRING,
                description="Text to type (Required for 'type') or key to press (Required for 'press', e.g., 'Enter')."
            )
        }

    def get_required(self) -> List[str]:
        return ["action"]

    async def execute(self, **kwargs) -> str:
        action = kwargs.get("action")
        
        try:
            # Persistent Context ကို လှမ်းယူမည်
            context = await BrowserManager.get_browser_context()
            
            # လက်ရှိ ဖွင့်ထားသော Page ကို ယူမည်၊ မရှိပါက အသစ်ဖွင့်မည်
            pages = context.pages
            page = pages[0] if pages else await context.new_page()

            if action == "goto":
                url = kwargs.get("url")
                if not url: return "Error: 'url' is required for goto."
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                return f"Successfully navigated to {url}"

            elif action == "click":
                selector = kwargs.get("selector")
                if not selector: return "Error: 'selector' is required for click."
                await page.click(selector, timeout=10000)
                return f"Successfully clicked element: {selector}"

            elif action == "type":
                selector = kwargs.get("selector")
                text = kwargs.get("text")
                if not selector or not text: return "Error: 'selector' and 'text' are required for type."
                await page.fill(selector, text, timeout=10000)
                return f"Successfully typed text into: {selector}"

            elif action == "read":
                selector = kwargs.get("selector")
                if not selector: return "Error: 'selector' is required for read."
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                    return f"Content extracted:\n{content}"
                return f"Error: Element {selector} not found on the page."

            elif action == "press":
                key = kwargs.get("text")
                if not key: return "Error: 'text' (key name) is required for press."
                await page.keyboard.press(key)
                return f"Successfully pressed key: {key}"

            else:
                return f"Error: Unknown action '{action}'."

        except Exception as e:
            logger.error(f"Navigator Error: {e}")
            return f"Browser Execution Error: {str(e)}"