import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import {
  getCurrentUser,
  login as loginRequest,
  logout as clearSession,
  register as registerRequest,
  changePassword as changePasswordRequest,
} from '../services/authService'
import { getMyProfile } from '../services/facultyService'
import { clearToken, getToken, setToken } from '../utils/auth'

const AuthContext = createContext(null)

async function loadProfile(currentUser) {
  if (!currentUser?.faculty_id) return null
  try {
    const { data } = await getMyProfile()
    return data
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(Boolean(getToken()))

  const refreshUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null)
      setProfile(null)
      setLoading(false)
      return null
    }
    try {
      const { data } = await getCurrentUser()
      setUser(data)
      setProfile(await loadProfile(data))
      return data
    } catch {
      clearToken()
      setUser(null)
      setProfile(null)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshUser()
  }, [refreshUser])

  const login = useCallback(async (email, password) => {
    const { data } = await loginRequest(email, password)
    setToken(data.access_token)
    try {
      const { data: currentUser } = await getCurrentUser()
      setUser(currentUser)
      setProfile(await loadProfile(currentUser))
      return currentUser
    } catch (error) {
      clearToken()
      setUser(null)
      setProfile(null)
      throw error
    }
  }, [])

  const register = useCallback(async (payload) => {
    const { data } = await registerRequest(payload)
    return data
  }, [])

  const changePassword = useCallback(
    async (newPassword, confirmPassword) => {
      const { data } = await changePasswordRequest(newPassword, confirmPassword)
      await refreshUser()
      return data
    },
    [refreshUser],
  )

  const logout = useCallback(() => {
    clearSession()
    setUser(null)
    setProfile(null)
  }, [])

  const value = useMemo(
    () => ({
      user,
      profile,
      loading,
      isAuthenticated: Boolean(user),
      login,
      register,
      changePassword,
      logout,
      refreshUser,
    }),
    [user, profile, loading, login, register, changePassword, logout, refreshUser],
  )

  return createElement(AuthContext.Provider, { value }, children)
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
