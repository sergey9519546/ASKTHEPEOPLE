import sys

with open('app/api/graph.py', 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """        # Snapshot locals for the background thread
        _project = project
        _doc_texts = document_texts
        _sim_req = simulation_requirement
        _extra_ctx = additional_context

        def ontology_task():
            gen_logger = get_logger('askthepeople.ontology')
            try:
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.PROCESSING,
                    message="Calling LLM to generate ontology...",
                    progress=10
                )
                gen_logger.info(f"[{task_id}] Calling LLM for ontology generation...")

                generator = OntologyGenerator()
                ontology = generator.generate(
                    document_texts=_doc_texts,
                    simulation_requirement=_sim_req,
                    additional_context=_extra_ctx if _extra_ctx else None
                )

                entity_count = len(ontology.get("entity_types", []))
                edge_count = len(ontology.get("edge_types", []))
                gen_logger.info(
                    f"[{task_id}] Ontology done: {entity_count} entity types, {edge_count} relation types"
                )

                _project.ontology = {
                    "entity_types": ontology.get("entity_types", []),
                    "edge_types": ontology.get("edge_types", [])
                }
                _project.analysis_summary = ontology.get("analysis_summary", "")
                _project.status = ProjectStatus.ONTOLOGY_GENERATED
                ProjectManager.save_project(_project)

                task_manager.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    message="Ontology generation completed",
                    progress=100,
                    result={
                        "project_id": _project.project_id,
                        "project_name": _project.name,
                        "ontology": _project.ontology,
                        "ontology_status": model_proposed_schema_disclosure(),
                        "analysis_summary": _project.analysis_summary,
                        "files": _project.files,
                        "total_text_length": _project.total_text_length
                    }
                )
                gen_logger.info(f"[{task_id}] === Ontology Generation Completed === Project ID: {_project.project_id}")

            except Exception as e:
                gen_logger.error(f"[{task_id}] Ontology generation failed: {str(e)}")
                gen_logger.debug(traceback.format_exc())

                _project.status = ProjectStatus.FAILED
                _project.error = "ontology_generation_failed"
                ProjectManager.save_project(_project)

                task_manager.update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    message="Ontology generation failed",
                    error="ontology_generation_failed",
                    public_error="ontology_generation_failed",
                )

        thread = threading.Thread(target=ontology_task, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "data": {
                "task_id": task_id,
                "project_id": project.project_id,
                "message": "Ontology generation started, poll /api/graph/task/{task_id} for progress"
            }
        })"""

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
        }), 202, {'Location': f'/api/graph/task/{task_id}'}"""

if target1 in content:
    content = content.replace(target1, replacement1)
    print("Replaced target 1")
else:
    print("Failed to find target 1")

target2 = """        # Start background task
        def build_task():
            build_logger = get_logger('askthepeople.build')
            try:
                build_logger.info(f"[{task_id}] Started building graph...")
                task_manager.update_task(
                    task_id, 
                    status=TaskStatus.PROCESSING,
                    message="Initializing graph building service..."
                )
                
                # Create graph building service
                builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
                
                # Chunking
                task_manager.update_task(
                    task_id,
                    message="Chunking text...",
                    progress=5
                )
                chunks = TextProcessor.split_text(
                    text, 
                    chunk_size=chunk_size, 
                    overlap=chunk_overlap
                )
                total_chunks = len(chunks)
                
                # Create graph
                task_manager.update_task(
                    task_id,
                    message="Creating Zep graph...",
                    progress=10
                )
                graph_id = builder.create_graph(name=graph_name)
                
                # Update project graph_id
                project.graph_id = graph_id
                ProjectManager.save_project(project)
                
                # Set ontology
                task_manager.update_task(
                    task_id,
                    message="Setting ontology definition...",
                    progress=15
                )
                builder.set_ontology(graph_id, ontology)
                
                # Add text (progress_callback signature is (msg, progress_ratio))
                def add_progress_callback(msg, progress_ratio):
                    progress = 15 + int(progress_ratio * 40)  # 15% - 55%
                    task_manager.update_task(
                        task_id,
                        message=msg,
                        progress=progress
                    )
                
                task_manager.update_task(
                    task_id,
                    message=f"Starting to add {total_chunks} text chunks...",
                    progress=15
                )
                
                episode_uuids = builder.add_text_batches(
                    graph_id, 
                    chunks,
                    batch_size=3,
                    progress_callback=add_progress_callback
                )
                
                # Wait for Zep to complete processing (query the processed status of each episode)
                task_manager.update_task(
                    task_id,
                    message="Waiting for Zep to process data...",
                    progress=55
                )
                
                def wait_progress_callback(msg, progress_ratio):
                    progress = 55 + int(progress_ratio * 35)  # 55% - 90%
                    task_manager.update_task(
                        task_id,
                        message=msg,
                        progress=progress
                    )
                
                builder._wait_for_episodes(episode_uuids, wait_progress_callback)
                
                # Get graph data
                task_manager.update_task(
                    task_id,
                    message="Getting graph data...",
                    progress=95
                )
                graph_data = builder.get_graph_data(graph_id)
                
                # Update project status
                project.status = ProjectStatus.GRAPH_COMPLETED
                ProjectManager.save_project(project)
                
                node_count = graph_data.get("node_count", 0)
                edge_count = graph_data.get("edge_count", 0)
                build_logger.info(f"[{task_id}] Graph building completed: graph_id={graph_id}, nodes={node_count}, edges={edge_count}")
                
                # Completed
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    message="Graph building completed",
                    progress=100,
                    result={
                        "project_id": project_id,
                        "graph_id": graph_id,
                        "node_count": node_count,
                        "edge_count": edge_count,
                        "chunk_count": total_chunks
                    }
                )
                
            except Exception as e:
                # Update project status to failed
                build_logger.error(f"[{task_id}] Graph building failed: {str(e)}")
                build_logger.debug(traceback.format_exc())
                
                project.status = ProjectStatus.FAILED
                project.error = "graph_build_failed"
                ProjectManager.save_project(project)
                
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    message="Graph build failed",
                    error="graph_build_failed",
                    public_error="graph_build_failed",
                )
        
        # Start background thread
        thread = threading.Thread(target=build_task, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "data": {
                "project_id": project_id,
                "task_id": task_id,
                "message": "Graph building task started, please check progress via /task/{task_id}"
            }
        })"""

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
        }), 202, {'Location': f'/api/graph/task/{task_id}'}"""

if target2 in content:
    content = content.replace(target2, replacement2)
    print("Replaced target 2")
else:
    print("Failed to find target 2")

with open('app/api/graph.py', 'w', encoding='utf-8') as f:
    f.write(content)
