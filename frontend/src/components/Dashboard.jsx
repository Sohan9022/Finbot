// src/pages/Dashboard.jsx
// Chart.js Dashboard (NO Recharts)

import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { analyticsAPI, billsAPI } from "../services/api";

import {
  Chart as ChartJS,
  LineElement,
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  Tooltip,
  Legend,
} from "chart.js";

import { Line, Doughnut, Bar } from "react-chartjs-2";

ChartJS.register(
  LineElement,
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  Tooltip,
  Legend
);

const COLORS = [
  "#7C3AED",
  "#06B6D4",
  "#F97316",
  "#10B981",
  "#EF4444",
  "#6366F1",
  "#F59E0B",
  "#14B8A6",
];

const SAFE_NUM = (v) => (Number.isFinite(Number(v)) ? Number(v) : 0);
const CURRENCY = (v) =>
  `₹${SAFE_NUM(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

export default function Dashboard({ user }) {
  const [loading, setLoading] = useState(true);

  const [overview, setOverview] = useState(null);
  const [dailyData, setDailyData] = useState([]);
  const [categoryData, setCategoryData] = useState([]);
  const [momData, setMomData] = useState([]);
  const [insights, setInsights] = useState([]);
  const [recentBills, setRecentBills] = useState([]);
  const [reminders, setReminders] = useState([]);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);

    try {
      const [
        dashRes,
        dailyRes,
        catRes,
        momRes,
        insightsRes,
        billsRes,
        remindersRes,
      ] = await Promise.all([
        analyticsAPI.getDashboard().catch(() => null),
        analyticsAPI.getDailyAnalysis(30).catch(() => null),
        analyticsAPI.getCategoryBreakdown(30).catch(() => null),
        analyticsAPI.getMonthOverMonth().catch(() => null),
        analyticsAPI.getInsights().catch(() => null),
        billsAPI.list({ limit: 8 }).catch(() => null),
        billsAPI.getReminders(30).catch(() => null),
      ]);

      setOverview(dashRes?.data?.data ?? null);

      const daily = dailyRes?.data?.data?.daily_data ?? [];
      setDailyData(
        daily.map((d) => ({
          date: d.date?.slice(5) ?? d.date,
          amount: SAFE_NUM(d.amount),
        }))
      );

      const catRaw = catRes?.data?.data ?? {};
      let categories = [];

      if (Array.isArray(catRaw)) {
        categories = catRaw.map((c) => ({
          name: c.category,
          amount: SAFE_NUM(c.amount),
        }));
      } else {
        categories = Object.entries(catRaw).map(([name, d]) => ({
          name,
          amount: SAFE_NUM(d.amount),
        }));
      }

      setCategoryData(categories);

      let momRaw = momRes?.data?.data;
      let momPoints = [];

      if (momRaw?.monthly_data) {
        momPoints = momRaw.monthly_data.map((m) => ({
          month: m.month,
          total: SAFE_NUM(m.amount),
        }));
      } else if (momRaw?.current_month) {
        momPoints = [
          {
            month: momRaw.previous_month.month,
            total: SAFE_NUM(momRaw.previous_month.total),
          },
          {
            month: momRaw.current_month.month,
            total: SAFE_NUM(momRaw.current_month.total),
          },
        ];
      }

      setMomData(momPoints);

      const ins = insightsRes?.data?.data ?? [];
      setInsights(Array.isArray(ins) ? ins.slice(0, 5) : []);

      setRecentBills(billsRes?.data?.data?.bills ?? []);
      setReminders(remindersRes?.data?.data?.reminders ?? []);
    } finally {
      setLoading(false);
    }
  }

  const totalSpent = useMemo(() => {
    if (overview?.total_revenue) return SAFE_NUM(overview.total_revenue);
    return categoryData.reduce((s, c) => s + SAFE_NUM(c.amount), 0);
  }, [overview, categoryData]);

  const totalBills = overview?.total_invoices ?? recentBills.length;

  const avgDaily = useMemo(() => {
    if (overview?.avg_daily) return SAFE_NUM(overview.avg_daily);
    if (!dailyData.length) return 0;
    const sum = dailyData.reduce((s, d) => s + SAFE_NUM(d.amount), 0);
    return Math.round(sum / dailyData.length);
  }, [overview, dailyData]);

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-6xl animate-pulse">📊</div>
      </div>
    );
  }

  // ---------- Chart.js DATA ----------

  const dailyChart = {
    labels: dailyData.map((d) => d.date),
    datasets: [
      {
        label: "Daily Spending",
        data: dailyData.map((d) => d.amount),
        borderColor: "#7C3AED",
        backgroundColor: "rgba(124,58,237,0.2)",
        tension: 0.4,
        fill: true,
      },
    ],
  };

  const donutChart = {
    labels: categoryData.map((c) => c.name),
    datasets: [
      {
        data: categoryData.map((c) => c.amount),
        backgroundColor: COLORS,
        borderWidth: 1,
      },
    ],
  };

  const momChart = {
    labels: momData.map((m) => m.month),
    datasets: [
      {
        label: "Monthly Total",
        data: momData.map((m) => m.total),
        backgroundColor: "rgba(6,182,212,0.8)",
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    plugins: { legend: { display: false } },
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* HEADER */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">
            Welcome back{user?.full_name ? `, ${user.full_name}` : ""} 👋
          </h1>
          <p className="text-gray-600 mt-1">
            Overview of your spending, trends and reminders.
          </p>
        </div>

        <div className="flex gap-3">
          <Link to="/upload" className="px-4 py-2 bg-purple-600 text-white rounded">
            Upload Invoice
          </Link>
          <Link to="/analytics" className="px-4 py-2 bg-green-600 text-white rounded">
            Full Analytics
          </Link>
        </div>
      </div>

      {/* TOP CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <StatCard title="Total Spent (30d)" value={CURRENCY(totalSpent)} color="purple" />
        <StatCard title="Total Bills" value={totalBills} color="blue" />
        <StatCard title="Avg Daily" value={CURRENCY(avgDaily)} color="green" />
        <StatCard title="Due Soon" value={reminders.length} color="orange" />
      </div>

      {/* MAIN CHARTS */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Daily */}
        <Card title="Daily Spending (last 30 days)">
          <Line data={dailyChart} options={chartOptions} />
        </Card>

        {/* Donut */}
        <Card title="Category Breakdown">
          <div className="w-64 mx-auto">
            <Doughnut data={donutChart} />
          </div>
        </Card>

        {/* MoM */}
        <Card title="Month-over-Month">
          <Bar data={momChart} options={chartOptions} />
        </Card>
      </div>

      {/* BOTTOM ROW */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Insights */}
        <Card title="AI Insights">
          {insights.length === 0 ? (
            <p className="text-gray-500 text-sm">No insights yet.</p>
          ) : (
            <div className="space-y-3">
              {insights.map((ins, idx) => (
                <Insight key={idx} item={ins} />
              ))}
            </div>
          )}
        </Card>

        {/* Reminders */}
        <Card title="Payment Reminders">
          {reminders.length === 0 ? (
            <p className="text-gray-500 text-sm">No reminders.</p>
          ) : (
            <div className="space-y-2">
              {reminders.slice(0, 5).map((r) => (
                <ReminderItem key={r.id} item={r} />
              ))}
            </div>
          )}
          <Link to="/payments" className="text-purple-600 text-sm">
            View all →
          </Link>
        </Card>

        {/* Recent */}
        <Card title="Recent Transactions">
          {recentBills.length === 0 ? (
            <p className="text-gray-500 text-sm">No transactions.</p>
          ) : (
            <div className="space-y-2">
              {recentBills.map((b) => (
                <RecentBill key={b.id} bill={b} />
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

// --------------------------------------------
// SMALL COMPONENTS
// --------------------------------------------

function StatCard({ title, value, color }) {
  const bg = {
    purple: "from-purple-500 to-purple-600",
    blue: "from-blue-500 to-blue-600",
    green: "from-green-500 to-green-600",
    orange: "from-orange-500 to-orange-600",
  }[color];

  return (
    <div className={`bg-gradient-to-br ${bg} rounded-lg p-5 text-white`}>
      <div className="text-sm">{title}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
    </div>
  );
}

function Card({ title, children }) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="font-semibold mb-3">{title}</h3>
      {children}
    </div>
  );
}

function Insight({ item }) {
  const style =
    item.type === "warning"
      ? "bg-orange-50 border-orange-300"
      : item.type === "alert"
      ? "bg-red-50 border-red-300"
      : "bg-green-50 border-green-300";

  return (
    <div className={`p-3 border rounded ${style}`}>
      <div className="font-medium">{item.title}</div>
      <div className="text-sm text-gray-600 mt-1">{item.message}</div>
    </div>
  );
}

function ReminderItem({ item }) {
  return (
    <div className="flex items-center justify-between p-2 rounded hover:bg-gray-50">
      <div>
        <div className="font-medium">{item.merchant_name}</div>
        <div className="text-xs text-gray-500">
          {new Date(item.bill_date).toLocaleDateString()}
        </div>
      </div>
      <div className="text-right">
        <div className="font-semibold text-red-600">
          {CURRENCY(item.total_amount)}
        </div>
        <div className="text-xs text-gray-400">
          {item.payment_status?.toUpperCase()}
        </div>
      </div>
    </div>
  );
}

function RecentBill({ bill }) {
  return (
    <div className="flex items-center justify-between p-2 rounded hover:bg-gray-50">
      <div className="flex items-center gap-3">
        <div className="text-2xl">
          {bill.category === "Groceries" ? "🛒" : "📄"}
        </div>
        <div>
          <div className="font-medium">
            {bill.merchant_name || bill.category}
          </div>
          <div className="text-xs text-gray-500">
            {new Date(bill.bill_date).toLocaleDateString()}
          </div>
        </div>
      </div>

      <div className="text-right">
        <div className="font-semibold">
          {CURRENCY(bill.total_amount || bill.amount)}
        </div>
        <div className="text-xs text-gray-400">
          {bill.payment_status?.toUpperCase()}
        </div>
      </div>
    </div>
  );
}
