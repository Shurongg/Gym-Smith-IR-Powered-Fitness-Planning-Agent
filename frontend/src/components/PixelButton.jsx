import '../styles/pixel.css'

export default function PixelButton({ children, onClick, disabled, variant = 'primary', style = {} }) {
  const styles = {
    primary: {
      background: disabled ? '#ccc' : 'var(--primary)',
      border: 'var(--border)',
      boxShadow: disabled ? 'none' : 'var(--shadow)',
      color: 'var(--text)',
    },
    danger: {
      background: disabled ? '#ccc' : 'var(--warning)',
      border: 'var(--border)',
      boxShadow: disabled ? 'none' : '4px 4px 0px #2D2D2D',
      color: 'var(--text)',
    },
    ghost: {
      background: 'transparent',
      border: 'var(--border)',
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
      onMouseDown={e => !disabled && (e.currentTarget.style.transform = 'translate(2px,2px)')}
      onMouseUp={e => !disabled && (e.currentTarget.style.transform = '')}
      onMouseLeave={e => (e.currentTarget.style.transform = '')}
    >
      {children}
    </button>
  )
}
