"""
Graph-related API Routes
Uses project context mechanism, server-side persistent state
"""

import os
import traceback
import threading
from flask import request, jsonify

from . import graph_bp
from ..config import Config
from ..services.ontology_generator import OntologyGenerator
from ..services.graph_builder import GraphBuilderService
from ..services.text_processor import TextProcessor
from ..utils.file_parser import FileParser
from ..utils.logger import get_logger
from ..models.task import TaskManager, TaskStatus
from ..models.project import ProjectManager, ProjectStatus

# Get Logger
logger = get_logger('askthepeople.api')


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return ext in Config.ALLOWED_EXTENSIONS


# ============== Project Management Interface ==============

@graph_bp.route('/project/<project_id>', methods=['GET'])
def get_project(project_id: str):
    """
    Get project details
    """
    project = ProjectManager.get_project(project_id)
    
    if not project:
        return jsonify({
            "success": False,
            "error": f"Project does not exist: {project_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "data": project.to_dict()
    })


@graph_bp.route('/project/list', methods=['GET'])
def list_projects():
    """
    List all projects
    """
    limit = request.args.get('limit', 50, type=int)
    projects = ProjectManager.list_projects(limit=limit)
    
    return jsonify({
        "success": True,
        "data": [p.to_dict() for p in projects],
        "count": len(projects)
    })


@graph_bp.route('/project/<project_id>', methods=['DELETE'])
def delete_project(project_id: str):
    """
    Delete project
    """
    success = ProjectManager.delete_project(project_id)
    
    if not success:
        return jsonify({
            "success": False,
            "error": f"Project does not exist or deletion failed: {project_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "message": f"Project deleted: {project_id}"
    })


@graph_bp.route('/project/<project_id>/reset', methods=['POST'])
def reset_project(project_id: str):
    """
    Reset project state (used for rebuilding graph)
    """
    project = ProjectManager.get_project(project_id)
    
    if not project:
        return jsonify({
            "success": False,
            "error": f"Project does not exist: {project_id}"
        }), 404
    
    # Reset to ontology generated state
    if project.ontology:
        project.status = ProjectStatus.ONTOLOGY_GENERATED
    else:
        project.status = ProjectStatus.CREATED
    
    project.graph_id = None
    project.graph_build_task_id = None
    project.error = None
    ProjectManager.save_project(project)
    
    return jsonify({
        "success": True,
        "message": f"Project reset: {project_id}",
        "data": project.to_dict()
    })


# ============== Endpoint 1: Upload File and Generate Ontology ==============

@graph_bp.route('/ontology/generate', methods=['POST'])
def generate_ontology():
    """
    Endpoint 1: Upload file, analyze and generate ontology definition (async)

    Saves files and extracts text synchronously, then runs the LLM call in a
    background thread to avoid Railway/proxy timeouts on long LLM responses.
    Returns a task_id immediately; poll /api/graph/task/{task_id} for progress.
    On completion, task.result contains the full project/ontology data.

    Request Method: multipart/form-data

    Parameters:
        files: Uploaded files (PDF/MD/TXT), multiple allowed
        simulation_requirement: Simulation requirement description (required)
        project_name: Project name (optional)
        additional_context: Additional context (optional)
        
    Returns immediately:
        {
            "success": true,
            "data": {
                "task_id": "task_xxxx",
                "project_id": "proj_xxxx",
                "message": "..."
            }
        }
    On task completion (task.result):
        {
            "project_id": "proj_xxxx",
            "ontology": {"entity_types": [...], "edge_types": [...]},
            "analysis_summary": "...",
            "files": [...],
            "total_text_length": 12345
        }
    """
    try:
        logger.info("=== Starting ontology generation task ===")

        # Validate API key upfront so we fail fast before touching the filesystem
        if not Config.LLM_API_KEY:
            return jsonify({"success": False, "error": "LLM_API_KEY is not configured"}), 500

        # Get parameters
        simulation_requirement = request.form.get('simulation_requirement', '')
        project_name = request.form.get('project_name', 'Unnamed Project')
        additional_context = request.form.get('additional_context', '')

        logger.debug(f"Project name: {project_name}")
        if simulation_requirement:
            logger.debug(f"Simulation requirements: {simulation_requirement[:100]}...")

        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error": "Please provide simulation requirement description (simulation_requirement)"
            }), 400

        # Get uploaded files
        uploaded_files = request.files.getlist('files')
        if not uploaded_files or all(not f.filename for f in uploaded_files):
            return jsonify({
                "success": False,
                "error": "Please upload at least one document file"
            }), 400

        # Create project
        project = ProjectManager.create_project(name=project_name)
        project.simulation_requirement = simulation_requirement
        logger.info(f"Created project: {project.project_id}")

        # Save files and extract text synchronously (fast — no LLM call yet)
        document_texts = []
        all_text = ""

        for file in uploaded_files:
            if file and file.filename and allowed_file(file.filename):
                file_info = ProjectManager.save_file_to_project(
                    project.project_id,
                    file,
                    file.filename
                )
                project.files.append({
                    "filename": file_info["original_filename"],
                    "size": file_info["size"]
                })
                text = FileParser.extract_text(file_info["path"])
                text = TextProcessor.preprocess_text(text)
                document_texts.append(text)
                all_text += f"\n\n=== {file_info['original_filename']} ===\n{text}"

        if not document_texts:
            ProjectManager.delete_project(project.project_id)
            return jsonify({
                "success": False,
                "error": "Did not successfully process any document, please check file formats"
            }), 400

        # Persist extracted text before handing off to background thread
        project.total_text_length = len(all_text)
        ProjectManager.save_extracted_text(project.project_id, all_text)
        ProjectManager.save_project(project)
        logger.info(f"Text extraction completed, total {len(all_text)} characters")

        # Create async task for the LLM call
        task_manager = TaskManager()
        task_id = task_manager.create_task(f"Generate Ontology: {project_name}")
        logger.info(f"Created ontology task: task_id={task_id}, project_id={project.project_id}")

        # Snapshot locals for the background thread
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
                _project.error = str(e)
                ProjectManager.save_project(_project)

                task_manager.update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    message=f"Ontology generation failed: {str(e)}",
                    error=traceback.format_exc()
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
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Endpoint 2: Build Graph ==============

@graph_bp.route('/build', methods=['POST'])
def build_graph():
    """
    Endpoint 2: Build graph based on project_id
    
    Request (JSON):
        {
            "project_id": "proj_xxxx",  // Required, from Endpoint 1
            "graph_name": "Graph Name",    // Optional
            "chunk_size": 500,          // Optional, default 500
            "chunk_overlap": 50         // Optional, default 50
        }
        
    Returns:
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "task_id": "task_xxxx",
                "message": "Graph building task started"
            }
        }
    """
    try:
        logger.info("=== Started building graph ===")
        
        # Check configurations
        errors = []
        if not Config.ZEP_API_KEY:
            errors.append("ZEP_API_KEY not configured")
        if errors:
            logger.error(f"Configuration error: {errors}")
            return jsonify({
                "success": False,
                "error": "Configuration error: " + "; ".join(errors)
            }), 500
        
        # Parse request
        data = request.get_json() or {}
        project_id = data.get('project_id')
        logger.debug(f"Request parameters: project_id={project_id}")
        
        if not project_id:
            return jsonify({
                "success": False,
                "error": "Please provide project_id"
            }), 400
        
        # Get project
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": f"Project does not exist: {project_id}"
            }), 404
        
        # Check project status
        force = data.get('force', False)  # Force rebuild
        
        if project.status == ProjectStatus.CREATED:
            return jsonify({
                "success": False,
                "error": "Project has not generated ontology yet, please call /ontology/generate first"
            }), 400
        
        if project.status == ProjectStatus.GRAPH_BUILDING and not force:
            return jsonify({
                "success": False,
                "error": "Graph is currently building, please do not submit repeatedly. To force rebuild, add force: true",
                "task_id": project.graph_build_task_id
            }), 400
        
        # If force rebuild, reset status
        if force and project.status in [ProjectStatus.GRAPH_BUILDING, ProjectStatus.FAILED, ProjectStatus.GRAPH_COMPLETED]:
            project.status = ProjectStatus.ONTOLOGY_GENERATED
            project.graph_id = None
            project.graph_build_task_id = None
            project.error = None
        
        # Get configuration
        graph_name = data.get('graph_name', project.name or 'ASKTHEPEOPLE Graph')
        chunk_size = data.get('chunk_size', project.chunk_size or Config.DEFAULT_CHUNK_SIZE)
        chunk_overlap = data.get('chunk_overlap', project.chunk_overlap or Config.DEFAULT_CHUNK_OVERLAP)
        
        # Update project configuration
        project.chunk_size = chunk_size
        project.chunk_overlap = chunk_overlap
        
        # Get extracted text
        text = ProjectManager.get_extracted_text(project_id)
        if not text:
            return jsonify({
                "success": False,
                "error": "Could not find extracted text content"
            }), 400
        
        # Get ontology
        ontology = project.ontology
        if not ontology:
            return jsonify({
                "success": False,
                "error": "Could not find ontology definition"
            }), 400
        
        # Create asynchronous task
        task_manager = TaskManager()
        task_id = task_manager.create_task(f"Build Graph: {graph_name}")
        logger.info(f"Created graph building task: task_id={task_id}, project_id={project_id}")
        
        # Update project status
        project.status = ProjectStatus.GRAPH_BUILDING
        project.graph_build_task_id = task_id
        ProjectManager.save_project(project)
        
        # Start background task
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
                project.error = str(e)
                ProjectManager.save_project(project)
                
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    message=f"Build failed: {str(e)}",
                    error=traceback.format_exc()
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
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Task Query Interface ==============

@graph_bp.route('/task/<task_id>', methods=['GET'])
def get_task(task_id: str):
    """
    Query task status
    """
    task = TaskManager().get_task(task_id)
    
    if not task:
        return jsonify({
            "success": False,
            "error": f"Task does not exist: {task_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "data": task.to_dict()
    })


@graph_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """
    List all tasks
    """
    tasks = TaskManager().list_tasks()
    
    return jsonify({
        "success": True,
        "data": [t.to_dict() for t in tasks],
        "count": len(tasks)
    })


# ============== Graph Data Interface ==============

@graph_bp.route('/data/<graph_id>', methods=['GET'])
def get_graph_data(graph_id: str):
    """
    Get graph data (nodes and edges)
    """
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": "ZEP_API_KEY not configured"
            }), 500
        
        builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
        graph_data = builder.get_graph_data(graph_id)
        
        return jsonify({
            "success": True,
            "data": graph_data
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@graph_bp.route('/delete/<graph_id>', methods=['DELETE'])
def delete_graph(graph_id: str):
    """
    Delete Zep graph
    """
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": "ZEP_API_KEY not configured"
            }), 500
        
        builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
        builder.delete_graph(graph_id)
        
        return jsonify({
            "success": True,
            "message": f"Graph deleted: {graph_id}"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500
