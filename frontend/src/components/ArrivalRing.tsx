const RING_KEYFRAMES = `
  @keyframes arrival-ring {
    0%   { transform: scale(0.3); opacity: 0; }
    15%  { opacity: 1; }
    100% { transform: scale(1.5); opacity: 0; }
  }
`

export function ArrivalRing() {
  return (
    <>
      <style>{RING_KEYFRAMES}</style>
      <div className="pointer-events-none fixed z-20" style={{ top: '50%', left: '50%' }}>
        <div
          style={{
            position: 'absolute',
            width: 80,
            height: 80,
            top: -40,
            left: -40,
            borderRadius: '50%',
            border: '2px solid rgb(252 211 77)',
            animation: 'arrival-ring 2s ease-out forwards',
          }}
        />
        <div
          style={{
            position: 'absolute',
            width: 128,
            height: 128,
            top: -64,
            left: -64,
            borderRadius: '50%',
            border: '1.5px solid rgb(252 211 77 / 0.5)',
            animation: 'arrival-ring 2s ease-out 0.18s forwards',
          }}
        />
      </div>
    </>
  )
}
