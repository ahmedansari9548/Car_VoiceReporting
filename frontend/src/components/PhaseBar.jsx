const PHASES = [
  { key: 'searching', label: 'Search' },
  { key: 'selected', label: 'Selected' },
  { key: 'inspection', label: 'Booking' },
  { key: 'confirmed', label: 'Confirmed' },
];

export default function PhaseBar({ phase }) {
  const idx = PHASES.findIndex(p => p.key === phase);
  return (
    <div className="phase-bar">
      {PHASES.map((p, i) => (
        <div
          key={p.key}
          className={`phase-step ${i === idx ? 'active' : i < idx ? 'done' : ''}`}
        >
          {i < idx ? '✓ ' : ''}{p.label}
        </div>
      ))}
    </div>
  );
}