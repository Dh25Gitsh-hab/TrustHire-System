/**
 * useHealth — asks the backend's GET /api/health whether it is running and
 * which optional services (database, web search, AI) are connected.
 *
 * Returns { state: 'checking' | 'online' | 'offline', services, refresh }.
 */
import { useCallback, useEffect, useState } from 'react'
import { getHealth } from '../services/api.js'

export default function useHealth() {
  const [state, setState] = useState('checking')
  const [services, setServices] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const data = await getHealth()
      setServices(data)
      setState(data?.status === 'ok' ? 'online' : 'offline')
    } catch {
      setServices(null)
      setState('offline')
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { state, services, refresh }
}
