import request from './index'

/**
 * Get available models from the configured LLM provider
 * @returns {Promise<Object>}
 */
export function getModels() {
  return request({
    url: '/api/models',
    method: 'get'
  })
}
