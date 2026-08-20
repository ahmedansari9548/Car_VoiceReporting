import { useState, useRef, useEffect, useCallback } from 'react';
import { WS_URL } from '../config';

/**
 * src/hooks/useWebSocket.js
 *
 * Fixes over the previous version:
 *   - points at the real backend (src/config.js), not the Vite dev server
 *   - CONNECTING is treated as busy, so connect() can't open a second socket
 *   - reset() no longer races its own onclose handler into two live sockets
 *   - exponential backoff with jitter instead of a fixed 2s hammer
 *   - JSON.parse is guarded; one malformed frame no longer kills the handler
 *   - tracks status/attempts/latency so the UI can say something true
 */

const MAX_BACKOFF = 15000;
const PING_EVERY = 20000;

export function useWebSocket() {
  const [status, setStatus] = useState('connecting'); // connecting|online|offline
  const [attempts, setAttempts] = useState(0);
  const [latency, setLatency] = useState(null);

  const [messages, setMessages] = useState([]);
  const [phase, setPhase] = useState('searching');
  const [slots, setSlots] = useState({});
  const [cars, setCars] = useState([]);
  const [selectedCar, setSelectedCar] = useState(null);
  const [inspection, setInspection] = useState(null);
  const [totalResults, setTotalResults] = useState(0);
  const [pakwheelsUrl, setPakwheelsUrl] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastError, setLastError] = useState(null);

  const ws = useRef(null);
  const retryTimer = useRef(null);
  const pingTimer = useRef(null);
  const retries = useRef(0);
  const intentionalClose = useRef(false);
  const sentAt = useRef(null);

  const clearTimers = () => {
    clearTimeout(retryTimer.current);
    clearInterval(pingTimer.current);
    retryTimer.current = null;
    pingTimer.current = null;
  };

  const connect = useCallback(() => {
    const state = ws.current?.readyState;
    if (state === WebSocket.OPEN || state === WebSocket.CONNECTING) return;

    clearTimers();
    intentionalClose.current = false;
    setStatus('connecting');

    let socket;
    try {
      socket = new WebSocket(WS_URL);
    } catch (err) {
      setStatus('offline');
      setLastError(`Cannot open ${WS_URL}`);
      return;
    }
    ws.current = socket;

    socket.onopen = () => {
      retries.current = 0;
      setAttempts(0);
      setStatus('online');
      setLastError(null);

      pingTimer.current = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: 'ping', t: Date.now() }));
        }
      }, PING_EVERY);
    };

    socket.onclose = () => {
      clearInterval(pingTimer.current);
      setStatus('offline');
      setLoading(false);
      if (intentionalClose.current) return;

      retries.current += 1;
      setAttempts(retries.current);
      const wait = Math.min(
        MAX_BACKOFF,
        500 * 2 ** (retries.current - 1) + Math.random() * 400
      );
      retryTimer.current = setTimeout(connect, wait);
    };

    socket.onerror = () => {
      setLastError('Connection to the assistant failed');
    };

    socket.onmessage = (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }

      switch (data.type) {
        case 'connected':
          return;

        case 'pong':
          if (data.t) setLatency(Date.now() - data.t);
          return;

        case 'transcript':
          setMessages((prev) => [
            ...prev,
            { role: 'user', text: data.text, at: Date.now(), spoken: true },
          ]);
          return;

        case 'error':
          setLoading(false);
          setLastError(data.message);
          setMessages((prev) => [
            ...prev,
            { role: 'error', text: data.message, at: Date.now() },
          ]);
          return;

        case 'turn': {
          setLoading(false);
          if (sentAt.current) {
            setLatency(Date.now() - sentAt.current);
            sentAt.current = null;
          }
          setSessionId(data.session_id);
          setPhase(data.phase);
          setSlots(data.slots || {});
          setCars(data.cars || []);
          setTotalResults(data.total_results || 0);
          setPakwheelsUrl(data.pakwheels_url ?? null);
          if (data.selected_car) setSelectedCar(data.selected_car);
          if (data.inspection) setInspection(data.inspection);

          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              text: data.reply,
              at: Date.now(),
              cars: data.cars,
              totalResults: data.total_results,
              slots: data.slots,
              pakwheelsUrl: data.pakwheels_url,
              phase: data.phase,
              selectedCar: data.selected_car,
              inspection: data.inspection,
            },
          ]);
          return;
        }

        default:
      }
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      intentionalClose.current = true;
      clearTimers();
      ws.current?.close(1000, 'unmount');
    };
  }, [connect]);

  const sendText = useCallback((text) => {
    if (ws.current?.readyState !== WebSocket.OPEN) {
      setLastError('Not connected. Reconnecting…');
      return false;
    }
    sentAt.current = Date.now();
    setMessages((prev) => [...prev, { role: 'user', text, at: Date.now() }]);
    setLoading(true);
    ws.current.send(JSON.stringify({ text }));
    return true;
  }, []);

  const sendAudio = useCallback(async (blob) => {
    if (ws.current?.readyState !== WebSocket.OPEN) {
      setLastError('Not connected. Reconnecting…');
      return false;
    }
    sentAt.current = Date.now();
    setLoading(true);
    ws.current.send(await blob.arrayBuffer());
    return true;
  }, []);

  const reset = useCallback(() => {
    intentionalClose.current = true; // stop onclose from queuing its own retry
    clearTimers();
    ws.current?.close(1000, 'reset');

    setMessages([]);
    setSlots({});
    setCars([]);
    setSelectedCar(null);
    setInspection(null);
    setPhase('searching');
    setSessionId(null);
    setTotalResults(0);
    setPakwheelsUrl(null);
    setLastError(null);
    setLatency(null);
    retries.current = 0;
    setAttempts(0);

    setTimeout(connect, 60);
  }, [connect]);

  const reconnectNow = useCallback(() => {
    retries.current = 0;
    setAttempts(0);
    clearTimers();
    connect();
  }, [connect]);

  const dismissError = useCallback(() => setLastError(null), []);

  return {
    connected: status === 'online',
    status,
    attempts,
    latency,
    messages,
    phase,
    slots,
    cars,
    selectedCar,
    inspection,
    totalResults,
    pakwheelsUrl,
    sessionId,
    loading,
    lastError,
    sendText,
    sendAudio,
    reset,
    reconnectNow,
    dismissError,
  };
}
