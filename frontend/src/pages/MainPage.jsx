import { useState, useEffect, useRef } from 'react'
import { getSession, generatePlan, deletePlan, pinPlan, unpinPlan, setIdentity, getPlan } from '../api'
import SidebarMemory from '../components/SidebarMemory'
import PlanCard from '../components/PlanCard'
import IrProcessPanel from '../components/IrProcessPanel'
import PixelButton from '../components/PixelButton'
import EquipmentPicker from '../components/EquipmentPicker'
import GoalCardB from '../components/GoalCardB'
import '../styles/pixel.css'

export default function MainPage({ apiKey, sessionToken }) {
  const [sessionData, setSessionData] = useState(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [activePlanId, setActivePlanId] = useState(null)
  const planRef = useRef(null)
  const [selectedEquipment, setSelectedEquipment] = useState([])
  const [specificMachines, setSpecificMachines] = useState([])
  const autoLoadedRef = useRef(false)

  useEffect(() => {
    getSession(sessionToken).then(setSessionData).catch(() => {})
  }, [sessionToken])

  // On first session load, if a pinned plan exists, auto-load it into the main area
  useEffect(() => {
    if (autoLoadedRef.current) return
    const pinId = sessionData?.memory?.pinned_plan_id
    if (!pinId) return
    autoLoadedRef.current = true
    getPlan(pinId, sessionToken).then(p => {
      setResult({
        is_medical_concern: false,
        plan: p.plan,
        plan_id: p.id,
        plan_reasoning: p.plan_reasoning,
        ir_process: null,
      })
      setInput(p.user_input)
      setActivePlanId(p.id)
    }).catch(() => {})
  }, [sessionData, sessionToken])

  useEffect(() => {
    if (!sessionData?.memory) return
    if (sessionData.memory.equipment?.length > 0) {
      setSelectedEquipment(sessionData.memory.equipment)
    }
    if (sessionData.memory.specific_machines?.length > 0) {
      setSpecificMachines(sessionData.memory.specific_machines)
    }
  }, [sessionData])

  function handleNewPlan() {
    setResult(null)
    setInput('')
    setError(null)
    setActivePlanId(null)
  }

  function handleHistoryClick(historyItem) {
    setResult({ is_medical_concern: false, plan: historyItem.plan, ir_process: null })
    setInput(historyItem.user_input)
    setError(null)
    setActivePlanId(historyItem.id)
    setTimeout(() => planRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
  }

  function refreshSession() {
    getSession(sessionToken).then(setSessionData).catch(() => {})
  }

  async function handlePinCurrent() {
    const id = result?.plan_id || activePlanId
    if (!id) return
    try {
      await pinPlan(id, sessionToken)
      refreshSession()
    } catch { /* swallow */ }
  }

  async function handleUnpin() {
    try {
      await unpinPlan(sessionToken)
      refreshSession()
    } catch { /* swallow */ }
  }

  async function handlePinHistory(planId) {
    const currentPinId = sessionData?.memory?.pinned_plan_id
    try {
      if (currentPinId === planId) {
        await unpinPlan(sessionToken)
      } else {
        await pinPlan(planId, sessionToken)
      }
      refreshSession()
    } catch { /* swallow */ }
  }

  async function handleIdentityUpdate(nickname, trainingLevel) {
    try {
      await setIdentity(sessionToken, nickname, trainingLevel)
      refreshSession()
    } catch { /* swallow */ }
  }

  function handleLoadPinned(pinnedHistoryEntry) {
    setResult({
      is_medical_concern: false,
      plan: pinnedHistoryEntry.plan,
      plan_id: pinnedHistoryEntry.id,
      plan_reasoning: pinnedHistoryEntry.plan_reasoning,
      ir_process: null,
    })
    setInput(pinnedHistoryEntry.user_input)
    setError(null)
    setActivePlanId(pinnedHistoryEntry.id)
    setTimeout(() => planRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
  }

  async function handleHistoryDelete(planId) {
    try {
      await deletePlan(planId, sessionToken)
      if (activePlanId === planId) {
        setResult(null)
        setInput('')
        setActivePlanId(null)
      }
      getSession(sessionToken).then(setSessionData).catch(() => {})
    } catch {
      // silently ignore
    }
  }

  async function handleGenerate() {
    if (!input.trim() || loading) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await generatePlan(sessionToken, apiKey, input.trim(), selectedEquipment, specificMachines)
      setResult(data)
      setActivePlanId(null)
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
        onHistoryClick={handleHistoryClick}
        onHistoryDelete={handleHistoryDelete}
        activePlanId={activePlanId}
        onIdentityUpdate={handleIdentityUpdate}
        onPinHistory={handlePinHistory}
        onLoadPinned={handleLoadPinned}
        onUnpin={handleUnpin}
      />

      <main style={{ flex: 1, padding: '24px', maxWidth: '1200px' }}>
        {/* Hero block — title is baked into hero.png */}
        <div style={{ marginBottom: '20px' }}>
          <img
            src="/hero.png"
            alt="GymSmith — pixel-art fitness workshop"
            style={{
              width: '100%',
              maxWidth: '1200px',
              height: 'auto',
              display: 'block',
              imageRendering: 'pixelated',
              border: 'var(--border-soft)',
              boxShadow: 'var(--shadow)',
            }}
          />
          <p style={{
            marginTop: '6px', textAlign: 'center',
            fontFamily: 'var(--font-body)', fontSize: '15px',
            color: 'var(--text-muted)',
          }}>
            IR Fitness Planner
          </p>
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
            placeholder="e.g. I want to build arm muscle, 3x/week, medium intensity"
            value={input}
            onChange={e => setInput(e.target.value)}
            style={{ resize: 'vertical', marginBottom: '12px' }}
          />
          <EquipmentPicker
            selected={selectedEquipment}
            specificMachines={specificMachines}
            onChange={(eq, machines) => { setSelectedEquipment(eq); setSpecificMachines(machines) }}
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
            {/* Goal Card — structured B layout */}
            <GoalCardB
              plan={plan}
              reasoning={result?.plan_reasoning}
              isPinned={
                (result?.plan_id && sessionData?.memory?.pinned_plan_id === result.plan_id) ||
                (activePlanId && sessionData?.memory?.pinned_plan_id === activePlanId)
              }
              onPin={handlePinCurrent}
              onUnpin={handleUnpin}
            />

            {/* Weekly Schedule */}
            <h2 style={{ fontSize: '0.7rem', marginBottom: '12px' }}>WEEKLY SCHEDULE</h2>
            <div className="weekly-grid">
              {(plan.weekly_schedule || []).map((day, i) => (
                <PlanCard key={i} day={day} />
              ))}
            </div>

            {/* Nutrition + Safety — side-by-side on wide screens */}
            {(plan.nutrition_notes?.length > 0 || plan.safety_reminder) && (
              <div className="aux-grid">
                {plan.nutrition_notes?.length > 0 && (
                  <div className="pixel-card">
                    <h2 style={{ fontSize: '0.7rem', marginBottom: '8px' }}>NUTRITION NOTES</h2>
                    <ul style={{ fontFamily: 'var(--font-body)', fontSize: '16px',
                                  paddingLeft: '16px', lineHeight: '1.7' }}>
                      {plan.nutrition_notes.map((n, i) => <li key={i}>{n}</li>)}
                    </ul>
                  </div>
                )}
                {plan.safety_reminder && (
                  <div className="pixel-card" style={{ background: 'var(--warning-soft)' }}>
                    <h2 style={{ fontSize: '0.7rem', marginBottom: '8px' }}>⚠ SAFETY</h2>
                    <p style={{ fontFamily: 'var(--font-body)', fontSize: '16px',
                                color: 'var(--text-body)', lineHeight: 1.6 }}>
                      {plan.safety_reminder}
                    </p>
                  </div>
                )}
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
