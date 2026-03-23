import os
import re

# Comprehensive translation dictionary
translations = {
    "功能特性": "Features",
    "完成模拟后不立即关闭环境,进入等待命令模式": "Enters command-wait mode instead of closing environment immediately after simulation",
    "支持通过IPC接收Interview命令": "Supports receiving Interview commands via IPC",
    "支持单个Agent采访和批量采访": "Supports single Agent interview and batch interviews",
    "支持远程关闭环境命令": "Supports remote environment closure commands",
    "使用方式": "Usage",
    "配置 OASIS 的日志,使用固定名称的日志文件": "Configure OASIS logs using fixed-name log files",
    "清理旧的日志文件": "Clean up old log files",
    "获取Agent": "Get Agent",
    "创建Interview动作": "Create Interview action",
    "没有有效的Agent": "No valid Agent found",
    "等待命令循环(使用全局 _shutdown_event)": "Wait for command loop (using global _shutdown_event)",
    "收到退出信号": "Received exit signal",
    "配置文件路径 (simulation_config.json)": "Configuration file path (simulation_config.json)",
    "在 main 函数开始时创建 shutdown 事件": "Create shutdown event at the start of main function",
    "错误: 配置文件不存在": "Error: Configuration file does not exist",
    "初始化日志配置(使用固定文件名,清理旧日志)": "Initialize logging configuration (using fixed filenames, cleaning old logs)",
    "Twitter platform action logs": "Twitter platform action logs",
    "Reddit platform action logs": "Reddit platform action logs",
    "Main simulation process log": "Main simulation process log",
    "Running state (for API queries)": "Running state (for API queries)",
    "尝试加载": "Try loading",
    "platform不可用": "platform is unavailable",
    "初始化...": "Initializing...",
    "错误: Profile文件不存在": "Error: Profile file does not exist",
    "从配置文件获取 Agent 真实名称映射(使用 entity_name 而非默认的 Agent_X)": "Get Agent real name mapping from configuration (using entity_name instead of default Agent_X)",
    "如果配置中没有某个 agent,则使用 OASIS 的默认名称": "If an agent is not in the configuration, use the OASIS default name",
    "OASISdual platforms并行模拟": "OASIS dual platform parallel simulation",
    "只Run Twitter simulation": "Only run Twitter simulation",
    "只Run Reddit simulation": "Only run Reddit simulation",
    "模拟完成后立即关闭环境,不进入等待命令模式": "Close environment immediately after simulation, do not enter command-wait mode",
    "在 main 函数开始时创建 shutdown 事件,确保整个程序都能响应退出信号": "Create shutdown event at the start of main function to ensure the entire program responds to exit signals",
    "初始化日志配置(禁用 OASIS 日志,清理旧文件)": "Initialize logging configuration (disable OASIS logs, clean up old files)",
    "创建日志管理器": "Create log manager",
    "OASIS dual platforms并行模拟": "OASIS dual platform parallel simulation",
    "配置文件:": "Configuration file:",
    "模拟ID:": "Simulation ID:",
    "等待命令模式:": "Wait-for-command mode:",
    "启用": "Enabled",
    "禁用": "Disabled",
    "模拟参数:": "Simulation parameters:",
    "总模拟时长:": "Total simulation duration:",
    "小时": "hours",
    "每轮时间:": "Minutes per round:",
    "分钟": "minutes",
    "总轮数:": "Total rounds:",
    "初始化LLM模型...": "Initializing LLM model...",
    "加载Agent Profile...": "Loading Agent Profile...",
    "已删除旧数据库:": "Deleted old database:",
    "创建OASIS环境...": "Creating OASIS environment...",
    "环境初始化完成": "Environment initialization complete",
    "开始模拟循环...": "Starting simulation loop...",
    "模拟循环完成!": "Simulation loop complete!",
    "总耗时:": "Total elapsed time:",
    "数据库:": "Database:",
    "进入等待命令模式 - 环境保持运行": "Entering wait-for-command mode - environment kept running",
    "支持的命令: interview, batch_interview, close_env": "Supported commands: interview, batch_interview, close_env",
    "收到 SIGTERM 信号,正在退出...": "Received SIGTERM signal, exiting...",
    "收到 SIGINT 信号,正在退出...": "Received SIGINT signal, exiting...",
    "收到中断信号": "Received interruption signal",
    "任务被取消": "Task cancelled",
    "命令处理出错:": "Command processing error:",
    "关闭环境...": "Closing environment...",
    "环境已关闭": "Environment closed",
    "程序被中断": "Program interrupted",
    "模拟进程已退出": "Simulation process exited",
    "文件:": "File:",
}

def translate_file(file_path):
    if not os.path.exists(file_path):
        return
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for zh, en in translations.items():
        content = content.replace(zh, en)
    
    # Handle some dynamic patterns
    content = content.replace("个Agent", "agents")
    content = content.replace("错误:", "Error:")
    content = content.replace("警告:", "Warning:")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Translated {file_path}")

files = [
    r"c:\Users\serge\OneDrive\Documents\GitHub\ASKTHEPEOPLE\backend\scripts\run_parallel_simulation.py",
    r"c:\Users\serge\OneDrive\Documents\GitHub\ASKTHEPEOPLE\backend\scripts\run_twitter_simulation.py",
    r"c:\Users\serge\OneDrive\Documents\GitHub\ASKTHEPEOPLE\backend\scripts\run_reddit_simulation.py",
    r"c:\Users\serge\OneDrive\Documents\GitHub\ASKTHEPEOPLE\backend\scripts\test_profile_format.py"
]

for f in files:
    translate_file(f)
