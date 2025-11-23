import React from 'react';
import { Link, useLocation } from 'react-router-dom';

export default function Sidebar({ user, onLogout }) {
  const location = useLocation();

  // Safe user handled via localStorage fallback
  const safeUser = user ?? JSON.parse(localStorage.getItem("user") || "{}");

  const menuItems = [
    { path: '/', icon: '📊', label: 'Dashboard' },
    { path: '/upload', icon: '📤', label: 'Upload' },
    { path: '/invoices', icon: '📋', label: 'Invoices' },
    { path: '/analytics', icon: '📈', label: 'Analytics' },
    { path: '/chat', icon: '💬', label: 'Chat' },
    { path: '/shopping', icon: '🛒', label: 'Shopping' },
    { path: '/voice', icon: '🎤', label: 'Voice' },
    { path: '/payments', icon: '💳', label: 'Payments' },
    { path: '/profile', icon: '👤', label: 'Profile' },
  ];

  return (
    <div className="w-64 bg-gradient-to-b from-purple-600 to-blue-600 text-white flex flex-col">

      {/* Logo */}
      <div className="p-6 border-b border-purple-500">
        <h1 className="text-2xl font-bold">💰 ChatFinance</h1>
        <p className="text-purple-200 text-sm mt-1">AI Powered</p>
      </div>

      {/* User */}
      <Link to="/profile" className="p-6 border-b border-purple-500 hover:bg-purple-500 transition-colors">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center text-purple-600 text-xl font-bold">
            {safeUser.full_name?.charAt(0)?.toUpperCase() || "U"}
          </div>
          <div>
            <div className="font-semibold">{safeUser.full_name || "User"}</div>
            <div className="text-sm text-purple-200">@{safeUser.username || "username"}</div>
          </div>
        </div>
      </Link>

      {/* Menu */}
      <nav className="flex-1 p-4 overflow-y-auto">
        {menuItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl mb-2 transition-all ${
              location.pathname.startsWith(item.path)
                ? 'bg-white text-purple-600 font-semibold shadow-lg'
                : 'text-white hover:bg-purple-500'
            }`}
          >
            <span className="text-2xl">{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>

      {/* Logout */}
      <div className="p-4 border-t border-purple-500">
        <button
          onClick={onLogout}
          className="w-full px-4 py-3 bg-purple-500 hover:bg-purple-400 rounded-xl font-semibold transition-colors"
        >
          🚪 Logout
        </button>
      </div>
    </div>
  );
}
