import argparse
import asyncio
import json
import os
from datetime import datetime

import actionlib
import rospy
import websockets
from actionlib_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseWithCovarianceStamped
from hexbot_cmd_server.srv import cmd
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
# from xf_mic_tts_offline.srv import Play_TTS_srv, Play_TTS_srvRequest


# 拍照队列, 拍照任务的生成逻辑，这个目前逻辑是 robot 内部去触发，不是外部传入的任务. 什么时候触发拍照。这个策略有待优化
take_photo_queue = asyncio.Queue(1)
task_queue = asyncio.PriorityQueue()  # 任务队列

IMAGES_DIR = "/home/vkrobot/hexbot_ws/src/hexbot/hexbot_cmd_server/photos/"
NAV_BASE_PRIORITY = 1000  # 导航任务的起始优先级，数字越小，优先级越高


class TourGuide:
    def __init__(self):
        rospy.init_node("tour_guide_robot")
        rospy.on_shutdown(self.shutdown)
        self.move_base = actionlib.SimpleActionClient("move_base", MoveBaseAction)
        self.move_base.wait_for_server(rospy.Duration(60))
        rospy.loginfo("Connected to move_base server")
        rospy.loginfo("Start Successfully!!!")
        initial_pose = PoseWithCovarianceStamped()
        rospy.loginfo("Click on the map in RViz to set the initial pose ...")
        rospy.wait_for_message("initialpose", PoseWithCovarianceStamped)
        rospy.Subscriber(
            "initialpose", PoseWithCovarianceStamped, self.update_initial_pose
        )

        if not rospy.get_node_uri():
            rospy.init_node("hexbot_cmd_client", anonymous=True, log_level=rospy.INFO)
            rospy.wait_for_service("hexbot_cmd_server")
        # rospy.wait_for_service('/xf_mic_tts_offline_node/play_txt_wav')
        while initial_pose.header.stamp == "":
            rospy.loginfo("Waiting for initial pose")
            rospy.sleep(5)
        rospy.loginfo("Starting navigation!!!")
        rospy.sleep(2)

    #######--------获取摄像头一帧图像接口---------#######
    def _send_hexbot_cmd_1(self, image_file):
        hexbot_cmd = rospy.ServiceProxy("hexbot_cmd_server", cmd)  # 调用 service
        resp = hexbot_cmd("take_photos", image_file)
        if resp.result:
            rospy.loginfo("succeed to send cmd to hexbot")
            rospy.loginfo("err_msg: " + resp.err_msg)
            return os.path.join(IMAGES_DIR, f"{image_file}.jpg")
        else:
            rospy.loginfo("fail to send cmd to hexbot: %s", resp.err_msg)
            raise rospy.ServiceException("call hexbot_cmd_server error")
        
    async def send_hexbot_cmd_1(self, image_file):
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._send_hexbot_cmd_1, image_file)
        return result

    def _execute(self, task: dict):
        if task["task"] == "nav":
            self.navigate_to(task)
        elif task["task"] == "alarm":
            self.alarm()
        elif task["task"] == "speak":
            self.speak(task)
        else:
            raise ValueError(f"Unknown task: {task}")
        
    async def execute(self, task: dict): 
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._execute, task)
        return result


    def navigate_to(self, task: dict):
        self.move_base.cancel_goal()
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.pose.position.x = task["position"]["x"]
        goal.target_pose.pose.position.y = task["position"]["y"]
        goal.target_pose.pose.position.z = task["position"]["z"]
        goal.target_pose.pose.orientation.x = task["orientation"]["x"]
        goal.target_pose.pose.orientation.y = task["orientation"]["y"]
        goal.target_pose.pose.orientation.z = task["orientation"]["z"]
        goal.target_pose.pose.orientation.w = task["orientation"]["w"]
        self.move_base.send_goal(goal)
        finished_within_time = self.move_base.wait_for_result(rospy.Duration(60))
        if not finished_within_time:
            self.move_base.cancel_goal()
            rospy.loginfo("Timed out achieving goal")
        else:
            state = self.move_base.get_state()
            if state == GoalStatus.SUCCEEDED:
                rospy.loginfo("Get to goal succeeded!!!")

    def alarm(self):
        hexbot_cmd = rospy.ServiceProxy("hexbot_cmd_server", cmd)  # 调用 service
        resp = hexbot_cmd("dance")
        if resp.result:
            rospy.loginfo("succeed to send cmd to hexbot")
            rospy.loginfo("err_msg: " + resp.err_msg)
        else:
            rospy.loginfo("fail to send cmd to hexbot: %s", resp.err_msg)

    def speak(self, task: dict):
        text = task['text']
        print('todo')
        # 调用语音合成客户端，进行语音合成操作
        # voice_client = rospy.ServiceProxy('/xf_mic_tts_offline_node/play_txt_wav', Play_TTS_srv)

        # # 请求语音合成服务调用，输入具体的语音内容
        # response = voice_client(0, text, "xiaoyan")
        # rospy.loginfo("vkbot speak ok!!")
        # print(response.result)


    def cancel_goal(self):
        # TODO, 这会不会让正在运行的navigation 提前结束。预期是可以
        self.move_base.cancel_goal()

    def update_initial_pose(self, initial_pose):
        self.initial_pose = initial_pose

    def shutdown(self):
        rospy.loginfo("Stopping the robot ...")
        self.move_base.cancel_goal()
        rospy.sleep(2)


async def send_msg(websocket, msg: dict):
    if "text" in msg:
        await websocket.send(f"TEXT:{msg['text']}")
    elif "file_path" in msg:
        with open(msg["file_path"], "rb") as image_file:
            image_data = image_file.read()
            await websocket.send(b"IMAGE:" + image_data)
    else:
        raise ValueError(f"Unknown message type: {msg}")


async def handler(websocket, robot: TourGuide):
    await asyncio.gather(
        receive_msg(websocket, robot),
        handle_image(websocket, robot),  # 独立一个线程
        handle_task(robot),
    )


async def receive_msg(websocket, robot: TourGuide):
    # 接受 websocket 传来的消息
    async for msg in websocket:
        push_msg(msg, robot)


def push_msg(msg, robot: TourGuide):
    if isinstance(msg, str) and msg.startswith("TEXT:"):
        text_msg = msg[5:]
        print(f"Received text message: {text_msg}")
        # 如果是json格式的消息，可以使用json.loads(msg)来解析

        tasks = json.loads(text_msg)
        print(f"Received tasks: {tasks}")

        if len(tasks) == 0:
            print("No task")
            # 没有紧急任务，触发拍照
            if take_photo_queue.empty():
                take_photo_queue.put_nowait(True)
                print("Put take photo task")
        else:
            print(f"Has tasks {len(tasks)}")
            i = 0
            has_urgent_task = False
            for t in tasks:
                if t["task"] == "nav":
                    # 将任务放入任务队列
                    print(f"Put nav task: {t}")
                    task_queue.put_nowait((NAV_BASE_PRIORITY + i, t))
                else:
                    has_urgent_task = True
                    print(f"Put urgent task: {t}")
                    task_queue.put_nowait((1 + i, t))
                i += 1

            # 如果是 紧急指令，先停止当前任务，执行紧急指令
            if has_urgent_task:
                print("Has urgent task. cancel goal")
                # robot.cancel_goal()  # TODO 提前中断当前任务
            else:
                print("No urgent task")
                # 没有紧急任务，触发拍照
                if take_photo_queue.empty():
                    take_photo_queue.put_nowait(True)
                    print("Put take photo task")


# 格式化时间为 "yyMMdd-hh:mm:ss"
def get_current_time_formatted():
    return datetime.now().strftime("%y%m%d-%H%M%S")


async def handle_image(websocket, robot):
    while not rospy.is_shutdown() :
        await take_photo_queue.get()
        image_path = await robot.send_hexbot_cmd_1("image" + get_current_time_formatted())
        await send_msg(websocket, {"file_path": image_path})


async def handle_task(robot: TourGuide):
    while not task_queue.empty():
        priority, task = await task_queue.get()
        print(f"start task: {task}")
        await robot.execute(task)
        if priority < NAV_BASE_PRIORITY:    # 执行完紧急任务后，触发拍照
            if take_photo_queue.empty():
                take_photo_queue.put_nowait(True)
                print("Put take photo task")
        print(f"end task: {task}")
    print("No more tasks")
    # task_queue.task_done()


async def main(robot: TourGuide, ws_uri: str, main_query: str):
    async with websockets.connect(ws_uri) as websocket:
        await send_msg(websocket, {"text": main_query})
        main_msg = await websocket.recv()
        push_msg(main_msg, robot)
        print("Start handling")
        await handler(websocket, robot)


if __name__ == "__main__":
    # 考虑从参数读取
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="192.168.1.160")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--query", type=str, required=True)
    args = parser.parse_args()
    ws_uri = f"ws://{args.host}:{args.port}"
    # main_query = "巡检任务是逆时针走一圈，机器人起始位置是右下角。如果遇到火灾场景，报警。这个巡检任务，机器人指令是什么？"
    main_query = args.query
    robot = TourGuide()
    loop = asyncio.get_event_loop()

    loop.run_until_complete(main(robot, ws_uri, main_query))  # 3.6以前语法
    loop.close()
