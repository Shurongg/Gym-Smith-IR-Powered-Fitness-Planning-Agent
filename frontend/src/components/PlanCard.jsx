import { useState } from 'react'
import '../styles/pixel.css'

function ExerciseRow({ ex }) {
  return (
    <div style={{
      padding: '8px 0', borderBottom: '1px dashed var(--wood-soft)',
      fontFamily: 'var(--font-body)', fontSize: '16px',
      wordBreak: 'break-word',
    }}>
      <div style={{ fontWeight: 'bold', lineHeight: 1.3 }}>▸ {ex.name}</div>
      <div style={{ color: 'var(--text-muted)', marginTop: '2px', fontSize: '14px' }}>
        {ex.sets} × {ex.reps} · rest {ex.rest} · {ex.equipment}
      </div>
      {ex.muscles?.length > 0 && (
        <div style={{ marginTop: '2px' }}>
          {ex.muscles.map(m => <span key={m} className="tag">{m}</span>)}
        </div>
      )}
      {ex.alternative && (
        <div style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '2px' }}>
          Alt: {ex.alternative}
        </div>
      )}
    </div>
  )
}

export default function PlanCard({ day }) {
  const [open, setOpen] = useState(true)

  return (
    <div className="pixel-card" style={{ minWidth: 0 }}>
      <div
        style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          cursor: 'pointer', marginBottom: open ? '10px' : '0', gap: '8px',
        }}
        onClick={() => setOpen(o => !o)}
      >
        <h3 style={{
          fontSize: '0.55rem', lineHeight: 1.4,
          overflow: 'hidden', textOverflow: 'ellipsis',
        }}>{day.day} — {day.focus}</h3>
        <span style={{ fontFamily: 'var(--font-body)', fontSize: '18px', flexShrink: 0 }}>
          {open ? '▲' : '▼'}
        </span>
      </div>
      {open && (
        <div>
          {day.exercises.map((ex, i) => <ExerciseRow key={i} ex={ex} />)}
        </div>
      )}
    </div>
  )
}
