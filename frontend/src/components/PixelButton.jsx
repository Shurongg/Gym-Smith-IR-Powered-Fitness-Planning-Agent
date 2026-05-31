import '../styles/pixel.css'

export default function PixelButton({ children, onClick, disabled, variant = 'primary', style = {} }) {
  const styles = {
    primary: {
      background: disabled ? '#d8c9b4' : 'var(--primary)',
      border: 'var(--border-strong)',
      boxShadow: disabled ? 'none' : 'var(--shadow-button)',
      color: 'var(--bg-card)',
    },
    danger: {
      background: disabled ? '#d8c9b4' : 'var(--warning)',
      border: 'var(--border-strong)',
      boxShadow: disabled ? 'none' : 'var(--shadow-button)',
      color: 'var(--bg-card)',
    },
    ghost: {
      background: 'transparent',
      border: 'var(--border-strong)',
      boxShadow: 'none',
      color: 'var(--text)',
    },
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        ...styles[variant],
        fontFamily: 'var(--font-title)',
        fontSize: '0.65rem',
        padding: '10px 16px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        letterSpacing: '0.05em',
        transition: 'box-shadow 0.1s, transform 0.1s',
        ...style,
      }}
      onMouseDown={e => !disabled && (e.currentTarget.style.transform = 'translateY(3px)')}
      onMouseUp={e => !disabled && (e.currentTarget.style.transform = '')}
      onMouseLeave={e => (e.currentTarget.style.transform = '')}
    >
      {children}
    </button>
  )
}
