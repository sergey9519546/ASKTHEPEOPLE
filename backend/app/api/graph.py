"""
Graph-related API Routes
Uses project context mechanism, server-side persistent state
"""

import os
import traceback

from flask import jsonify, request

from ..config import Config
from ..models.project import ProjectManager, ProjectStatus
from ..models.task import TaskManager
from ..services.claim_boundary import (
    graph_record_disclosure,
    model_proposed_schema_disclosure,
    synthetic_output_disclosure,
)
from ..services.graph_association import (
    GraphAssociationError,
    resolve_project_graph,
)
from ..services.graph_builder import GraphBuilderService
from ..services.text_processor import TextProcessor
from ..utils.file_parser import FileParser, FileParserLimitError
from ..utils.file_security import validate_file_upload
from ..utils.input_policy import (
    ADDITIONAL_CONTEXT_MAX,
    EXTRACTED_TEXT_CHARACTERS_MAX,
    PROJECT_NAME_MAX,
    SCENARIO_QUESTION_MAX,
    UPLOAD_FILE_COUNT_MAX,
    InputPolicyError,
    bounded_text,
    validate_exploratory_use,
    validate_item_count,
)
from ..utils.logger import get_logger
from ..utils.response import truth_metadata
from . import graph_bp, limiter

# Get Logger
logger = get_logger('askthepeople.api')


def _attach_model_schema_status(payload: dict) -> dict:
    """Label model-proposed ontology data without relabeling uploaded sources."""
    disclosed = dict(payload)
    if disclosed.get("ontology") is not None:
        disclosed["ontology_status"] = model_proposed_schema_disclosure()
    nested_result = disclosed.get("result")
    if isinstance(nested_result, dict):
        disclosed["result"] = _attach_model_schema_status(nested_result)
    return disclosed


def _attach_graph_record_provenance(graph_data: dict) -> dict:
    """Add conservative, compatibility-safe provenance to graph payloads."""
    disclosed = dict(graph_data)
    disclosed.update(graph_record_disclosure())
    disclosed["edges"] = [
        {
            **edge,
            **graph_record_disclosure(edge.get("fact", "")),
        }
        for edge in graph_data.get("edges", [])
    ]
    return disclosed


def _resolve_owned_graph(graph_id: str):
    """Resolve the canonical project association before any provider access.

    A ZEP graph identifier is not an authorization capability.  The caller
    must also supply a server-owned project identifier, and the current
    canonical project record must name this exact completed graph.
    """
    try:
        association = resolve_project_graph(
            request.args.get("project_id"),
            graph_id,
        )
    except GraphAssociationError as exc:
        return None, (
            jsonify({"success": False, "error": exc.code}),
            exc.status_code,
        )
    return association.project, None


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
        "data": _attach_model_schema_status(project.to_dict()),
        **truth_metadata()
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
        "data": [
            _attach_model_schema_status(project.to_dict())
            for project in projects
        ],
        "count": len(projects),
        **truth_metadata()
    })


@graph_bp.route('/project/<project_id>', methods=['DELETE'])
def delete_project(project_id: str):
    """
    Delete project
    """
    project = ProjectManager.get_project(project_id)
    if not project:
        return jsonify({
            "success": False,
            "error": f"Project does not exist: {project_id}",
        }), 404
    if project.status == ProjectStatus.GRAPH_BUILDING or project.graph_id:
        return jsonify({
            "success": False,
            "error": "project_deletion_unavailable",
        }), 409

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

    if project.status == ProjectStatus.GRAPH_BUILDING or project.graph_id:
        return jsonify({
            "success": False,
            "error": "graph_reset_unavailable",
        }), 409
    
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
        "data": _attach_model_schema_status(project.to_dict())
    })


# ============== Endpoint 1: Upload File and Generate Ontology ==============

@graph_bp.route('/ontology/generate', methods=['POST'])
@limiter.limit(Config.RATELIMIT_LLM_HEAVY)
def generate_ontology():
    """
    Endpoint 1: Upload file, analyze and generate ontology definition (async)

    In the legacy filesystem mode, saves files and extracts text synchronously,
    then queues the LLM call through Celery. Canonical persistence fails closed
    until the reviewed source-ingestion pipeline owns object retrieval and
    parsing. Returns a task_id immediately; poll /api/graph/task/{task_id} for progress.
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

        # The canonical repository returns an opaque object-store key from the
        # upload seam. Passing that key to FileParser would treat it as a local
        # path and either fail or bypass the required scan/review lifecycle.
        # Keep the unfinished canonical source path dark until Task 4 owns the
        # object read, quarantine, parser attempt, and review state.
        if Config.USE_SUPABASE_PERSISTENCE:
            return jsonify({
                "success": False,
                "error": "canonical_source_ingestion_unavailable",
                "message": "Canonical source ingestion is not available.",
            }), 503

        # Get parameters
        try:
            simulation_requirement = bounded_text(
                request.form.get('simulation_requirement'),
                field="simulation_requirement",
                max_length=SCENARIO_QUESTION_MAX,
                required=True,
            )
            project_name = bounded_text(
                request.form.get('project_name', 'Unnamed Project'),
                field="project_name",
                max_length=PROJECT_NAME_MAX,
                required=True,
            )
            bounded_text(
                request.form.get('additional_context', ''),
                field="additional_context",
                max_length=ADDITIONAL_CONTEXT_MAX,
            )
            validate_exploratory_use(
                intended_use=request.form.get('intended_use'),
                acknowledged=request.form.get('use_policy_acknowledged'),
            )
        except InputPolicyError as exc:
            return jsonify({
                "success": False,
                "error": exc.code,
                "message": exc.message,
            }), 400

        logger.debug(f"Project name: {project_name}")
        if simulation_requirement:
            logger.debug(f"Simulation requirements: {simulation_requirement[:100]}...")

        # Get uploaded files
        try:
            uploaded_files = validate_item_count(
                request.files.getlist('files'),
                field="files",
                maximum=UPLOAD_FILE_COUNT_MAX,
            )
        except InputPolicyError as exc:
            return jsonify({
                "success": False,
                "error": exc.code,
                "message": exc.message,
            }), 400
        if not uploaded_files or all(not f.filename for f in uploaded_files):
            return jsonify({
                "success": False,
                "error": "Please upload at least one document file"
            }), 400

        # Validate provider configuration only after rejecting malformed input.
        if not Config.LLM_API_KEY:
            return jsonify({"success": False, "error": "LLM_API_KEY is not configured"}), 500

        # Create project
        project = ProjectManager.create_project(name=project_name)
        project.simulation_requirement = simulation_requirement
        logger.info(f"Created project: {project.project_id}")

        # Save files and extract text synchronously (fast — no LLM call yet)
        document_texts = []
        all_text = ""

        for file in uploaded_files:
            if file and file.filename and allowed_file(file.filename):
                # P0 adversarial-upload defense (audit §5 P0). The extension
                # allowlist above is a first line; validate_file_upload adds
                # magic-byte / MIME / size / empty-file checks so a renamed
                # payload cannot reach extraction or the LLM. This used to be
                # dead code referenced only by tests; it is now on the live
                # upload path.
                is_valid, validation_error = validate_file_upload(file)
                if not is_valid:
                    ProjectManager.delete_project(project.project_id)
                    return jsonify({
                        "success": False,
                        "error": "invalid_file",
                        "message": validation_error,
                    }), 400
                file_info = ProjectManager.save_file_to_project(
                    project.project_id,
                    file,
                    file.filename
                )
                project.files.append({
                    "filename": file_info["original_filename"],
                    "size": file_info["size"],
                    "content_hash": file_info.get("content_hash"),
                })
                text_header = f"\n\n=== {file_info['original_filename']} ===\n"
                remaining_characters = (
                    EXTRACTED_TEXT_CHARACTERS_MAX
                    - len(all_text)
                    - len(text_header)
                )
                if remaining_characters < 1:
                    ProjectManager.delete_project(project.project_id)
                    return jsonify({
                        "success": False,
                        "error": "extracted_text_too_large",
                        "message": (
                            "The extracted document text exceeds the "
                            f"{EXTRACTED_TEXT_CHARACTERS_MAX}-character limit."
                        ),
                    }), 413
                try:
                    text = FileParser.extract_text(
                        file_info["path"],
                        max_characters=remaining_characters,
                    )
                except FileParserLimitError:
                    ProjectManager.delete_project(project.project_id)
                    return jsonify({
                        "success": False,
                        "error": "extracted_text_too_large",
                        "message": (
                            "The uploaded documents exceed the PDF page or "
                            f"{EXTRACTED_TEXT_CHARACTERS_MAX}-character "
                            "extraction limit."
                        ),
                    }), 413
                text = TextProcessor.preprocess_text(text)
                text_fragment = f"{text_header}{text}"
                if (
                    len(all_text) + len(text_fragment)
                    > EXTRACTED_TEXT_CHARACTERS_MAX
                ):
                    ProjectManager.delete_project(project.project_id)
                    return jsonify({
                        "success": False,
                        "error": "extracted_text_too_large",
                        "message": (
                            "The extracted document text exceeds the "
                            f"{EXTRACTED_TEXT_CHARACTERS_MAX}-character limit."
                        ),
                    }), 413
                document_texts.append(text)
                all_text += text_fragment

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

        from ..tasks.graph_tasks import generate_ontology_task
        
        generate_ontology_task.apply_async(
            kwargs={
                "project_id": project.project_id,
                "text": all_text,
                "requirements": simulation_requirement,
                "task_id": task_id,
            },
            task_id=task_id,
        )

        return jsonify({
            "success": True,
            "data": {
                "task_id": task_id,
                "project_id": project.project_id,
                "status": "processing"
            }
        }), 202, {'Location': f'/api/graph/task/{task_id}'}

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Endpoint 2: Build Graph ==============

@graph_bp.route('/build', methods=['POST'])
@limiter.limit(Config.RATELIMIT_LLM_MEDIUM)
def build_graph():
    """
    Endpoint 2: Build graph based on project_id
    
    Request (JSON):
        {
            "project_id": "proj_xxxx",  // Required, from Endpoint 1
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
    task_manager = None
    task_id = None
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
        
        if project.status == ProjectStatus.GRAPH_BUILDING:
            return jsonify({
                "success": False,
                "error": "graph_build_conflict",
            }), 409

        if force and (
            project.status == ProjectStatus.GRAPH_COMPLETED or project.graph_id
        ):
            return jsonify({
                "success": False,
                "error": "graph_rebuild_unavailable",
            }), 409
        
        # If force rebuild, reset status
        prior_graph_state = {
            "status": project.status,
            "graph_id": project.graph_id,
            "graph_build_task_id": project.graph_build_task_id,
            "error": project.error,
        }
        # Get configuration
        chunk_size = data.get('chunk_size', project.chunk_size or Config.DEFAULT_CHUNK_SIZE)
        chunk_overlap = data.get('chunk_overlap', project.chunk_overlap or Config.DEFAULT_CHUNK_OVERLAP)
        
        # Update project configuration
        project.chunk_size = chunk_size
        project.chunk_overlap = chunk_overlap
        
        # Create asynchronous task
        task_manager = TaskManager()
        task_id = task_manager.create_task("graph_build")
        logger.info(f"Created graph building task: task_id={task_id}, project_id={project_id}")
        
        if not ProjectManager.begin_graph_build(
            project_id,
            task_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            expected_status=prior_graph_state["status"],
            expected_task_id=prior_graph_state["graph_build_task_id"],
            force=force,
        ):
            try:
                task_manager.fail_task(
                    task_id,
                    "graph_build_conflict",
                    public_error="graph_build_conflict",
                )
            except Exception:
                logger.error("graph begin conflict recovery failed project_id=%s", project_id)
            return jsonify({"success": False, "error": "graph_build_conflict"}), 409
        
        from ..tasks.graph_tasks import build_graph_task
        
        try:
            build_graph_task.apply_async(
                kwargs={"project_id": project_id},
                task_id=task_id,
            )
        except Exception:
            recovery_state = dict(prior_graph_state)
            if recovery_state["status"] != ProjectStatus.GRAPH_COMPLETED:
                recovery_state["error"] = "graph_dispatch_failed"
            try:
                ProjectManager.unwind_graph_build_dispatch(
                    project_id,
                    task_id,
                    recovery_state,
                )
            except Exception:
                logger.error("graph dispatch unwind failed project_id=%s task_id=%s", project_id, task_id)
            try:
                task_manager.fail_task(
                    task_id,
                    "graph_dispatch_failed",
                    public_error="graph_dispatch_failed",
                )
            except Exception:
                logger.error("graph dispatch task recovery failed project_id=%s task_id=%s", project_id, task_id)
            return jsonify({"success": False, "error": "graph_dispatch_failed"}), 503
        
        return jsonify({
            "success": True,
            "data": {
                "task_id": task_id,
                "status": "processing"
            }
        }), 202, {'Location': f'/api/graph/task/{task_id}'}
        
    except Exception as exc:
        logger.error(
            "graph build setup failed exception_type=%s",
            type(exc).__name__,
        )
        if task_manager is not None and task_id is not None:
            try:
                task_manager.fail_task(
                    task_id,
                    "graph_build_setup_failed",
                    public_error="graph_build_setup_failed",
                )
            except Exception:
                logger.error(
                    "graph build setup task recovery failed task_id=%s",
                    task_id,
                )
        return jsonify({
            "success": False,
            "error": "graph_build_setup_failed",
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
        "data": _attach_model_schema_status(task.to_public_dict()),
        **truth_metadata()
    })


@graph_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """
    List all tasks
    """
    tasks = TaskManager().list_tasks()
    
    return jsonify({
        "success": True,
        "data": [
            _attach_model_schema_status(task)
            for task in tasks
        ],
        "count": len(tasks),
        **truth_metadata()
    })


# ============== Graph Data Interface ==============

@graph_bp.route('/data/<graph_id>', methods=['GET'])
def get_graph_data(graph_id: str):
    """
    Get graph data (nodes and edges)
    """
    _project, ownership_error = _resolve_owned_graph(graph_id)
    if ownership_error is not None:
        return ownership_error

    if not Config.ZEP_API_KEY:
        return jsonify({
            "success": False,
            "error": "graph_dependency_unavailable",
        }), 503

    try:
        builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
        graph_data = _attach_graph_record_provenance(
            builder.get_graph_data(graph_id)
        )
        
        return jsonify({
            "success": True,
            "data": graph_data,
            "disclosure": synthetic_output_disclosure(),
        })
        
    except Exception as exc:
        logger.warning(
            "graph read unavailable exception_type=%s",
            type(exc).__name__,
        )
        return jsonify({
            "success": False,
            "error": "graph_read_unavailable",
        }), 503


@graph_bp.route('/delete/<graph_id>', methods=['DELETE'])
def delete_graph(graph_id: str):
    """
    Delete Zep graph
    """
    _project, ownership_error = _resolve_owned_graph(graph_id)
    if ownership_error is not None:
        return ownership_error

    # The current Project aggregate has no owner-fenced graph-delete state or
    # recovery transition for an ambiguous provider response.  Mutating ZEP
    # here could therefore orphan the canonical association.  Keep deletion
    # unavailable until that durable state machine exists.
    return jsonify({
        "success": False,
        "error": "graph_delete_unavailable",
    }), 503
