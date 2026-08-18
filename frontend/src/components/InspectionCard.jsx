export default function InspectionCard({ inspection, car }) {
  return (
    <div className="inspection-card">
      <h3>✓ Inspection Booked</h3>
      {car && (
        <div className="inspection-row">
          <span className="label">Vehicle</span>
          <span className="value">{car.year} {car.make} {car.model} {car.variant || ''}</span>
        </div>
      )}
      <div className="inspection-row">
        <span className="label">Name</span>
        <span className="value">{inspection.name}</span>
      </div>
      <div className="inspection-row">
        <span className="label">Phone</span>
        <span className="value">{inspection.phone}</span>
      </div>
      <div className="inspection-row">
        <span className="label">Date</span>
        <span className="value">{inspection.date}</span>
      </div>
      <div className="inspection-row">
        <span className="label">Time</span>
        <span className="value">{inspection.time}</span>
      </div>
    </div>
  );
}