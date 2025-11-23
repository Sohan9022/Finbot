// src/pages/ViewInvoices.jsx
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { billsAPI } from "../services/api";

/**
 * ViewInvoices - improved version
 * - Pagination (limit/offset, Next/Prev)
 * - Debounced search
 * - Safe async cancellation via mounted flag
 * - Better error handling & UX
 * - Export handling using blob content-disposition fallback
 */

const PAGE_LIMIT = 20;

export default function ViewInvoices({ user }) {
  const [bills, setBills] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Filters & sorting
  const [filter, setFilter] = useState("all");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [sortBy, setSortBy] = useState("date_desc");

  // Pagination
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);

  // Search (debounced)
  const [searchQuery, setSearchQuery] = useState("");
  const [searchText, setSearchText] = useState("");

  // UI state for editing
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedBill, setSelectedBill] = useState(null);
  const [editData, setEditData] = useState({ amount: "", category: "", payment_status: "" });

  // categories (computed from server or bills)
  const [categories, setCategories] = useState([]);

  // -----------------------------------------
  // Load bills (with params)
  // -----------------------------------------
  const loadBills = useCallback(
    async (opts = {}) => {
      setLoading(true);
      setError(null);
      let mounted = true;
      try {
        const params = {
          limit: opts.limit ?? PAGE_LIMIT,
          offset: opts.offset ?? offset,
        };

        if (filter && filter !== "all") params.status = filter;
        if (selectedCategory) params.category = selectedCategory;
        if (searchText && searchText.trim()) params.q = searchText.trim();

        // server may accept a sort param; if not, fallback to client sorting
        params.sort = sortBy;

        const res = await billsAPI.list(params);
        const data = res?.data?.data ?? {};
        const rows = data.bills || [];
        const totalRows = data.total ?? (rows.length + (params.offset || 0));

        // If backend didn't support sort param, do client-side
        let sorted = [...rows];
        switch (sortBy) {
          case "amount_asc":
            sorted.sort((a, b) => (parseFloat(a.amount) || 0) - (parseFloat(b.amount) || 0));
            break;
          case "amount_desc":
            sorted.sort((a, b) => (parseFloat(b.amount) || 0) - (parseFloat(a.amount) || 0));
            break;
          case "date_asc":
            sorted.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
            break;
          default:
            // date_desc
            sorted.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
            break;
        }

        if (mounted) {
          setBills(sorted);
          setTotal(Number(totalRows) || sorted.length);
        }
      } catch (err) {
        console.error("loadBills error:", err);
        setError(err?.response?.data?.detail || err?.message || "Failed to load invoices");
      } finally {
        if (mounted) setLoading(false);
      }

      return () => {
        mounted = false;
      };
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [filter, selectedCategory, sortBy, offset, searchText]
  );

  // -----------------------------------------
  // Load categories (smart: from server endpoint if available, else derive)
  // -----------------------------------------
  const loadCategories = useCallback(async () => {
    try {
      // prefer dedicated endpoint if implemented
      if (billsAPI.listCategories) {
        const res = await billsAPI.listCategories();
        setCategories(res?.data?.data?.categories || []);
        return;
      }

      // fallback: fetch a page and derive categories
      const res = await billsAPI.list({ limit: 500, offset: 0 });
      const rows = res?.data?.data?.bills || [];
      const unique = [...new Set(rows.map((b) => (b.category || "").trim()).filter(Boolean))];
      setCategories(unique);
    } catch (err) {
      console.warn("loadCategories:", err);
    }
  }, []);

  // -----------------------------------------
  // Debounced search effect (300ms)
  // -----------------------------------------
  useEffect(() => {
    const t = setTimeout(() => {
      // when searchText changes, go to first page
      setOffset(0);
      setSearchText(searchQuery);
    }, 300);
    return () => clearTimeout(t);
  }, [searchQuery]);

  // Load bills & categories on mount and when dependencies change
  useEffect(() => {
    let cancelled = false;
    (async () => {
      await loadBills({ offset });
      if (!cancelled) {
        loadCategories().catch(() => {});
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadBills, loadCategories, offset]);

  // When filters or sort change, reset to first page
  useEffect(() => {
    setOffset(0);
    // loadBills will trigger from dependency array
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, selectedCategory, sortBy, searchText]);

  // -----------------------------------------
  // Helpers: format date & safe number
  // -----------------------------------------
  const fmtDate = (d) => {
    try {
      return d ? new Date(d).toLocaleDateString() : "—";
    } catch {
      return "—";
    }
  };
  const safeNumber = (v) => (v == null || v === "" ? 0 : parseFloat(v) || 0);

  // -----------------------------------------
  // Actions: mark as paid / edit / delete / export
  // -----------------------------------------
  const handleMarkAsPaid = async (id) => {
    if (!window.confirm("Mark this invoice as paid?")) return;
    try {
      await billsAPI.markAsPaid(id, { payment_date: new Date().toISOString(), payment_method: "manual" });
      await loadBills({ offset: 0 });
    } catch (err) {
      console.error(err);
      alert("Failed to mark as paid: " + (err?.response?.data?.detail || err?.message || "unknown"));
    }
  };

  const handleEdit = (bill) => {
    setSelectedBill(bill);
    setEditData({
      amount: bill.amount ?? "",
      category: bill.category ?? "",
      payment_status: bill.payment_status ?? "pending",
    });
    setShowEditModal(true);
  };

  const saveEdit = async () => {
    if (!selectedBill) return;
    try {
      const payload = {
        amount: safeNumber(editData.amount),
        category: editData.category || null,
        payment_status: editData.payment_status || "pending",
      };
      await billsAPI.update(selectedBill.id, payload);
      setShowEditModal(false);
      setSelectedBill(null);
      await loadBills({ offset });
      alert("Invoice updated.");
    } catch (err) {
      console.error("saveEdit:", err);
      alert("Failed to update: " + (err?.response?.data?.detail || err?.message || "unknown"));
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to permanently delete this invoice?")) return;
    try {
      await billsAPI.delete(id);
      // after delete, keep offset but reload; if page becomes empty and offset>0, shift back
      const nextOffset = Math.max(0, offset - (bills.length === 1 ? PAGE_LIMIT : 0));
      setOffset(nextOffset);
      await loadBills({ offset: nextOffset });
      alert("Deleted.");
    } catch (err) {
      console.error("handleDelete:", err);
      alert("Delete failed: " + (err?.response?.data?.detail || err?.message || "unknown"));
    }
  };

  const handleExport = async () => {
    try {
      const params = {
        category: selectedCategory || undefined,
        status: filter !== "all" ? filter : undefined,
        q: searchText || undefined,
      };
      const res = await billsAPI.export("csv", params);
      // res.data might be blob or arraybuffer
      const blobData = res?.data;
      const blob = blobData instanceof Blob ? blobData : new Blob([blobData]);
      // attempt to use filename from content-disposition
      let filename = `bills_${Date.now()}.csv`;
      const dispo = res?.headers?.["content-disposition"] || res?.headers?.["Content-Disposition"];
      if (dispo) {
        const m = dispo.match(/filename="?([^"]+)"?/);
        if (m && m[1]) filename = m[1];
      }
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed:", err);
      alert("Export failed: " + (err?.response?.data?.detail || err?.message || "unknown"));
    }
  };

  // -----------------------------------------
  // Paging controls
  // -----------------------------------------
  const canPrev = offset > 0;
  const canNext = offset + PAGE_LIMIT < (total || bills.length);

  const goPrev = () => {
    if (!canPrev) return;
    setOffset(Math.max(0, offset - PAGE_LIMIT));
  };
  const goNext = () => {
    if (!canNext) return;
    setOffset(offset + PAGE_LIMIT);
  };

  // -----------------------------------------
  // Derived totals
  // -----------------------------------------
  const totalSpent = useMemo(() => bills.reduce((s, b) => s + safeNumber(b.amount), 0), [bills]);
  const paidAmount = useMemo(() => bills.filter((b) => b.payment_status === "paid").reduce((s, b) => s + safeNumber(b.amount), 0), [bills]);
  const pendingAmount = totalSpent - paidAmount;

  // -----------------------------------------
  // Render
  // -----------------------------------------
  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-start justify-between mb-6 gap-4">
        <h1 className="text-3xl font-bold">📋 My Invoices</h1>

        <div className="flex gap-2">
          <button onClick={handleExport} className="px-4 py-2 bg-green-600 text-white rounded-md">📥 Export CSV</button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="p-4 bg-white rounded-lg shadow">
          <div className="text-sm text-gray-500">Total Bills</div>
          <div className="text-xl font-bold">{total || bills.length}</div>
        </div>
        <div className="p-4 bg-white rounded-lg shadow">
          <div className="text-sm text-gray-500">Total Amount</div>
          <div className="text-xl font-bold">₹{totalSpent.toFixed(2)}</div>
        </div>
        <div className="p-4 bg-white rounded-lg shadow">
          <div className="text-sm text-gray-500">Paid</div>
          <div className="text-xl font-bold">₹{paidAmount.toFixed(2)}</div>
        </div>
        <div className="p-4 bg-white rounded-lg shadow">
          <div className="text-sm text-gray-500">Pending</div>
          <div className="text-xl font-bold">₹{pendingAmount.toFixed(2)}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 items-center">
          <div className="md:col-span-2 flex gap-2">
            <input
              placeholder="Search filename, merchant, item..."
              className="flex-1 border rounded-md px-3 py-2"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  setSearchText(searchQuery);
                  setOffset(0);
                }
              }}
            />
            <button
              onClick={() => { setSearchText(searchQuery); setOffset(0); }}
              className="px-3 py-2 bg-purple-600 text-white rounded-md"
            >
              🔍
            </button>
            <button onClick={() => { setSearchQuery(""); setSearchText(""); }} className="px-3 py-2 border rounded-md">Clear</button>
          </div>

          <select value={filter} onChange={(e) => setFilter(e.target.value)} className="px-3 py-2 border rounded-md">
            <option value="all">All Status</option>
            <option value="paid">Paid</option>
            <option value="pending">Pending</option>
            <option value="unpaid">Unpaid</option>
          </select>

          <select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)} className="px-3 py-2 border rounded-md">
            <option value="">All Categories</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>

          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="px-3 py-2 border rounded-md">
            <option value="date_desc">Newest First</option>
            <option value="date_asc">Oldest First</option>
            <option value="amount_desc">Highest Amount</option>
            <option value="amount_asc">Lowest Amount</option>
          </select>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="text-center py-12">Loading invoices...</div>
      ) : error ? (
        <div className="text-center text-red-600 py-6">{error}</div>
      ) : bills.length === 0 ? (
        <div className="text-center py-12">No invoices found.</div>
      ) : (
        <div className="space-y-4">
          {bills.map((bill) => (
            <div key={bill.id} className="bg-white p-4 rounded-lg shadow flex flex-col md:flex-row justify-between gap-4">
              <div className="flex gap-3 items-start">
                <div className="text-2xl">
                  {bill.category === "Groceries" ? "🛒" : bill.category === "Coffee" ? "☕" : bill.category === "Transport" ? "🚗" : "📄"}
                </div>
                <div>
                  <div className="font-semibold text-lg">{bill.category || "Uncategorized"}</div>
                  <div className="text-sm text-gray-500">{bill.filename} • {fmtDate(bill.created_at)}</div>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="text-right">
                  <div className="font-bold text-lg">₹{safeNumber(bill.amount).toFixed(2)}</div>
                  <div className={`text-sm inline-block mt-1 px-3 py-1 rounded-full ${bill.payment_status === "paid" ? "bg-green-100 text-green-700" : bill.payment_status === "pending" ? "bg-yellow-100 text-yellow-700" : "bg-red-100 text-red-700"}`}>
                    {String(bill.payment_status || "unknown").toUpperCase()}
                  </div>
                </div>

                <div className="flex gap-2">
                  {bill.payment_status !== "paid" && (
                    <button onClick={() => handleMarkAsPaid(bill.id)} className="px-3 py-2 bg-green-600 text-white rounded-md text-sm">✅ Mark as Paid</button>
                  )}
                  <button onClick={() => handleEdit(bill)} className="px-3 py-2 bg-blue-600 text-white rounded-md text-sm">✏️ Edit</button>
                  <button onClick={() => handleDelete(bill.id)} className="px-3 py-2 bg-red-600 text-white rounded-md text-sm">🗑️ Delete</button>
                </div>
              </div>
            </div>
          ))}

          {/* Pagination */}
          <div className="flex items-center justify-between mt-4">
            <div className="text-sm text-gray-600">
              Showing {Math.min(offset + 1, total || bills.length)} - {Math.min(offset + PAGE_LIMIT, (total || bills.length))} of {total || bills.length}
            </div>

            <div className="flex gap-2">
              <button onClick={goPrev} disabled={!canPrev} className={`px-3 py-2 rounded-md ${canPrev ? "bg-gray-200" : "bg-gray-100 opacity-60"}`}>Prev</button>
              <button onClick={goNext} disabled={!canNext} className={`px-3 py-2 rounded-md ${canNext ? "bg-gray-200" : "bg-gray-100 opacity-60"}`}>Next</button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold mb-4">Edit Invoice</h3>

            <div className="space-y-3">
              <div>
                <label className="block text-sm text-gray-600">Amount</label>
                <input type="number" value={editData.amount} onChange={(e) => setEditData({ ...editData, amount: e.target.value })} className="w-full border rounded-md px-3 py-2" />
              </div>

              <div>
                <label className="block text-sm text-gray-600">Category</label>
                <input type="text" value={editData.category} onChange={(e) => setEditData({ ...editData, category: e.target.value })} className="w-full border rounded-md px-3 py-2" />
              </div>

              <div>
                <label className="block text-sm text-gray-600">Payment Status</label>
                <select value={editData.payment_status} onChange={(e) => setEditData({ ...editData, payment_status: e.target.value })} className="w-full border rounded-md px-3 py-2">
                  <option value="paid">Paid</option>
                  <option value="pending">Pending</option>
                  <option value="unpaid">Unpaid</option>
                </select>
              </div>
            </div>

            <div className="mt-5 flex gap-3">
              <button onClick={saveEdit} className="flex-1 bg-purple-600 text-white px-4 py-2 rounded-md">Save</button>
              <button onClick={() => setShowEditModal(false)} className="flex-1 border px-4 py-2 rounded-md">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
