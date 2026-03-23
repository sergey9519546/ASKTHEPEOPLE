import os
import re

# Comprehensive translation dictionary
translations = {
    "Twitter模拟": "Twitter Simulation",
    "Reddit模拟": "Reddit Simulation",
    "完成后立即关闭": "Close immediately after completion",
    "获取Agent": "Get Agent",
    "创建Interview动作": "Create Interview action",
    "没有有效的Agent": "No valid Agent found",
    "并确保整个程序都能响应退出信号": "and ensure the entire program can respond to exit signals",
    "配置Total rounds:": "Configured Total rounds:",
    "最大轮数限制:": "Max rounds limit:",
    "实际执行轮数:": "Actual execution rounds:",
    "(已截断)": "(Truncated)",
    "Agent数量:": "Agent count:",
    "日志结构:": "Log structure:",
    "主日志:": "Main log:",
    "Twitter动作:": "Twitter actions:",
    "Reddit动作:": "Reddit actions:",
    "存储两个platform的模拟结果": "Store simulation results for both platforms",
    "并行运行(每个platform使用独立的日志记录器)": "Run in parallel (each platform uses an independent logger)",
    "是否进入等待命令模式": "Whether to enter command-wait mode",
    "创建IPC处理器": "Create IPC handler",
    "使用 wait_for 替代 sleep,这样可以响应 shutdown_event": "Use wait_for instead of sleep, so it can respond to shutdown_event",
    "超时继续循环": "Timeout continues the loop",
    "关闭环境": "Close environment",
    "全部完成!": "All complete!",
    "日志File:": "Log files:",
    "Setting信号处理器,确保收到 SIGTERM/SIGINT 时能够正确退出": "Set up signal handlers to ensure clean exit on SIGTERM/SIGINT",
    "持久化模拟场景:模拟完成后不退出,等待 interview 命令": "Persistent simulation scenario: do not exit after simulation, wait for interview command",
    "当收到终止信号时,需要:": "When a termination signal is received, need to:",
    "1. 通知 asyncio 循环退出等待": "1. Notify asyncio loop to exit wait",
    "2. 让程序有机会正常清理资源(关闭数据库、环境等)": "2. Allow the program to perform necessary cleanup (closing DB, env, etc)",
    "3. 然后才退出": "3. Then exit",
    "收到 {sig_name} 信号,正在退出...": "Received {sig_name} signal, exiting...",
    "Setting事件通知 asyncio 循环退出(让循环有机会清理资源)": "Set event to notify asyncio loop to exit (allowing resource cleanup)",
    "不要直接 sys.exit(),让 asyncio 循环正常退出并清理资源": "Do not call sys.exit() directly, let the asyncio loop exit normally and clean up",
    "如果是重复收到信号,才强制退出": "If repeated signals are received, force exit",
    "清理 multiprocessing 资源跟踪器(防止退出时的警告)": "Clean up multiprocessing resource tracker (prevent warnings on exit)",
    "Twitter platform action log": "Twitter platform action log",
    "Reddit platform action log": "Reddit platform action log",
    "OASIS Twitter模拟": "OASIS Twitter Simulation",
    "OASIS Reddit模拟": "OASIS Reddit Simulation",
    "描述:": "Description:",
    "配置文件不存在": "Configuration file does not exist",
    "初始化日志配置": "Initialize logging configuration",
    "清理旧日志": "Clean up old logs",
    "使用固定文件名": "Use fixed filenames",
}

def translate_file(file_path):
    if not os.path.exists(file_path):
        return
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Sort keys by length descending to handle overlapping phrases
    for zh in sorted(translations.keys(), key=len, reverse=True):
        content = content.replace(zh, translations[zh])
    
    # Handle some dynamic patterns
    content = content.replace("秒", "s")
    content = content.replace("错误", "Error")
    content = content.replace("警告", "Warning")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Translated {file_path}")

files = [
    r"c:\Users\serge\OneDrive\Documents\GitHub\ASKTHEPEOPLE\backend\scripts\run_parallel_simulation.py",
    r"c:\Users\serge\OneDrive\Documents\GitHub\ASKTHEPEOPLE\backend\scripts\run_twitter_simulation.py",
    r"c:\Users\serge\OneDrive\Documents\GitHub\ASKTHEPEOPLE\backend\scripts\run_reddit_simulation.py",
    r"c:\Users\serge\OneDrive\Documents\GitHub\ASKTHEPEOPLE\backend\scripts\test_profile_format.py",
    r"c:\Users\serge\OneDrive\Documents\GitHub\ASKTHEPEOPLE\backend\scripts\action_logger.py"
]

for f in files:
    translate_file(f)
