// FULLY UPDATED UploadInvoice.jsx
// (with backend-compatible response handling)

import React, { useState } from 'react';
import { billsAPI } from '../services/api';

export default function UploadInvoice({ user }) {
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [bulkMode, setBulkMode] = useState(false);

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);

    if (selectedFiles.length > 10) {
      alert('❌ Maximum 10 files at once!');
      return;
    }

    setFiles(selectedFiles);

    const newPreviews = selectedFiles.map((file) => URL.createObjectURL(file));
    setPreviews(newPreviews);

    if (selectedFiles.length > 1) setBulkMode(true);
  };

  const uploadSingle = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await billsAPI.upload(formData);
      const result = res.data.data; // FIXED

      return {
        filename: file.name,
        success: true,
        document_id: result.document_id,
        suggestions: result.suggestions || [],
      };
    } catch (error) {
      return {
        filename: file.name,
        success: false,
        error: error.response?.data?.detail || error.message,
      };
    }
  };

  const uploadBulk = async () => {
    setLoading(true);
    setResults([]);

    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));

    try {
      const res = await billsAPI.bulkUpload(formData);
      const result = res.data.data; // FIXED

      setResults(result.results || []);

      alert(`✅ Upload complete! ${result.successful}/${result.total} successful`);
    } catch (error) {
      alert('Bulk upload failed: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const uploadAllIndividually = async () => {
    setLoading(true);
    setResults([]);

    const uploadResults = [];

    for (const file of files) {
      const result = await uploadSingle(file);
      uploadResults.push(result);
      setResults([...uploadResults]);
    }

    setLoading(false);

    const successful = uploadResults.filter((r) => r.success).length;
    alert(`✅ Upload complete! ${successful}/${files.length} successful`);
  };

  const clearAll = () => {
    setFiles([]);
    setPreviews([]);
    setResults([]);
    setBulkMode(false);
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
        📤 Upload Invoices
      </h1>
      <p className="text-gray-600 mb-8">Upload single or multiple bills - AI categorizes automatically!</p>

      <div className="bg-white rounded-2xl shadow-lg p-8 mb-6">
        <label className="block mb-4">
          <div className="border-4 border-dashed border-purple-300 rounded-2xl p-12 text-center hover:border-purple-500 transition-colors cursor-pointer">
            <input
              type="file"
              onChange={handleFileChange}
              accept="image/*"
              multiple
              className="hidden"
            />
            <div className="text-6xl mb-4">📸</div>
            <p className="text-lg font-semibold text-gray-700">Click to upload or drag & drop</p>
            <p className="text-sm text-gray-500 mt-2">PNG, JPG up to 10MB • Maximum 10 files</p>
          </div>
        </label>

        {files.length > 0 && (
          <div className="mt-6">
            <div className="flex justify-between items-center mb-4">
              <p className="font-semibold text-gray-700">
                {files.length} file{files.length > 1 ? 's' : ''} selected
              </p>
              <button onClick={clearAll} className="px-4 py-2 bg-red-100 text-red-700 rounded-xl font-semibold hover:bg-red-200">
                🗑️ Clear All
              </button>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {previews.map((preview, idx) => (
                <div key={idx} className="relative">
                  <img src={preview} alt={`Preview ${idx + 1}`} className="w-full h-32 object-cover rounded-xl shadow-md" />
                  <div className="absolute top-2 right-2 bg-white rounded-full px-2 py-1 text-xs font-bold">{idx + 1}</div>
                </div>
              ))}
            </div>

            <div className="flex gap-4">
              {bulkMode ? (
                <>
                  <button
                    onClick={uploadBulk}
                    disabled={loading}
                    className="flex-1 px-6 py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl font-semibold hover:shadow-lg disabled:opacity-50"
                  >
                    {loading ? '⏳ Processing Bulk...' : '🚀 Bulk Upload (Faster)'}
                  </button>

                  <button
                    onClick={uploadAllIndividually}
                    disabled={loading}
                    className="flex-1 px-6 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-semibold hover:shadow-lg disabled:opacity-50"
                  >
                    {loading ? '⏳ Processing...' : '📋 Process Individually'}
                  </button>
                </>
              ) : (
                <button
                  onClick={uploadAllIndividually}
                  disabled={loading}
                  className="w-full px-6 py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl font-semibold hover:shadow-lg disabled:opacity-50"
                >
                  {loading ? '⏳ Processing...' : '🚀 Process with OCR'}
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {results.length > 0 && (
        <div className="bg-white rounded-2xl shadow-lg p-8">
          <h3 className="text-2xl font-bold mb-6 text-gray-800">📊 Upload Results</h3>

          <div className="space-y-3">
            {results.map((result, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-xl border-l-4 ${
                  result.success ? 'bg-green-50 border-green-500' : 'bg-red-50 border-red-500'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="font-semibold text-gray-800">{result.success ? '✅' : '❌'} {result.filename}</div>

                    {result.success ? (
                      <div className="mt-2 text-sm text-gray-600">
                        <div>📄 Document ID: {result.document_id}</div>

                        {result.suggestions?.length > 0 && (
                          <div className="mt-1">
                            💡 Suggestions: {result.suggestions.map((s) => s[0]).join(', ')}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="mt-1 text-sm text-red-600">{result.error}</div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 p-4 bg-blue-50 rounded-xl">
            <div className="text-sm text-blue-800">
              <strong>Summary:</strong> {results.filter((r) => r.success).length} successful,{' '}
              {results.filter((r) => !r.success).length} failed
            </div>
          </div>
        </div>
      )}
    </div>
  );
}