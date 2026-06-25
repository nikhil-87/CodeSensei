import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { parseLanguages } from "@/lib/format";

interface LanguageChartProps {
  packed: string | null | undefined;
  height?: number;
}

const PALETTE = [
  "#1f5fef",
  "#3a7eff",
  "#5aa3ff",
  "#8ec3ff",
  "#a855f7",
  "#16a34a",
  "#d97706",
  "#dc2626",
  "#5a6275",
];

export function LanguageChart({ packed, height = 240 }: LanguageChartProps) {
  const data = parseLanguages(packed).map((l, i) => ({
    name: l.language,
    value: l.count,
    fill: PALETTE[i % PALETTE.length],
  }));
  if (data.length === 0) {
    return <p className="text-sm text-ink-400">No language data yet.</p>;
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius={45}
          outerRadius={80}
          paddingAngle={2}
          label={({ name, percent }) =>
            `${name} ${((percent ?? 0) * 100).toFixed(0)}%`
          }
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.fill} />
          ))}
        </Pie>
      </PieChart>
    </ResponsiveContainer>
  );
}
