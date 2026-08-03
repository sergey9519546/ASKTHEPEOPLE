import os
import re

# PATCH GRAPH
with open('backend/app/api/graph.py', 'r', encoding='utf-8') as f:
    content = f.read()

pattern1 = r'# Snapshot locals for the background thread.*?return jsonify\(\{.*?\}\)\n'
replacement1 = """        from ..tasks.graph_tasks import generate_ontology_task
        
        generate_ontology_task.delay(
            project_id=project.project_id,
            text=all_text,
            requirements=simulation_requirement,
            task_id=task_id
        )

        return jsonify({
            "success": True,
            "data": {
                "task_id": task_id,
                "status": "processing"
            }
        }), 202, {'Location': f'/api/graph/task/{task_id}'}
"""

content = re.sub(pattern1, replacement1, content, flags=re.DOTALL)

pattern2 = r'# Start background task\n\s+def build_task.*?\n\s+return jsonify\(\{.*?\}\)\n'
replacement2 = """        from ..tasks.graph_tasks import build_graph_task
        
        build_graph_task.delay(
            project_id=project_id,
            graph_name=graph_name,
            task_id=task_id
        )
        
        return jsonify({
            "success": True,
            "data": {
                "task_id": task_id,
                "status": "processing"
            }
        }), 202, {'Location': f'/api/graph/task/{task_id}'}
"""
content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)

with open('backend/app/api/graph.py', 'w', encoding='utf-8') as f:
    f.write(content)

# PATCH REPORT
with open('backend/app/api/report.py', 'r', encoding='utf-8') as f:
    content = f.read()

pattern3 = r'# Define background task\n\s+def run_generate.*?return jsonify\(\{.*?\}\)\n'
replacement3 = """        from ..tasks.report_tasks import generate_report_task
        
        generation_thread_started = True
        
        generate_report_task.delay(
            simulation_id=simulation_id,
            report_id=report_id,
            user_prompt=data.get('user_prompt'),
            custom_instructions=data.get('custom_instructions'),
            task_id=task_id
        )
        
        return jsonify({
            "success": True,
            "data": {
                "report_id": report_id,
                "task_id": task_id,
                "status": "pending"
            }
        }), 202, {'Location': f'/api/jobs/{task_id}'}
"""
content = re.sub(pattern3, replacement3, content, flags=re.DOTALL)

with open('backend/app/api/report.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch complete")
