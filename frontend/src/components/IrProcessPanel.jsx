import { useState } from 'react'
import '../styles/pixel.css'

export default function IrProcessPanel({ irProcess }) {
  const [open, setOpen] = useState(false)
  if (!irProcess) return null

  const { parsed_intent, exercises_retrieved, exercises_after_filter,
          training_rules_used, nutrition_rules_used, memory_loaded } = irProcess

  return (
    <div style={{ marginTop: '24px' }}>
      <div
        style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px',
                 fontFamily: 'var(--font-title)', fontSize: '0.6rem', padding: '8px 0',
                 borderTop: 'var(--border)' }}
        onClick={() => setOpen(o => !o)}
      >
        <span>IR PROCESS TRACE</span>
        <span style={{ fontFamily: 'var(--font-body)', fontSize: '18px' }}>{open ? '▲' : '▼'}</span>
      </div>

      {open && (
        <div className="pixel-card" style={{ fontFamily: 'var(--font-body)', fontSize: '16px',
                                              lineHeight: '1.7' }}>
          <Section title="1. PARSED INTENT">
            <pre style={{ background: '#f0f0e8', padding: '8px', border: '1px solid #ccc',
                          fontSize: '14px', overflow: 'auto' }}>
              {JSON.stringify(parsed_intent, null, 2)}
            </pre>
          </Section>

          <Section title="2. EXERCISES RETRIEVED">
            <div>{(exercises_retrieved || []).map(n => <span key={n} className="tag">{n}</span>)}</div>
          </Section>

          <Section title="3. AFTER EQUIPMENT FILTER">
            <div>{(exercises_after_filter || []).map(n => <span key={n} className="tag" style={{ background: 'var(--primary)' }}>{n}</span>)}</div>
            {exercises_retrieved && exercises_after_filter && (
              <div style={{ color: 'var(--text-muted)', marginTop: '4px', fontSize: '15px' }}>
                {exercises_retrieved.length - exercises_after_filter.length} exercises removed by equipment filter
              </div>
            )}
          </Section>

          <Section title="4. TRAINING RULES USED">
            <ul style={{ paddingLeft: '16px' }}>
              {(training_rules_used || []).map(r => <li key={r}>{r}</li>)}
            </ul>
          </Section>

          <Section title="5. NUTRITION RULES USED">
            <ul style={{ paddingLeft: '16px' }}>
              {(nutrition_rules_used || []).map(r => <li key={r}>{r}</li>)}
            </ul>
          </Section>

          <Section title="6. MEMORY LOADED">
            {memory_loaded ? (
              <pre style={{ background: '#f0f0e8', padding: '8px', border: '1px solid #ccc',
                            fontSize: '14px', overflow: 'auto' }}>
                {JSON.stringify(memory_loaded, null, 2)}
              </pre>
            ) : (
              <span style={{ color: 'var(--text-muted)' }}>No previous session found.</span>
            )}
          </Section>
        </div>
      )}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ fontFamily: 'var(--font-title)', fontSize: '0.5rem', marginBottom: '6px',
                    color: 'var(--text-muted)' }}>
        {title}
      </div>
      {children}
    </div>
  )
}
