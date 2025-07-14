"use client";

import { useEffect, useState } from "react";
import { apiClient, Script } from "@/lib/api";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  PointElement,
  LineElement,
  TimeScale,
} from "chart.js";
import { Bar, Pie, Line } from "react-chartjs-2";
import "chartjs-adapter-date-fns";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  PointElement,
  LineElement,
  TimeScale
);

export default function CostManagementPage() {
  const [scripts, setScripts] = useState<Script[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchScripts = async () => {
      try {
        setLoading(true);
        const data = await apiClient.getStudioScripts();
        setScripts(data);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to fetch scripts"
        );
      } finally {
        setLoading(false);
      }
    };
    fetchScripts();
  }, []);

  // Aggregate cost data
  const totalScriptCost = scripts.reduce(
    (sum, s) => sum + (s.script_cost || 0),
    0
  );
  const totalVideoCost = scripts.reduce(
    (sum, s) => sum + (s.video_cost || 0),
    0
  );
  const totalCost = totalScriptCost + totalVideoCost;

  // Pie chart data for overall cost breakdown
  const pieData = {
    labels: ["Script Generation", "Video Production"],
    datasets: [
      {
        data: [totalScriptCost, totalVideoCost],
        backgroundColor: ["#6366f1", "#f59e42"],
        borderWidth: 1,
      },
    ],
  };

  // Bar chart for per-script cost
  const barData = {
    labels: scripts.map((s) => s.user_prompt?.slice(0, 30) || s.id),
    datasets: [
      {
        label: "Script Generation ($)",
        data: scripts.map((s) => s.script_cost || 0),
        backgroundColor: "#6366f1",
      },
      {
        label: "Video Production ($)",
        data: scripts.map((s) => s.video_cost || 0),
        backgroundColor: "#f59e42",
      },
    ],
  };

  // Line chart for cost over time
  const sortedScripts = [...scripts].sort((a, b) => {
    const aDate = a.updated_at ? new Date(a.updated_at).getTime() : 0;
    const bDate = b.updated_at ? new Date(b.updated_at).getTime() : 0;
    return aDate - bDate;
  });
  const lineData = {
    labels: sortedScripts.map((s) => s.updated_at || s.id),
    datasets: [
      {
        label: "Cumulative Cost ($)",
        data: sortedScripts.reduce<number[]>((acc, s, i) => {
          const prev = acc[i - 1] || 0;
          return [...acc, prev + (s.script_cost || 0) + (s.video_cost || 0)];
        }, []),
        borderColor: "#6366f1",
        backgroundColor: "rgba(99,102,241,0.1)",
        fill: true,
        tension: 0.3,
        pointRadius: 2,
      },
    ],
  };

  return (
    <div className="min-h-screen bg-white">
      <div className="p-6">
        <h1 className="text-2xl font-semibold text-[#1a1a1a]">
          Cost Management
        </h1>
        <p className="text-[#6b7280] mt-2">
          Track and visualize your project costs
        </p>
      </div>
      <div className="p-6 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
        {loading ? (
          <div className="col-span-full flex items-center justify-center h-64">
            <span className="text-[#6b7280] text-lg">Loading cost data...</span>
          </div>
        ) : error ? (
          <div className="col-span-full bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        ) : (
          <>
            {/* Overall Cost Breakdown Pie Chart */}
            <div className="bg-[#fafafa] rounded-lg p-6 border border-[#e0e0e0] flex flex-col items-center">
              <h2 className="text-lg font-semibold mb-4 text-[#1a1a1a]">
                Overall Cost Breakdown
              </h2>
              <Pie data={pieData} />
              <div className="mt-4 text-sm text-[#6b7280]">
                <div>
                  Total Cost:{" "}
                  <span className="font-semibold text-[#1a1a1a]">
                    ${totalCost.toFixed(2)}
                  </span>
                </div>
                <div>Script Generation: ${totalScriptCost.toFixed(2)}</div>
                <div>Video Production: ${totalVideoCost.toFixed(2)}</div>
              </div>
            </div>

            {/* Per-Script Cost Bar Chart */}
            <div className="bg-[#fafafa] rounded-lg p-6 border border-[#e0e0e0] flex flex-col items-center">
              <h2 className="text-lg font-semibold mb-4 text-[#1a1a1a]">
                Per-Script Cost
              </h2>
              <Bar
                data={barData}
                options={{
                  responsive: true,
                  plugins: {
                    legend: { position: "top" as const },
                    title: { display: false },
                  },
                  scales: {
                    x: { title: { display: true, text: "Script" } },
                    y: {
                      title: { display: true, text: "Cost ($)" },
                      beginAtZero: true,
                    },
                  },
                }}
              />
            </div>

            {/* Cost Over Time Line Chart */}
            <div className="bg-[#fafafa] rounded-lg p-6 border border-[#e0e0e0] flex flex-col items-center col-span-full xl:col-span-1">
              <h2 className="text-lg font-semibold mb-4 text-[#1a1a1a]">
                Cost Over Time
              </h2>
              <Line
                data={lineData}
                options={{
                  responsive: true,
                  plugins: {
                    legend: { position: "top" as const },
                    title: { display: false },
                  },
                  scales: {
                    x: {
                      type: "time",
                      time: { unit: "day" },
                      title: { display: true, text: "Date" },
                    },
                    y: {
                      title: { display: true, text: "Cumulative Cost ($)" },
                      beginAtZero: true,
                    },
                  },
                }}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
