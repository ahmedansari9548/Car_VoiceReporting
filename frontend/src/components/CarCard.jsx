const fmtPrice = (p) => {
  if (p >= 10000000) return `${(p / 10000000).toFixed(2)} Crore`;
  if (p >= 100000) return `${(p / 100000).toFixed(1)} Lakh`;
  return p?.toLocaleString() ?? '—';
};

const fmtKm = (km) => {
  if (!km) return '—';
  return km >= 1000 ? `${Math.round(km / 1000)}k km` : `${km} km`;
};

export default function CarCard({ car, selected, onClick }) {
  const fallback = `https://placehold.co/400x250/1a2234/4b5563?text=${encodeURIComponent(car.make + ' ' + car.model)}`;

  return (
    <div className={`car ${selected ? 'selected' : ''}`} onClick={onClick}>
      <img
        className="car-img"
        src={car.image_url || fallback}
        alt={`${car.year} ${car.make} ${car.model}`}
        onError={(e) => { e.currentTarget.src = fallback; }}
      />
      <div className="car-body">
        <div className="car-name">
          {car.year} {car.make} {car.model} {car.variant || ''}
        </div>
        <div className="car-specs">
          <span>📍 {car.city}</span>
          <span>⚙ {car.transmission}</span>
          <span>🛣 {fmtKm(car.mileage)}</span>
          {car.color && <span>● {car.color}</span>}
        </div>
        <div className="car-foot">
          <div className="car-price">Rs {fmtPrice(car.price)}</div>
          <span className="car-tag">{car.seller_type}</span>
        </div>
      </div>
    </div>
  );
}