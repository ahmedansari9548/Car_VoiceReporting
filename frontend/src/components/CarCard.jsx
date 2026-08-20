import { useState } from 'react';
import {
  fmtPrice,
  fmtKm,
  carTitle,
  carYear,
  carMileage,
  placeholderImg,
} from '../lib/format';

/**
 * src/components/CarCard.jsx
 *
 * Every affordance is a real action: pick it, shortlist it, put it side by
 * side, open the specs, book the inspection. Buttons stop propagation so the
 * card's own "pick this one" click never fires by accident.
 */
export default function CarCard({
  car,
  selected,
  shortlisted,
  comparing,
  compareDisabled,
  onPick,
  onAsk,
  onShortlist,
  onCompare,
  onBook,
  variant = 'chat',
}) {
  const [open, setOpen] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const fallback = placeholderImg(car);

  const stop = (fn) => (e) => {
    e.stopPropagation();
    fn?.();
  };

  return (
    <article
      className={`car ${selected ? 'is-selected' : ''} ${comparing ? 'is-comparing' : ''} car--${variant}`}
      onClick={() => onPick?.(car)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onPick?.(car);
        }
      }}
      role="button"
      tabIndex={0}
      aria-label={`${carTitle(car)}, Rs ${fmtPrice(car.price)}`}
    >
      <div className="car-media">
        {!loaded && <div className="car-skeleton" />}
        <img
          className="car-img"
          src={car.image_url || fallback}
          alt={carTitle(car)}
          loading="lazy"
          onLoad={() => setLoaded(true)}
          onError={(e) => {
            e.currentTarget.src = fallback;
            setLoaded(true);
          }}
        />
        <span className="car-price-tag">
          Rs <b>{fmtPrice(car.price)}</b>
        </span>

        <div className="car-quick">
          <button
            type="button"
            className={`chipbtn ${shortlisted ? 'on' : ''}`}
            onClick={stop(() => onShortlist?.(car))}
            aria-pressed={!!shortlisted}
            title={shortlisted ? 'Remove from shortlist' : 'Save to shortlist'}
          >
            {shortlisted ? '★' : '☆'}
          </button>
          <button
            type="button"
            className={`chipbtn ${comparing ? 'on' : ''}`}
            onClick={stop(() => onCompare?.(car))}
            disabled={!comparing && compareDisabled}
            aria-pressed={!!comparing}
            title={comparing ? 'Remove from comparison' : 'Add to comparison'}
          >
            ⇄
          </button>
        </div>
      </div>

      <div className="car-body">
        <h3 className="car-name">{carTitle(car)}</h3>

        <ul className="car-specs">
          <li>{car.city || '—'}</li>
          <li>{car.transmission || '—'}</li>
          <li className="mono">{fmtKm(carMileage(car))}</li>
          {car.color && <li>{car.color}</li>}
        </ul>

        {open && (
          <dl className="car-detail">
            <div><dt>Year</dt><dd className="mono">{carYear(car) ?? '—'}</dd></div>
            <div><dt>Variant</dt><dd>{car.variant || '—'}</dd></div>
            <div><dt>Seller</dt><dd>{car.seller_type || '—'}</dd></div>
            <div><dt>Listing</dt><dd className="mono">#{car.id ?? '—'}</dd></div>
          </dl>
        )}

        <div className="car-actions">
          <button type="button" className="btn btn-primary" onClick={stop(() => onAsk?.(car))}>
            Ask about this car
          </button>
          {onBook && (
            <button type="button" className="btn btn-ghost" onClick={stop(() => onBook(car))}>
              Book inspection
            </button>
          )}
          <button
            type="button"
            className="btn btn-quiet"
            onClick={stop(() => setOpen((v) => !v))}
            aria-expanded={open}
          >
            {open ? 'Less' : 'Specs'}
          </button>
        </div>
      </div>
    </article>
  );
}
