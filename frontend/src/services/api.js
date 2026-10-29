import axios from 'axios'
import { clearToken } from '../utils/auth'

const api = axios.create({
  // Relative by default so requests are same-origin and go through the Vite
  // dev proxy (`/api` -> FastAPI). This works regardless of which port Vite
  // uses (5173, 5174, ...) and avoids cross-origin/CORS problems in dev.
  // Set VITE_API_BASE_URL only when the API lives on a different origin
  // (e.g. a production backend).
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

const PUBLIC_PATHS = ['/login', '/register']

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status
    const path = window.location.pathname
    if (status === 401 && !PUBLIC_PATHS.includes(path)) {
      clearToken()
      window.location.assign('/login')
    }
    return Promise.reject(error)
  },
)

export default api
