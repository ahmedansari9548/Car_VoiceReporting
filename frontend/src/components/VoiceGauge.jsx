/**
 * src/components/VoiceGauge.jsx
 *
 * The signature control: a dashboard instrument dial. Ticks around the rim
 * light up with real microphone level, the readout is a mono elapsed timer,
 * and the whole thing is a single button.
 */

const TICKS = 32;
const R = 40;

export default function VoiceGauge({
  recording,
  level = 0,
  seconds = 0,
  disabled,
  onToggle,
  onCancel,
  label,
}) {
  const lit = Math.round(Math.min(1, level * 1.8) * TICKS);
  const mmss = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(
    seconds % 60
  ).padStart(2, '0')}`;

  return (
    <div className={`gauge-wrap ${recording ? 'is-live' : ''}`}>
      <button
        type="button"
        className="gauge"
        onClick={onToggle}
        disabled={disabled}
        aria-pressed={recording}
        aria-label={recording ? 'Stop recording and send' : 'Record a voice message'}
        title={label}
      >
        <svg viewBox="0 0 100 100" aria-hidden="true">
          <circle className="gauge-face" cx="50" cy="50" r="46" />
          {Array.from({ length: TICKS }).map((_, i) => {
            const angle = (i / TICKS) * 2 * Math.PI - Math.PI / 2;
            const inner = R - (i % 4 === 0 ? 8 : 5);
            return (
              <line
                key={i}
                className={`gauge-tick ${recording && i < lit ? 'on' : ''}`}
                x1={50 + Math.cos(angle) * inner}
                y1={50 + Math.sin(angle) * inner}
                x2={50 + Math.cos(angle) * R}
                y2={50 + Math.sin(angle) * R}
              />
            );
          })}
          <circle
            className="gauge-core"
            cx="50"
            cy="50"
            r={recording ? 20 + level * 9 : 20}
          />
          {recording ? (
            <rect className="gauge-glyph" x="44" y="44" width="12" height="12" rx="2" />
          ) : (
            <path
              className="gauge-glyph"
              d="M50 38a5 5 0 0 1 5 5v9a5 5 0 0 1-10 0v-9a5 5 0 0 1 5-5Zm-9 14a9 9 0 0 0 18 0M50 61v4"
              fill="none"
              strokeWidth="2.2"
              strokeLinecap="round"
            />
          )}
        </svg>
      </button>

      {recording && (
        <div className="gauge-readout">
          <span className="gauge-time">{mmss}</span>
          <button type="button" className="gauge-cancel" onClick={onCancel}>
            Discard
          </button>
        </div>
      )}
    </div>
  );
}
