import { useState, useEffect } from 'react'
import IdentityPage from './pages/IdentityPage'
import ApiKeyPage from './pages/ApiKeyPage'
import MainPage from './pages/MainPage'
import { getSession } from './api'

export default function App() {
  const [token, setToken] = useState(null)
  const [hasIdentity, setHasIdentity] = useState(false)
  const [apiKey, setApiKey] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const t = localStorage.getItem('gym_smith_token')
    const k = sessionStorage.getItem('gym_smith_key')
    if (!t) { setLoading(false); return }
    // Probe the token against the backend; if it's stale (e.g. DB was reset),
    // wipe local storage so IdentityPage can mint a fresh session.
    getSession(t)
      .then(s => {
        setToken(t)
        if (k) setApiKey(k)
        if (s?.memory?.nickname) setHasIdentity(true)
      })
      .catch(() => {
        localStorage.removeItem('gym_smith_token')
        sessionStorage.removeItem('gym_smith_key')
        setToken(null)
        setApiKey(null)
        setHasIdentity(false)
      })
      .finally(() => setLoading(false))
  }, [])

  function handleIdentitySet(newToken) {
    setToken(newToken)
    setHasIdentity(true)
  }

  function handleKeyConnected(key, newToken) {
    sessionStorage.setItem('gym_smith_key', key)
    setApiKey(key)
    if (newToken && newToken !== token) setToken(newToken)
  }

  if (loading) return null

  // Onboarding gate 1: identity (name + training level)
  if (!token || !hasIdentity) {
    return <IdentityPage existingToken={token} onIdentitySet={handleIdentitySet} />
  }

  // Onboarding gate 2: OpenAI API key
  if (!apiKey) {
    return <ApiKeyPage onConnected={handleKeyConnected} />
  }

  return <MainPage apiKey={apiKey} sessionToken={token} />
}
