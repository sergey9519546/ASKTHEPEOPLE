import os

filepath = r"c:\Users\serge\OneDrive\Documents\GitHub\ASKTHEPEOPLE\backend\app\services\zep_graph_memory_updater.py"
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

replacements = {
    "尝试从队列获取活动（超时1seconds）": "Try to get activity from queue (timeout 1 second)",
    "成功Sending 的批次数": "Batches successfully sent",
    "成功Sending 的活动条数": "Activities successfully sent",
    "Sending {display_name}platform's remaining {len(buffer)} 活动": f"Sending {{display_name}} platform's remaining {{len(buffer)}} activities",
    "获取Statistics信息": "Get statistics info",
    "获取所有更新器的Statistics信息": "Get all updaters statistics info",
    "管理多个模拟的Zep Graph Memory Updater": "Manage Zep Graph Memory Updaters for multiple simulations",
}

for k, v in replacements.items():
    text = text.replace(k, v)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)

print("done")
