"use client";

import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";

const RISK_DATA = [
  { name: "Low", value: 14, color: "#16a34a" },
  { name: "Medium", value: 7, color: "#d97706" },
  { name: "High", value: 3, color: "#dc2626" },
];

const SIGNAL_DATA = [
  { name: "UCP Discrepancy", count: 8 },
  { name: "Duplicate Financing", count: 3 },
  { name: "Cross-IBU", count: 4 },
  { name: "TBML", count: 2 },
  { name: "Vessel", count: 3 },
  { name: "Entity", count: 1 },
];

const IBU_DATA = [
  { name: "IBU-GIFT-01", cases: 12 },
  { name: "IBU-GIFT-02", cases: 7 },
  { name: "IBU-GIFT-03", cases: 5 },
];

export function RiskOverview() {
  return (
    <div className="grid grid-cols-3 gap-4">
      {/* Risk Distribution */}
      <div className="bg-white rounded-lg border border-border p-4">
        <h3 className="text-[13px] font-semibold text-slate-900 mb-3">Risk Distribution</h3>
        <ResponsiveContainer width="100%" height={180}>
          <PieChart>
            <Pie
              data={RISK_DATA}
              cx="50%"
              cy="50%"
              innerRadius={45}
              outerRadius={70}
              dataKey="value"
              stroke="none"
            >
              {RISK_DATA.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Legend
              verticalAlign="bottom"
              height={30}
              formatter={(value: string) => (
                <span className="text-[11px] text-slate-600">{value}</span>
              )}
            />
            <Tooltip
              contentStyle={{
                fontSize: "12px",
                borderRadius: "6px",
                border: "1px solid #e2e7ee",
                boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Cases by Signal */}
      <div className="bg-white rounded-lg border border-border p-4">
        <h3 className="text-[13px] font-semibold text-slate-900 mb-3">Cases by Signal</h3>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={SIGNAL_DATA} layout="vertical" margin={{ left: 0 }}>
            <XAxis type="number" tick={{ fontSize: 10, fill: "#64748b" }} axisLine={false} tickLine={false} />
            <YAxis
              dataKey="name"
              type="category"
              width={100}
              tick={{ fontSize: 10, fill: "#64748b" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                fontSize: "12px",
                borderRadius: "6px",
                border: "1px solid #e2e7ee",
                boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
              }}
            />
            <Bar dataKey="count" fill="#1e40af" radius={[0, 3, 3, 0]} barSize={14} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Cases by IBU */}
      <div className="bg-white rounded-lg border border-border p-4">
        <h3 className="text-[13px] font-semibold text-slate-900 mb-3">Cases by IBU</h3>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={IBU_DATA} margin={{ left: 0 }}>
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#64748b" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: "#64748b" }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{
                fontSize: "12px",
                borderRadius: "6px",
                border: "1px solid #e2e7ee",
                boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
              }}
            />
            <Bar dataKey="cases" fill="#2563eb" radius={[3, 3, 0, 0]} barSize={36} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
