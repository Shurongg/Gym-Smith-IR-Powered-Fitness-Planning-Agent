import { useState } from 'react'
import '../styles/pixel.css'

export default function IrProcessPanel({ irProcess }) {
  const [open, setOpen] = useState(false)
  if (!irProcess) return null

  const { plan_reasoning, exercises_retrieved, exercises_after_filter,
          web_exercise_searches, training_rules_used, nutrition_rules_used,
          web_searches, memory_loaded } = irProcess

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
          <Section title="1. AGENT REASONING (STAGE 1)">
            {plan_reasoning ? (
              <ReasoningView reasoning={plan_reasoning} />
            ) : (
              <span style={{ color: 'var(--text-muted)' }}>No reasoning captured.</span>
            )}
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
            {(web_exercise_searches || []).length > 0 && (
              <div style={{ marginTop: '6px' }}>
                <span style={{ color: 'var(--warning)', fontSize: '14px' }}>
                  ⚡ Web fallback used ({web_exercise_searches.length} search{web_exercise_searches.length > 1 ? 'es' : ''}):
                </span>
                {web_exercise_searches.map(q => (
                  <span key={q} className="tag" style={{ background: 'var(--warning-soft)', fontSize: '13px' }}>{q}</span>
                ))}
              </div>
            )}
          </Section>

          <Section title="4. TRAINING RULES USED">
            <ul style={{ paddingLeft: '16px' }}>
              {(training_rules_used || []).map(r => <li key={r}>{r}</li>)}
            </ul>
          </Section>

          <Section title="5. NUTRITION RULES + WEB SEARCH">
            <ul style={{ paddingLeft: '16px' }}>
              {(nutrition_rules_used || []).map(r => <li key={r}>{r}</li>)}
            </ul>
            {(web_searches || []).length > 0 && (
              <div style={{ marginTop: '4px' }}>
                <span style={{ color: 'var(--warning)', fontSize: '14px' }}>⚡ Nutrition web searches:</span>
                {web_searches.map(q => (
                  <span key={q} className="tag" style={{ background: 'var(--warning-soft)', fontSize: '13px' }}>{q}</span>
                ))}
              </div>
            )}
          </Section>

          <Section title="6. MEMORY LOADED">
            {memory_loaded ? (
              <pre style={{ background: 'var(--bg-soft)', padding: '8px', border: '1px solid var(--wood-soft)',
                            fontSize: '14px', overflow: 'auto', color: 'var(--text)' }}>
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

function formatCardioFrequency(freq) {
  if (freq === 'every_day') return 'every training day'
  if (freq === 'off_days') return 'on rest days'
  if (freq && Array.isArray(freq.days)) return `on day ${freq.days.join(', ')}`
  return String(freq)
}

function ReasoningView({ reasoning }) {
  const {
    interpreted_goal, target_muscles, training_split,
    frequency_per_week, intensity, intensity_reasoning,
    sets_reps_scheme, scheme_reasoning, daily_cardio,
  } = reasoning

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {interpreted_goal && (
        <Field label="INTERPRETED GOAL" value={interpreted_goal} />
      )}
      {target_muscles?.length > 0 && (
        <div>
          <FieldLabel>TARGET MUSCLES</FieldLabel>
          <div>{target_muscles.map(m => <span key={m} className="tag">{m}</span>)}</div>
        </div>
      )}
      {training_split?.length > 0 && (
        <div>
          <FieldLabel>TRAINING SPLIT ({frequency_per_week || training_split.length} days/week)</FieldLabel>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '4px', marginTop: '4px' }}>
            {training_split.map((d, i) => (
              <div key={i} style={{
                padding: '6px 8px', background: 'var(--secondary-soft)',
                border: '1px dashed var(--secondary)', fontSize: '15px',
              }}>
                <strong>{d.day}</strong> — <em>{d.focus}</em>
                {d.exercises_count != null && (
                  <span style={{ color: 'var(--text-muted)' }}> · {d.exercises_count} exercises</span>
                )}
                {d.muscles?.length > 0 && (
                  <div style={{ marginTop: '2px' }}>
                    {d.muscles.map(m => (
                      <span key={m} style={{
                        fontSize: '13px', marginRight: '4px', color: 'var(--text-muted)',
                      }}>{m}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      {intensity && (
        <Field
          label="INTENSITY"
          value={`${intensity}${intensity_reasoning ? ` — ${intensity_reasoning}` : ''}`}
        />
      )}
      {sets_reps_scheme && (
        <Field
          label="SETS / REPS SCHEME"
          value={`${sets_reps_scheme}${scheme_reasoning ? ` — ${scheme_reasoning}` : ''}`}
        />
      )}
      {daily_cardio && (
        <div>
          <FieldLabel>SUPPLEMENTARY CARDIO</FieldLabel>
          <div style={{
            padding: '6px 8px', background: 'var(--warning-soft)',
            border: '1px dashed var(--primary)', fontSize: '15px',
          }}>
            <strong>{daily_cardio.protocol}</strong>
            {daily_cardio.equipment && (
              <span style={{ color: 'var(--text-muted)' }}> · {daily_cardio.equipment}</span>
            )}
            <div style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '2px' }}>
              Schedule: {formatCardioFrequency(daily_cardio.frequency)}
            </div>
            {daily_cardio.reasoning && (
              <div style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '2px' }}>
                {daily_cardio.reasoning}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function Field({ label, value }) {
  return (
    <div>
      <FieldLabel>{label}</FieldLabel>
      <div style={{ fontSize: '15px' }}>{value}</div>
    </div>
  )
}

function FieldLabel({ children }) {
  return (
    <div style={{
      fontFamily: 'var(--font-title)', fontSize: '0.42rem',
      color: 'var(--text-muted)', marginBottom: '2px',
    }}>
      {children}
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
