import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useRecorder } from './hooks/useRecorder';
import { useSpeech, usePersistentState } from './hooks/useSpeech';
import { MIC_AVAILABLE, MIXED_CONTENT, API_BASE } from './config';
import { buildAskAiMessage, carTitle, isUrdu } from './lib/format';

import PhaseBar from './components/PhaseBar';
import CarCard from './components/CarCard';
import CarCatalog from './components/CarCatalog';
import InspectionCard from './components/InspectionCard';
import Sidebar from './components/Sidebar';
import VoiceGauge from './components/VoiceGauge';
import { CompareModal, ShortcutsModal, Toasts } from './components/Overlays';

const SUGGESTIONS = [
  { text: 'Corolla in Lahore under 40 lakh', lang: 'en' },
  { text: 'Automatic hatchback, 25 lakh budget', lang: 'en' },
  { text: 'مجھے اسلام آباد میں ایس یو وی چاہیے', lang: 'ur' },
  { text: 'سب سے سستی گاڑی دکھائیں', lang: 'ur' },
];

const PLACEHOLDERS = {
  searching: 'Budget, city, and the kind of car you want',
  selected: 'Ask anything about this car, or say book the inspection',
  inspection: 'Your name, phone number, date and time',
  confirmed: 'Anything else I can look up?',
};

const prefersReducedMotion = () =>
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;

/** Reveals text a few characters at a time so replies feel spoken, not pasted. */
function Reveal({ text, animate, onTick }) {
  const [n, setN] = useState(animate ? 0 : text.length);
  // Held in a ref: if onTick were a dependency, a scroll-position change
  // would restart the reveal from zero mid-sentence.
  const tickRef = useRef(onTick);
  tickRef.current = onTick;

  useEffect(() => {
    if (!animate) {
      setN(text.length);
      return undefined;
    }
    let i = 0;
    const step = Math.max(1, Math.round(text.length / 80));
    const id = setInterval(() => {
      i += step;
      setN(Math.min(i, text.length));
      tickRef.current?.();
      if (i >= text.length) clearInterval(id);
    }, 18);
    return () => clearInterval(id);
  }, [text, animate]);

  return <>{text.slice(0, n)}</>;
}

export default function App() {
  const {
    status, attempts, latency, messages, phase, slots, selectedCar,
    totalResults, pakwheelsUrl, sessionId, loading, lastError,
    sendText, sendAudio, reset, reconnectNow, dismissError,
  } = useWebSocket();

  const connected = status === 'online';

  const [input, setInput] = useState('');
  const [tab, setTab] = useState('assistant');
  const [toasts, setToasts] = useState([]);
  const [shortlist, setShortlist] = usePersistentState('pw.shortlist', []);
  const [compare, setCompare] = useState([]);
  const [showCompare, setShowCompare] = useState(false);
  const [showKeys, setShowKeys] = useState(false);
  const [voiceOn, setVoiceOn] = usePersistentState('pw.voice', false);
  const [atBottom, setAtBottom] = useState(true);

  const chatRef = useRef(null);
  const endRef = useRef(null);
  const inputRef = useRef(null);
  const spokenFor = useRef(new Set());

  const toast = useCallback((text, kind = 'info') => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, text, kind }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 5200);
  }, []);

  const { speak, cancel: cancelSpeech } = useSpeech(voiceOn);

  const recorder = useRecorder({
    onComplete: (blob) => {
      if (!sendAudio(blob)) toast('Not connected — the clip was not sent', 'error');
    },
    onError: (msg) => toast(msg, 'error'),
  });

  // ── surface socket errors as toasts, once each ──────────────────────
  useEffect(() => {
    if (!lastError) return;
    toast(lastError, 'error');
    dismissError();
  }, [lastError, toast, dismissError]);

  // ── read the newest assistant reply aloud ───────────────────────────
  const lastAssistantIndex = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === 'assistant') return i;
    }
    return -1;
  }, [messages]);

  useEffect(() => {
    if (lastAssistantIndex < 0 || !voiceOn) return;
    const msg = messages[lastAssistantIndex];
    if (spokenFor.current.has(msg.at)) return;
    spokenFor.current.add(msg.at);
    speak(msg.text);
  }, [lastAssistantIndex, messages, voiceOn, speak]);

  // ── autoscroll, but only if the reader is already at the bottom ─────
  const stickToBottom = useCallback(() => {
    if (!atBottom) return;
    endRef.current?.scrollIntoView({
      behavior: prefersReducedMotion() ? 'auto' : 'smooth',
      block: 'end',
    });
  }, [atBottom]);

  useEffect(stickToBottom, [messages, loading, stickToBottom]);

  const onChatScroll = () => {
    const el = chatRef.current;
    if (!el) return;
    setAtBottom(el.scrollHeight - el.scrollTop - el.clientHeight < 90);
  };

  // ── sending ─────────────────────────────────────────────────────────
  const send = useCallback(
    (text) => {
      const value = (text ?? input).trim();
      if (!value || loading) return;
      if (sendText(value)) {
        setInput('');
        setAtBottom(true);
      }
    },
    [input, loading, sendText]
  );

  const askAbout = useCallback(
    (car) => {
      setTab('assistant');
      setAtBottom(true);
      // Exact wording the backend's parse_ask_ai_message() regex expects.
      const message = buildAskAiMessage(car);
      setTimeout(() => {
        if (!sendText(message)) toast('Not connected yet — try again in a moment', 'error');
      }, 120);
    },
    [sendText, toast]
  );

  const bookFor = useCallback(
    (car) => {
      setTab('assistant');
      setTimeout(() => sendText(`Book a PakWheels inspection for the ${carTitle(car)}`), 120);
    },
    [sendText]
  );

  const draft = useCallback((text) => {
    setTab('assistant');
    setInput(text);
    setTimeout(() => inputRef.current?.focus(), 60);
  }, []);

  const toggleShortlist = useCallback(
    (car) => {
      setShortlist((list) => {
        const has = list.some((c) => c.id === car.id);
        toast(has ? 'Removed from shortlist' : `Saved ${carTitle(car)}`, has ? 'info' : 'ok');
        return has ? list.filter((c) => c.id !== car.id) : [...list, car];
      });
    },
    [setShortlist, toast]
  );

  const toggleCompare = useCallback(
    (car) => {
      setCompare((list) => {
        if (list.some((c) => c.id === car.id)) return list.filter((c) => c.id !== car.id);
        if (list.length >= 3) {
          toast('Compare holds three cars at a time', 'warn');
          return list;
        }
        return [...list, car];
      });
    },
    [toast]
  );

  // ── keyboard ────────────────────────────────────────────────────────
  useEffect(() => {
    const onKey = (e) => {
      const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(
        document.activeElement?.tagName
      );

      if (e.key === 'Escape') {
        if (recorder.recording) recorder.cancel();
        else if (showCompare) setShowCompare(false);
        else if (showKeys) setShowKeys(false);
        return;
      }
      if (typing) return;

      if (e.key === '/') {
        e.preventDefault();
        setTab('assistant');
        inputRef.current?.focus();
      } else if (e.key === '?') {
        setShowKeys(true);
      } else if (e.key.toLowerCase() === 'm' && MIC_AVAILABLE && connected) {
        recorder.toggle();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [recorder, showCompare, showKeys, connected]);

  const lastUserText = useMemo(
    () => [...messages].reverse().find((m) => m.role === 'user')?.text ?? '',
    [messages]
  );

  const onComposerKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    } else if (e.key === 'ArrowUp' && !input) {
      e.preventDefault();
      setInput(lastUserText);
    }
  };

  const statusCopy = {
    online: latency != null ? `Live · ${latency} ms` : 'Live',
    connecting: 'Connecting',
    offline: attempts ? `Reconnecting (${attempts})` : 'Offline',
  }[status];

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <div>
            <h1>PakWheels Assistant</h1>
            <p className="brand-sub">
              Buy a used car by talking — English or اردو
            </p>
          </div>
        </div>

        <nav className="tabs" role="tablist" aria-label="Sections">
          <button
            role="tab"
            aria-selected={tab === 'assistant'}
            className={tab === 'assistant' ? 'on' : ''}
            onClick={() => setTab('assistant')}
          >
            Assistant
          </button>
          <button
            role="tab"
            aria-selected={tab === 'catalog'}
            className={tab === 'catalog' ? 'on' : ''}
            onClick={() => setTab('catalog')}
          >
            Inventory
          </button>
        </nav>

        <div className="topbar-actions">
          <button
            type="button"
            className={`toggle ${voiceOn ? 'on' : ''}`}
            onClick={() => {
              setVoiceOn((v) => !v);
              if (voiceOn) cancelSpeech();
            }}
            aria-pressed={voiceOn}
            title={voiceOn ? 'Stop reading replies aloud' : 'Read replies aloud'}
          >
            {voiceOn ? 'Sound on' : 'Sound off'}
          </button>

          <button
            type="button"
            className={`status status-${status}`}
            onClick={reconnectNow}
            title="Reconnect"
          >
            <span className="dot" aria-hidden="true" />
            {statusCopy}
          </button>

          <button type="button" className="btn btn-quiet" onClick={() => setShowKeys(true)}>
            ?
          </button>
          <button type="button" className="btn btn-ghost" onClick={reset}>
            New session
          </button>
        </div>
      </header>

      {MIXED_CONTENT && (
        <div className="banner banner-error">
          This page is on https but the backend at {API_BASE} is plain http, so the
          browser blocks every request. Serve the frontend over http, or put TLS in
          front of the backend.
        </div>
      )}
      {!MIC_AVAILABLE && (
        <div className="banner">
          Voice input needs a secure page. Run the app on localhost or behind https to
          use the microphone — typing works everywhere.
        </div>
      )}

      <div className="layout">
        <main className="main">
          {tab === 'catalog' ? (
            <CarCatalog
              onAsk={askAbout}
              onBook={bookFor}
              shortlist={shortlist}
              onShortlist={toggleShortlist}
              compare={compare}
              onCompare={toggleCompare}
            />
          ) : (
            <>
              <PhaseBar phase={phase} />

              <div className="chat" ref={chatRef} onScroll={onChatScroll}>
                {messages.length === 0 && (
                  <div className="opener">
                    <p className="eyebrow">Start anywhere</p>
                    <h2>What are you looking for?</h2>
                    <p className="opener-sub">
                      Type or hold the mic. Answer in whichever language is easier —
                      the reply comes back in the same one.
                    </p>
                    <div className="chips">
                      {SUGGESTIONS.map((s) => (
                        <button
                          key={s.text}
                          type="button"
                          className="chip"
                          lang={s.lang}
                          dir={s.lang === 'ur' ? 'rtl' : 'ltr'}
                          onClick={() => send(s.text)}
                        >
                          {s.text}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {messages.map((m, i) => {
                  const urdu = isUrdu(m.text);
                  const newest = i === lastAssistantIndex;
                  return (
                    <div key={`${m.at}-${i}`} className={`turn turn-${m.role}`}>
                      <div
                        className={`bubble bubble-${m.role} ${urdu ? 'urdu' : ''}`}
                        dir={urdu ? 'rtl' : 'ltr'}
                      >
                        {m.role === 'assistant' ? (
                          <Reveal
                            text={m.text}
                            animate={newest && !prefersReducedMotion()}
                            onTick={stickToBottom}
                          />
                        ) : (
                          m.text
                        )}
                      </div>

                      {m.role !== 'error' && (
                        <div className="turn-tools">
                          <time dateTime={new Date(m.at).toISOString()}>
                            {new Date(m.at).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </time>
                          {m.spoken && <span className="tag">voice</span>}
                          <button
                            type="button"
                            onClick={() => {
                              navigator.clipboard?.writeText(m.text);
                              toast('Copied', 'ok');
                            }}
                          >
                            Copy
                          </button>
                          {m.role === 'assistant' && (
                            <button type="button" onClick={() => speak(m.text, { force: true })}>
                              Play
                            </button>
                          )}
                          {m.role === 'user' && (
                            <button type="button" onClick={() => send(m.text)}>
                              Send again
                            </button>
                          )}
                        </div>
                      )}

                      {m.inspection && (
                        <InspectionCard
                          inspection={m.inspection}
                          car={m.selectedCar || selectedCar}
                          onToast={toast}
                        />
                      )}

                      {m.cars?.length > 0 && !m.inspection && (
                        <>
                          <p className="cars-head">
                            {m.phase === 'selected'
                              ? 'On the table'
                              : `${m.totalResults} listing${m.totalResults === 1 ? '' : 's'} matched`}
                          </p>
                          <div className="cars">
                            {m.cars.map((car) => (
                              <CarCard
                                key={`${m.at}-${car.id}`}
                                car={car}
                                selected={selectedCar?.id === car.id}
                                shortlisted={shortlist.some((c) => c.id === car.id)}
                                comparing={compare.some((c) => c.id === car.id)}
                                compareDisabled={compare.length >= 3}
                                onPick={askAbout}
                                onAsk={askAbout}
                                onShortlist={toggleShortlist}
                                onCompare={toggleCompare}
                                onBook={bookFor}
                              />
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}

                {loading && (
                  <div className="thinking" aria-live="polite">
                    <i /><i /><i />
                    <span>Looking through the inventory</span>
                  </div>
                )}
                <div ref={endRef} />
              </div>

              {!atBottom && (
                <button
                  type="button"
                  className="jump"
                  onClick={() => {
                    setAtBottom(true);
                    endRef.current?.scrollIntoView({ behavior: 'smooth' });
                  }}
                >
                  Jump to latest
                </button>
              )}

              <div className={`composer ${recorder.recording ? 'is-recording' : ''}`}>
                <VoiceGauge
                  recording={recorder.recording}
                  level={recorder.level}
                  seconds={recorder.seconds}
                  disabled={!connected || loading || !MIC_AVAILABLE}
                  onToggle={recorder.toggle}
                  onCancel={recorder.cancel}
                  label={
                    MIC_AVAILABLE
                      ? 'Record a voice message (M)'
                      : 'Microphone needs a secure page'
                  }
                />

                <textarea
                  ref={inputRef}
                  className="composer-input"
                  rows={1}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={onComposerKey}
                  dir={isUrdu(input) ? 'rtl' : 'ltr'}
                  placeholder={
                    recorder.recording
                      ? 'Listening…'
                      : PLACEHOLDERS[phase] ?? PLACEHOLDERS.searching
                  }
                  disabled={loading || !connected}
                />

                <button
                  type="button"
                  className="btn btn-send"
                  onClick={() => send()}
                  disabled={loading || !input.trim() || !connected}
                >
                  Send
                </button>
              </div>
            </>
          )}
        </main>

        <Sidebar
          status={status}
          attempts={attempts}
          latency={latency}
          sessionId={sessionId}
          phase={phase}
          slots={slots}
          totalResults={totalResults}
          pakwheelsUrl={pakwheelsUrl}
          shortlist={shortlist}
          onDraft={draft}
          onAsk={askAbout}
          onUnshortlist={toggleShortlist}
          onReconnect={reconnectNow}
        />
      </div>

      {compare.length > 0 && (
        <div className="tray">
          <span className="tray-label">
            Comparing <b className="mono">{compare.length}</b>
          </span>
          <div className="tray-items">
            {compare.map((c) => (
              <button
                key={c.id}
                type="button"
                className="tray-item"
                onClick={() => toggleCompare(c)}
                title="Remove"
              >
                {carTitle(c)} <span aria-hidden="true">×</span>
              </button>
            ))}
          </div>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setShowCompare(true)}
            disabled={compare.length < 2}
          >
            Compare
          </button>
          <button type="button" className="btn btn-quiet" onClick={() => setCompare([])}>
            Clear
          </button>
        </div>
      )}

      {showCompare && (
        <CompareModal
          cars={compare}
          onClose={() => setShowCompare(false)}
          onAsk={(car) => {
            setShowCompare(false);
            askAbout(car);
          }}
          onRemove={(car) => {
            toggleCompare(car);
            if (compare.length <= 2) setShowCompare(false);
          }}
        />
      )}

      {showKeys && <ShortcutsModal onClose={() => setShowKeys(false)} />}

      <Toasts items={toasts} onDismiss={(id) => setToasts((t) => t.filter((x) => x.id !== id))} />
    </div>
  );
}
