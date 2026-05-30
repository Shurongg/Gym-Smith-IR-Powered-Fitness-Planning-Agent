import { useState } from 'react'
import { validateKey, createSession } from '../api'
import PixelButton from '../components/PixelButton'
import '../styles/pixel.css'

export default function ApiKeyPage({ onConnected }) {
  const [key, setKey] = useState('')
  const [status, setStatus] = useState(null) // null | 'loading' | 'ok' | 'error'
  const [message, setMessage] = useState('')

  async function handleConnect() {
    if (!key.trim()) return
    setStatus('loading')
    setMessage('')
    try {
      const result = await validateKey(key.trim())
      if (result.valid) {
        let token = localStorage.getItem('gym_smith_token')
        if (!token) {
          const session = await createSession()
          token = session.session_token
          localStorage.setItem('gym_smith_token', token)
        }
        setStatus('ok')
        setTimeout(() => onConnected(key.trim(), token), 600)
      } else {
        setStatus('error')
        setMessage(result.message || 'Invalid API key')
      }
    } catch {
      setStatus('error')
      setMessage('Could not reach the server.')
    }
  }

  const dumbbell = '🏋'

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', padding: '24px',
      background: 'var(--bg)',
    }}>
      {/* Decorative pixel icons */}
      <div style={{ fontSize: '2rem', marginBottom: '8px', letterSpacing: '12px' }}>
        {dumbbell} {dumbbell} {dumbbell}
      </div>

      <div className="pixel-card" style={{ width: '100%', maxWidth: '480px' }}>
        <h1 style={{ textAlign: 'center', marginBottom: '8px', fontSize: '1.2rem' }}>
          GYM SMITH
        </h1>
        <p style={{ fontFamily: 'var(--font-body)', fontSize: '18px', textAlign: 'center',
                    color: 'var(--text-muted)', marginBottom: '24px' }}>
          Your IR-Powered Fitness Planner
        </p>

        <label style={{ fontFamily: 'var(--font-title)', fontSize: '0.6rem',
                        display: 'block', marginBottom: '8px' }}>
          OPENAI API KEY
        </label>
        <input
          className="pixel-input"
          type="password"
          placeholder="sk-..."
          value={key}
          onChange={e => setKey(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleConnect()}
          style={{ marginBottom: '16px' }}
        />

        <PixelButton
          onClick={handleConnect}
          disabled={status === 'loading' || !key.trim()}
          style={{ width: '100%', justifyContent: 'center' }}
        >
          {status === 'loading' ? 'CONNECTING...' : status === 'ok' ? '✓ CONNECTED!' : '[ CONNECT ]'}
        </PixelButton>

        {status === 'error' && (
          <div className="warning-box" style={{ marginTop: '16px', fontSize: '16px' }}>
            ✗ {message}
          </div>
        )}

        {status === 'ok' && (
          <div style={{ marginTop: '16px', padding: '10px', background: '#e8f8e8',
                        border: '2px solid var(--primary)', fontSize: '16px',
                        fontFamily: 'var(--font-body)' }}>
            ✓ Connected! Loading your workspace...
          </div>
        )}
      </div>

      <p style={{ marginTop: '16px', fontFamily: 'var(--font-body)', fontSize: '14px',
                  color: 'var(--text-muted)', textAlign: 'center' }}>
        Your key is never stored on the server.
      </p>
    </div>
  )
}
