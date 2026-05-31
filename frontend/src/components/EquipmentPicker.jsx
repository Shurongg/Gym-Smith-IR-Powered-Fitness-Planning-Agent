import { useState } from 'react'
import '../styles/pixel.css'

const TOP_CHIPS = [
  { label: 'Bodyweight', value: 'bodyweight' },
  { label: 'Dumbbell', value: 'dumbbell' },
  { label: 'Barbell', value: 'barbell' },
  { label: 'Cable', value: 'cable' },
  { label: 'Machine', value: 'machine' },
  { label: 'Bench', value: 'bench' },
  { label: 'Pull-up bar', value: 'pull-up bar' },
  { label: 'Kettlebell', value: 'kettlebell' },
  { label: 'Resistance band', value: 'resistance band' },
]

const STANDARD_VALUES = new Set(TOP_CHIPS.map(c => c.value))

const MACHINE_GROUPS = [
  { group: 'CHEST', machines: ['Chest Press Machine', 'Incline Chest Press Machine', 'Decline Chest Press Machine', 'Pec Deck (Chest Fly)'] },
  { group: 'BACK', machines: ['Lat Pulldown Machine', 'Seated Row Machine', 'Chest-Supported Row Machine', 'Assisted Pull-up Machine', 'Back Extension Machine'] },
  { group: 'SHOULDERS', machines: ['Shoulder Press Machine', 'Lateral Raise Machine', 'Rear Delt Machine', 'Shrug Machine'] },
  { group: 'LEGS — QUADS', machines: ['Leg Press Machine', 'Leg Extension Machine', 'Hack Squat Machine'] },
  { group: 'LEGS — HAMSTRINGS', machines: ['Seated Leg Curl Machine', 'Lying Leg Curl Machine'] },
  { group: 'LEGS — GLUTES', machines: ['Hip Thrust Machine', 'Glute Kickback Machine'] },
  { group: 'LEGS — ADDUCTORS', machines: ['Hip Abductor Machine', 'Hip Adductor Machine'] },
  { group: 'CALVES', machines: ['Seated Calf Raise Machine', 'Standing Calf Raise Machine'] },
  { group: 'ARMS', machines: ['Bicep Curl Machine', 'Preacher Curl Machine', 'Triceps Press Machine', 'Triceps Extension Machine', 'Assisted Dip Machine'] },
  { group: 'CORE', machines: ['Ab Crunch Machine', 'Torso Rotation Machine'] },
  { group: 'COMPOUND', machines: ['Smith Machine', 'Multi-Station Machine'] },
  { group: 'CARDIO', machines: ['Treadmill', 'Elliptical', 'Stationary Bike', 'Spin Bike', 'Stair Climber', 'Rowing Machine', 'Assault Bike'] },
]

export default function EquipmentPicker({ selected, specificMachines, onChange }) {
  const [machineOpen, setMachineOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [customInput, setCustomInput] = useState('')

  const isMachineSelected = selected.includes('machine')
  const hasAny = selected.length > 0 || specificMachines.length > 0
  const customItems = selected.filter(v => !STANDARD_VALUES.has(v))

  function addCustom() {
    const trimmed = customInput.trim()
    if (!trimmed) return
    if (selected.some(v => v.toLowerCase() === trimmed.toLowerCase())) {
      setCustomInput('')
      return
    }
    onChange([...selected, trimmed], specificMachines)
    setCustomInput('')
  }

  function removeCustom(name) {
    onChange(selected.filter(v => v !== name), specificMachines)
  }

  function toggleChip(value) {
    if (value === 'machine') {
      if (isMachineSelected) {
        onChange(selected.filter(v => v !== 'machine'), [])
        setMachineOpen(false)
        setSearch('')
      } else {
        onChange([...selected, 'machine'], specificMachines)
        setMachineOpen(true)
      }
    } else {
      const next = selected.includes(value)
        ? selected.filter(v => v !== value)
        : [...selected, value]
      onChange(next, specificMachines)
    }
  }

  function toggleMachine(name) {
    const next = specificMachines.includes(name)
      ? specificMachines.filter(m => m !== name)
      : [...specificMachines, name]
    onChange(selected, next)
  }

  function handleClear() {
    onChange([], [])
    setMachineOpen(false)
    setSearch('')
  }

  const filteredGroups = search
    ? MACHINE_GROUPS
        .map(g => ({ ...g, machines: g.machines.filter(m => m.toLowerCase().includes(search.toLowerCase())) }))
        .filter(g => g.machines.length > 0)
    : MACHINE_GROUPS

  return (
    <div style={{ marginBottom: '12px' }}>
      {/* Label + clear row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <label style={{ fontFamily: 'var(--font-title)', fontSize: '0.5rem', color: 'var(--text-muted)' }}>
          EQUIPMENT (optional)
        </label>
        {hasAny && (
          <button
            onClick={handleClear}
            style={{
              fontFamily: 'var(--font-title)', fontSize: '0.4rem',
              background: 'none', border: '1px dashed var(--text-muted)',
              cursor: 'pointer', padding: '2px 6px', color: 'var(--text-muted)',
            }}
          >
            CLEAR
          </button>
        )}
      </div>

      {/* Top-level chips */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
        {TOP_CHIPS.map(({ label, value }) => {
          const isSelected = selected.includes(value)
          const machineCount = value === 'machine' && specificMachines.length > 0
            ? ` ×${specificMachines.length}` : ''
          const arrow = value === 'machine' ? (machineOpen ? ' ▴' : ' ▾') : ''
          return (
            <button
              key={value}
              onClick={() => toggleChip(value)}
              style={{
                fontFamily: 'var(--font-body)', fontSize: '15px',
                padding: '3px 10px', cursor: 'pointer',
                background: isSelected ? 'var(--primary)' : 'var(--card-bg)',
                border: isSelected ? 'var(--border)' : '1px dashed var(--wood-soft)',
                boxShadow: isSelected ? 'var(--shadow-sm)' : 'none',
                color: isSelected ? 'var(--text)' : 'var(--text-muted)',
              }}
            >
              {label}{machineCount}{arrow}
            </button>
          )
        })}
      </div>

      {/* Custom equipment chips (anything user-typed that isn't in TOP_CHIPS) */}
      {customItems.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
          {customItems.map(name => (
            <span
              key={name}
              style={{
                fontFamily: 'var(--font-body)', fontSize: '15px',
                padding: '3px 8px 3px 10px', display: 'inline-flex',
                alignItems: 'center', gap: '6px',
                background: 'var(--primary)',
                border: '1px dashed var(--wood-dark)',
                boxShadow: 'var(--shadow-sm)',
                color: 'var(--text)',
              }}
            >
              {name}
              <button
                onClick={() => removeCustom(name)}
                title="Remove"
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: 'var(--warning)', fontSize: '14px', lineHeight: 1,
                  padding: '0 2px',
                }}
              >×</button>
            </span>
          ))}
        </div>
      )}

      {/* Custom equipment input */}
      <div style={{ display: 'flex', gap: '6px', marginTop: '8px' }}>
        <input
          type="text"
          placeholder="add custom equipment (e.g. TRX, sandbag, sled)..."
          value={customInput}
          onChange={e => setCustomInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addCustom() } }}
          className="pixel-input"
          style={{
            flex: 1, fontSize: '14px', padding: '4px 8px', boxSizing: 'border-box',
          }}
        />
        <button
          onClick={addCustom}
          disabled={!customInput.trim()}
          style={{
            fontFamily: 'var(--font-title)', fontSize: '0.45rem',
            padding: '4px 10px', cursor: customInput.trim() ? 'pointer' : 'not-allowed',
            background: customInput.trim() ? 'var(--card-bg)' : 'transparent',
            border: '1px dashed var(--wood-soft)',
            color: customInput.trim() ? 'var(--text)' : 'var(--text-muted)',
          }}
        >
          + ADD
        </button>
      </div>

      {/* Machine sub-panel */}
      {machineOpen && (
        <div style={{
          marginTop: '8px', border: 'var(--border)', padding: '12px',
          boxShadow: 'var(--shadow)', background: 'var(--card-bg)',
        }}>
          <input
            type="text"
            placeholder="search machines..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="pixel-input"
            style={{
              width: '100%', marginBottom: '10px', fontSize: '14px',
              padding: '4px 8px', boxSizing: 'border-box',
            }}
          />
          {filteredGroups.length === 0 && (
            <p style={{ fontFamily: 'var(--font-body)', fontSize: '15px', color: 'var(--text-muted)' }}>
              No machines match.
            </p>
          )}
          {filteredGroups.map(({ group, machines }) => (
            <div key={group} style={{ marginBottom: '10px' }}>
              <div style={{
                fontFamily: 'var(--font-title)', fontSize: '0.38rem',
                color: 'var(--text-muted)', marginBottom: '5px',
              }}>
                {group}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                {machines.map(name => {
                  const isSelected = specificMachines.includes(name)
                  return (
                    <button
                      key={name}
                      onClick={() => toggleMachine(name)}
                      style={{
                        fontFamily: 'var(--font-body)', fontSize: '14px',
                        padding: '2px 8px', cursor: 'pointer',
                        background: isSelected ? 'var(--primary)' : 'var(--bg)',
                        border: isSelected ? 'var(--border)' : '1px dashed var(--wood-soft)',
                        boxShadow: isSelected ? '0 1px 0 var(--wood-soft)' : 'none',
                        color: isSelected ? 'var(--text)' : 'var(--text-muted)',
                      }}
                    >
                      {name}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
