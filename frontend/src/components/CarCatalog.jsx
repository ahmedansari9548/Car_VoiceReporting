import { useState, useEffect } from 'react';

const fmtPrice = (p) => {
  if (p >= 10000000) return `${(p / 10000000).toFixed(2)} Crore`;
  if (p >= 100000) return `${(p / 100000).toFixed(1)} Lakh`;
  return p?.toLocaleString() ?? '—';
};

const fmtKm = (km) => {
  if (!km) return '—';
  return km >= 1000 ? `${Math.round(km / 1000)}k km` : `${km} km`;
};

export default function CarCatalog({ onVoiceCommand }) {
  const [cars, setCars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMake, setSelectedMake] = useState('All');
  const [selectedCity, setSelectedCity] = useState('All');

  useEffect(() => {
    fetchCars();
  }, []);

  const fetchCars = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/cars?limit=100');
      if (res.ok) {
        const data = await res.json();
        setCars(data.cars || []);
      } else {
        console.error('Failed to fetch cars');
      }
    } catch (err) {
      console.error('Error fetching catalog cars:', err);
    } finally {
      setLoading(false);
    }
  };

  const makes = ['All', ...new Set(cars.map((c) => c.make).filter(Boolean))];
  const cities = ['All', ...new Set(cars.map((c) => c.city).filter(Boolean))];

  const filteredCars = cars.filter((car) => {
    const title = `${car.model_year || car.year || ''} ${car.make || ''} ${car.model || ''} ${car.variant || ''}`.toLowerCase();
    const matchesQuery = !searchQuery || title.includes(searchQuery.toLowerCase()) || car.city?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesMake = selectedMake === 'All' || car.make === selectedMake;
    const matchesCity = selectedCity === 'All' || car.city === selectedCity;
    return matchesQuery && matchesMake && matchesCity;
  });

  return (
    <div className="catalog-container">
      <div className="catalog-header">
        <div className="catalog-title">
          <h2>🚗 Available Car Menu</h2>
          <p>Browse our catalog and launch voice commands directly on any car.</p>
        </div>

        {/* Filters */}
        <div className="catalog-filters">
          <input
            type="text"
            className="search-input"
            placeholder="Search make, model, city..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          
          <select value={selectedMake} onChange={(e) => setSelectedMake(e.target.value)} className="filter-select">
            <option value="All">All Makes</option>
            {makes.filter(m => m !== 'All').map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>

          <select value={selectedCity} onChange={(e) => setSelectedCity(e.target.value)} className="filter-select">
            <option value="All">All Cities</option>
            {cities.filter(c => c !== 'All').map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="catalog-loading">
          <div className="spinner"></div>
          <p>Loading cars menu...</p>
        </div>
      ) : filteredCars.length === 0 ? (
        <div className="empty-catalog">
          <p>No cars found matching your filters.</p>
        </div>
      ) : (
        <div className="catalog-grid">
          {filteredCars.map((car) => {
            const year = car.model_year || car.year;
            const fallback = `https://placehold.co/400x250/1a2234/ffffff?text=${encodeURIComponent(car.make + ' ' + car.model)}`;
            return (
              <div key={car.id} className="catalog-card">
                <div className="catalog-card-img-wrap">
                  <img
                    src={car.image_url || fallback}
                    alt={`${year} ${car.make} ${car.model}`}
                    onError={(e) => { e.currentTarget.src = fallback; }}
                  />
                  <span className="price-badge">Rs {fmtPrice(car.price)}</span>
                </div>
                <div className="catalog-card-content">
                  <h3>{year} {car.make} {car.model} {car.variant || ''}</h3>
                  <div className="catalog-card-specs">
                    <span>📍 {car.city}</span>
                    <span>⚙ {car.transmission}</span>
                    <span>🛣 {fmtKm(car.mileage_km || car.mileage)}</span>
                    {car.color && <span>🎨 {car.color}</span>}
                  </div>
                  <button
                    className="btn-voice-command"
                    onClick={() => onVoiceCommand(car)}
                  >
                    🎙️ Voice Command with AI
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
