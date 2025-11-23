import React, { useState } from 'react';
import { chatAPI } from '../services/api';

export default function VoiceInterface({ user }) {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  const [recognition, setRecognition] = useState(null);

  const startRecording = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert('Speech recognition not supported in this browser. Try Chrome.');
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognizer = new SpeechRecognition();
    
    recognizer.continuous = false;
    recognizer.interimResults = false;
    recognizer.lang = 'en-US';

    recognizer.onstart = () => {
      setIsRecording(true);
      setTranscript('');
      setResponse('');
    };

    recognizer.onresult = async (event) => {
      const text = event.results[0][0].transcript;
      setTranscript(text);
      
      // Send to backend
      try {
        const { data } = await chatAPI.sendMessage(text);
        setResponse(data.message);
        
        // Speak response
        if ('speechSynthesis' in window) {
          const utterance = new SpeechSynthesisUtterance(data.message.substring(0, 200));
          window.speechSynthesis.speak(utterance);
        }
      } catch (error) {
        setResponse('Error: ' + error.message);
      }
    };

    recognizer.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      setIsRecording(false);
    };

    recognizer.onend = () => {
      setIsRecording(false);
    };

    recognizer.start();
    setRecognition(recognizer);
  };

  const stopRecording = () => {
    if (recognition) {
      recognition.stop();
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
        🎤 Voice Commands
      </h1>
      <p className="text-gray-600 mb-8">Speak naturally - AI understands!</p>

      <div className="bg-gradient-to-br from-purple-500 to-blue-600 rounded-3xl p-12 text-center shadow-2xl mb-8">
        <div className="text-white mb-8">
          <div className="text-6xl mb-4">
            {isRecording ? '🎙️' : '🎤'}
          </div>
          <h2 className="text-3xl font-bold mb-2">
            {isRecording ? 'Listening...' : 'Ready to Listen'}
          </h2>
          <p className="text-purple-100">
            {isRecording ? 'Speak now!' : 'Click the button to start'}
          </p>
        </div>

        <button
          onClick={isRecording ? stopRecording : startRecording}
          className={`px-12 py-6 rounded-2xl font-bold text-xl transition-all shadow-lg ${
            isRecording
              ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse'
              : 'bg-white text-purple-600 hover:shadow-2xl hover:scale-105'
          }`}
        >
          {isRecording ? '⏹️ Stop Recording' : '🎤 Start Recording'}
        </button>
      </div>

      {transcript && (
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-6">
          <h3 className="text-xl font-bold mb-4 text-gray-800">🎤 You Said:</h3>
          <p className="text-lg text-gray-700 bg-gray-50 p-6 rounded-xl">
            "{transcript}"
          </p>
        </div>
      )}

      {response && (
        <div className="bg-white rounded-2xl shadow-lg p-8">
          <h3 className="text-xl font-bold mb-4 text-gray-800">💬 AI Response:</h3>
          <div className="text-gray-700 bg-purple-50 p-6 rounded-xl">
            <pre className="whitespace-pre-wrap font-sans">{response}</pre>
          </div>
        </div>
      )}

      <div className="mt-8 bg-blue-50 rounded-2xl p-6">
        <h4 className="font-bold text-gray-800 mb-3">💡 Try saying:</h4>
        <ul className="space-y-2 text-gray-700">
          <li>• "Saved 200 rupees today"</li>
          <li>• "Spent 500 on groceries at D-Mart"</li>
          <li>• "How much did I spend on food?"</li>
          <li>• "Give me a summary"</li>
        </ul>
      </div>
    </div>
  );
}
