import axios from 'axios'

// Build-time app token (single-user deploy). Read once at module load.
// localStorage (runtime token, e.g. from a future login/setup screen) is read
// lazily inside the request interceptor since it can change at runtime.
const VITE_APP_TOKEN = import.meta.env.VITE_APP_TOKEN || ''

// Create Axios instance
const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:5001',
  timeout: 300000, // 5 minute timeout (ontology generation can take a while)
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor — attach bearer token when one is available.
service.interceptors.request.use(
  config => {
    // Token sources, in priority order:
    //   1. localStorage.app_token  (set at runtime, e.g. from a login/setup screen — future)
    //   2. import.meta.env.VITE_APP_TOKEN  (build-time env, clean for single-user deploy)
    const APP_TOKEN = localStorage.getItem('app_token') || VITE_APP_TOKEN
    if (APP_TOKEN) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${APP_TOKEN}`
    }
    return config
  },
  error => {
    console.error('Request error:', error)
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
      console.error('API Error:', res.error || res.message || 'Unknown error')
      return Promise.reject(new Error(res.error || res.message || 'Error'))
    }
    
    return res
  },
  error => {
    console.error('Response error:', error)

    // Handle 401 Unauthorized: the backend has opt-in bearer-token auth
    // (APP_TOKEN). A 401 means no/invalid token was attached. The global crash
    // handler surfaces user-facing messaging; here we just log in dev.
    if (error.response?.status === 401) {
      if (import.meta.env.DEV) console.warn('API returned 401 Unauthorized — a valid app token may be required (APP_TOKEN).')
    }

    // Handle timeout
    if (error.code === 'ECONNABORTED' && error.message.includes('timeout')) {
      console.error('Request timeout')
    }

    // Handle network error
    if (error.message === 'Network Error') {
      console.error('Network error - please check your connection')
    }

    return Promise.reject(error)
  }
)

// Request function with exponential backoff retry
export const requestWithRetry = async (requestFn, maxRetries = 3, delay = 1000) => {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await requestFn()
    } catch (error) {
      if (i === maxRetries - 1) throw error
      
      console.warn(`Request failed, retrying (${i + 1}/${maxRetries})...`)
      await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)))
    }
  }
}

export default service
