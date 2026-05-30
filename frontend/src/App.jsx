import { useState, useEffect } from 'react'
import ApiKeyPage from './pages/ApiKeyPage'
import MainPage from './pages/MainPage'

export default function App() {
  const [apiKey, setApiKey] = useState(null)
  const [sessionToken, setSessionToken] = useState(null)

  useEffect(() => {
    const token = localStorage.getItem('gym_smith_token')
    const key = sessionStorage.getItem('gym_smith_key')
    if (token && key) {
      setSessionToken(token)
      setApiKey(key)
    }
  }, [])

  function handleConnected(key, token) {
    sessionStorage.setItem('gym_smith_key', key)
    setApiKey(key)
    setSessionToken(token)
  }

  if (!apiKey || !sessionToken) {
    return <ApiKeyPage onConnected={handleConnected} />
  }

  return <MainPage apiKey={apiKey} sessionToken={sessionToken} />
}
