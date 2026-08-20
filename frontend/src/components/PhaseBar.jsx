/**
 * src/components/PhaseBar.jsx
 *
 * The four phases are a real sequence, so they're drawn as a shifter gate:
 * a knob that travels along a rail. Order carries meaning here, which is why
 * the sequence device is honest rather than decorative.
 */

const PHASES = [
  { key: 'searching', label: 'Search', hint: 'Tell me budget, city and car type' },
  { key: 'selected', label: 'Shortlist', hint: 'One car is on the table' },
  { key: 'inspection', label: 'Booking', hint: 'Collecting your details' },
  { key: 'confirmed', label: 'Booked', hint: 'Inspection confirmed' },
];

export default function PhaseBar({ phase }) {
  const idx = Math.max(0, PHASES.findIndex((p) => p.key === phase));
  const pct = (idx / (PHASES.length - 1)) * 100;

  return (
    <div className="gate" role="status" aria-label={`Stage ${idx + 1} of 4`}>
      <div className="gate-rail">
        <div className="gate-fill" style={{ width: `${pct}%` }} />
        <div className="gate-knob" style={{ left: `${pct}%` }} />
      </div>
      <div className="gate-stops">
        {PHASES.map((p, i) => (
          <div
            key={p.key}
            className={`gate-stop ${i === idx ? 'active' : ''} ${i < idx ? 'done' : ''}`}
            title={p.hint}
          >
            <span className="gate-label">{p.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
