// src/pages/PaymentTracker.jsx
import React, { useEffect, useState } from "react";
import { billsAPI } from "../services/api";

export default function PaymentTracker() {
  const [bills, setBills] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("unpaid"); // default unpaid

  // Load on mount and when filter changes
  useEffect(() => {
    loadData();
  }, [filter]);

  // --------------------------------------------
  // LOAD BILLS + REMINDERS (fixed backend format)
  // --------------------------------------------
  const loadData = async () => {
    setLoading(true);
    try {
      const [billsRes, remindersRes] = await Promise.all([
        billsAPI.list({
          status: filter === "all" ? undefined : filter,
          limit: 500,
          offset: 0,
        }),
        billsAPI.getReminders(30),
      ]);

      // Backend returns { success, data: { bills: [...] } }
      setBills(billsRes?.data?.data?.bills || []);

      // Backend returns { success, data: { reminders: [...] } }
      setReminders(remindersRes?.data?.data?.reminders || []);
    } catch (err) {
      console.error("Load error:", err);
    } finally {
      setLoading(false);
    }
  };

  // --------------------------------------------
  // MARK BILL AS PAID
  // --------------------------------------------
  const handleMarkAsPaid = async (billId) => {
    if (!window.confirm("Mark this bill as paid?")) return;

    try {
      await billsAPI.markAsPaid(billId, {
        payment_date: new Date().toISOString(),
        payment_method: "manual",
      });

      loadData();
    } catch (err) {
      alert("Failed to mark as paid: " + (err.response?.data?.detail || err.message));
    }
  };

  // computed
  const pendingBills = bills.filter((b) => b.payment_status !== "paid");
  const totalPending = pendingBills.reduce(
    (sum, b) => sum + (parseFloat(b.total_amount || b.amount || 0) || 0),
    0
  );

  const overdueCount = reminders.length;

  const fmtDate = (d) => {
    try {
      return d ? new Date(d).toLocaleDateString() : "—";
    } catch {
      return "—";
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-4xl font-bold mb-8 bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
        💳 Payment Tracker
      </h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-2xl p-8 text-white shadow-lg">
          <div className="text-4xl mb-3">⏰</div>
          <div className="text-4xl font-bold mb-2">{pendingBills.length}</div>
          <div className="text-orange-100">Pending Bills</div>
        </div>

        <div className="bg-gradient-to-br from-red-500 to-red-600 rounded-2xl p-8 text-white shadow-lg">
          <div className="text-4xl mb-3">💰</div>
          <div className="text-4xl font-bold mb-2">₹{totalPending.toFixed(0)}</div>
          <div className="text-red-100">Amount Due</div>
        </div>

        <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl p-8 text-white shadow-lg">
          <div className="text-4xl mb-3">⚠️</div>
          <div className="text-4xl font-bold mb-2">{overdueCount}</div>
          <div className="text-purple-100">Due This Month</div>
        </div>
      </div>

      {/* Urgent Reminders */}
      {reminders.length > 0 && (
        <div className="bg-gradient-to-r from-red-50 to-orange-50 border-l-4 border-red-500 rounded-2xl p-6 mb-8">
          <h3 className="text-xl font-bold text-red-800 mb-4">
            🔔 Urgent Payment Reminders
          </h3>

          <div className="space-y-3">
            {reminders.slice(0, 5).map((r) => (
              <div
                key={r.id}
                className="bg-white rounded-xl p-4 flex items-center justify-between"
              >
                <div className="flex-1">
                  <div className="font-semibold text-gray-800">
                    {r.merchant_name || r.category || "Bill"}
                  </div>
                  <div className="text-sm text-gray-600">
                    Due: {fmtDate(r.bill_date)}
                    {new Date(r.bill_date) < new Date() && (
                      <span className="ml-2 text-red-600 font-semibold">(OVERDUE)</span>
                    )}
                  </div>
                </div>

                <div className="text-right mr-4">
                  <div className="text-xl font-bold text-red-600">
                    ₹{(r.total_amount || r.amount || 0).toFixed(0)}
                  </div>
                </div>

                <button
                  onClick={() => handleMarkAsPaid(r.id)}
                  className="px-4 py-2 bg-green-600 text-white rounded-xl font-semibold hover:bg-green-700 text-sm"
                >
                  ✅ Pay
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
        <div className="flex gap-4">
          {["all", "unpaid", "pending", "paid"].map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-6 py-2 rounded-xl font-semibold transition-all ${
                filter === status
                  ? "bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow-lg"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Bills List */}
      {loading ? (
        <div className="text-center py-12">
          <div className="text-6xl mb-4 animate-pulse">💳</div>
          <p className="text-gray-600">Loading payments...</p>
        </div>
      ) : pendingBills.length === 0 ? (
        <div className="bg-white rounded-2xl shadow-lg p-12 text-center">
          <div className="text-6xl mb-4">🎉</div>
          <h3 className="text-2xl font-bold text-gray-800 mb-2">All Caught Up!</h3>
          <p className="text-gray-600">No pending payments</p>
        </div>
      ) : (
        <div className="space-y-4">
          {bills.map((bill) => (
            <div
              key={bill.id}
              className="bg-white rounded-2xl shadow-lg p-6 hover:shadow-xl transition-shadow"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-4 mb-2">
                    <div className="text-3xl">
                      {bill.payment_status === "paid"
                        ? "✅"
                        : bill.payment_status === "pending"
                        ? "⏳"
                        : "❌"}
                    </div>
                    <div>
                      <h3 className="text-xl font-bold text-gray-800">
                        {bill.category || bill.merchant_name || "Uncategorized"}
                      </h3>
                      <p className="text-gray-600 text-sm">
                        {fmtDate(bill.bill_date || bill.created_at)} • {bill.filename}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-3xl font-bold text-gray-800 mb-2">
                    ₹{(bill.total_amount || bill.amount || 0).toFixed(2)}
                  </div>
                  <span
                    className={`inline-block px-4 py-2 rounded-full text-sm font-semibold ${
                      bill.payment_status === "paid"
                        ? "bg-green-100 text-green-700"
                        : bill.payment_status === "pending"
                        ? "bg-orange-100 text-orange-700"
                        : "bg-red-100 text-red-700"
                    }`}
                  >
                    {bill.payment_status?.toUpperCase()}
                  </span>
                </div>
              </div>

              {bill.payment_status !== "paid" && (
                <div className="mt-4 pt-4 border-t border-gray-100 flex gap-3">
                  <button
                    onClick={() => handleMarkAsPaid(bill.id)}
                    className="px-6 py-2 bg-green-600 text-white rounded-xl font-semibold hover:bg-green-700"
                  >
                    ✅ Mark as Paid
                  </button>

                  <button className="px-6 py-2 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700">
                    💳 Add Payment Details
                  </button>

                  <button className="px-6 py-2 bg-purple-600 text-white rounded-xl font-semibold hover:bg-purple-700">
                    🔔 Set Reminder
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
