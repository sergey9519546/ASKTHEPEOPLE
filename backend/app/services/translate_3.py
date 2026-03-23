import os

filepath = r"c:\Users\serge\OneDrive\Documents\GitHub\ASKTHEPEOPLE\backend\app\services\simulation_ipc.py"
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

replacements = {
    "模拟IPC通信模块": "Simulation IPC Communication Module",
    "用于Flask后端和模拟脚本之间的进程间通信": "Used for inter-process communication between Flask backend and simulation scripts",
    "通过文件系统实现简单的命令/响应模式：": "Implements simple command/response pattern via file system:",
    "1. Flask写入命令到 commands/ 目录": "1. Flask writes commands to commands/ directory",
    "2. 模拟脚本轮询命令目录，执行命令并写入响应到 responses/ 目录": "2. Simulation script polls command directory, executes commands, and writes responses to responses/ directory",
    "3. Flask轮询响应目录获取结果": "3. Flask polls response directory for results",
    "命令类型": "Command Type",
    "单个Agent采访": "Single Agent Interview",
    "批量采访": "Batch Interview",
    "关闭环境": "Close Environment",
    "命令状态": "Command Status",
    "IPC命令": "IPC Command",
    "IPC响应": "IPC Response",
    "模拟IPC客户端（Flask端使用）": "Simulation IPC Client (for Flask)",
    "用于向模拟进程发送命令并等待响应": "Used to send commands to simulation processes and wait for responses",
    "初始化IPC客户端": "Initialize IPC client",
    "模拟数据目录": "Simulation data directory",
    "确保目录存在": "Ensure directory exists",
    "发送命令并等待响应": "Send command and wait for response",
    "命令参数": "Command arguments",
    "超时时间（秒）": "Timeout (seconds)",
    "轮询间隔（秒）": "Polling interval (seconds)",
    "等待响应超时": "Timeout waiting for response",
    "写入命令文件": "Write command file",
    "发送IPC命令: ": "Sent IPC command: ",
    "等待响应": "Wait for response",
    "清理命令和响应文件": "Clean up command and response files",
    "收到IPC响应: ": "Received IPC response: ",
    "解析响应失败: ": "Failed to parse response: ",
    "超时": "Timeout",
    "等待IPC响应超时: ": "Timeout waiting for IPC response: ",
    "清理命令文件": "Clean up command file",
    "等待命令响应超时 (": "Timeout waiting for command response (",
    "秒)": "s)",
    "发送单个Agent采访命令": "Send single Agent interview command",
    "采访问题": "Interview prompt",
    "指定平台（可选）": "Target platform (optional)",
    "- \"twitter\": 只采访Twitter平台": "- \"twitter\": Only interview Twitter platform",
    "- \"reddit\": 只采访Reddit平台": "- \"reddit\": Only interview Reddit platform",
    "- None: 双平台模拟时同时采访两个平台，单平台模拟时采访该平台": "- None: Interview both platforms if dual, or specific platform if single",
    "超时时间": "Timeout",
    "result字段包含采访结果": "result field contains interview results",
    "发送批量采访命令": "Send batch interview command",
    "采访列表，每个元素包含": "Interview list, each element contains",
    "(可选)}": "(optional)}",
    "默认平台（可选，会被每个采访项的platform覆盖）": "Default platform (optional, overridden by platform in each interview item)",
    "- \"twitter\": 默认只采访Twitter平台": "- \"twitter\": Default only interview Twitter platform",
    "- \"reddit\": 默认只采访Reddit平台": "- \"reddit\": Default only interview Reddit platform",
    "- None: 双平台模拟时每个Agent同时采访两个平台": "- None: Each Agent interviewed on both platforms if dual simulation",
    "result字段包含所有采访结果": "result field contains all interview results",
    "发送关闭环境命令": "Send close environment command",
    "检查模拟环境是否存活": "Check if simulation environment is alive",
    "通过检查 env_status.json 文件来判断": "Determined by checking env_status.json file",
    "模拟IPC服务器（模拟脚本端使用）": "Simulation IPC Server (for simulation scripts)",
    "轮询命令目录，执行命令并返回响应": "Poll command directory, execute commands and return responses",
    "初始化IPC服务器": "Initialize IPC server",
    "环境状态": "Environment state",
    "标记服务器为运行状态": "Mark server as running state",
    "标记服务器为停止状态": "Mark server as stopped state",
    "更新环境状态文件": "Update environment state file",
    "轮询命令目录，返回第一个待处理的命令": "Poll command directory, return first pending command",
    "或 None": "or None",
    "按时间排序获取命令文件": "Sort command files by time",
    "读取命令文件失败: ": "Failed to read command file: ",
    "发送响应": "Send response",
    "删除命令文件": "Delete command file",
    "发送成功响应": "Send success response",
    "发送错误响应": "Send error response",
}

for k, v in replacements.items():
    text = text.replace(k, v)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)

print("done")
