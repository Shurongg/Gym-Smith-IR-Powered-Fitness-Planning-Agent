import { useState } from 'react'
import '../styles/pixel.css'

function cardioLabel(freq) {
  if (freq === 'every_day') return 'every day'
  if (freq === 'off_days') return 'rest days'
  if (freq && Array.isArray(freq.days)) return `day ${freq.days.join(', ')}`
  return ''
}

function StatBlock({ label, value, sub }) {
  if (!value && !sub) return null
  return (
    <div style={{ minWidth: 0 }}>
      <div style={{
        fontFamily: 'var(--font-title)', fontSize: '0.4rem',
        color: 'var(--text-muted)', marginBottom: '2px',
      }}>{label}</div>
      <div style={{
        fontFamily: 'var(--font-body)', fontSize: '16px',
        color: 'var(--text)', lineHeight: 1.4,
      }}>
        <strong>{value}</strong>
        {sub && (
          <span style={{ color: 'var(--text-muted)', fontWeight: 'normal' }}>
            {' '}— {sub}
          </span>
        )}
      </div>
    </div>
  )
}

export default function GoalCardB({ plan, reasoning, isPinned, onPin, onUnpin }) {
  const [showSummary, setShowSummary] = useState(false)
  const r = reasoning || {}

  const goalTitle = r.interpreted_goal || plan?.goal_summary || 'Your training plan'
  const splitDays = r.frequency_per_week || r.training_split?.length
  const intensityValue = r.intensity ? r.intensity.toUpperCase() : null
  const cardioText = r.daily_cardio
    ? `${r.daily_cardio.protocol}${cardioLabel(r.daily_cardio.frequency) ? `, ${cardioLabel(r.daily_cardio.frequency)}` : ''}`
    : null

  return (
    <div
      className="pixel-card"
      style={{
        marginBottom: '20px',
        background: 'var(--secondary-soft)',
        position: 'relative',
      }}
    >
      {/* Title row with Pin button */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        marginBottom: '12px', gap: '12px',
      }}>
        <div style={{ minWidth: 0, flex: 1 }}>
          <h2 style={{ fontSize: '0.7rem', marginBottom: '6px' }}>GOAL</h2>
          <div style={{
            fontFamily: 'var(--font-body)', fontSize: '19px',
            color: 'var(--text)', lineHeight: 1.4,
          }}>
            {goalTitle}
          </div>
        </div>
        {(onPin || onUnpin) && (
          <button
            onClick={isPinned ? onUnpin : onPin}
            title={isPinned ? 'Unpin from sidebar' : 'Pin to sidebar'}
            style={{
              fontFamily: 'var(--font-title)', fontSize: '0.45rem',
              padding: '6px 10px', cursor: 'pointer',
              background: isPinned ? 'var(--primary)' : 'var(--bg-card)',
              border: 'var(--border-strong)',
              boxShadow: 'var(--shadow-sm)',
              color: isPinned ? 'var(--bg-card)' : 'var(--text)',
              flexShrink: 0,
              transition: 'background 0.1s',
            }}
          >
            {isPinned ? '★ PINNED' : '☆ PIN'}
          </button>
        )}
      </div>

      {/* Divider */}
      <div style={{
        borderTop: '1px dashed var(--wood-soft)', margin: '8px 0 12px',
      }} />

      {/* Two-column stat grid */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px 20px',
        marginBottom: '12px',
      }}>
        <StatBlock
          label="SPLIT"
          value={splitDays ? `${splitDays} days/week` : '—'}
        />
        <StatBlock
          label="INTENSITY"
          value={intensityValue || '—'}
          sub={r.intensity_reasoning}
        />
        <StatBlock
          label="SCHEME"
          value={r.sets_reps_scheme || '—'}
          sub={r.scheme_reasoning}
        />
        <StatBlock
          label="CARDIO"
          value={cardioText || '—'}
          sub={r.daily_cardio?.reasoning}
        />
      </div>

      {/* Target muscles */}
      {r.target_muscles?.length > 0 && (
        <div style={{ marginBottom: '8px' }}>
          <div style={{
            fontFamily: 'var(--font-title)', fontSize: '0.4rem',
            color: 'var(--text-muted)', marginBottom: '4px',
          }}>TARGET</div>
          <div>
            {r.target_muscles.map(m => (
              <span key={m} className="tag">{m}</span>
            ))}
          </div>
        </div>
      )}

      {/* Equipment list (carried over from old goal card behaviour) */}
      {plan?.equipment_needed?.filter(e => e.toLowerCase() !== 'none').length > 0 && (
        <div style={{ marginTop: '8px' }}>
          <div style={{
            fontFamily: 'var(--font-title)', fontSize: '0.4rem',
            color: 'var(--text-muted)', marginBottom: '4px',
          }}>EQUIPMENT</div>
          <div>
            {plan.equipment_needed
              .filter(e => e.toLowerCase() !== 'none')
              .map(e => (
                <span key={e} className="tag" style={{
                  background: 'var(--bg-card)', borderColor: 'var(--wood-soft)',
                }}>{e}</span>
              ))}
          </div>
        </div>
      )}

      {/* Collapsed AI summary */}
      {plan?.goal_summary && plan.goal_summary !== goalTitle && (
        <div style={{ marginTop: '12px' }}>
          <button
            onClick={() => setShowSummary(s => !s)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              fontFamily: 'var(--font-body)', fontSize: '14px',
              color: 'var(--text-muted)', padding: 0,
            }}
          >
            {showSummary ? '▴' : '▾'} See AI's full interpretation
          </button>
          {showSummary && (
            <p style={{
              marginTop: '6px', padding: '8px',
              background: 'var(--bg-card)', border: '1px dashed var(--wood-soft)',
              fontFamily: 'var(--font-body)', fontSize: '15px',
              color: 'var(--text-body)', lineHeight: 1.5,
            }}>
              {plan.goal_summary}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
