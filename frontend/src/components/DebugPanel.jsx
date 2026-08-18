import { useState, useEffect } from 'react';

export default function DebugPanel({ connected, sessionId, phase, slots, totalResults, pakwheelsUrl, lastError }) {
  const [dbInfo, setDbInfo] = useState(null);
  const [open, setOpen] = useState(true);

  const refresh = async () => {
    try {
      const res = await fetch('/api/debug');
      setDbInfo(await res.json());
    } catch { setDbInfo({ db_connected: false, error: 'fetch failed' }); }
  };

  useEffect(() => { refresh(); }, [sessionId, phase]);

  const filterSlots = Object.entries(slots).filter(([k]) => !k.startsWith('_'));

  return (
    <>
      {/* Active filters */}
      <div className="panel">
        <div className="panel-head">Active Filters</div>
        <div className="panel-body">
          {filterSlots.length === 0 ? (
            <div style={{ fontSize: 12, color: 'var(--text-faint)' }}>None yet</div>
          ) : filterSlots.map(([k, v]) => (
            <div className="slot-row" key={k}>
              <span className="slot-key">{k.replace(/_/g, ' ')}</span>
              <span className="slot-val">
                {String(v.value)}
                <span className={`badge ${v.source}`}>{v.source}</span>
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* PakWheels link */}
      {pakwheelsUrl && (
        <div className="panel">
          <div className="panel-head">PakWheels Link</div>
          <div className="panel-body">
            <a className="pw-link" href={pakwheelsUrl} target="_blank" rel="noopener noreferrer">
              {pakwheelsUrl.replace('https://www.pakwheels.com', '')}
            </a>
          </div>
        </div>
      )}

      {/* Debug */}
      <div className="panel">
        <div className="panel-head" onClick={() => setOpen(!open)}>
          <span>Debug</span>
          <span onClick={(e) => { e.stopPropagation(); refresh(); }} style={{ cursor: 'pointer' }}>↻</span>
        </div>
        {open && (
          <div className="panel-body">
            <div className="debug-row">
              <span className="k">websocket</span>
              <span className={`v ${connected ? 'ok' : 'bad'}`}>{connected ? 'connected' : 'offline'}</span>
            </div>
            <div className="debug-row">
              <span className="k">session</span>
              <span className="v">{sessionId ? sessionId.slice(5, 15) : '—'}</span>
            </div>
            <div className="debug-row">
              <span className="k">phase</span>
              <span className="v ok">{phase}</span>
            </div>
            <div className="debug-row">
              <span className="k">results</span>
              <span className="v">{totalResults}</span>
            </div>
            {lastError && (
              <div className="debug-row">
                <span className="k">error</span>
                <span className="v bad">{lastError.slice(0, 20)}</span>
              </div>
            )}
            <div style={{ height: 8 }} />
            {dbInfo && (
              <>
                <div className="debug-row">
                  <span className="k">database</span>
                  <span className={`v ${dbInfo.db_connected ? 'ok' : 'bad'}`}>
                    {dbInfo.db_connected ? 'ok' : 'down'}
                  </span>
                </div>
                {dbInfo.model && (
                  <div className="debug-row">
                    <span className="k">model</span>
                    <span className="v">{dbInfo.model.split('/').pop()}</span>
                  </div>
                )}
                {dbInfo.counts && Object.entries(dbInfo.counts).map(([t, c]) => (
                  <div className="debug-row" key={t}>
                    <span className="k">{t}</span>
                    <span className="v">{c}</span>
                  </div>
                ))}
              </>
            )}
          </div>
        )}
      </div>
    </>
  );
}