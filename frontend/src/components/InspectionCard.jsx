import { carTitle, fmtPrice, downloadIcs } from '../lib/format';

/**
 * src/components/InspectionCard.jsx
 * The end of the funnel, so it gets the one green moment in the whole UI
 * plus a way to actually put the appointment somewhere useful.
 */
export default function InspectionCard({ inspection, car, onToast }) {
  const addToCalendar = () => {
    const ok = downloadIcs({
      title: car ? `PakWheels inspection — ${carTitle(car)}` : 'PakWheels inspection',
      description: `Booked for ${inspection.name} (${inspection.phone})`,
      date: inspection.date,
      time: inspection.time,
    });
    onToast?.(
      ok ? 'Calendar file downloaded' : 'That date could not be read as a calendar entry',
      ok ? 'ok' : 'warn'
    );
  };

  const rows = [
    car && ['Vehicle', carTitle(car)],
    car && ['Price', `Rs ${fmtPrice(car.price)}`],
    ['Name', inspection.name],
    ['Phone', inspection.phone],
    ['Date', inspection.date],
    ['Time', inspection.time],
  ].filter(Boolean);

  return (
    <div className="booked">
      <div className="booked-head">
        <span className="booked-mark" aria-hidden="true">✓</span>
        <div>
          <h3>Inspection booked</h3>
          <p>A PakWheels inspector will call to confirm.</p>
        </div>
      </div>

      <dl className="booked-rows">
        {rows.map(([k, v]) => (
          <div key={k}>
            <dt>{k}</dt>
            <dd className={k === 'Phone' || k === 'Price' ? 'mono' : ''}>{v || '—'}</dd>
          </div>
        ))}
      </dl>

      <button type="button" className="btn btn-primary" onClick={addToCalendar}>
        Add to calendar
      </button>
    </div>
  );
}
