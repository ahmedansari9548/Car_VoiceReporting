import { useEffect } from 'react';
import { fmtPrice, fmtKm, carTitle, carYear, carMileage } from '../lib/format';

/**
 * src/components/Overlays.jsx
 * Compare sheet, keyboard help, and toast stack — small pieces that share
 * one dismissal contract (Escape closes, backdrop click closes).
 */

function Modal({ title, onClose, children, wide }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="backdrop" onClick={onClose} role="presentation">
      <div
        className={`modal ${wide ? 'modal-wide' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="modal-head">
          <h2>{title}</h2>
          <button type="button" className="btn btn-quiet" onClick={onClose}>
            Close
          </button>
        </header>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

const ROWS = [
  ['Price', (c) => `Rs ${fmtPrice(c.price)}`, true],
  ['Year', (c) => carYear(c) ?? '—', true],
  ['Mileage', (c) => fmtKm(carMileage(c)), true],
  ['City', (c) => c.city || '—'],
  ['Gearbox', (c) => c.transmission || '—'],
  ['Colour', (c) => c.color || '—'],
  ['Variant', (c) => c.variant || '—'],
  ['Seller', (c) => c.seller_type || '—'],
];

export function CompareModal({ cars, onClose, onAsk, onRemove }) {
  const cheapest = Math.min(...cars.map((c) => c.price || Infinity));
  const newest = Math.max(...cars.map((c) => carYear(c) || 0));
  const lowestKm = Math.min(...cars.map((c) => carMileage(c) ?? Infinity));

  const best = (label, car) => {
    if (label === 'Price') return car.price === cheapest;
    if (label === 'Year') return carYear(car) === newest;
    if (label === 'Mileage') return carMileage(car) === lowestKm;
    return false;
  };

  return (
    <Modal title={`Comparing ${cars.length} cars`} onClose={onClose} wide>
      <div className="compare" style={{ '--cols': cars.length }}>
        <div className="compare-row compare-head">
          <div className="compare-label" />
          {cars.map((c) => (
            <div key={c.id} className="compare-cell">
              <strong>{carTitle(c)}</strong>
              <div className="compare-cta">
                <button type="button" className="btn btn-primary" onClick={() => onAsk(c)}>
                  Ask about it
                </button>
                <button type="button" className="btn btn-quiet" onClick={() => onRemove(c)}>
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>

        {ROWS.map(([label, get, mono]) => (
          <div className="compare-row" key={label}>
            <div className="compare-label">{label}</div>
            {cars.map((c) => (
              <div
                key={c.id}
                className={`compare-cell ${mono ? 'mono' : ''} ${best(label, c) ? 'best' : ''}`}
              >
                {get(c)}
              </div>
            ))}
          </div>
        ))}
      </div>
      <p className="compare-note">Highlighted values are the best of the set.</p>
    </Modal>
  );
}

const KEYS = [
  ['Enter', 'Send the message'],
  ['Shift + Enter', 'New line'],
  ['↑', 'Edit your last message'],
  ['/', 'Jump to the message box'],
  ['M', 'Start or stop recording'],
  ['Esc', 'Discard a recording or close a panel'],
  ['?', 'Open this list'],
];

export function ShortcutsModal({ onClose }) {
  return (
    <Modal title="Keyboard shortcuts" onClose={onClose}>
      <ul className="keys">
        {KEYS.map(([k, what]) => (
          <li key={k}>
            <kbd>{k}</kbd>
            <span>{what}</span>
          </li>
        ))}
      </ul>
    </Modal>
  );
}

export function Toasts({ items, onDismiss }) {
  return (
    <div className="toasts" role="status" aria-live="polite">
      {items.map((t) => (
        <div key={t.id} className={`toast toast-${t.kind}`}>
          <span>{t.text}</span>
          <button type="button" onClick={() => onDismiss(t.id)} aria-label="Dismiss">
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
