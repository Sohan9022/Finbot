import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import Login from './components/Login';
import Dashboard from './components/Dashboard';
import UploadInvoice from './components/UploadInvoice';
import ViewInvoices from './components/ViewInvoices';
import Analytics from './components/Analytics';
import ChatAssistant from './components/ChatAssistant';
import ShoppingAssistant from './components/ShoppingAssistant';
import VoiceInterface from './components/VoiceInterface';
import PaymentTracker from './components/PaymentTracker';
import UserProfile from './components/UserProfile';
import Sidebar from './components/Sidebar';

import { authAPI } from './services/api';

function App() {
  const [user, setUser] = useState(null);
  const [authenticated, setAuthenticated] = useState(false);
  const [loadingProfile, setLoadingProfile] = useState(true);

  // ------------------------------------------------------------
  // Initial Load - Check token & fetch profile if needed
  // ------------------------------------------------------------
  useEffect(() => {
    async function init() {
      const token = localStorage.getItem("token");
      const savedUser = localStorage.getItem("user");

      // CASE 1 — token + saved user → use saved user
      if (token && savedUser) {
        setUser(JSON.parse(savedUser));
        setAuthenticated(true);
        setLoadingProfile(false);
        return;
      }

      // CASE 2 — only token → fetch fresh profile
      if (token && !savedUser) {
        try {
          const res = await authAPI.getProfile(token);
          const profile = res.data.data.profile;

          setUser(profile);
          localStorage.setItem("user", JSON.stringify(profile));
          setAuthenticated(true);
        } catch (err) {
          // Invalid or expired token
          localStorage.removeItem("token");
        }
        setLoadingProfile(false);
        return;
      }

      // CASE 3 — no token → not authenticated
      setLoadingProfile(false);
    }

    init();
  }, []);

  // ------------------------------------------------------------
  // LOGIN Handler — receives (userObject, token)
  // ------------------------------------------------------------
  const handleLogin = (userObj, token) => {
    localStorage.setItem("token", token);
    localStorage.setItem("user", JSON.stringify(userObj));

    setUser(userObj);
    setAuthenticated(true);
  };

  // ------------------------------------------------------------
  // LOGOUT
  // ------------------------------------------------------------
  const handleLogout = () => {
    setUser(null);
    setAuthenticated(false);
    localStorage.removeItem("token");
    localStorage.removeItem("user");
  };

  // ------------------------------------------------------------
  // UPDATE USER (after profile edit)
  // ------------------------------------------------------------
  const handleUpdateUser = (updatedUser) => {
    setUser(updatedUser);
    localStorage.setItem("user", JSON.stringify(updatedUser));
  };

  // ------------------------------------------------------------
  // LOADING SCREEN
  // ------------------------------------------------------------
  if (loadingProfile) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-6xl mb-4">🔄</div>
          <p className="text-gray-600">Checking authentication...</p>
        </div>
      </div>
    );
  }

  // ------------------------------------------------------------
  // NOT AUTHENTICATED → Show Login Page
  // ------------------------------------------------------------
  if (!authenticated) {
    return <Login onLogin={handleLogin} />;
  }

  // ------------------------------------------------------------
  // AUTHENTICATED → Show App
  // ------------------------------------------------------------
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-gray-100">
        
        <Sidebar user={user} onLogout={handleLogout} />

        <div className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Dashboard user={user} />} />
            <Route path="/upload" element={<UploadInvoice user={user} />} />
            <Route path="/invoices" element={<ViewInvoices user={user} />} />
            <Route path="/analytics" element={<Analytics user={user} />} />
            <Route path="/chat" element={<ChatAssistant user={user} />} />
            <Route path="/shopping" element={<ShoppingAssistant user={user} />} />
            <Route path="/voice" element={<VoiceInterface user={user} />} />
            <Route path="/payments" element={<PaymentTracker user={user} />} />
            <Route path="/profile" element={<UserProfile user={user} onUpdateUser={handleUpdateUser} />} />
            
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </div>

      </div>
    </BrowserRouter>
  );
}

export default App;
