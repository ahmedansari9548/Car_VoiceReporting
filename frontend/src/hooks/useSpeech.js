import { useCallback, useEffect, useRef, useState } from 'react';
import { isUrdu } from '../lib/format';

/**
 * src/hooks/useSpeech.js
 *
 * Reads assistant replies aloud. Picks an Urdu voice for Urdu script and an
 * English voice otherwise, so a bilingual reply is never read by the wrong
 * engine. Voices load asynchronously in Chrome, hence the voiceschanged
 * listener.
 */
export function useSpeech(enabled) {
  const [voices, setVoices] = useState([]);
  const [speaking, setSpeaking] = useState(false);
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window;
  const current = useRef(null);

  useEffect(() => {
    if (!supported) return undefined;
    const load = () => setVoices(window.speechSynthesis.getVoices());
    load();
    window.speechSynthesis.addEventListener('voiceschanged', load);
    return () => window.speechSynthesis.removeEventListener('voiceschanged', load);
  }, [supported]);

  const pickVoice = useCallback(
    (urdu) => {
      const want = urdu ? ['ur-pk', 'ur-in', 'ur'] : ['en-gb', 'en-us', 'en'];
      for (const tag of want) {
        const hit = voices.find((v) => v.lang?.toLowerCase().startsWith(tag));
        if (hit) return hit;
      }
      return null;
    },
    [voices]
  );

  const cancel = useCallback(() => {
    if (!supported) return;
    window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [supported]);

  const speak = useCallback(
    (text, { force = false } = {}) => {
      if (!supported || !text) return;
      if (!enabled && !force) return;

      window.speechSynthesis.cancel();
      const urdu = isUrdu(text);
      const utter = new SpeechSynthesisUtterance(text);
      const voice = pickVoice(urdu);
      if (voice) utter.voice = voice;
      utter.lang = urdu ? 'ur-PK' : 'en-GB';
      utter.rate = urdu ? 0.92 : 1;
      utter.onstart = () => setSpeaking(true);
      utter.onend = () => setSpeaking(false);
      utter.onerror = () => setSpeaking(false);
      current.current = utter;
      window.speechSynthesis.speak(utter);
    },
    [supported, enabled, pickVoice]
  );

  useEffect(() => {
    if (!enabled) cancel();
  }, [enabled, cancel]);

  return { speak, cancel, speaking, supported };
}

/** Tiny localStorage-backed state. Wrapped so private mode can't crash boot. */
export function usePersistentState(key, initial) {
  const [value, setValue] = useState(() => {
    try {
      const raw = window.localStorage.getItem(key);
      return raw === null ? initial : JSON.parse(raw);
    } catch {
      return initial;
    }
  });

  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* storage unavailable — keep working in memory */
    }
  }, [key, value]);

  return [value, setValue];
}
