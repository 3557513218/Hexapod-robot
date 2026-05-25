import argparse
import asyncio
import json
import os
from datetime import datetime

import websockets

from .agent import BotAgent
from .config import IMAGE_DIR, SYSTEM_PROMPT_PATH, SYSTEM_PROMPT_VL_PATH


def init_agent_service():
    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f1:
        with open(SYSTEM_PROMPT_VL_PATH, "r", encoding="utf-8") as f2:
            system_prompt = f1.read()
            system_prompt_vl = f2.read()
            bot = BotAgent(
                system_message=system_prompt, vl_system_message=system_prompt_vl
            )
            return bot


def get_current_time_formatted():
    now = datetime.now()
    # 格式化时间为 "yyMMdd-hh:mm:ss"
    formatted_time = now.strftime("%y%m%d-%H%M%S")
    return formatted_time


async def consumer_handler(websocket):
    # 注意这里的命名约定， websocket 的消息用msg，chatbot 的消息用 message，不要混淆
    messages = []
    bot = init_agent_service()
    async for msg in websocket:
        if isinstance(msg, str) and msg.startswith("TEXT:"):
            text_msg = msg[5:]
            print(f"Received text message: {text_msg}")
            # logger.info(f"Received text message: {text_msg}")
            messages.append({"role": "user", "content": text_msg, "name": "user"})
        elif isinstance(msg, bytes) and msg.startswith(b"IMAGE:"):
            image_data = msg[6:]
            image_path = os.path.join(IMAGE_DIR, f"{get_current_time_formatted()}.jpg")
            with open(image_path, "wb") as image_file:
                image_file.write(image_data)
            print("Received image message")
            messages.append(
                {
                    "role": "user",
                    "content": [{"image": "file://" + image_path}],
                    "name": "user",
                }
            )
        else:
            raise ValueError(f"Unknown message type: {msg}")

        *_, last_responses = bot.run(messages)
        print(f"Bot responses: {last_responses}")
        messages.extend(last_responses)
        last_msg = last_responses[-1]
        stripped = last_msg["content"].replace("```json", "").replace("```", "")
        print(f"Stripped: {stripped}")
        try:
            tasks = json.loads(stripped)
            await websocket.send("TEXT:" + json.dumps(tasks))  # 发送回复
            print(f"Sent tasks: {tasks}")
        except json.JSONDecodeError as e:
            print(f"Error decoding json: {e}")
            await websocket.send("TEXT:" + json.dumps([]))  # 发送回复
            print("Sent empty task list")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    os.makedirs(IMAGE_DIR, exist_ok=True)

    async with websockets.serve(consumer_handler, args.host, args.port):
        await asyncio.Future()  # 运行直到被取消


if __name__ == "__main__":
    asyncio.run(main())
