import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function SettingsModal({ isOpen, onClose }) {
  const [geminiKey, setGeminiKey] = useState('');
  const [sarvamKey, setSarvamKey] = useState('');
  const [isSaved, setIsSaved] = useState(false);

  useEffect(() => {
    // Load from local storage initially
    const storedGemini = localStorage.getItem('GEMINI_API_KEY') || '';
    const storedSarvam = localStorage.getItem('SARVAM_API_KEY') || '';
    setGeminiKey(storedGemini);
    setSarvamKey(storedSarvam);
  }, []);

  const handleSave = () => {
    if (geminiKey) localStorage.setItem('GEMINI_API_KEY', geminiKey);
    if (sarvamKey) localStorage.setItem('SARVAM_API_KEY', sarvamKey);
    
    setIsSaved(true);
    setTimeout(() => {
      setIsSaved(false);
      onClose();
    }, 1000);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="settings-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="settings-modal glass-panel"
            initial={{ y: 50, opacity: 0, scale: 0.95 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: 20, opacity: 0, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
          >
            <div className="settings-header">
              <h2>Configuration</h2>
              <button className="close-btn" onClick={onClose}>&times;</button>
            </div>
            
            <p className="settings-desc">
              Enter your API keys to enable multimodal analysis and synthesis.
              Keys are stored locally in your browser.
            </p>

            <div className="form-group">
              <label>Gemini API Key</label>
              <input
                type="password"
                placeholder="AIzaSy..."
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                className="glass-input"
              />
            </div>

            <div className="form-group">
              <label>Sarvam API Key (TTS/STT)</label>
              <input
                type="password"
                placeholder="Enter Sarvam key..."
                value={sarvamKey}
                onChange={(e) => setSarvamKey(e.target.value)}
                className="glass-input"
              />
            </div>

            <div className="settings-actions">
              <button className="btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button className="btn-primary" onClick={handleSave}>
                {isSaved ? 'Saved! ✓' : 'Save Keys'}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
