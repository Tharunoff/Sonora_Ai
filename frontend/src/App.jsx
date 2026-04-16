import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useWebSocket } from './hooks/useWebSocket';
import Scanner from './components/Scanner';
import SettingsModal from './components/SettingsModal';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

export default function App() {
  const { isConnected, sendPayload, lastMessage } = useWebSocket(WS_URL);
  
  const [reconstructed, setReconstructed] = useState('');
  const [pipelineData, setPipelineData] = useState({
    transcript: '',
    emotion_context: '',
    latency: 0
  });
  const [isScanning, setIsScanning] = useState(true);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // When Scanner completes its 1.5s cycle, it hands us the payload
  const handlePayloadReady = useCallback((payload) => {
    if (isConnected) {
      // Append API keys from local storage
      const geminiKey = localStorage.getItem('GEMINI_API_KEY');
      const sarvamKey = localStorage.getItem('SARVAM_API_KEY');
      
      const payloadWithKeys = {
        ...payload,
        config: {
          ...payload.config,
          gemini_api_key: geminiKey || undefined,
          sarvam_api_key: sarvamKey || undefined,
        }
      };

      sendPayload(payloadWithKeys);
      console.log("Sent Edge Payload (1.5s Chunk) -> FastAPI", {
         pts: payload.metrics?.target_pts,
         audio_size: payload.data?.audio_chunk_b64?.length
      });
    }
  }, [isConnected, sendPayload]);

  // Handle incoming websocket messages
  useEffect(() => {
    if (!lastMessage) return;

    if (lastMessage.type === 'stt_result') {
      // ⚡ LIVE: Show STT + emotions the moment they arrive, before LLM finishes
      setPipelineData({
        transcript: lastMessage.transcript || '',
        emotion_context: lastMessage.emotion_context || '',
        latency: lastMessage.latency_sec || 0
      });
      if (lastMessage.transcript) {
        setReconstructed(`🎙️ Heard: "${lastMessage.transcript}" — Running LLM...`);
      }
    } else if (lastMessage.type === 'result' && lastMessage.reconstructed) {
      // ✅ FINAL: Full pipeline complete
      setReconstructed(lastMessage.reconstructed);
      setPipelineData(prev => ({
        ...prev,
        transcript: lastMessage.transcript || prev.transcript,
        emotion_context: lastMessage.emotion_context || prev.emotion_context,
        latency: lastMessage.latency_sec || prev.latency
      }));
      
      // Autoplay the TTS audio response if it exists
      if (lastMessage.audio_b64) {
        const audio = new Audio('data:audio/wav;base64,' + lastMessage.audio_b64);
        audio.play().catch(e => console.error('Audio playback failed:', e));
      }
    } else if (lastMessage.status === 'ack') {
      setReconstructed('Analyzing multisensory stream...');
    }
  }, [lastMessage]);

  const parseEmotionContext = (context) => {
     if (!context) return { visual: '-', acoustic: '-', gesture: '-' };
     const visualMatch = context.match(/Visual Emotion:\s*([^.]+)/);
     const acousticMatch = context.match(/Acoustic Emotion:\s*([^.]+)/);
     const gestureMatch = context.match(/Gesture Detected:\s*([^.]+)/);
     
     return {
        visual: visualMatch ? visualMatch[1].trim() : '-',
        acoustic: acousticMatch ? acousticMatch[1].trim() : '-',
        gesture: gestureMatch ? gestureMatch[1].trim() : '-',
     };
  };

  const parsedContext = parseEmotionContext(pipelineData.emotion_context);

  return (
    <div className="app-container">
      
      {/* LEFT: The Edge Scanner */}
      <Scanner onPayloadReady={handlePayloadReady} disabled={!isScanning} />

      {/* RIGHT: Modern Dashboard */}
      <div className="dashboard-section">
        
        {/* Header Panel */}
        <div className="glass-panel header">
          <div className="title-row">
            <h1>IntentCast</h1>
            <button className="btn-icon" onClick={() => setIsSettingsOpen(true)}>
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
            </button>
          </div>
          <p>Real-time Multimodal AAC Edge Hub</p>
          
          <div className="status-indicator">
             {isConnected ? 
                <><div className="status-dot"></div> Connected</> : 
                <><div className="status-dot offline"></div> Offline</>
             }
          </div>
        </div>

        {/* Live Telemetry View */}
        <div className="glass-panel telemetry-panel">
          <h3>Live Telemetry</h3>
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-label">Facial Emotion</div>
              <div className="metric-value">{parsedContext.visual}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Acoustic Urgency</div>
              <div className="metric-value">{parsedContext.acoustic}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Hand Gesture</div>
              <div className="metric-value">{parsedContext.gesture}</div>
            </div>
            <div className="metric-card">
              <div className="metric-label">LLM Latency</div>
              <div className="metric-value">{pipelineData.latency ? `${pipelineData.latency.toFixed(2)}s` : '-'}</div>
            </div>
          </div>
          
          <div className="transcript-box" style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
             <div className="metric-label">Raw Speech-to-Text (Sarvam):</div>
             <div className="metric-value" style={{ fontSize: '1.1rem', marginTop: '0.5rem', fontWeight: 400 }}>
                 {pipelineData.transcript || <span style={{opacity: 0.5}}>Awaiting speech...</span>}
             </div>
          </div>
        </div>

        {/* Final Intent Output Panel */}
        <div className="glass-panel terminal-panel">
          <h3 style={{ margin: '0 0 10px 0', fontSize: '0.9rem', color: 'rgba(255,255,255,0.6)' }}>LLM Reconstructed Intent:</h3>
          <AnimatePresence mode="wait">
             {reconstructed ? (
               <motion.span 
                 key="text"
                 initial={{ opacity: 0, y: 10 }}
                 animate={{ opacity: 1, y: 0 }}
                 exit={{ opacity: 0, y: -10 }}
                 className="output-text"
               >
                 "{reconstructed}"
               </motion.span>
             ) : (
               <motion.span 
                 key="placeholder"
                 initial={{ opacity: 0 }}
                 animate={{ opacity: 1 }}
                 className="output-text output-placeholder"
               >
                 Waiting for intent signature...
               </motion.span>
             )}
          </AnimatePresence>
        </div>

        <div className="controls">
           <button className="btn-primary" onClick={() => setIsScanning(!isScanning)}>
             {isScanning ? 'Halt Scanner' : 'Resume Scanner'}
           </button>
        </div>

      </div>

      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => setIsSettingsOpen(false)} 
      />
    </div>
  );
}
