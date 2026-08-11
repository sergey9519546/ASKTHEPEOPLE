import service from './index'

/**
 * Generate ontology (upload documents and simulation requirements)
 * @param {Object} formData - Contains files, simulation_requirement, project_name, etc.
 * @returns {Promise}
 */
export function generateOntology(formData) {
  // Clear the instance-level Content-Type default so axios can auto-set
  // multipart/form-data with the correct boundary for FormData.
  return service({
    url: '/api/graph/ontology/generate',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': null },
  })
}

/**
 * Build graph
 * @param {Object} data - Contains project_id, graph_name, etc.
 * @returns {Promise}
 */
export function buildGraph(data) {
  return service({
    url: '/api/graph/build',
    method: 'post',
    data
  })
}

/**
 * Query task status
 * @param {String} taskId - Task ID
 * @returns {Promise}
 */
export function getTaskStatus(taskId) {
  return service({
    url: `/api/graph/task/${taskId}`,
    method: 'get'
  })
}

function requireOwnedGraphIds(projectId, graphId) {
  if (
    typeof projectId !== 'string' ||
    !projectId.trim() ||
    typeof graphId !== 'string' ||
    !graphId.trim()
  ) {
    throw new TypeError('projectId and graphId are required')
  }
}

/**
 * Get graph data through its canonical project association.
 * @param {String} projectId - Server-owned project ID
 * @param {String} graphId - Graph ID associated with the project
 * @returns {Promise}
 */
export function getGraphData(projectId, graphId) {
  requireOwnedGraphIds(projectId, graphId)
  return service({
    url: `/api/graph/data/${graphId}`,
    method: 'get',
    params: { project_id: projectId }
  }).catch(error => {
    if (error?.response?.data?.error === 'graph_not_available_for_project') {
      return {
        success: false,
        error: 'graph_not_available_for_project'
      }
    }
    throw error
  })
}

/**
 * Request graph deletion through its canonical project association.
 * The server currently fails closed until durable graph deletion exists.
 * @param {String} projectId - Server-owned project ID
 * @param {String} graphId - Graph ID associated with the project
 * @returns {Promise}
 */
export function deleteGraph(projectId, graphId) {
  requireOwnedGraphIds(projectId, graphId)
  return service({
    url: `/api/graph/delete/${graphId}`,
    method: 'delete',
    params: { project_id: projectId }
  })
}

/**
 * Get simulation templates
 * @returns {Promise}
 */
export function getTemplates() {
  return service({
    url: '/api/graph/templates',
    method: 'get'
  })
}

/**
 * Get project information
 * @param {String} projectId - Project ID
 * @returns {Promise}
 */
export function getProject(projectId) {
  return service({
    url: `/api/graph/project/${projectId}`,
    method: 'get'
  })
}
