import { useState } from 'react'
import { createSession, setIdentity } from '../api'
import PixelButton from '../components/PixelButton'
import '../styles/pixel.css'

const LEVELS = [
  { value: 'beginner', label: 'BEGINNER', sub: 'just starting out' },
  { value: 'intermediate', label: 'INTERMEDIATE', sub: '6+ months training' },
  { value: 'advanced', label: 'ADVANCED', sub: 'years of consistent work' },
]

export default function IdentityPage({ existingToken, onIdentitySet }) {
  const [name, setName] = useState('')
  const [level, setLevel] = useState('intermediate')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit() {
    const trimmed = name.trim()
    if (!trimmed || busy) return
    setBusy(true)
    setError('')
    try {
      let token = existingToken || localStorage.getItem('gym_smith_token')
      if (!token) {
        const session = await createSession()
        token = session.session_token
        localStorage.setItem('gym_smith_token', token)
      }
      await setIdentity(token, trimmed, level)
      onIdentitySet(token)
    } catch (e) {
      setError('Could not save — is the backend running?')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', padding: '24px',
      background: 'var(--bg-main)',
    }}>
      {/* Friendly pixel icons */}
      <div style={{ fontSize: '2rem', marginBottom: '8px', letterSpacing: '12px' }}>
        🌱 💪 🌿
      </div>

      <div className="pixel-card" style={{ width: '100%', maxWidth: '520px' }}>
        <h1 style={{ textAlign: 'center', marginBottom: '8px', fontSize: '1.1rem' }}>
          WELCOME TO GYM SMITH
        </h1>
        <p style={{ fontFamily: 'var(--font-body)', fontSize: '18px', textAlign: 'center',
                    color: 'var(--text-body)', marginBottom: '24px' }}>
          Let's get to know you first.
        </p>

        {/* Name */}
        <label style={{ fontFamily: 'var(--font-title)', fontSize: '0.6rem',
                        display: 'block', marginBottom: '8px' }}>
          WHAT'S YOUR NAME?
        </label>
        <input
          className="pixel-input"
          type="text"
          placeholder="e.g. Alex"
          value={name}
          onChange={e => setName(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSubmit()}
          maxLength={40}
          style={{ marginBottom: '20px' }}
          autoFocus
        />

        {/* Training level */}
        <label style={{ fontFamily: 'var(--font-title)', fontSize: '0.6rem',
                        display: 'block', marginBottom: '8px' }}>
          YOUR TRAINING LEVEL
        </label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px',
                      marginBottom: '24px' }}>
          {LEVELS.map(({ value, label, sub }) => {
            const isSelected = level === value
            return (
              <button
                key={value}
                onClick={() => setLevel(value)}
                style={{
                  fontFamily: 'var(--font-body)',
                  textAlign: 'left',
                  padding: '10px 14px',
                  background: isSelected ? 'var(--secondary-soft)' : 'var(--bg-card)',
                  border: isSelected ? 'var(--border-strong)' : 'var(--border-soft)',
                  boxShadow: isSelected ? 'var(--shadow-sm)' : 'none',
                  color: 'var(--text)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'baseline',
                  gap: '12px',
                }}
              >
                <span style={{ fontFamily: 'var(--font-title)', fontSize: '0.55rem' }}>
                  {label}
                </span>
                <span style={{ fontSize: '15px', color: 'var(--text-muted)' }}>
                  · {sub}
                </span>
              </button>
            )
          })}
        </div>

        <PixelButton
          onClick={handleSubmit}
          disabled={busy || !name.trim()}
          style={{ width: '100%', justifyContent: 'center' }}
        >
          {busy ? 'SAVING...' : '[ CONTINUE ]'}
        </PixelButton>

        {error && (
          <div className="warning-box" style={{ marginTop: '16px', fontSize: '16px' }}>
            ✗ {error}
          </div>
        )}
      </div>

      <p style={{ marginTop: '16px', fontFamily: 'var(--font-body)', fontSize: '14px',
                  color: 'var(--text-muted)', textAlign: 'center', maxWidth: '420px' }}>
        Your name stays on your device — we don't track or share anything.
      </p>
    </div>
  )
}
