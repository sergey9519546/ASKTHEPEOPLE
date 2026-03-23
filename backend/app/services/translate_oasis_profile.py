import os

filepath = r"c:\Users\serge\OneDrive\Documents\GitHub\ASKTHEPEOPLE\backend\app\services\oasis_profile_generator.py"
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

replacements = {
    "使用Zep图谱混合搜索功能获取实体相关的丰富信息": "Use Zep graph hybrid search to retrieve rich information related to the entity",
    "Zep没有内置混合搜索接口，需要分别搜索edges和nodes然后合并结果。": "Zep has no built-in hybrid search interface; edges and nodes must be searched separately and results merged.",
    "使用并行请求同时搜索，提高效率。": "Use parallel requests to search simultaneously and improve efficiency.",
    "Args:\n            entity: 实体节点对象": "Args:\n            entity: Entity node object",
    "Returns:\n            包含facts, node_summaries, context的字典": "Returns:\n            Dictionary containing facts, node_summaries, and context",
    "并行执行edges和nodes搜索": "Execute searches for edges and nodes in parallel",
    "获取结果": "Get results",
    "尝试修复损坏的JSON": "Attempt to repair corrupted JSON",
    "首先尝试修复被截断的情况": "First attempt to repair truncation",
    "尝试提取JSON部分": "Attempt to extract the JSON part",
    "处理字符串中的换行符问题": "Handle newline characters within strings",
    "找到所有字符串值并替换其中的换行符": "Find all string values and replace newlines within them",
    "替换字符串内的实际换行符为空格": "Replace actual newlines within strings with spaces",
    "替换多余空格": "Replace redundant spaces",
    "匹配JSON字符串值": "Match JSON string values",
    "尝试解析": "Attempt to parse",
    "如果还是失败，尝试更激进的修复": "If still failed, attempt more aggressive repair",
    "移除所有控制字符": "Remove all control characters",
    "替换所有连续空白": "Replace all consecutive whitespaces",
    "机构虚拟年龄": "Institutional virtual age",
    "机构使用other": "Institutions use 'other'",
    "机构风格：严谨保守": "Institutional style: Rigorous and conservative",
    "指定实体类型": "Specify entity types",
}

for k, v in replacements.items():
    text = text.replace(k, v)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)

print("done")
