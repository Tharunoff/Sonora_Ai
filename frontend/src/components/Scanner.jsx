import React, { useEffect, useRef, useState, useCallback } from 'react';

// ── VAD Tuning Constants ───────────────────────────────────────────────────
const SPEECH_THRESHOLD   = 18;   // RMS dB above noise floor → speech detected
const SILENCE_TIMEOUT_MS = 1800; // ms of silence after speech → stop & send
const MAX_RECORD_MS      = 30000; // hard cap: force-send after 30s
const VAD_POLL_MS        = 50;    // how often we sample the analyser (~20fps)
// ──────────────────────────────────────────────────────────────────────────

export default function Scanner({ onPayloadReady, disabled }) {
  const videoRef         = useRef(null);
  const streamRef        = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef   = useRef([]);
  const analyserRef      = useRef(null);
  const vadTimerRef      = useRef(null);   // silence debounce timer
  const maxTimerRef      = useRef(null);   // hard-cap timer
  const isSpeakingRef    = useRef(false);  // are we currently recording?
  const disabledRef      = useRef(disabled);
  const vadLoopRef       = useRef(null);   // requestAnimationFrame id

  const [vadStatus, setVadStatus]   = useState('Listening…');
  const [volumeLevel, setVolumeLevel] = useState(0); // 0–100 for meter
  const [recDuration, setRecDuration] = useState(0);
  const recStartRef = useRef(null);

  // Keep disabledRef in sync
  useEffect(() => { disabledRef.current = disabled; }, [disabled]);

  // ── Helpers ──────────────────────────────────────────────────────────────

  const getRMS = useCallback(() => {
    const analyser = analyserRef.current;
    if (!analyser) return 0;
    const buf = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(buf);
    let sum = 0;
    for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
    return Math.sqrt(sum / buf.length); // 0–255 range
  }, []);

  const buildPayload = useCallback((blob, mimeType) => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        let faceCropB64 = '';
        try {
          const v = videoRef.current;
          if (v && v.videoWidth > 0) {
            const tmp = document.createElement('canvas');
            tmp.width  = v.videoWidth;
            tmp.height = v.videoHeight;
            tmp.getContext('2d').drawImage(v, 0, 0);
            faceCropB64 = tmp.toDataURL('image/jpeg', 0.7);
          }
        } catch (_) {}

        resolve({
          timestamp:    Date.now(),
          audio_b64:    reader.result,
          face_crop_b64: faceCropB64,
          metrics:      { ear: '0.000', target_pts: 0 },
          data:         { coordinates: [] },
        });
      };
      reader.readAsDataURL(blob);
    });
  }, []);

  const stopRecording = useCallback(() => {
    const mr = mediaRecorderRef.current;
    if (!mr || mr.state !== 'recording') return;
    mr.stop();
    clearTimeout(maxTimerRef.current);
    clearTimeout(vadTimerRef.current);
    isSpeakingRef.current = false;
    setVadStatus('Processing…');
    setRecDuration(0);
    recStartRef.current = null;
  }, []);

  const startRecording = useCallback(() => {
    if (disabledRef.current) return;
    const mr = mediaRecorderRef.current;
    if (!mr || mr.state === 'recording') return;

    audioChunksRef.current = [];
    mr.start(200); // collect data every 200ms
    isSpeakingRef.current = true;
    recStartRef.current = Date.now();
    setVadStatus('🎙️ Recording…');

    // Hard-cap: send after MAX_RECORD_MS even if still speaking
    maxTimerRef.current = setTimeout(() => {
      console.log('[VAD] Max duration hit, force-stopping.');
      stopRecording();
    }, MAX_RECORD_MS);
  }, [stopRecording]);

  // ── VAD Loop (throttled to VAD_POLL_MS) ──────────────────────────

  const lastVadPollRef = useRef(0);

  const vadLoop = useCallback(() => {
    const now = performance.now();
    if (now - lastVadPollRef.current >= VAD_POLL_MS) {
      lastVadPollRef.current = now;

      const rms = getRMS();
      const lvl = Math.min(100, (rms / 255) * 100 * 3);
      setVolumeLevel(lvl);

      const isSpeech = rms > SPEECH_THRESHOLD;

      if (!disabledRef.current) {
        if (isSpeech) {
          if (vadTimerRef.current) {
            clearTimeout(vadTimerRef.current);
            vadTimerRef.current = null;
          }
          if (!isSpeakingRef.current) {
            console.log('[VAD] Speech detected — starting recording');
            startRecording();
          }
        } else {
          if (isSpeakingRef.current && !vadTimerRef.current) {
            vadTimerRef.current = setTimeout(() => {
              console.log('[VAD] Silence timeout — stopping recording');
              vadTimerRef.current = null;
              stopRecording();
            }, SILENCE_TIMEOUT_MS);
          }
        }

        if (isSpeakingRef.current && recStartRef.current) {
          setRecDuration(((Date.now() - recStartRef.current) / 1000).toFixed(1));
        }
      }
    }

    vadLoopRef.current = requestAnimationFrame(vadLoop);
  }, [getRMS, startRecording, stopRecording]);


  // ── Main Setup ─────────────────────────────────────────────────────────

  useEffect(() => {
    let audioCtx;

    async function setup() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
          audio: { echoCancellation: true, noiseSuppression: true, sampleRate: 16000 },
        });
        streamRef.current = stream;

        if (videoRef.current) videoRef.current.srcObject = stream;

        // AudioContext for VAD
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const source   = audioCtx.createMediaStreamSource(stream);
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);
        analyserRef.current = analyser;

        // MediaRecorder for capturing
        const mr = new MediaRecorder(stream);
        mediaRecorderRef.current = mr;

        mr.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) audioChunksRef.current.push(e.data);
        };

        mr.onstop = async () => {
          const chunks = [...audioChunksRef.current];
          audioChunksRef.current = [];
          if (chunks.length === 0) {
            setVadStatus('Listening…');
            return;
          }
          const blob = new Blob(chunks, { type: mr.mimeType || 'audio/webm' });
          console.log('[Scanner] Sending to STT — size:', blob.size, 'bytes');

          const payload = await buildPayload(blob, mr.mimeType);
          if (!disabledRef.current) onPayloadReady(payload);
          setVadStatus('Listening…');
        };

        // Start VAD loop
        vadLoopRef.current = requestAnimationFrame(vadLoop);
        setVadStatus('Listening…');

      } catch (err) {
        console.error('[Scanner] Setup error:', err);
        setVadStatus('ERROR: ' + err.message);
      }
    }

    setup();

    return () => {
      cancelAnimationFrame(vadLoopRef.current);
      clearTimeout(vadTimerRef.current);
      clearTimeout(maxTimerRef.current);
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
      if (audioCtx) audioCtx.close();
    };
  }, [vadLoop, buildPayload, onPayloadReady]);

  // ── Pause / Resume when disabled changes ──────────────────────────────

  useEffect(() => {
    if (disabled) {
      // Stop any in-progress recording
      stopRecording();
      setVadStatus('Paused');
      setVolumeLevel(0);
    } else {
      setVadStatus('Listening…');
    }
  }, [disabled, stopRecording]);

  // ── Derived UI values ─────────────────────────────────────────────────

  const isRecording = vadStatus === '🎙️ Recording…';
  const isProcessing = vadStatus === 'Processing…';

  return (
    <div className="scanner-wrapper">
      <video
        ref={videoRef}
        autoPlay playsInline muted
        className="scanner-video"
        style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '12px' }}
      />

      {/* HUD Overlay */}
      <div style={{
        position: 'absolute', top: 16, left: 16,
        color: '#22d3ee', fontFamily: 'monospace', fontSize: '12px',
        background: 'rgba(0,0,0,0.6)', padding: '10px 14px', borderRadius: '10px',
        lineHeight: '2', backdropFilter: 'blur(8px)',
        border: `1px solid ${isRecording ? 'rgba(239,68,68,0.5)' : 'rgba(34,211,238,0.2)'}`,
        transition: 'border-color 0.3s ease',
        minWidth: 160,
      }}>
        <div style={{ fontWeight: 700, letterSpacing: '0.08em' }}>⬡ EDGE SENSOR HUB</div>
        <div>VAD: <span style={{
          color: isRecording ? '#f87171' : isProcessing ? '#fbbf24' : '#4ade80',
          fontWeight: 600,
        }}>{vadStatus}</span></div>
        {isRecording && (
          <div>Duration: <span style={{ color: '#fbbf24' }}>{recDuration}s</span></div>
        )}
        <div style={{ marginTop: 6 }}>
          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginBottom: 3 }}>MIC LEVEL</div>
          <div style={{
            width: 120, height: 5, background: 'rgba(255,255,255,0.1)',
            borderRadius: 3, overflow: 'hidden'
          }}>
            <div style={{
              height: '100%',
              width: `${volumeLevel}%`,
              background: volumeLevel > 60
                ? 'linear-gradient(90deg,#fbbf24,#ef4444)'
                : 'linear-gradient(90deg,#22d3ee,#4ade80)',
              transition: `width ${VAD_POLL_MS}ms linear`,
              boxShadow: volumeLevel > SPEECH_THRESHOLD * 0.4
                ? '0 0 6px rgba(34,211,238,0.8)' : 'none'
            }} />
          </div>
        </div>
      </div>

      {/* Recording progress bar at bottom */}
      {isRecording && (
        <div style={{
          position: 'absolute', bottom: 0, left: 0, right: 0,
          height: '4px', background: 'rgba(0,0,0,0.4)',
          borderRadius: '0 0 12px 12px', overflow: 'hidden'
        }}>
          <div style={{
            height: '100%',
            width: `${Math.min(100, (parseFloat(recDuration) / (MAX_RECORD_MS / 1000)) * 100)}%`,
            background: 'linear-gradient(90deg, #ef4444, #f97316)',
            transition: 'width 0.1s linear',
            boxShadow: '0 0 8px rgba(239,68,68,0.6)'
          }} />
        </div>
      )}

      {/* REC dot */}
      {isRecording && (
        <div style={{
          position: 'absolute', top: 16, right: 16,
          width: 12, height: 12, borderRadius: '50%',
          background: '#ef4444',
          animation: 'pulse-ring 1.2s infinite'
        }} />
      )}

      {/* Listening indicator — subtle waveform bars */}
      {!isRecording && !isProcessing && !disabled && (
        <div style={{
          position: 'absolute', bottom: 16, right: 16,
          display: 'flex', alignItems: 'flex-end', gap: 3, height: 20
        }}>
          {[0.4, 0.7, 1, 0.6, 0.3].map((h, i) => (
            <div key={i} style={{
              width: 3, borderRadius: 2,
              height: `${Math.max(3, volumeLevel * h * 0.2)}px`,
              background: '#22d3ee',
              transition: `height ${VAD_POLL_MS}ms ease`,
              opacity: 0.7,
            }} />
          ))}
        </div>
      )}
    </div>
  );
}
