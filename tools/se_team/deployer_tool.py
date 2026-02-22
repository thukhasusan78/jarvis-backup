import logging
import os
from typing import Dict, List
from google.genai import types
from tools.base import BaseTool

logger = logging.getLogger("JARVIS_DEPLOYER_TOOL")

class DeployerTool(BaseTool):
    """
    Tool for deploying a project to the VPS so it runs 24/7.
    """
    name = "manage_deployment"
    description = "Deploy a completed project (Frontend or Backend) to the VPS so it runs 24/7 in the background."
    owner_role = "ceo"

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "project_name": types.Schema(
                type=types.Type.STRING, 
                description="The name of the project to deploy (e.g., 'SaaS_Dashboard')."
            ),
            "target": types.Schema(
                type=types.Type.STRING,
                enum=["frontend", "backend", "fullstack"],
                description="What part of the project to deploy."
            )
        }

    def get_required(self) -> List[str]:
        return ["project_name", "target"]

    async def execute(self, **kwargs) -> str:
        from core.agent import JarvisAgent
        project_name = kwargs.get("project_name")
        target = kwargs.get("target")

        logger.info(f"🚀 Initiating Deployment for {project_name} ({target})...")

        deployer_agent = JarvisAgent(role="deployer")
        prompt_path = os.path.join(os.getcwd(), 'core', 'prompts', 'deployer.md')
        
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                deployer_agent.brain.system_instruction = f.read()

        deploy_msg = f"PROJECT: {project_name}\nTARGET: {target}\nMission: Deploy this project so it runs 24/7 in the background. Output the local Port number and Cloudflare Tunnel instructions."
        
        result = await deployer_agent.chat(deploy_msg, user_id=999999)
        
        return f"✅ **DEPLOYMENT COMPLETE**\n\n{result}"