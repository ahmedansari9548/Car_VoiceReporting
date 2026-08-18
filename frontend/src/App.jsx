import { useState, useRef, useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import CarCard from './components/CarCard';
import InspectionCard from './components/InspectionCard';
import PhaseBar from './components/PhaseBar';
import DebugPanel from './components/DebugPanel';
import CarCatalog from './components/CarCatalog';

const SUGGESTIONS = [
  'Corolla in Lahore under 40 lakh',
  'Family car chahiye 35 lakh tak',
  'SUV Islamabad 1 crore',
  'مجھے سستی گاڑی چاہیے',
];

export default function App() {
  const {
    connected, messages, phase, slots, cars, selectedCar, inspection,
    totalResults, pakwheelsUrl, sessionId, loading, lastError,
    sendText, sendAudio, reset,
  } = useWebSocket();

  const [input, setInput] = useState('');
  const [activeTab, setActiveTab] = useState('menu'); // 'menu' or 'voice'
  const [isListening, setIsListening] = useState(false);
  const endRef = useRef(null);
  const inputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, loading]);
  useEffect(() => { if (activeTab === 'voice') inputRef.current?.focus(); }, [activeTab]);

  const send = (text) => {
    const t = (text ?? input).trim();
    if (!t || loading) return;
    if (sendText(t)) setInput('');
    if (activeTab === 'voice') inputRef.current?.focus();
  };

  const handleVoiceCommand = (car) => {
    const year = car.model_year || car.year;
    const text = `Show details and options for ${year} ${car.make} ${car.model} ${car.variant || ''} in ${car.city}`;
    setActiveTab('voice');
    setTimeout(() => {
      sendText(text);
    }, 150);
  };

  // Browser Mic Speech/Audio input recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      mediaRecorderRef.current = new MediaRecorder(stream);

      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorderRef.current.onstop = async () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await sendAudio(blob);
        stream.getTracks().forEach(t => t.stop());
      };

      mediaRecorderRef.current.start();
      setIsListening(true);
    } catch (err) {
      console.error('Microphone access denied or error:', err);
      alert('Could not access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isListening) {
      mediaRecorderRef.current.stop();
      setIsListening(false);
    }
  };

  const toggleRecording = () => {
    if (isListening) stopRecording();
    else startRecording();
  };

  return (
    <div className="app">
      <div className="main">
        {/* Header */}
        <div className="header">
          <div className="logo">🚗</div>
          <div className="header-text">
            <h1>PakWheels Voice & Menu System</h1>
            <p>{sessionId ? sessionId.slice(0, 17) : 'Find & Buy Your Next Car'}</p>
          </div>

          {/* Navigation Bar Tabs */}
          <div className="nav-tabs">
            <button
              className={`nav-tab ${activeTab === 'menu' ? 'active' : ''}`}
              onClick={() => setActiveTab('menu')}
            >
              📋 Car Menu
            </button>
            <button
              className={`nav-tab ${activeTab === 'voice' ? 'active' : ''}`}
              onClick={() => setActiveTab('voice')}
            >
              🎙️ Voice Assistant
            </button>
          </div>

          <div className="header-actions">
            <span className={`status-dot ${connected ? '' : 'off'}`} title={connected ? 'Connected' : 'Offline'} />
            <button className="btn-ghost" onClick={reset}>New session</button>
          </div>
        </div>

        {/* Tab 1: Car Catalog Menu */}
        {activeTab === 'menu' && (
          <CarCatalog onVoiceCommand={handleVoiceCommand} />
        )}

        {/* Tab 2: Voice Assistant */}
        {activeTab === 'voice' && (
          <>
            <PhaseBar phase={phase} />

            {/* Chat */}
            <div className="chat">
              {messages.length === 0 && (
                <div className="empty-state">
                  <div className="icon">🔍</div>
                  <h2>What car are you looking for?</h2>
                  <p>Speak or type in English, Urdu, or Roman Urdu</p>
                  <div className="suggestions">
                    {SUGGESTIONS.map((s, i) => (
                      <div key={i} className="suggestion" onClick={() => send(s)}>{s}</div>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((m, i) => (
                <div key={i} className={`msg ${m.role}`}>
                  <div className={`bubble ${m.role}`}>{m.text}</div>

                  {m.inspection && (
                    <InspectionCard inspection={m.inspection} car={m.selectedCar || selectedCar} />
                  )}

                  {m.cars?.length > 0 && !m.inspection && (
                    <>
                      <div className="cars-header">
                        {m.phase === 'selected' ? 'Your selection' : `${m.totalResults} cars found`}
                      </div>
                      <div className="cars">
                        {m.cars.map((car, j) => (
                          <CarCard
                            key={j}
                            car={car}
                            selected={selectedCar?.id === car.id}
                            onClick={() => send(`I am interested in the ${car.year} ${car.make} ${car.model}`)}
                          />
                        ))}
                      </div>
                    </>
                  )}
                </div>
              ))}

              {loading && <div className="typing"><i /><i /><i /></div>}
              <div ref={endRef} />
            </div>

            {/* Input Bar with Voice Mic */}
            <div className="input-bar">
              <button
                className={`btn-mic ${isListening ? 'recording' : ''}`}
                onClick={toggleRecording}
                title={isListening ? 'Click to stop & send voice' : 'Click to speak voice command'}
                disabled={loading || !connected}
              >
                {isListening ? '🛑' : '🎙️'}
              </button>
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && send()}
                placeholder={
                  isListening ? 'Listening to your voice command...' :
                    phase === 'searching' ? 'Corolla chahiye Lahore mein 40 lakh tak...' :
                      phase === 'selected' ? 'Schedule an inspection?' :
                        phase === 'inspection' ? 'Your name, phone, and preferred date...' :
                          'Anything else?'
                }
                disabled={loading || !connected}
              />
              <button className="btn-send" onClick={() => send()} disabled={loading || !input.trim() || !connected}>
                ↑
              </button>
            </div>
          </>
        )}
      </div>

      {/* Sidebar */}
      <div className="sidebar">
        <DebugPanel
          connected={connected}
          sessionId={sessionId}
          phase={phase}
          slots={slots}
          totalResults={totalResults}
          pakwheelsUrl={pakwheelsUrl}
          lastError={lastError}
        />
      </div>
    </div>
  );
}