import React, { useState } from "react";
import { authAPI } from "../services/api";

export default function Login({ onLogin }) {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    full_name: "",
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isLogin) {
        // LOGIN
        const res = await authAPI.login(
          formData.username,
          formData.password
        );

        const token = res.data.data.token;

        // FETCH PROFILE with token (IMPORTANT)
        const profileRes = await authAPI.getProfile(token);
        const profile = profileRes.data.data.profile;

        // STORE and update UI
        onLogin(profile, token);
      } else {
        // REGISTER
        const payload = {
          username: formData.username,
          email: formData.email,
          password: formData.password,
          full_name: formData.full_name,
        };

        await authAPI.register(payload);

        alert("Registration successful! Please login.");
        setIsLogin(true);
      }
    } catch (error) {
      alert(error.response?.data?.detail || error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center p-6">
      <div className="bg-white rounded-3xl shadow-2xl p-12 w-full max-w-md">
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">💰</div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent mb-2">
            ChatFinance-AI
          </h1>
          <p className="text-gray-600">AI-powered financial management</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            placeholder="Username"
            value={formData.username}
            onChange={(e) =>
              setFormData({ ...formData, username: e.target.value })
            }
            className="w-full px-6 py-4 border-2 border-gray-200 rounded-xl"
            required
          />

          {!isLogin && (
            <>
              <input
                type="email"
                placeholder="Email"
                value={formData.email}
                onChange={(e) =>
                  setFormData({ ...formData, email: e.target.value })
                }
                className="w-full px-6 py-4 border-2 border-gray-200 rounded-xl"
                required
              />
              <input
                type="text"
                placeholder="Full Name"
                value={formData.full_name}
                onChange={(e) =>
                  setFormData({ ...formData, full_name: e.target.value })
                }
                className="w-full px-6 py-4 border-2 border-gray-200 rounded-xl"
                required
              />
            </>
          )}

          <input
            type="password"
            placeholder="Password"
            value={formData.password}
            onChange={(e) =>
              setFormData({ ...formData, password: e.target.value })
            }
            className="w-full px-6 py-4 border-2 border-gray-200 rounded-xl"
            required
          />

          <button
            type="submit"
            disabled={loading}
            className="w-full px-6 py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl font-semibold"
          >
            {loading ? "⏳ Please wait..." : isLogin ? "🔐 Login" : "✨ Register"}
          </button>
        </form>

        <button
          onClick={() => setIsLogin(!isLogin)}
          className="w-full mt-4 text-purple-600 font-semibold"
        >
          {isLogin
            ? "✨ Need an account? Register"
            : "🔐 Already have an account? Login"}
        </button>
      </div>
    </div>
  );
}
