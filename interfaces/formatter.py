def format_response(text: str) -> str:
    """
    Jarvis က ပြန်လိုက်တဲ့ စာတွေကို Telegram နဲ့ ကိုက်ညီအောင် ပြင်ဆင်ခြင်း။
    အထူးသဖြင့် Markdown တွေ ပျက်မသွားအောင် ထိန်းညှိပေးခြင်း။
    """
    if not text:
        return "..."
    
    # Telegram ရဲ့ Message Length Limit (4096 chars) ကို စစ်မယ်
    if len(text) > 4000:
        return text[:4000] + "\n...(Message Truncated due to length)"
    
    return text

def format_code(code: str, language: str = "python") -> str:
    """Code တွေကို Telegram Code Block ထဲ ထည့်ပေးခြင်း"""
    return f"```{language}\n{code}\n```"