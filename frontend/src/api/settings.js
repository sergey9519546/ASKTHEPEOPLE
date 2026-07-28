import request from './index'

/**
 * Get current system configuration settings
 * @returns {Promise<Object>}
 */
export function getSettings() {
  return request({
    url: '/api/settings',
    method: 'get'
  })
}

/**
 * Update system configuration settings
 * @param {Object} data - Configuration settings dict
 * @returns {Promise<Object>}
 */
export function updateSettings(data) {
  return request({
    url: '/api/settings',
    method: 'post',
    data
  })
}

/**
 * Test LLM connection with provided temporary settings
 * @param {Object} data - Settings data to test
 * @returns {Promise<Object>}
 */
export function testConnection(data) {
  return request({
    url: '/api/settings/test',
    method: 'post',
    data
  })
}
