import React, { useState, useEffect } from 'react';
import { authAPI } from '../services/api';

export default function UserProfile({ user, onUpdateUser }) {
  const [profile, setProfile] = useState(null);
  const [stats, setStats] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [editData, setEditData] = useState({});
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [loading, setLoading] = useState(true);

  const token = localStorage.getItem('token');

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [profileRes, statsRes] = await Promise.all([
        authAPI.getProfile(token),
        authAPI.getStats(token),
      ]);

      // Correct extraction (backend returns profile inside data.profile)
      const profileData = profileRes?.data?.data?.profile || null;
      const statsData = statsRes?.data?.data || null;

      setProfile(profileData);
      setStats(statsData);

      if (profileData) {
        setEditData({
          full_name: profileData.full_name,
          email: profileData.email,
        });
      }

    } catch (err) {
      console.error('Failed to load profile/stats:', err);
      alert('Failed to load profile. Please login again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProfile = async () => {
    try {
      await authAPI.updateProfile(editData, token);

      await loadAll();

      const updatedUser = {
        ...user,
        full_name: editData.full_name,
        email: editData.email,
      };

      localStorage.setItem('user', JSON.stringify(updatedUser));
      onUpdateUser?.(updatedUser);

      setEditMode(false);
      alert('✅ Profile updated successfully!');
    } catch (error) {
      alert('Failed to update profile: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleChangePassword = async () => {
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      alert('❌ New passwords do not match!');
      return;
    }
    if (passwordData.newPassword.length < 6) {
      alert('❌ Password must be at least 6 characters!');
      return;
    }

    try {
      await authAPI.changePassword(
        passwordData.currentPassword,
        passwordData.newPassword,
        token
      );

      setShowPasswordModal(false);
      setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' });
      alert('✅ Password changed successfully!');
    } catch (error) {
      alert('Failed to change password: ' + (error.response?.data?.detail || error.message));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-6xl mb-4">👤</div>
          <p className="text-gray-600">Loading profile...</p>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="p-8 text-center text-red-600 text-xl font-semibold">
        Failed to load profile. Please login again.
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-4xl font-bold mb-8 bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
        👤 My Profile
      </h1>

      {/* Profile Card */}
      <div className="bg-white rounded-2xl shadow-lg p-8 mb-6">
        <div className="flex items-center gap-6 mb-8">
          <div className="w-24 h-24 bg-gradient-to-br from-purple-600 to-blue-600 rounded-full flex items-center justify-center text-white text-4xl font-bold">
            {profile.full_name?.charAt(0)?.toUpperCase() || profile.username?.charAt(0)?.toUpperCase()}
          </div>

          <div className="flex-1">
            {editMode ? (
              <div className="space-y-3">
                <input
                  type="text"
                  value={editData.full_name}
                  onChange={(e) => setEditData({ ...editData, full_name: e.target.value })}
                  className="w-full px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-purple-600 focus:outline-none"
                  placeholder="Full Name"
                />
                <input
                  type="email"
                  value={editData.email}
                  onChange={(e) => setEditData({ ...editData, email: e.target.value })}
                  className="w-full px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-purple-600 focus:outline-none"
                  placeholder="Email"
                />
              </div>
            ) : (
              <>
                <h2 className="text-3xl font-bold text-gray-800">{profile.full_name}</h2>
                <p className="text-gray-600 mt-1">@{profile.username}</p>
                <p className="text-gray-600">{profile.email}</p>
              </>
            )}
          </div>

          <div>
            {editMode ? (
              <div className="flex gap-2">
                <button
                  onClick={handleSaveProfile}
                  className="px-6 py-2 bg-green-600 text-white rounded-xl font-semibold hover:bg-green-700"
                >
                  💾 Save
                </button>
                <button
                  onClick={() => {
                    setEditMode(false);
                    setEditData({
                      full_name: profile.full_name,
                      email: profile.email,
                    });
                  }}
                  className="px-6 py-2 bg-gray-200 text-gray-700 rounded-xl font-semibold hover:bg-gray-300"
                >
                  ❌ Cancel
                </button>
              </div>
            ) : (
              <button
                onClick={() => setEditMode(true)}
                className="px-6 py-2 bg-purple-600 text-white rounded-xl font-semibold hover:bg-purple-700"
              >
                ✏️ Edit Profile
              </button>
            )}
          </div>
        </div>

        {/* Account Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-6 bg-gray-50 rounded-xl">
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">{stats?.total_bills || 0}</div>
            <div className="text-gray-600 text-sm mt-1">Total Bills</div>
          </div>

          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              ₹{Number(stats?.total_spent || 0).toFixed(0)}
            </div>
            <div className="text-gray-600 text-sm mt-1">Total Spent</div>
          </div>

          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{stats?.active_days || 0}</div>
            <div className="text-gray-600 text-sm mt-1">Active Days</div>
          </div>
        </div>
      </div>

      {/* Account Details */}
      <div className="bg-white rounded-2xl shadow-lg p-8 mb-6">
        <h3 className="text-2xl font-bold mb-6 text-gray-800">Account Details</h3>

        <div className="space-y-4">
          <div className="flex justify-between items-center py-3 border-b border-gray-100">
            <div>
              <div className="font-semibold text-gray-800">Username</div>
              <div className="text-gray-600 text-sm">Your unique identifier</div>
            </div>
            <div className="text-gray-800 font-medium">@{profile.username}</div>
          </div>

          <div className="flex justify-between items-center py-3 border-b border-gray-100">
            <div>
              <div className="font-semibold text-gray-800">Member Since</div>
              <div className="text-gray-600 text-sm">Account creation date</div>
            </div>
            <div className="text-gray-800 font-medium">
              {profile.created_at ? new Date(profile.created_at).toLocaleDateString() : '-'}
            </div>
          </div>

          <div className="flex justify-between items-center py-3 border-b border-gray-100">
            <div>
              <div className="font-semibold text-gray-800">Account Type</div>
              <div className="text-gray-600 text-sm">Your access level</div>
            </div>
            <div className="px-4 py-1 bg-purple-100 text-purple-700 rounded-full font-semibold text-sm">
              {profile.role?.toUpperCase?.() || 'USER'}
            </div>
          </div>
        </div>
      </div>

      {/* Security */}
      <div className="bg-white rounded-2xl shadow-lg p-8">
        <h3 className="text-2xl font-bold mb-6 text-gray-800">Security</h3>
        <button
          onClick={() => setShowPasswordModal(true)}
          className="w-full md:w-auto px-6 py-3 bg-red-600 text-white rounded-xl font-semibold hover:bg-red-700"
        >
          🔒 Change Password
        </button>
      </div>

      {/* Change Password Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-8 max-w-md w-full mx-4">
            <h3 className="text-2xl font-bold mb-6">Change Password</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Current Password
                </label>
                <input
                  type="password"
                  value={passwordData.currentPassword}
                  onChange={(e) => setPasswordData({ ...passwordData, currentPassword: e.target.value })}
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  New Password
                </label>
                <input
                  type="password"
                  value={passwordData.newPassword}
                  onChange={(e) => setPasswordData({ ...passwordData, newPassword: e.target.value })}
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Confirm New Password
                </label>
                <input
                  type="password"
                  value={passwordData.confirmPassword}
                  onChange={(e) => setPasswordData({ ...passwordData, confirmPassword: e.target.value })}
                  className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-600 focus:outline-none"
                />
              </div>
            </div>

            <div className="flex gap-4 mt-6">
              <button
                onClick={handleChangePassword}
                className="flex-1 px-6 py-3 bg-red-600 text-white rounded-xl font-semibold hover:bg-red-700"
              >
                🔒 Change Password
              </button>
              <button
                onClick={() => {
                  setShowPasswordModal(false);
                  setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' });
                }}
                className="flex-1 px-6 py-3 bg-gray-200 text-gray-700 rounded-xl font-semibold hover:bg-gray-300"
              >
                ❌ Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
