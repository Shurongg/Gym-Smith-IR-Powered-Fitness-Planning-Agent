import '../styles/pixel.css'
import PixelButton from './PixelButton'

export default function SidebarMemory({ memory, history, onNewPlan }) {
  return (
    <div style={{
      width: '220px', minHeight: '100vh', borderRight: 'var(--border)',
      background: 'var(--card-bg)', padding: '16px', flexShrink: 0,
    }}>
      {/* Logo */}
      <h2 style={{ fontSize: '0.7rem', marginBottom: '20px', borderBottom: 'var(--border)',
                   paddingBottom: '10px' }}>
        ⚙ GYM SMITH
      </h2>

      {/* Stats */}
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ fontSize: '0.55rem', marginBottom: '10px', color: 'var(--text-muted)' }}>
          YOUR PROFILE
        </h3>
        {memory ? (
          <div style={{ fontFamily: 'var(--font-body)', fontSize: '16px', lineHeight: '1.8' }}>
            <div><span style={{ color: 'var(--text-muted)' }}>Goal:</span> {memory.last_goal || '—'}</div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Equipment:</span>
              <div style={{ marginTop: '4px' }}>
                {(memory.equipment || []).map(e => (
                  <span key={e} className="tag">{e}</span>
                ))}
              </div>
            </div>
            <div><span style={{ color: 'var(--text-muted)' }}>Intensity:</span> {memory.intensity_preference || '—'}</div>
          </div>
        ) : (
          <p style={{ fontFamily: 'var(--font-body)', fontSize: '16px', color: 'var(--text-muted)' }}>
            No profile yet.
          </p>
        )}
      </div>

      {/* History */}
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ fontSize: '0.55rem', marginBottom: '10px', color: 'var(--text-muted)' }}>
          HISTORY
        </h3>
        {history && history.length > 0 ? (
          <ul style={{ listStyle: 'none', fontFamily: 'var(--font-body)', fontSize: '15px' }}>
            {history.map((h, i) => (
              <li key={i} style={{ padding: '4px 0', borderBottom: '1px dashed #ccc',
                                   overflow: 'hidden', textOverflow: 'ellipsis',
                                   whiteSpace: 'nowrap', color: 'var(--text-muted)' }}
                  title={h.user_input}>
                · {h.user_input.slice(0, 22)}{h.user_input.length > 22 ? '…' : ''}
              </li>
            ))}
          </ul>
        ) : (
          <p style={{ fontFamily: 'var(--font-body)', fontSize: '16px', color: 'var(--text-muted)' }}>
            No history yet.
          </p>
        )}
      </div>

      <PixelButton onClick={onNewPlan} style={{ width: '100%' }} variant="ghost">
        + NEW PLAN
      </PixelButton>
    </div>
  )
}
