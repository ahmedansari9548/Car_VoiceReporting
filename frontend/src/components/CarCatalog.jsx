import { useEffect, useMemo, useRef, useState } from 'react';
import { apiUrl } from '../config';
import CarCard from './CarCard';
import { fmtPrice, carYear, carMileage } from '../lib/format';

/**
 * src/components/CarCatalog.jsx
 *
 * Now goes through apiUrl() instead of a hardcoded localhost:8000, and
 * filters/sorts client side so every control responds instantly. Search is
 * debounced; the network is only touched on mount and on Refresh.
 */

const SORTS = {
  'price-asc': { label: 'Price, low to high', fn: (a, b) => a.price - b.price },
  'price-desc': { label: 'Price, high to low', fn: (a, b) => b.price - a.price },
  'year-desc': { label: 'Newest first', fn: (a, b) => carYear(b) - carYear(a) },
  'km-asc': { label: 'Lowest mileage', fn: (a, b) => carMileage(a) - carMileage(b) },
};

const PAGE = 12;

export default function CarCatalog({
  onAsk,
  shortlist,
  onShortlist,
  compare,
  onCompare,
  onBook,
}) {
  const [cars, setCars] = useState([]);
  const [state, setState] = useState('loading'); // loading | ready | error
  const [error, setError] = useState('');

  const [query, setQuery] = useState('');
  const [debounced, setDebounced] = useState('');
  const [make, setMake] = useState('All');
  const [city, setCity] = useState('All');
  const [gearbox, setGearbox] = useState('All');
  const [maxPrice, setMaxPrice] = useState(0);
  const [sort, setSort] = useState('price-asc');
  const [layout, setLayout] = useState('grid');
  const [shown, setShown] = useState(PAGE);
  const searchRef = useRef(null);

  useEffect(() => {
    const id = setTimeout(() => setDebounced(query.trim().toLowerCase()), 180);
    return () => clearTimeout(id);
  }, [query]);

  const load = async () => {
    setState('loading');
    setError('');
    try {
      const res = await fetch(apiUrl('/api/cars?limit=200'));
      if (!res.ok) throw new Error(`Server replied ${res.status}`);
      const data = await res.json();
      const list = data.cars || [];
      setCars(list);
      const ceiling = list.reduce((m, c) => Math.max(m, c.price || 0), 0);
      setMaxPrice(ceiling);
      setState('ready');
    } catch (err) {
      setError(
        `Could not load the catalog from ${apiUrl('/api/cars')} — ${err.message}`
      );
      setState('error');
    }
  };

  useEffect(() => {
    load();
  }, []);

  const ceiling = useMemo(
    () => cars.reduce((m, c) => Math.max(m, c.price || 0), 0),
    [cars]
  );
  const makes = useMemo(
    () => ['All', ...new Set(cars.map((c) => c.make).filter(Boolean))].sort(),
    [cars]
  );
  const cities = useMemo(
    () => ['All', ...new Set(cars.map((c) => c.city).filter(Boolean))].sort(),
    [cars]
  );

  const filtered = useMemo(() => {
    const out = cars.filter((car) => {
      const hay = `${carYear(car) ?? ''} ${car.make ?? ''} ${car.model ?? ''} ${
        car.variant ?? ''
      } ${car.city ?? ''} ${car.color ?? ''}`.toLowerCase();
      if (debounced && !hay.includes(debounced)) return false;
      if (make !== 'All' && car.make !== make) return false;
      if (city !== 'All' && car.city !== city) return false;
      if (gearbox !== 'All' && car.transmission !== gearbox) return false;
      if (maxPrice && car.price > maxPrice) return false;
      return true;
    });
    return out.sort(SORTS[sort].fn);
  }, [cars, debounced, make, city, gearbox, maxPrice, sort]);

  useEffect(() => setShown(PAGE), [debounced, make, city, gearbox, maxPrice, sort]);

  const activeFilters =
    (debounced ? 1 : 0) +
    (make !== 'All' ? 1 : 0) +
    (city !== 'All' ? 1 : 0) +
    (gearbox !== 'All' ? 1 : 0) +
    (maxPrice && maxPrice < ceiling ? 1 : 0);

  const clearAll = () => {
    setQuery('');
    setMake('All');
    setCity('All');
    setGearbox('All');
    setMaxPrice(ceiling);
    searchRef.current?.focus();
  };

  return (
    <section className="catalog">
      <header className="catalog-head">
        <div>
          <p className="eyebrow">Live inventory</p>
          <h2 className="catalog-title">
            {state === 'ready' ? (
              <>
                <span className="mono count">{filtered.length}</span> cars ready to view
              </>
            ) : (
              'Loading inventory'
            )}
          </h2>
        </div>
        <button type="button" className="btn btn-ghost" onClick={load}>
          Refresh
        </button>
      </header>

      <div className="filters">
        <div className="field field-grow">
          <input
            ref={searchRef}
            className="input"
            type="search"
            placeholder="Search make, model, city or colour"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search inventory"
          />
        </div>

        <select className="select" value={make} onChange={(e) => setMake(e.target.value)} aria-label="Make">
          {makes.map((m) => (
            <option key={m} value={m}>{m === 'All' ? 'All makes' : m}</option>
          ))}
        </select>

        <select className="select" value={city} onChange={(e) => setCity(e.target.value)} aria-label="City">
          {cities.map((c) => (
            <option key={c} value={c}>{c === 'All' ? 'All cities' : c}</option>
          ))}
        </select>

        <select className="select" value={gearbox} onChange={(e) => setGearbox(e.target.value)} aria-label="Transmission">
          <option value="All">Any gearbox</option>
          <option value="Automatic">Automatic</option>
          <option value="Manual">Manual</option>
        </select>

        <select className="select" value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort">
          {Object.entries(SORTS).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>

        <div className="layout-toggle" role="group" aria-label="Layout">
          <button
            type="button"
            className={layout === 'grid' ? 'on' : ''}
            onClick={() => setLayout('grid')}
            aria-pressed={layout === 'grid'}
          >
            Grid
          </button>
          <button
            type="button"
            className={layout === 'list' ? 'on' : ''}
            onClick={() => setLayout('list')}
            aria-pressed={layout === 'list'}
          >
            List
          </button>
        </div>
      </div>

      {ceiling > 0 && (
        <div className="price-rail">
          <label htmlFor="maxprice">
            Under <b className="mono">Rs {fmtPrice(maxPrice || ceiling)}</b>
          </label>
          <input
            id="maxprice"
            type="range"
            min={Math.min(...cars.map((c) => c.price || 0), ceiling)}
            max={ceiling}
            step={50000}
            value={maxPrice || ceiling}
            onChange={(e) => setMaxPrice(Number(e.target.value))}
          />
          {activeFilters > 0 && (
            <button type="button" className="btn btn-quiet" onClick={clearAll}>
              Clear {activeFilters} filter{activeFilters > 1 ? 's' : ''}
            </button>
          )}
        </div>
      )}

      {state === 'loading' && (
        <div className="catalog-grid">
          {Array.from({ length: 6 }).map((_, i) => (
            <div className="card-skeleton" key={i} />
          ))}
        </div>
      )}

      {state === 'error' && (
        <div className="notice notice-error">
          <p>{error}</p>
          <p className="notice-hint">
            Check that the backend is up and that this origin is listed in
            CORS_ORIGINS.
          </p>
          <button type="button" className="btn btn-primary" onClick={load}>
            Try again
          </button>
        </div>
      )}

      {state === 'ready' && filtered.length === 0 && (
        <div className="notice">
          <p>Nothing matches those filters.</p>
          <button type="button" className="btn btn-primary" onClick={clearAll}>
            Clear filters
          </button>
        </div>
      )}

      {state === 'ready' && filtered.length > 0 && (
        <>
          <div className={layout === 'grid' ? 'catalog-grid' : 'catalog-list'}>
            {filtered.slice(0, shown).map((car) => (
              <CarCard
                key={car.id}
                car={car}
                variant={layout}
                shortlisted={shortlist.some((c) => c.id === car.id)}
                comparing={compare.some((c) => c.id === car.id)}
                compareDisabled={compare.length >= 3}
                onPick={onAsk}
                onAsk={onAsk}
                onShortlist={onShortlist}
                onCompare={onCompare}
                onBook={onBook}
              />
            ))}
          </div>

          {shown < filtered.length && (
            <div className="more">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setShown((s) => s + PAGE)}
              >
                Show {Math.min(PAGE, filtered.length - shown)} more
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}
