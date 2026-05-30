import { useState, useEffect, useRef } from 'react'
import { getSession, generatePlan } from '../api'
import SidebarMemory from '../components/SidebarMemory'
import PlanCard from '../components/PlanCard'
import IrProcessPanel from '../components/IrProcessPanel'
import PixelButton from '../components/PixelButton'
import '../styles/pixel.css'

export default function MainPage({ apiKey, sessionToken }) {
  const [sessionData, setSessionData] = useState(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const planRef = useRef(null)

  useEffect(() => {
    getSession(sessionToken).then(setSessionData).catch(() => {})
  }, [sessionToken])

  function handleNewPlan() {
    setResult(null)
    setInput('')
    setError(null)
  }

  async function handleGenerate() {
    if (!input.trim() || loading) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await generatePlan(sessionToken, apiKey, input.trim())
      setResult(data)
      if (!data.is_medical_concern) {
        getSession(sessionToken).then(setSessionData).catch(() => {})
        setTimeout(() => planRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
      }
    } catch (e) {
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const plan = result?.plan
  const irProcess = result?.ir_process

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <SidebarMemory
        memory={sessionData?.memory}
        history={sessionData?.history}
        onNewPlan={handleNewPlan}
      />

      <main style={{ flex: 1, padding: '24px', maxWidth: '800px' }}>
        {/* Header */}
        <div style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '1.5rem' }}>🏋</span>
          <h1 style={{ fontSize: '0.9rem' }}>GYM SMITH</h1>
          <span style={{ fontFamily: 'var(--font-body)', fontSize: '16px',
                         color: 'var(--text-muted)' }}>IR Fitness Planner</span>
        </div>

        {/* Input Area */}
        <div className="pixel-card" style={{ marginBottom: '24px' }}>
          <label style={{ fontFamily: 'var(--font-title)', fontSize: '0.55rem',
                          display: 'block', marginBottom: '8px' }}>
            DESCRIBE YOUR GOAL
          </label>
          <textarea
            className="pixel-input"
            rows={4}
            placeholder="e.g. I want to build arm muscle, 3x/week, I have dumbbells and resistance bands, medium intensity"
            value={input}
            onChange={e => setInput(e.target.value)}
            style={{ resize: 'vertical', marginBottom: '12px' }}
          />
          <PixelButton onClick={handleGenerate} disabled={loading || !input.trim()}>
            {loading ? 'GENERATING...' : '[ GENERATE PLAN ]'}
          </PixelButton>
        </div>

        {/* Error */}
        {error && (
          <div className="warning-box" style={{ marginBottom: '16px' }}>
            {error}
          </div>
        )}

        {/* Medical Concern */}
        {result?.is_medical_concern && (
          <div className="warning-box" style={{ marginBottom: '24px' }}>
            <h3 style={{ marginBottom: '8px', fontSize: '0.6rem' }}>⚠ OUTSIDE SCOPE</h3>
            <p style={{ fontFamily: 'var(--font-body)', fontSize: '17px' }}>
              {result.message}
            </p>
          </div>
        )}

        {/* Plan Output */}
        {plan && (
          <div ref={planRef}>
            {/* Goal Summary */}
            <div className="pixel-card" style={{ marginBottom: '16px', background: '#eef8ee' }}>
              <h2 style={{ fontSize: '0.7rem', marginBottom: '8px' }}>GOAL</h2>
              <p style={{ fontFamily: 'var(--font-body)', fontSize: '18px' }}>
                {plan.goal_summary}
              </p>
              {plan.equipment_needed?.length > 0 && (
                <div style={{ marginTop: '8px' }}>
                  <span style={{ fontFamily: 'var(--font-title)', fontSize: '0.5rem',
                                 color: 'var(--text-muted)' }}>EQUIPMENT: </span>
                  {plan.equipment_needed.map(e => (
                    <span key={e} className="tag">{e}</span>
                  ))}
                </div>
              )}
            </div>

            {/* Weekly Schedule */}
            <h2 style={{ fontSize: '0.7rem', marginBottom: '12px' }}>WEEKLY SCHEDULE</h2>
            {(plan.weekly_schedule || []).map((day, i) => (
              <PlanCard key={i} day={day} />
            ))}

            {/* Nutrition Notes */}
            {plan.nutrition_notes?.length > 0 && (
              <div className="pixel-card" style={{ marginBottom: '16px' }}>
                <h2 style={{ fontSize: '0.7rem', marginBottom: '8px' }}>NUTRITION NOTES</h2>
                <ul style={{ fontFamily: 'var(--font-body)', fontSize: '17px',
                              paddingLeft: '16px', lineHeight: '1.8' }}>
                  {plan.nutrition_notes.map((n, i) => <li key={i}>{n}</li>)}
                </ul>
              </div>
            )}

            {/* Safety Reminder */}
            {plan.safety_reminder && (
              <div style={{ padding: '10px', background: '#fff9f0',
                            border: '1px dashed #ccc', fontFamily: 'var(--font-body)',
                            fontSize: '16px', color: 'var(--text-muted)', marginBottom: '16px' }}>
                ⚠ {plan.safety_reminder}
              </div>
            )}

            {/* IR Process Panel */}
            <IrProcessPanel irProcess={irProcess} />
          </div>
        )}
      </main>
    </div>
  )
}
