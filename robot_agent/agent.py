import copy
from typing import Iterator, List, Optional

from qwen_agent import Agent
from qwen_agent.agents import Assistant
from qwen_agent.llm.schema import Message


class BotAgent(Agent):
    def __init__(
        self,
        system_message: Optional[str] = None,
        vl_system_message: Optional[str] = None,
    ):
        llm = {"model": "qwen-max"}
        ##llm = {"model":"qwen1half-4b-chat","model_server":"http://192.168.202.53:7878/v1"}
        super().__init__(llm=llm)

        self.main_agent = Assistant(
            llm=self.llm,
            name="巡检机器人助手",
            description="基于大模型，具有路线规划能力，具有根据具体场景具体分析的任务分解能力。回答格式是机器人指令的JSON。",
            system_message=system_message,
        )
        self.image_agent = Assistant(
            llm={"model": "qwen-vl-max"},
            name="巡检视觉",
            description="基于视觉模型，具有图像理解能力。",
            system_message=vl_system_message,
        )

    def _run(
        self, messages: List[Message], lang: str = "zh", **kwargs
    ) -> Iterator[List[Message]]:
        """Define the workflow"""

        # Image understanding
        new_messages = copy.deepcopy(messages)
        last_message = new_messages[-1]
        print("last message", last_message)
        response = []

        if (
            last_message["role"] == "user"
            and isinstance(last_message["content"], list)
            and any([item.image for item in last_message["content"]])
        ):
            # 遇到图片类型，交给视觉大模型处理，插入视觉大模型的处理结果
            print("image detected")
            # new_messages[-1]["content"].append(
            #     ContentItem(text=VL_PROMPT)
            # )  # TODO 要改text

            for rsp in self.image_agent.run(messages=[last_message]):  # 单轮对话
                yield response + rsp
            print("rsp", rsp)
            response.extend(rsp)
            new_messages.extend(rsp)
            new_messages.append(Message("user", "这个场景，要干啥"))
            print(new_messages)

        for rsp in self.main_agent.run(new_messages, lang=lang, **kwargs):
            yield response + rsp
