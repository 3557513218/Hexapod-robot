# 六足机器人 AI 巡检系统

基于大语言模型（LLM）和视觉语言模型（VLM）驱动的六足机器人自主巡检系统，支持路线规划、异常场景识别、语音播报和巡检报告生成。

---

## 📖 项目介绍

本项目是一个 **AI Agent + 六足机器人** 的完整巡检解决方案。系统核心是一个双模型 AI Agent：

- **通用大模型（qwen-max）**：负责文本理解、路线规划、任务分解和报告生成
- **视觉大模型（qwen-vl-max）**：负责图像识别，检测巡检过程中的异常场景（火灾、未戴安全帽、货车等）

### 核心功能

| 功能 | 说明 |
|------|------|
| **自主路线规划** | 根据起点和方向自动分解行走路线为机器人指令 |
| **多场景识别** | 视觉模型识别火灾、安全帽佩戴、货车等场景 |
| **智能响应** | 根据场景自动执行报警、语音播报等操作 |
| **任务优先级** | 异常事件优先处理，打断当前导航任务 |
| **巡检报告** | 巡检完成后自动汇总异常场景并生成语音汇报 |
| **多种交互方式** | WebSocket 直连、WebUI 界面、REST API |

### 应用场景

- 工厂/工地安全巡检
- 危险环境巡逻（火灾、泄漏检测）
- 安全规范监控（安全帽佩戴检测）
- 仓储物流区域巡查

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────┐
│                   AI Agent 服务端                      │
│  ┌──────────────────────────────────────────────┐   │
│  │              BotAgent (agent.py)               │   │
│  │  ┌─────────────┐       ┌──────────────────┐  │   │
│  │  │  主助手      │       │   视觉助手        │  │   │
│  │  │ qwen-max    │ ◄──►  │ qwen-vl-max     │  │   │
│  │  │ 文本推理     │       │ 图像理解         │  │   │
│  │  └─────────────┘       └──────────────────┘  │   │
│  └──────────────────────────────────────────────┘   │
│                                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ WebSocket │  │  WebUI   │  │  REST API        │ │
│  │ run_wss.py│  │run_webui │  │  api.py (Flask) │ │
│  │ :8765     │  │ :7860    │  │ :6562            │ │
│  └─────┬─────┘  └──────────┘  └──────────────────┘ │
└────────┼────────────────────────────────────────────┘
         │ WebSocket (TEXT:指令 / IMAGE:照片)
         ▼
┌─────────────────────────────────────────────────────┐
│               六足机器人 (vkhexOld.py)              │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ ROS      │  │ move_base│  │ 语音合成/报警    │ │
│  │ 导航控制  │  │ 路径规划  │  │                  │ │
│  └──────────┘  └──────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### 工作流程

1. **任务下达**：用户输入巡检任务（如"从右下角逆时针走一圈，遇到火灾报警"）
2. **路线规划**：AI Agent 分解路线为 JSON 导航指令列表
3. **逐点巡航**：机器人依次执行导航指令
4. **实时拍照**：到达每个点位后自动拍摄现场照片
5. **场景识别**：视觉大模型分析图片，识别异常场景
6. **智能响应**：根据场景类型执行报警、播报等操作
7. **汇报总结**：巡检完成后汇总所有异常场景并汇报

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- DASHSCOPE_API_KEY（通义千问 API Key）

### 安装

```bash
# 克隆仓库
git clone https://github.com/HongMengSeng/repo-agent.git
cd repo-agent

# 创建虚拟环境（推荐）
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 配置 API Key

```bash
# Linux/Mac
export DASHSCOPE_API_KEY=sk-您的有效API_KEY

# Windows (CMD)
set DASHSCOPE_API_KEY=sk-您的有效API_KEY

# Windows (PowerShell)
$env:DASHSCOPE_API_KEY="sk-您的有效API_KEY"
```

### 启动 WebUI（推荐）

```bash
python -m robot_agent.run_webui
```

默认访问地址：`http://192.168.103.67:7860`

### 启动 WebSocket 服务

```bash
python -m robot_agent.run_wss
```

WebSocket 服务默认运行在 `ws://0.0.0.0:8765`，等待机器人连接。

### 启动 REST API

```bash
python -m robot_agent.api
```

API 服务默认运行在 `http://192.168.103.67:6562`。

---

## 🤖 Agent 提示词使用

系统由两套提示词分别驱动两个大模型：

### 主提示词（主助手）

用于 **qwen-max** 模型，负责路线规划、场景响应和报告生成。

**文件位置**：`resource/1011.md`

**核心规则**：

```
你是一个巡检机器人，具有路线规划能力，
可以将路线分解为多条机器人行走指令，
只用回复JSON指令，不用回复其他文字。
具有记忆多个场景并提出解决方案的能力。
```

**回答格式**：JSON 数组

```json
[
  {"desc": "右上角", "task": "nav"},
  {"desc": "左上角", "task": "nav"},
  {"desc": "左下角", "task": "nav"},
  {"desc": "右下角", "task": "nav"}
]
```

### 视觉提示词（视觉助手）

用于 **qwen-vl-max** 模型，负责图像场景识别。

**文件位置**：`resource/1.md`

```markdown
你是一个巡检机器人视觉助手,针对提问,你需要对图片
的内容进行分析是哪一种场景：
- 火灾

若是符合场景,则将此场景作为答案,若是没有则输出一切正常
```

### 指令协议

| 指令类型 | task 字段 | 说明 |
|---------|-----------|------|
| 导航 | `nav` | 移动到指定坐标点 |
| 语音播报 | `speak` | 通过喇叭播报文本内容 |
| 报警 | `alarm` | 触发机器人跳舞报警动作 |

**导航指令示例**：
```json
{"desc": "走到右上角", "task": "nav", "position": {"x": 1.136546, "y": -1.62110, "z": 0.0}, "orientation": {"x": 0.0, "y": 0.0, "z": 0.71291, "w": 0.701248}}
```

**语音播报指令示例**：
```json
{"desc": "火灾", "task": "speak", "text": "发现火灾场景，立刻报警并立刻撤离"}
```

**报警指令示例**：
```json
{"desc": "报警", "task": "alarm"}
```

### 场景-解决方案映射

| 场景 | 响应指令 |
|------|---------|
| 火灾 | 语音播报火灾报警 |
| 工人未戴安全帽 | 语音提醒注意安全合规 |
| 货车 | 语音播报避让提示 |
| 工人佩戴安全帽 | 语音确认合规 |

### 巡检汇报示例

```json
{"desc": "汇报", "task": "speak", "text": "今日巡检任务完成，发现火灾已报警，遇到货车已避让，巡检发现工人已佩戴头盔"}
```

### 提示词迭代历史

项目提供了多个版本的提示词（`resource/` 目录下）：
- `1011.md` — 主提示词成熟版本
- `1005.md` / `1007.md` / `1008.md` / `10081.md` — 迭代版本
- `system_prompt.md` — 备选主提示词
- `system_prompt_vl.md` — 备选视觉提示词
- `demo.md` — 含实际坐标的演示版本

---

## 📖 项目使用教程

### 场景一：仅使用 AI Agent 测试（无机器人）

最简单的方式，使用 WebUI 界面与 AI Agent 交互，验证提示词和指令生成效果。

```bash
export DASHSCOPE_API_KEY=sk-您的有效API_KEY
python -m robot_agent.run_webui
```

打开浏览器访问 `http://192.168.103.67:7860`，在对话框中输入：

> "巡检任务是走一圈，机器人起始位置是右下角。如果遇到火灾场景，报警。这个巡检任务，机器人指令是什么？"

Agent 会返回 JSON 导航指令列表。

### 场景二：通过 REST API 调用

适合集成到其他系统中。

```bash
curl -X POST http://192.168.103.67:6562/ModelHelper \
  -H "Content-Type: application/json" \
  -d '{"prompt": "巡检任务是逆时针走一圈，机器人起始位置是右下角。如果遇到火灾场景，报警。"}'
```

### 场景三：完整机器人巡检

需要准备一台运行 ROS 的六足机器人。

**步骤 1**：启动 AI Agent 服务端
```bash
python -m robot_agent.run_wss
```

**步骤 2**：启动机器人端程序
```bash
cd ~
python3 vkhexOld.py --host 192.168.1.160 --port 8765 --query "巡检任务是逆时针走一圈，机器人起始位置是右下角。如果遇到火灾场景，报警。"
```

机器人会自动：接收任务 → 规划路线 → 逐点巡航 → 拍照识别 → 场景响应 → 巡检汇报。

### 场景四：训练数据制作（微调用）

参考 `resource/` 目录下的 JSONL 训练数据格式：

- `单论对话模板.jsonl` — 76 条单轮对话数据（路线规划 + 场景问答）
- `单轮对话训练1.jsonl` — 16 条逐步导航训练数据

数据格式为 JSONL 每行一条：
```jsonl
{"messages": [{"role": "user", "content": "巡检任务是走一圈，机器人起始位置是右下角。"}, {"role": "assistant", "content": "[{\"desc\": \"右上角\", \"task\": \"nav\"}, {\"desc\": \"左上角\", \"task\": \"nav\"}, {\"desc\": \"左下角\", \"task\": \"nav\"}, {\"desc\": \"右下角\", \"task\": \"nav\"}]"}]}
```

---

## 📁 项目结构

```
gzc-agent/
├── README.md                    # 项目文档
├── requirements.txt             # Python 依赖
├── demo.json                    # 演示导航坐标点
├── vkhexOld.py                  # 六足机器人 ROS 驱动
│
├── robot_agent/                 # AI Agent 核心模块
│   ├── agent.py                 # BotAgent 双模型 Agent
│   ├── api.py                   # Flask REST API
│   ├── config.py                # 配置文件路径
│   ├── command_executor.py      # WebSocket 指令发送客户端
│   ├── run_webui.py             # Gradio WebUI 启动脚本
│   └── run_wss.py               # WebSocket 服务端
│
├── resource/                    # 提示词、训练数据、文档
│   ├── 1.md                     # 视觉助手提示词
│   ├── 1011.md                  # 主助手提示词（正式版）
│   ├── 1005.md / 1007.md / 1008.md / 10081.md  # 迭代版本
│   ├── system_prompt.md         # 备选主提示词
│   ├── system_prompt_vl.md      # 备选视觉提示词
│   ├── demo.md                  # 含坐标的演示提示词
│   ├── 任务书.md                # 项目需求文档
│   ├── 单论对话模板.jsonl       # 训练数据集（76条）
│   └── 单轮对话训练1.jsonl      # 训练数据集（16条）
│
├── uploads/images/              # 巡检拍摄图片存储
└── workspace/                   # qwen-agent 自动创建工作区
```

---

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| AI Agent 框架 | qwen-agent（通义千问 Agent 框架） |
| 通用大模型 | qwen-max |
| 视觉大模型 | qwen-vl-max |
| Web 服务 | Flask / Gradio |
| WebSocket | websockets（Python） |
| 机器人框架 | ROS（Robot Operating System） |
| 导航 | move_base（ROS） |

---

## 📚 参考资料

- [关于 ToB 垂直领域大模型的一点探索和尝试](https://mp.weixin.qq.com/s/9eBFvu8POn9uNhv9CFAaQA)
- [通义千问 Agent 框架](https://github.com/QwenLM/qwen-agent)
