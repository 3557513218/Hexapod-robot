from flask_cors import CORS
from fastapi.openapi.models import Encoding
from flask import Flask, jsonify, request
from .agent import BotAgent
from .config import (
    SYSTEM_PROMPT_PATH,
    SYSTEM_PROMPT_VL_PATH,
)

app = Flask(__name__)
CORS(app)

def init_agent_service():
    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f1:
        with open(SYSTEM_PROMPT_VL_PATH, "r", encoding="utf-8") as f2:
            system_prompt = f1.read()
            system_prompt_vl = f2.read()
            return BotAgent(
                system_message=system_prompt, 
                vl_system_message=system_prompt_vl
            )

@app.route("/ModelHelper", methods=['POST'])
def ModelHelper():
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({"status": "error", "message": "Missing prompt parameter"}), 400

    bot = init_agent_service()
    messages = [
        {"role": "user", "content": data['prompt']},
    ]
    result = []
    for response in bot._run(messages):
        result.append(response)
    
    # 确保result不为空且正确处理响应
    if not result:
        return jsonify({"status": "error", "message": "No response from agent"}), 500
    
    try:
        response_data = {
            "status": "success",
            "message": "BotAgent initialized",
            "code": result[-1][0]["content"] if result else ""
        }
        response = jsonify(response_data)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(port=6562, debug=True, host="192.168.103.67")