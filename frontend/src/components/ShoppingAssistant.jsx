import React, { useState } from 'react';
import { analyticsAPI } from '../services/api';

export default function ShoppingAssistant() {
  const [items, setItems] = useState('');
  const [shoppingList, setShoppingList] = useState(null);
  const [loading, setLoading] = useState(false);

  const generateList = async () => {
    if (!items.trim()) return;

    setLoading(true);
    try {
      const res = await analyticsAPI.getShoppingList(items);

      // FIXED → backend returns { success, data: {...} }
      setShoppingList(res.data.data);

    } catch (error) {
      alert(
        'Failed to generate list: ' +
          (error.response?.data?.detail || error.message)
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
        🛒 Shopping Assistant
      </h1>
      <p className="text-gray-600 mb-8">
        AI predicts prices based on your purchase history!
      </p>

      <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
        <label className="block text-lg font-semibold text-gray-800 mb-4">
          📝 Enter items (comma-separated):
        </label>
        <textarea
          value={items}
          onChange={(e) => setItems(e.target.value)}
          placeholder="Milk, Bread, Eggs, Tomatoes, Coffee..."
          className="w-full px-6 py-4 border-2 border-gray-200 rounded-xl focus:border-purple-600 focus:outline-none text-lg"
          rows={4}
        />

        <button
          onClick={generateList}
          disabled={loading || !items.trim()}
          className="mt-4 w-full md:w-auto px-8 py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl font-semibold hover:shadow-lg disabled:opacity-50"
        >
          {loading ? '⏳ Analyzing...' : '🎯 Generate Smart List'}
        </button>
      </div>

      {shoppingList && (
        <div className="bg-white rounded-2xl shadow-lg p-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-purple-50 rounded-xl p-6 text-center">
              <div className="text-3xl mb-2">📦</div>
              <div className="text-2xl font-bold text-purple-600">
                {shoppingList.item_count}
              </div>
              <div className="text-gray-600 mt-1">Items</div>
            </div>

            <div className="bg-blue-50 rounded-xl p-6 text-center">
              <div className="text-3xl mb-2">💰</div>
              <div className="text-2xl font-bold text-blue-600">
                ₹{shoppingList.total_estimated?.toFixed(0)}
              </div>
              <div className="text-gray-600 mt-1">Est. Total</div>
            </div>

            <div className="bg-green-50 rounded-xl p-6 text-center">
              <div className="text-3xl mb-2">💚</div>
              <div className="text-2xl font-bold text-green-600">
                ₹{shoppingList.savings_potential?.toFixed(0)}
              </div>
              <div className="text-gray-600 mt-1">Potential Savings</div>
            </div>
          </div>

          <h3 className="text-2xl font-bold mb-6 text-gray-800">
            Shopping List
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b-2 border-gray-200">
                  <th className="text-left px-6 py-4 font-semibold text-gray-700">
                    Item
                  </th>
                  <th className="text-right px-6 py-4 font-semibold text-gray-700">
                    Predicted Price
                  </th>
                  <th className="text-left px-6 py-4 font-semibold text-gray-700">
                    Best Store
                  </th>
                  <th className="text-right px-6 py-4 font-semibold text-gray-700">
                    Best Price
                  </th>
                  <th className="text-center px-6 py-4 font-semibold text-gray-700">
                    Trend
                  </th>
                </tr>
              </thead>

              <tbody>
                {shoppingList.items?.map((item, idx) => (
                  <tr
                    key={idx}
                    className="border-b border-gray-100 hover:bg-gray-50"
                  >
                    <td className="px-6 py-4 font-medium text-gray-800">
                      {item.item}
                    </td>

                    <td className="px-6 py-4 text-right font-semibold text-gray-800">
                      ₹{item.predicted_price?.toFixed(2) || 'N/A'}
                    </td>

                    <td className="px-6 py-4 text-gray-600">
                      {item.best_store || 'Unknown'}
                    </td>

                    <td className="px-6 py-4 text-right font-semibold text-green-600">
                      ₹{item.best_store_price?.toFixed(2) || 'N/A'}
                    </td>

                    <td className="px-6 py-4 text-center">
                      {item.price_trend === 'up'
                        ? '📈'
                        : item.price_trend === 'down'
                        ? '📉'
                        : '➡️'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button className="mt-6 w-full md:w-auto px-8 py-3 bg-green-600 text-white rounded-xl font-semibold hover:bg-green-700">
            📥 Download List
          </button>
        </div>
      )}
    </div>
  );
}
