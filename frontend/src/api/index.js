import axios from 'axios'
import { getAccessKey, requireAccess } from '../composables/useAccessKey.js'

const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.DEV ? 'http://localhost:5001' : '')

// Create Axios instance
const service = axios.create({
  baseURL: apiBaseUrl,
  timeout: 300000, // 5 minute timeout (ontology generation can take a while)
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor — attach bearer token when one is available.
service.interceptors.request.use(
  config => {
    // A deployment access key is entered at runtime and lives only for this
    // browser tab. Never bundle one into the Vite build: client-side
    // environment variables are public by definition.
    const accessKey = getAccessKey()
    if (accessKey) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${accessKey}`
    }
    return config
  },
  error => {
    if (import.meta.env.DEV) console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor (with error tolerance)
service.interceptors.response.use(
  response => {
    // Global safety net: normalize null / non-object responses so downstream
    // views never crash on unexpected API shapes (NoneType bug, plain string,
    // HTML error page from a proxy, or any other non-object primitive).
    if (response.data == null || typeof response.data !== 'object') {
      response.data = { success: false, error: 'empty_response' }
    }
    const res = response.data

    // Some models (e.g. stepfun) return a null content field; normalize it so
    // views can safely render it as an empty string.
    if (res.content == null) res.content = ''

    // If the response status is not success, reject the promise
    if (!res.success && res.success !== undefined) {
      if (import.meta.env.DEV) {
        console.error('API Error:', res.error || res.message || 'Unknown error')
      }
      return Promise.reject(new Error(res.error || res.message || 'Error'))
    }
    
    return res
  },
  error => {
    // Axios error objects can carry the request configuration, including the
    // in-memory Authorization header. Never place them in production consoles.
    if (import.meta.env.DEV) console.error('Response error:', error)

    if (error.response?.status === 401) {
      requireAccess('The access key is missing or was not accepted.')
      const accessError = new Error('Access key required or invalid.')
      accessError.code = 'ACCESS_REQUIRED'
      accessError.status = 401
      return Promise.reject(accessError)
    }

    // Handle timeout
    if (error.code === 'ECONNABORTED' && error.message.includes('timeout')) {
      if (import.meta.env.DEV) console.error('Request timeout')
    }

    // Handle network error
    if (error.message === 'Network Error') {
      if (import.meta.env.DEV) {
        console.error('Network error - please check your connection')
      }
    }

    return Promise.reject(error)
  }
)

export default service
