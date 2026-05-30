import { useState } from 'react'
import '../styles/pixel.css'

function ExerciseRow({ ex }) {
  return (
    <div style={{ padding: '8px 0', borderBottom: '1px dashed #ccc', fontFamily: 'var(--font-body)',
                  fontSize: '17px' }}>
      <div style={{ fontWeight: 'bold' }}>▸ {ex.name}</div>
      <div style={{ color: 'var(--text-muted)', marginTop: '2px' }}>
        {ex.sets} sets × {ex.reps} reps · rest {ex.rest} · {ex.equipment}
      </div>
      {ex.muscles?.length > 0 && (
        <div style={{ marginTop: '2px' }}>
          {ex.muscles.map(m => <span key={m} className="tag">{m}</span>)}
        </div>
      )}
      {ex.alternative && (
        <div style={{ color: 'var(--text-muted)', fontSize: '15px', marginTop: '2px' }}>
          Alt: {ex.alternative}
        </div>
      )}
    </div>
  )
}

export default function PlanCard({ day }) {
  const [open, setOpen] = useState(true)

  return (
    <div className="pixel-card" style={{ marginBottom: '16px' }}>
      <div
        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                 cursor: 'pointer', marginBottom: open ? '12px' : '0' }}
        onClick={() => setOpen(o => !o)}
      >
        <h3 style={{ fontSize: '0.7rem' }}>{day.day} — {day.focus}</h3>
        <span style={{ fontFamily: 'var(--font-body)', fontSize: '20px' }}>{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div>
          {day.exercises.map((ex, i) => <ExerciseRow key={i} ex={ex} />)}
        </div>
      )}
    </div>
  )
}
