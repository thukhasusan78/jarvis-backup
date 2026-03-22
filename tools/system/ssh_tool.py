import paramiko
import logging
from typing import Dict, List
from google.genai import types
from tools.base import BaseTool

logger = logging.getLogger("JARVIS_SSH_TOOL")

class SSHRemoteTool(BaseTool):
    """
    Execute shell commands on a REMOTE server via SSH.
    """
    name = "ssh_remote_exec"
    description = "Execute Linux commands on a REMOTE server via SSH. Use this to setup, manage, or migrate data to another VPS instance."
    owner_role = "sysadmin" # Sysadmin Agent ကပဲ ဒီ Tool ကို ကိုင်တွယ်ပါမည်

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "host": types.Schema(
                type=types.Type.STRING, 
                description="Remote server IP address (e.g., '142.250.192.0')."
            ),
            "username": types.Schema(
                type=types.Type.STRING, 
                description="SSH username (usually 'root')."
            ),
            "password": types.Schema(
                type=types.Type.STRING, 
                description="SSH password for the remote server."
            ),
            "command": types.Schema(
                type=types.Type.STRING, 
                description="The Linux command to execute on the remote server."
            )
        }

    def get_required(self) -> List[str]:
        return ["host", "username", "password", "command"]

    async def execute(self, **kwargs) -> str:
        host = kwargs.get("host")
        username = kwargs.get("username")
        password = kwargs.get("password")
        command = kwargs.get("command")

        logger.info(f"🌐 Connecting to Remote Server: {username}@{host}")
        
        # SSH Client အသစ်ဖန်တီးခြင်း
        client = paramiko.SSHClient()
        # Security Certificate အသစ်များကို အလိုအလျောက် လက်ခံရန်
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            # ဆာဗာအသစ်ဆီသို့ လှမ်း၍ ချိတ်ဆက်ခြင်း
            client.connect(hostname=host, username=username, password=password, timeout=15)
            
            # Command ကို ရိုက်ထည့်ခြင်း
            logger.info(f"💻 Executing remote command: {command}")
            stdin, stdout, stderr = client.exec_command(command)
            
            # ထွက်လာသည့် ရလဒ်များကို ဖတ်ခြင်း
            out = stdout.read().decode('utf-8').strip()
            err = stderr.read().decode('utf-8').strip()
            
            result = ""
            if out: result += f"STDOUT:\n{out}\n"
            if err: result += f"STDERR:\n{err}\n"
            
            if not result:
                return f"✅ [Success] Command '{command}' executed silently on remote server {host}."
            
            return f"📡 Remote Execution Result from {host}:\n{result}"
            
        except Exception as e:
            logger.error(f"SSH Error on {host}: {e}")
            return f"❌ SSH Connection/Execution Error: {str(e)}"
        finally:
            # အလုပ်ပြီးလျှင် လုံခြုံရေးအရ ချိတ်ဆက်မှုကို ပြန်ပိတ်မည်
            client.close()