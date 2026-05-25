import json
import websockets

class CommandExecutor:
    def __init__(self, ws_url="ws://localhost:8765"):
        self.ws_url = ws_url
    
    async def execute_command(self, command):
        try:
            async with websockets.connect(self.ws_url) as websocket:
                await websocket.send("TEXT:" + command)
                response = await websocket.recv()
                return json.loads(response[5:])  # 去掉"TEXT:"前缀
        except Exception as e:
            print(f"Command execution error: {str(e)}")
            return None