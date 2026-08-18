import { useState, useRef, useEffect, useCallback } from 'react';

export function useWebSocket() {
  const [connected, setConnected] = useState(false);
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
  const reconnectTimer = useRef(null);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${proto}//${window.location.host}/ws`;
    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      setConnected(true);
      setLastError(null);
      clearTimeout(reconnectTimer.current);
    };

    ws.current.onclose = () => {
      setConnected(false);
      // auto-reconnect after 2s
      reconnectTimer.current = setTimeout(connect, 2000);
    };

    ws.current.onerror = () => {
      setLastError('Connection failed');
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'connected') return;

      if (data.type === 'transcript') {
        setMessages(prev => [...prev, { role: 'user', text: data.text }]);
        return;
      }

      if (data.type === 'error') {
        setLoading(false);
        setLastError(data.message);
        setMessages(prev => [...prev, { role: 'error', text: data.message }]);
        return;
      }

      if (data.type === 'turn') {
        setLoading(false);
        setSessionId(data.session_id);
        setPhase(data.phase);
        setSlots(data.slots || {});
        setCars(data.cars || []);
        setTotalResults(data.total_results || 0);
        setPakwheelsUrl(data.pakwheels_url);
        if (data.selected_car) setSelectedCar(data.selected_car);
        if (data.inspection) setInspection(data.inspection);

        setMessages(prev => [...prev, {
          role: 'assistant',
          text: data.reply,
          cars: data.cars,
          totalResults: data.total_results,
          slots: data.slots,
          pakwheelsUrl: data.pakwheels_url,
          phase: data.phase,
          selectedCar: data.selected_car,
          inspection: data.inspection,
        }]);
      }
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      ws.current?.close();
    };
  }, [connect]);

  const sendText = useCallback((text) => {
    if (ws.current?.readyState !== WebSocket.OPEN) {
      setLastError('Not connected');
      return false;
    }
    setMessages(prev => [...prev, { role: 'user', text }]);
    setLoading(true);
    ws.current.send(JSON.stringify({ text }));
    return true;
  }, []);

  const sendAudio = useCallback(async (blob) => {
    if (ws.current?.readyState !== WebSocket.OPEN) return false;
    setLoading(true);
    const buffer = await blob.arrayBuffer();
    ws.current.send(buffer);
    return true;
  }, []);

  const reset = useCallback(() => {
    ws.current?.close();
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
    setTimeout(connect, 100);
  }, [connect]);

  return {
    connected, messages, phase, slots, cars, selectedCar, inspection,
    totalResults, pakwheelsUrl, sessionId, loading, lastError,
    sendText, sendAudio, reset,
  };
}