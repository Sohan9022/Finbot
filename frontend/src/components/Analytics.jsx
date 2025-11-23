import React, { useEffect, useMemo, useState } from "react";
import { analyticsAPI } from "../services/api";
import { Line, Pie, Bar } from "react-chartjs-2";

import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(
  ArcElement,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

export default function Analytics() {
  // -------------------
  // State (all hooks at top)
  // -------------------
  const [dashboard, setDashboard] = useState(null);
  const [dailyData, setDailyData] = useState(null);
  const [monthlyData, setMonthlyData] = useState(null);
  const [insights, setInsights] = useState([]);
  const [momData, setMomData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState(null);

  const [timeRange, setTimeRange] = useState(30);

  // Helper
  const safeNum = (n) => {
    const v = Number(n);
    return Number.isFinite(v) ? v : 0;
  };

  // -------------------
  // Effects
  // -------------------
  useEffect(() => {
    let mounted = true;

    async function loadAnalytics() {
      setLoading(true);
      setErrorMsg(null);

      try {
        const [dash, daily, monthly, insightRes, mom] = await Promise.all([
          analyticsAPI.getDashboard().catch(() => ({ data: null })),
          analyticsAPI.getDailyAnalysis(timeRange).catch(() => ({ data: null })),
          analyticsAPI.getMonthlyAnalysis(6).catch(() => ({ data: null })),
          analyticsAPI.getInsights().catch(() => ({ data: null })),
          analyticsAPI.getMonthOverMonth().catch(() => ({ data: null })),
        ]);

        if (!mounted) return;

        const dashData = dash?.data?.data ?? dash?.data ?? {};
        const dailyRaw = daily?.data?.data ?? daily?.data ?? {};
        const monthlyRaw = monthly?.data?.data ?? monthly?.data ?? {};
        const insightsRaw = insightRes?.data?.data ?? insightRes?.data ?? [];
        const momRaw = mom?.data?.data ?? mom?.data ?? {};

        setDashboard(dashData || {});
        setDailyData(dailyRaw || null);
        setMonthlyData(monthlyRaw || null);

        if (Array.isArray(insightsRaw)) setInsights(insightsRaw);
        else if (insightsRaw?.insights) setInsights(insightsRaw.insights);
        else setInsights([]);

        setMomData(momRaw || null);
      } catch (e) {
        console.error("Analytics load error:", e);
        if (!mounted) return;
        setErrorMsg("Failed to load analytics.");
      } finally {
        if (!mounted) return;
        setLoading(false);
      }
    }

    loadAnalytics();

    return () => {
      mounted = false;
    };
  }, [timeRange]);

  // -------------------
  // Derived values (useMemo) — still hooks, defined before any conditional return
  // -------------------
  const categoryDataRaw = dashboard?.category_breakdown ?? dashboard?.categories ?? {};

  const categoryDataObj = useMemo(() => {
    const obj = {};

    if (Array.isArray(categoryDataRaw)) {
      categoryDataRaw.forEach((c) => {
        const name = c.category ?? c.name ?? "Unknown";
        obj[name] = {
          amount: safeNum(c.amount),
          count: safeNum(c.count),
          average: safeNum(c.average),
          percentage: safeNum(c.percentage),
        };
      });
    } else if (typeof categoryDataRaw === "object" && categoryDataRaw !== null) {
      Object.entries(categoryDataRaw).forEach(([k, v]) => {
        obj[k] = {
          amount: safeNum(v?.amount),
          count: safeNum(v?.count),
          average: safeNum(v?.average),
          percentage: safeNum(v?.percentage),
        };
      });
    }

    return obj;
  }, [categoryDataRaw]);

  const categories = useMemo(() => Object.keys(categoryDataObj), [categoryDataObj]);

  const amounts = useMemo(() => categories.map((c) => categoryDataObj[c].amount), [categories, categoryDataObj]);

  const total = useMemo(() => amounts.reduce((a, b) => a + b, 0), [amounts]);

  // PIE DATA
  const pieData = useMemo(() => ({
    labels: categories,
    datasets: [
      {
        data: amounts,
        backgroundColor: [
          "#8b5cf6",
          "#3b82f6",
          "#10b981",
          "#f59e0b",
          "#ef4444",
          "#ec4899",
          "#06b6d4",
          "#84cc16",
          "#f97316",
          "#6366f1",
        ],
        borderWidth: 0,
      },
    ],
  }), [categories, amounts]);

  // DAILY CHART DATA
  const dailyChartData = useMemo(() => {
    const raw = dailyData?.daily_data ?? dailyData?.daily ?? dailyData?.data ?? null;
    if (!raw || !Array.isArray(raw)) return null;

    return {
      labels: raw.map((d) => {
        try {
          return new Date(d.date).toLocaleDateString(undefined, { month: "short", day: "numeric" });
        } catch {
          return d.date;
        }
      }),
      datasets: [
        {
          label: "Daily Spending",
          data: raw.map((d) => safeNum(d.amount ?? d.total)),
          borderColor: "#8b5cf6",
          backgroundColor: "rgba(139,92,246,0.15)",
          tension: 0.4,
          fill: true,
        },
      ],
    };
  }, [dailyData]);

  // MONTHLY CHART DATA
  const monthlyChartData = useMemo(() => {
    const raw = monthlyData?.monthly_data ?? monthlyData?.data ?? monthlyData?.monthly ?? null;
    if (!raw || !Array.isArray(raw)) return null;

    return {
      labels: raw.map((m) => m.month),
      datasets: [
        {
          label: "Monthly Spending",
          data: raw.map((m) => safeNum(m.amount)),
          backgroundColor: "rgba(59,130,246,0.85)",
          borderRadius: 8,
        },
      ],
    };
  }, [monthlyData]);

  const chartOptions = useMemo(() => ({
    responsive: true,
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true } },
  }), []);

  const momChange = useMemo(() => (
    momData?.change ?? momData?.delta ?? momData?.difference ?? null
  ), [momData]);

  // -------------------
  // Now safe to early-return UI states
  // -------------------
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="text-6xl mb-4">📊</div>
          <p className="text-gray-600">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (errorMsg) {
    return (
      <div className="p-10 text-center text-red-600 font-semibold">{errorMsg}</div>
    );
  }

  if (!categories || categories.length === 0) {
    return (
      <div className="p-10 text-center text-gray-600">
        <h2 className="text-3xl font-bold mb-3">No Analytics Yet</h2>
        <p>Upload invoices to generate analytics.</p>
      </div>
    );
  }

  // -------------------
  // RENDER
  // -------------------
  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* HEADER */}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">📈 Analytics Dashboard</h1>

        <select
          value={timeRange}
          onChange={(e) => setTimeRange(Number(e.target.value))}
          className="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-purple-600"
        >
          <option value={7}>Last 7 Days</option>
          <option value={30}>Last 30 Days</option>
          <option value={90}>Last 90 Days</option>
        </select>
      </div>

      {/* SUMMARY CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-gradient-to-br from-purple-500 to-purple-600 text-white rounded-2xl p-6 shadow-lg">
          <div className="text-3xl mb-2">💰</div>
          <div className="text-3xl font-bold">₹{total.toFixed(0)}</div>
          <div className="text-purple-100 mt-1">Total Spent</div>
        </div>

        <div className="bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-2xl p-6 shadow-lg">
          <div className="text-3xl mb-2">📊</div>
          <div className="text-3xl font-bold">{categories.length}</div>
          <div className="text-blue-100 mt-1">Categories</div>
        </div>

        <div className="bg-gradient-to-br from-green-500 to-green-600 text-white rounded-2xl p-6 shadow-lg">
          <div className="text-3xl mb-2">📈</div>
          <div className="text-3xl font-bold">₹{safeNum(dailyData?.average_daily).toFixed(0)}</div>
          <div className="text-green-100 mt-1">Avg Daily Spending</div>
        </div>

        <div className="bg-gradient-to-br from-orange-500 to-orange-600 text-white rounded-2xl p-6 shadow-lg">
          <div className="text-3xl mb-2">{momChange?.direction === "increase" ? "📈" : "📉"}</div>
          <div className="text-3xl font-bold">{momChange ? `${Math.abs(safeNum(momChange.percent)).toFixed(1)}%` : "N/A"}</div>
          <div className="text-orange-100 mt-1">Month Change</div>
        </div>
      </div>

      {/* INSIGHTS */}
      <div className="bg-white rounded-2xl shadow-lg p-6 mb-8">
        <h3 className="text-2xl font-bold mb-4 text-gray-800">💡 Insights</h3>

        {insights.length === 0 ? (
          <p className="text-gray-500">No insights available.</p>
        ) : (
          <div className="space-y-3">
            {insights.map((i, idx) => (
              <div key={idx} className={`p-4 rounded-xl ${i.type === "warning" ? "bg-orange-50 border-l-4 border-orange-500" : i.type === "alert" ? "bg-red-50 border-l-4 border-red-500" : i.type === "tip" ? "bg-blue-50 border-l-4 border-blue-500" : "bg-green-50 border-l-4 border-green-500"}`}>
                <h4 className="font-bold text-gray-800">{i.title}</h4>
                <p className="text-gray-600 mt-1">{i.message}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* CHARTS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {dailyChartData && (
          <div className="bg-white rounded-2xl shadow-lg p-6">
            <h3 className="text-2xl font-bold mb-6 text-gray-800">📅 Daily Spending Trend</h3>
            <Line data={dailyChartData} options={chartOptions} />
          </div>
        )}

        <div className="bg-white rounded-2xl shadow-lg p-6">
          <h3 className="text-2xl font-bold mb-6 text-gray-800">💼 Category Breakdown</h3>
          <div className="flex justify-center">
            <div className="w-80 h-80">
              <Pie data={pieData} />
            </div>
          </div>
        </div>
      </div>

      {monthlyChartData && (
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-8">
          <h3 className="text-2xl font-bold mb-6 text-gray-800">📊 Monthly Overview</h3>
          <Bar data={monthlyChartData} options={chartOptions} />
        </div>
      )}

      {/* TABLE */}
      <div className="bg-white rounded-2xl shadow-lg p-6 mb-12">
        <h3 className="text-2xl font-bold mb-6 text-gray-800">📋 Detailed Breakdown</h3>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b-2 border-gray-200">
                <th className="px-6 py-4 text-left">Category</th>
                <th className="px-6 py-4 text-right">Amount</th>
                <th className="px-6 py-4 text-right">Count</th>
                <th className="px-6 py-4 text-right">Average</th>
                <th className="px-6 py-4 text-right">% of Total</th>
              </tr>
            </thead>

            <tbody>
              {categories.map((cat) => {
                const c = categoryDataObj[cat];
                return (
                  <tr key={cat} className="border-b hover:bg-gray-50">
                    <td className="px-6 py-4 font-medium">{cat}</td>
                    <td className="px-6 py-4 text-right">₹{safeNum(c.amount).toFixed(2)}</td>
                    <td className="px-6 py-4 text-right">{c.count}</td>
                    <td className="px-6 py-4 text-right">₹{safeNum(c.average).toFixed(2)}</td>
                    <td className="px-6 py-4 text-right text-purple-600">{safeNum(c.percentage).toFixed(1)}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
