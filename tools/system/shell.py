import subprocess
import logging

logger = logging.getLogger("JARVIS_SHELL")

# ⛔ ဒီဖိုင်နဲ့ ဖိုဒါတွေကိုပဲ သီးသန့် ကာကွယ်မယ် (Blacklist)
PROTECTED_ITEMS = [
    "core",               # Brain part
    "tools",              # Hands part
    "memory",             # Memory part
    "interfaces",         # UI  
    "main.py",            # Engine
    "config.py",          # Secrets
    "tasks",              # Hands
    "venv",
    ".env",               # API Keys
    ".git",               # Git History
    "/etc",               # System Configs
    "/boot",              # Boot Files
    "/bin",               # System Binaries
]

def execute_command(command: str) -> str:
    """
    Executes Linux shell commands but blocks deletion of SPECIFIC core files.
    """
    try:
        # --- 🛡️ SMART SAFETY CHECK ---
        # 1. ဖျက်မယ့် Command ဟုတ်မဟုတ် စစ်မယ်
        dangerous_keywords = ["rm ", "mv ", ">", "truncate"]
        is_destructive = any(keyword in command for keyword in dangerous_keywords)
        
        # 2. ဖျက်မယ့် Target က Protected List ထဲ ပါနေလား စစ်မယ်
        # (ဥပမာ: 'rm core/brain.py' ဆိုရင် 'core' ပါနေလို့ Block မယ်)
        targets_protected = False
        if is_destructive:
            for protected in PROTECTED_ITEMS:
                if protected in command:
                    targets_protected = True
                    break

        # 3. ဆုံးဖြတ်မယ်
        if is_destructive and targets_protected:
            logger.warning(f"⛔ Blocked dangerous command: {command}")
            return f"⛔ SAFETY ALERT: Access Denied! You are trying to delete/move a CORE file ('{protected}'). Only non-essential files (like logs, tests) can be deleted."
        # ------------------------------------

        logger.info(f"💻 Executing Shell: {command}")
        
        # Timeout 5 မိနစ်
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=300 
        )
        
        output = f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"\nSTDERR (Warnings/Errors):\n{result.stderr}"
            
        if len(output) > 4000:
            return output[-4000:] + "\n...(Old logs truncated)"
        
        return output.strip() or "Command executed successfully."

    except subprocess.TimeoutExpired:
        return "Error: Command timed out."
    except Exception as e:
        return f"System Execution Error: {str(e)}"