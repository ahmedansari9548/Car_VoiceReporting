import { useEffect, useState } from 'react';
import { apiUrl, API_BASE, WS_URL } from '../config';
import { carTitle, fmtPrice } from '../lib/format';

/**
 * src/components/Sidebar.jsx  (replaces DebugPanel.jsx)
 *
 * Three panels: what the assistant currently believes, what you've saved,
 * and what the connection is doing. The filter chips are interactive — click
 * one and it drafts the message that would undo it, rather than silently
 * mutating server state behind the user's back.
 */

const SLOT_LABELS = {
  price_max: 'Budget',
  price_min: 'From',
  city: 'City',
  make: 'Make',
  model: 'Model',
  body_type: 'Body',
  transmission: 'Gearbox',
  color: 'Colour',
  mileage_max: 'Max km',
  year_min: 'From year',
  year_max: 'To year',
  assembly: 'Assembly',
};

const DROP_TEXT = {
  city: 'Search in any city',
  price_max: 'Ignore my budget limit for now',
  make: 'Show other makes too',
  model: 'Show other models too',
  body_type: 'Any body type is fine',
  transmission: 'Either gearbox is fine',
  color: 'Any colour is fine',
};

const prettyValue = (key, value) => {
  if (key === 'price_max' || key === 'price_min') return `Rs ${fmtPrice(Number(value))}`;
  if (key === 'mileage_max') return `${Number(value).toLocaleString()} km`;
  return String(value);
};

export default function Sidebar({
  status,
  attempts,
  latency,
  sessionId,
  phase,
  slots,
  totalResults,
  pakwheelsUrl,
  shortlist,
  onDraft,
  onAsk,
  onUnshortlist,
  onReconnect,
}) {
  const [health, setHealth] = useState(null);
  const [openDebug, setOpenDebug] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await fetch(apiUrl('/api/debug'));
        const json = await res.json();
        if (alive) setHealth(json);
      } catch {
        if (alive) setHealth({ db_connected: false, error: 'unreachable' });
      }
    })();
    return () => {
      alive = false;
    };
  }, [sessionId, phase]);

  const filters = Object.entries(slots).filter(([k]) => !k.startsWith('_'));

  return (
    <aside className="sidebar">
      <section className="panel">
        <h2 className="panel-head">What I've understood</h2>
        <div className="panel-body">
          {filters.length === 0 ? (
            <p className="muted">
              Nothing yet. Say a budget, a city and a body type and it fills in here.
            </p>
          ) : (
            <ul className="slot-list">
              {filters.map(([key, slot]) => (
                <li key={key}>
                  <button
                    type="button"
                    className={`slot ${slot.source === 'derived' ? 'derived' : ''}`}
                    onClick={() => onDraft?.(DROP_TEXT[key] || `Forget the ${SLOT_LABELS[key] || key}`)}
                    title="Draft a message that changes this"
                  >
                    <span className="slot-key">{SLOT_LABELS[key] || key.replace(/_/g, ' ')}</span>
                    <span className="slot-val mono">{prettyValue(key, slot.value)}</span>
                    {slot.source === 'derived' && <span className="slot-tag">guessed</span>}
                  </button>
                </li>
              ))}
            </ul>
          )}

          {totalResults > 0 && (
            <p className="panel-foot">
              <span className="mono">{totalResults}</span> matching listings
            </p>
          )}

          {pakwheelsUrl && (
            <a className="pw-link" href={pakwheelsUrl} target="_blank" rel="noopener noreferrer">
              Open this search on PakWheels →
            </a>
          )}
        </div>
      </section>

      <section className="panel">
        <h2 className="panel-head">
          Shortlist
          {shortlist.length > 0 && <span className="pill mono">{shortlist.length}</span>}
        </h2>
        <div className="panel-body">
          {shortlist.length === 0 ? (
            <p className="muted">Star a car to keep it here across the session.</p>
          ) : (
            <ul className="mini-list">
              {shortlist.map((car) => (
                <li key={car.id}>
                  <button type="button" className="mini" onClick={() => onAsk(car)}>
                    <span className="mini-name">{carTitle(car)}</span>
                    <span className="mini-price mono">Rs {fmtPrice(car.price)}</span>
                  </button>
                  <button
                    type="button"
                    className="mini-x"
                    onClick={() => onUnshortlist(car)}
                    aria-label={`Remove ${carTitle(car)} from shortlist`}
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <section className="panel">
        <button
          type="button"
          className="panel-head panel-toggle"
          onClick={() => setOpenDebug((v) => !v)}
          aria-expanded={openDebug}
        >
          <span>Connection</span>
          <span className={`dot dot-${status}`} aria-hidden="true" />
        </button>

        {openDebug && (
          <div className="panel-body">
            <dl className="kv">
              <div>
                <dt>Socket</dt>
                <dd className={status === 'online' ? 'ok' : 'bad'}>
                  {status}
                  {attempts > 0 && status !== 'online' ? ` · retry ${attempts}` : ''}
                </dd>
              </div>
              <div>
                <dt>Round trip</dt>
                <dd className="mono">{latency != null ? `${latency} ms` : '—'}</dd>
              </div>
              <div>
                <dt>Session</dt>
                <dd className="mono">{sessionId ? sessionId.slice(0, 8) : '—'}</dd>
              </div>
              <div>
                <dt>Stage</dt>
                <dd>{phase}</dd>
              </div>
              <div>
                <dt>Database</dt>
                <dd className={health?.db_connected ? 'ok' : 'bad'}>
                  {health ? (health.db_connected ? 'connected' : 'down') : 'checking'}
                </dd>
              </div>
              {health?.model && (
                <div>
                  <dt>Model</dt>
                  <dd className="mono">{String(health.model).split('/').pop()}</dd>
                </div>
              )}
              <div>
                <dt>API</dt>
                <dd className="mono wrap">{API_BASE || 'same origin'}</dd>
              </div>
              <div>
                <dt>Socket URL</dt>
                <dd className="mono wrap">{WS_URL}</dd>
              </div>
            </dl>

            {status !== 'online' && (
              <button type="button" className="btn btn-primary" onClick={onReconnect}>
                Reconnect now
              </button>
            )}
          </div>
        )}
      </section>
    </aside>
  );
}
