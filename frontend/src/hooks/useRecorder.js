import { useCallback, useEffect, useRef, useState } from 'react';
import { MIC_AVAILABLE } from '../config';

/**
 * src/hooks/useRecorder.js
 *
 * MediaRecorder plus a live AnalyserNode so the mic control can show real
 * input level instead of a decorative pulse. Also supports cancelling a
 * recording without sending it, which the old inline implementation could
 * not do.
 */

const MIME_CANDIDATES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/mp4', // Safari
];

const pickMime = () =>
  MIME_CANDIDATES.find((m) => window.MediaRecorder?.isTypeSupported?.(m)) || '';

export function useRecorder({ onComplete, onError }) {
  const [recording, setRecording] = useState(false);
  const [level, setLevel] = useState(0);
  const [seconds, setSeconds] = useState(0);

  const recorder = useRef(null);
  const chunks = useRef([]);
  const stream = useRef(null);
  const audioCtx = useRef(null);
  const analyser = useRef(null);
  const raf = useRef(null);
  const tick = useRef(null);
  const cancelled = useRef(false);

  const teardown = useCallback(() => {
    cancelAnimationFrame(raf.current);
    clearInterval(tick.current);
    stream.current?.getTracks().forEach((t) => t.stop());
    audioCtx.current?.close().catch(() => {});
    stream.current = null;
    audioCtx.current = null;
    analyser.current = null;
    recorder.current = null;
    setLevel(0);
    setSeconds(0);
  }, []);

  useEffect(() => teardown, [teardown]);

  const start = useCallback(async () => {
    if (recording) return;

    if (!MIC_AVAILABLE) {
      onError?.(
        'The microphone needs a secure page. Open the app on localhost or put the site behind https.'
      );
      return;
    }

    try {
      cancelled.current = false;
      const media = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      });
      stream.current = media;

      // Live level metering
      const Ctx = window.AudioContext || window.webkitAudioContext;
      audioCtx.current = new Ctx();
      const source = audioCtx.current.createMediaStreamSource(media);
      analyser.current = audioCtx.current.createAnalyser();
      analyser.current.fftSize = 512;
      source.connect(analyser.current);

      const buffer = new Uint8Array(analyser.current.frequencyBinCount);
      const measure = () => {
        analyser.current?.getByteTimeDomainData(buffer);
        let peak = 0;
        for (let i = 0; i < buffer.length; i += 1) {
          peak = Math.max(peak, Math.abs(buffer[i] - 128) / 128);
        }
        setLevel((prev) => prev * 0.6 + peak * 0.4); // smooth
        raf.current = requestAnimationFrame(measure);
      };
      measure();

      const mime = pickMime();
      const rec = new MediaRecorder(media, mime ? { mimeType: mime } : undefined);
      chunks.current = [];
      rec.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.current.push(e.data);
      };
      rec.onstop = () => {
        const blob = new Blob(chunks.current, {
          type: mime || 'audio/webm',
        });
        const wasCancelled = cancelled.current;
        teardown();
        setRecording(false);
        if (!wasCancelled && blob.size > 1200) onComplete?.(blob);
        else if (!wasCancelled) onError?.('That clip was too short to hear.');
      };

      recorder.current = rec;
      rec.start();
      setRecording(true);
      setSeconds(0);
      tick.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    } catch (err) {
      teardown();
      setRecording(false);
      onError?.(
        err?.name === 'NotAllowedError'
          ? 'Microphone permission was denied. Allow it in your browser settings.'
          : `Microphone unavailable: ${err?.message ?? err}`
      );
    }
  }, [recording, onComplete, onError, teardown]);

  const stop = useCallback(() => {
    if (recorder.current?.state === 'recording') recorder.current.stop();
  }, []);

  const cancel = useCallback(() => {
    cancelled.current = true;
    stop();
  }, [stop]);

  const toggle = useCallback(() => {
    if (recording) stop();
    else start();
  }, [recording, start, stop]);

  return { recording, level, seconds, start, stop, cancel, toggle, available: MIC_AVAILABLE };
}
