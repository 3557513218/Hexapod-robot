import argparse

from qwen_agent.gui import WebUI

from .agent import BotAgent
from .config import (
    SYSTEM_PROMPT_PATH,
    SYSTEM_PROMPT_VL_PATH,
)


def init_agent_service():
    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f1:
        with open(SYSTEM_PROMPT_VL_PATH, "r", encoding="utf-8") as f2:
            system_prompt = f1.read()
            system_prompt_vl = f2.read()
            bot = BotAgent(
                system_message=system_prompt, vl_system_message=system_prompt_vl
            )
            return bot


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="192.168.103.67")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    agent = init_agent_service()
    chatbot_config = {
        "prompt.suggestions": [
            "巡检任务是走一圈。如果遇到火灾场景，报警。这个巡检任务，机器人指令是什么？",
            "遇到火灾，机器人应该怎么做？",
        ]
    }
    WebUI(agent, chatbot_config=chatbot_config).run(
        server_name=args.host, server_port=args.port
    )
