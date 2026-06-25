import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useMediaQuery } from "@/hooks/useMediaQuery";
import type { FileComplexity } from "@/types/api";

interface ComplexityChartProps {
  files: FileComplexity[];
  height?: number;
}

export function ComplexityChart({ files, height = 320 }: ComplexityChartProps) {
  const isMobile = useMediaQuery("(max-width: 639px)");
  const data = files.map((f) => ({
    path: shortName(f.path),
    cyclomatic: f.cyclomatic,
    cognitive: f.cognitive,
  }));

  const gridStroke = "#eceef2";
  const tickStyle = { fontSize: 11, fill: "#5a6275" } as const;
  const tooltipProps = {
    contentStyle: { fontSize: 12, borderRadius: 8, border: "1px solid #d4d8e0" },
    cursor: { fill: "#eceef2" },
  };

  // Mobile: a horizontal bar chart reads far better than cramming N vertical
  // bars with rotated labels into ~320px. File names sit on the Y axis and the
  // chart grows downward (the page scrolls naturally) — the pattern Datadog,
  // Vercel and Linear use for ranked categorical data on small screens.
  if (isMobile) {
    const rowHeight = 34;
    const mobileHeight = Math.max(240, data.length * rowHeight + 48);
    return (
      <ResponsiveContainer width="100%" height={mobileHeight}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 12, bottom: 4, left: 4 }}
          barCategoryGap={6}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} horizontal={false} />
          <XAxis type="number" tick={tickStyle} />
          <YAxis
            type="category"
            dataKey="path"
            tick={tickStyle}
            width={120}
            interval={0}
          />
          <Tooltip {...tooltipProps} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="cyclomatic" name="Cyclomatic" fill="#1f5fef" radius={[0, 4, 4, 0]} />
          <Bar dataKey="cognitive" name="Cognitive" fill="#5aa3ff" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 12, right: 8, bottom: 8, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
        <XAxis
          dataKey="path"
          tick={tickStyle}
          interval={0}
          angle={-25}
          textAnchor="end"
          height={70}
        />
        <YAxis tick={tickStyle} />
        <Tooltip {...tooltipProps} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="cyclomatic" name="Cyclomatic" fill="#1f5fef" radius={[4, 4, 0, 0]} />
        <Bar dataKey="cognitive" name="Cognitive" fill="#5aa3ff" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function shortName(path: string): string {
  const parts = path.split("/");
  return parts.slice(-2).join("/");
}
