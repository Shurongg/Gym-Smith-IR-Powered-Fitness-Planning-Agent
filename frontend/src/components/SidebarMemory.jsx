import { useState } from 'react'
import '../styles/pixel.css'
import PixelButton from './PixelButton'

const LEVELS = ['beginner', 'intermediate', 'advanced']

/* ───────── Helpers ───────── */

function timeAgo(isoStr) {
  if (!isoStr) return '—'
  const diff = Math.floor((Date.now() - new Date(isoStr + 'Z')) / 1000)
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  const d = Math.floor(diff / 86400)
  return d === 1 ? '1 day ago' : `${d} days ago`
}

function aggregateStats(history) {
  /* Count muscles and equipment across every exercise in every history plan. */
  const muscleCount = new Map()
  const equipCount = new Map()
  for (const h of history || []) {
    const days = h?.plan?.weekly_schedule || []
    for (const day of days) {
      for (const ex of (day.exercises || [])) {
        for (const m of (ex.muscles || [])) {
          if (!m) continue
          const key = String(m).toLowerCase()
          muscleCount.set(key, (muscleCount.get(key) || 0) + 1)
        }
        if (ex.equipment) {
          const key = String(ex.equipment).toLowerCase()
          equipCount.set(key, (equipCount.get(key) || 0) + 1)
        }
      }
    }
  }
  const top3 = (m) => [...m.entries()]
    .sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k]) => k)
  return {
    totalPlans: (history || []).length,
    topMuscles: top3(muscleCount),
    topEquipment: top3(equipCount),
  }
}

/* ───────── Subcomponents ───────── */

function SectionLabel({ children }) {
  return (
    <h3 style={{
      fontSize: '0.5rem', marginBottom: '8px',
      color: 'var(--text-muted)', letterSpacing: '0.05em',
    }}>{children}</h3>
  )
}

function IdentitySection({ nickname, trainingLevel, onUpdate }) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(nickname || '')
  const [level, setLevel] = useState(trainingLevel || 'intermediate')

  function save() {
    const trimmed = name.trim()
    if (!trimmed) return
    onUpdate(trimmed, level)
    setEditing(false)
  }

  return (
    <div style={{ marginBottom: '18px' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px',
      }}>
        <div style={{
          width: '40px', height: '40px',
          background: 'var(--bg-soft)', border: 'var(--border-soft)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '22px', flexShrink: 0,
        }}>
          🌱
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{
            fontFamily: 'var(--font-title)', fontSize: '0.55rem',
            color: 'var(--text)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            Hi, {nickname || 'friend'}!
          </div>
          <div
            onClick={() => setEditing(e => !e)}
            title="Click to edit"
            style={{
              fontFamily: 'var(--font-body)', fontSize: '14px',
              color: 'var(--text-muted)', cursor: 'pointer',
              textDecoration: editing ? 'underline' : 'none',
            }}
          >
            Level: <strong style={{ color: 'var(--text)' }}>{trainingLevel || '—'}</strong>
            <span style={{ marginLeft: '4px', fontSize: '12px' }}>✎</span>
          </div>
        </div>
      </div>

      {editing && (
        <div style={{
          padding: '10px', background: 'var(--bg-soft)',
          border: 'var(--border-soft)', marginTop: '6px',
        }}>
          <input
            className="pixel-input"
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            maxLength={40}
            style={{ marginBottom: '8px', fontSize: '14px', padding: '6px 8px' }}
            placeholder="Your name"
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '8px' }}>
            {LEVELS.map(l => (
              <button
                key={l}
                onClick={() => setLevel(l)}
                style={{
                  fontFamily: 'var(--font-body)', fontSize: '14px',
                  padding: '4px 8px', textAlign: 'left', cursor: 'pointer',
                  background: level === l ? 'var(--secondary-soft)' : 'var(--bg-card)',
                  border: level === l ? 'var(--border-strong)' : 'var(--border-soft)',
                  color: 'var(--text)',
                }}
              >{l}</button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              onClick={save}
              style={{
                flex: 1, fontFamily: 'var(--font-title)', fontSize: '0.4rem',
                padding: '4px 8px', background: 'var(--primary)', color: 'var(--bg-card)',
                border: 'var(--border-strong)', cursor: 'pointer',
              }}
            >SAVE</button>
            <button
              onClick={() => { setEditing(false); setName(nickname || ''); setLevel(trainingLevel || 'intermediate') }}
              style={{
                flex: 1, fontFamily: 'var(--font-title)', fontSize: '0.4rem',
                padding: '4px 8px', background: 'transparent', color: 'var(--text-muted)',
                border: '1px dashed var(--wood-soft)', cursor: 'pointer',
              }}
            >CANCEL</button>
          </div>
        </div>
      )}
    </div>
  )
}

function PinnedPlanSection({ pinnedPlan, onClick, onUnpin }) {
  if (!pinnedPlan) {
    return (
      <div style={{ marginBottom: '18px' }}>
        <SectionLabel>★ PINNED PLAN</SectionLabel>
        <p style={{
          fontFamily: 'var(--font-body)', fontSize: '14px',
          color: 'var(--text-muted)', fontStyle: 'italic',
          padding: '8px', border: '1px dashed var(--wood-soft)',
          background: 'var(--bg-soft)',
        }}>
          No pinned plan — click ★ on any plan to pin.
        </p>
      </div>
    )
  }

  const r = pinnedPlan.plan_reasoning || {}
  const title = r.interpreted_goal || pinnedPlan.user_input || 'Plan'
  const intensity = r.intensity
  const freq = r.frequency_per_week || r.training_split?.length
  const muscles = (r.target_muscles || []).slice(0, 3)
  const cardio = r.daily_cardio

  return (
    <div style={{ marginBottom: '18px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <SectionLabel>★ PINNED PLAN</SectionLabel>
        <button
          onClick={(e) => { e.stopPropagation(); onUnpin() }}
          title="Unpin"
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-muted)', fontSize: '14px', padding: 0,
            marginBottom: '8px',
          }}
        >✕</button>
      </div>
      <div
        onClick={onClick}
        style={{
          cursor: 'pointer', padding: '10px',
          background: 'var(--secondary-soft)',
          border: 'var(--border-soft)', boxShadow: 'var(--shadow-sm)',
          fontFamily: 'var(--font-body)',
        }}
      >
        <div style={{
          fontWeight: 'bold', fontSize: '15px', color: 'var(--text)',
          marginBottom: '6px', lineHeight: 1.3,
          overflow: 'hidden', display: '-webkit-box',
          WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
        }}>
          {title}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '4px' }}>
          {intensity && (
            <span style={{
              fontSize: '12px', padding: '1px 6px',
              background: 'var(--primary)', color: 'var(--bg-card)',
              border: '1px solid var(--wood-dark)',
              fontFamily: 'var(--font-title)',
            }}>{intensity.toUpperCase()}</span>
          )}
          {freq && (
            <span style={{
              fontSize: '12px', padding: '1px 6px',
              background: 'var(--bg-card)', color: 'var(--text)',
              border: '1px solid var(--wood-soft)',
              fontFamily: 'var(--font-title)',
            }}>{freq}×/WK</span>
          )}
        </div>
        {muscles.length > 0 && (
          <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            💪 {muscles.join(' · ')}{(r.target_muscles?.length || 0) > 3 ? '…' : ''}
          </div>
        )}
        {cardio && (
          <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>
            🏃 {cardio.protocol}
          </div>
        )}
      </div>
    </div>
  )
}

function ActivitySection({ stats, lastSession }) {
  return (
    <div style={{ marginBottom: '18px' }}>
      <SectionLabel>ACTIVITY</SectionLabel>
      <div style={{ fontFamily: 'var(--font-body)', fontSize: '14px',
                    lineHeight: 1.7, color: 'var(--text-body)' }}>
        <div>📋 <strong>{stats.totalPlans}</strong> plans generated</div>
        {stats.topMuscles.length > 0 && (
          <div title={stats.topMuscles.join(', ')}>
            💪 Top muscles: <strong style={{ color: 'var(--text)' }}>
              {stats.topMuscles.join(' · ')}
            </strong>
          </div>
        )}
        {stats.topEquipment.length > 0 && (
          <div title={stats.topEquipment.join(', ')}>
            🏋 Top equipment: <strong style={{ color: 'var(--text)' }}>
              {stats.topEquipment.join(' · ')}
            </strong>
          </div>
        )}
        {lastSession && (
          <div style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '2px' }}>
            ⏱ Last: {timeAgo(lastSession)}
          </div>
        )}
      </div>
    </div>
  )
}

function HistorySection({ history, activePlanId, pinnedPlanId,
                         onHistoryClick, onHistoryDelete, onPinHistory }) {
  const [hoveredId, setHoveredId] = useState(null)

  if (!history || history.length === 0) {
    return (
      <div style={{ marginBottom: '18px' }}>
        <SectionLabel>HISTORY</SectionLabel>
        <p style={{ fontFamily: 'var(--font-body)', fontSize: '14px',
                    color: 'var(--text-muted)' }}>
          No history yet.
        </p>
      </div>
    )
  }

  return (
    <div style={{ marginBottom: '18px' }}>
      <SectionLabel>HISTORY</SectionLabel>
      <ul style={{ listStyle: 'none', fontFamily: 'var(--font-body)', fontSize: '14px' }}>
        {history.map(h => {
          const isActive = h.id === activePlanId
          const isPinned = h.id === pinnedPlanId
          const isHovered = h.id === hoveredId
          return (
            <li
              key={h.id}
              title={h.user_input}
              onClick={() => onHistoryClick && onHistoryClick(h)}
              onMouseEnter={() => setHoveredId(h.id)}
              onMouseLeave={() => setHoveredId(null)}
              style={{
                padding: '5px 4px',
                borderBottom: '1px dashed var(--wood-soft)',
                cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: '4px',
                background: isActive ? 'var(--secondary-soft)'
                  : isHovered ? 'var(--bg-soft)' : 'transparent',
                transition: 'background 0.1s',
              }}
            >
              <span style={{
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                color: isActive ? 'var(--text)' : 'var(--text-muted)',
                flex: 1,
              }}>
                · {h.user_input.slice(0, 20)}{h.user_input.length > 20 ? '…' : ''}
              </span>
              {(isHovered || isActive || isPinned) && (
                <>
                  <button
                    onClick={e => { e.stopPropagation(); onPinHistory && onPinHistory(h.id) }}
                    title={isPinned ? 'Unpin' : 'Pin'}
                    style={{
                      background: 'none', border: 'none', cursor: 'pointer',
                      color: isPinned ? 'var(--primary)' : 'var(--text-muted)',
                      fontSize: '14px', lineHeight: 1, padding: '0 2px',
                    }}
                  >{isPinned ? '★' : '☆'}</button>
                  <button
                    onClick={e => { e.stopPropagation(); onHistoryDelete && onHistoryDelete(h.id) }}
                    title="Delete"
                    style={{
                      background: 'none', border: 'none', cursor: 'pointer',
                      color: 'var(--warning)', fontSize: '14px', lineHeight: 1,
                      padding: '0 2px',
                    }}
                  >×</button>
                </>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

/* ───────── Main ───────── */

export default function SidebarMemory({
  memory, history,
  onNewPlan, onHistoryClick, onHistoryDelete, activePlanId,
  onIdentityUpdate, onPinHistory, onLoadPinned, onUnpin,
}) {
  const stats = aggregateStats(history)
  const pinnedPlanId = memory?.pinned_plan_id
  const pinnedPlan = pinnedPlanId
    ? (history || []).find(h => h.id === pinnedPlanId)
    : null
  const lastSession = history && history.length > 0 ? history[0].created_at : null

  return (
    <div style={{
      width: '230px', minHeight: '100vh',
      borderRight: 'var(--border-soft)',
      background: 'var(--bg-card)', padding: '16px',
      flexShrink: 0, display: 'flex', flexDirection: 'column',
    }}>
      <IdentitySection
        nickname={memory?.nickname}
        trainingLevel={memory?.training_level}
        onUpdate={onIdentityUpdate}
      />

      {/* Primary action — placed high so it's always visible without scrolling */}
      <div style={{ marginBottom: '18px' }}>
        <PixelButton onClick={onNewPlan} style={{ width: '100%' }}>
          + NEW PLAN
        </PixelButton>
      </div>

      <PinnedPlanSection
        pinnedPlan={pinnedPlan}
        onClick={() => pinnedPlan && onLoadPinned && onLoadPinned(pinnedPlan)}
        onUnpin={onUnpin}
      />

      <ActivitySection stats={stats} lastSession={lastSession} />

      <HistorySection
        history={history}
        activePlanId={activePlanId}
        pinnedPlanId={pinnedPlanId}
        onHistoryClick={onHistoryClick}
        onHistoryDelete={onHistoryDelete}
        onPinHistory={onPinHistory}
      />
    </div>
  )
}
