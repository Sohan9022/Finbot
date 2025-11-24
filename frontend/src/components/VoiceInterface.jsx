import React, { useState, useRef } from 'react';
import { chatAPI } from "../services/api";   // correct path for YOUR project

export default function VoiceInterface({ user }) {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  const recognitionRef = useRef(null);

  const startRecording = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert('Speech recognition not supported in this browser. Try Chrome.');
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognizer = new SpeechRecognition();

    // Indian English model for accuracy
    recognizer.lang = 'en-IN';

    recognizer.continuous = false;
    recognizer.interimResults = false;

    recognizer.onstart = () => {
      recognitionRef.current = recognizer;
      setIsRecording(true);
      setTranscript('');
      setResponse('');
    };

    recognizer.onresult = async (event) => {
      const text = event.results?.[0]?.[0]?.transcript || "";
      setTranscript(text);

      if (!text.trim()) {
        setResponse("❌ I couldn't understand you.");
        setIsRecording(false);
        return;
      }

      try {
        // IMPORTANT: Send only message; no chat_id field
        const { data } = await chatAPI.sendMessage(text);

        const reply = data?.reply || data?.message || "⚠️ No response from AI.";
        setResponse(reply);

        if ('speechSynthesis' in window && reply) {
          const utterance = new SpeechSynthesisUtterance(reply.substring(0, 200));

          const voices = window.speechSynthesis.getVoices();
          const enInVoice = voices.find(v => v.lang.includes("en-IN"));
          if (enInVoice) utterance.voice = enInVoice;

          window.speechSynthesis.speak(utterance);
        }

      } catch (error) {
        const err = error.response?.data || error.message;
        setResponse("❌ Error: " + JSON.stringify(err));
      } finally {
        setIsRecording(false);
      }
    };

    recognizer.onerror = () => {
      setIsRecording(false);
    };

    recognizer.onend = () => {
      setIsRecording(false);
    };

    recognizer.start();
  };

  const stopRecording = () => {
    const rec = recognitionRef.current;
    if (rec) {
      try { rec.stop(); } catch (_) {}
    }
    setIsRecording(false);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">

      {/* Waveform + Glow Styles */}
      <style>{`
        .mic-button { transition: 0.2s; }
        .mic-glow {
          box-shadow: 0 0 20px rgba(99,102,241,0.6),
                      0 0 40px rgba(99,102,241,0.4);
          transform: scale(1.02);
        }
        .waveform {
          display: flex;
          gap: 6px;
          height: 36px;
          justify-content: center;
          margin: 12px 0;
        }
        .bar {
          width: 6px;
          background: rgba(255,255,255,0.8);
          border-radius: 4px;
          animation: bounce 0.8s infinite ease-in-out;
        }
        @keyframes bounce {
          0% { height: 6px; opacity: 0.3; }
          50% { height: 30px; opacity: 1; }
          100% { height: 6px; opacity: 0.3; }
        }
        .paused .bar {
          animation-play-state: paused;
          opacity: 0.2 !important;
          height: 6px !important;
        }
      `}</style>

      <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
        🎤 Voice Commands
      </h1>

      <div className="bg-gradient-to-br from-purple-500 to-blue-600 rounded-3xl p-12 text-center shadow-2xl mb-8">
        
        {/* Waveform */}
        <div className={`waveform ${isRecording ? "" : "paused"}`}>
          <div className="bar" />
          <div className="bar" style={{ animationDelay: "0.1s" }} />
          <div className="bar" style={{ animationDelay: "0.2s" }} />
          <div className="bar" style={{ animationDelay: "0.3s" }} />
          <div className="bar" style={{ animationDelay: "0.4s" }} />
        </div>

        <button
          onClick={isRecording ? stopRecording : startRecording}
          className={`mic-button px-12 py-6 rounded-2xl font-bold text-xl ${
            isRecording
              ? "bg-red-500 text-white mic-glow"
              : "bg-white text-purple-600 hover:shadow-xl hover:scale-105"
          }`}
        >
          {isRecording ? "⏹ Stop" : "🎤 Start Recording"}
        </button>
      </div>

      {/* Transcript */}
      {transcript && (
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-6">
          <h3 className="text-xl font-bold mb-3">🎤 You Said:</h3>
          <p className="text-gray-700 text-lg">"{transcript}"</p>
        </div>
      )}

      {/* AI Response */}
      {response && (
        <div className="bg-white rounded-2xl shadow-lg p-8">
          <h3 className="text-xl font-bold mb-3">💬 AI Response:</h3>
          <p className="text-gray-800 whitespace-pre-wrap">{response}</p>
        </div>
      )}
    </div>
  );
}
