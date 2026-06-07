import type { TapPoint } from "@/lib/api";

interface Props {
  points: TapPoint[];
}

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

// Dark Electric line colors. Stamps are the primary loyalty action (cyan);
// reviews use amber, matching the Reviews card badge.
const STAMP_COLOR = "#00D4FF";
const REVIEW_COLOR = "#FBBF24";
const GRID_COLOR = "#1A2A3A";
const AXIS_TEXT = "#8899AA";

function formatLabel(iso: string): string {
  const parts = iso.split("-");
  const month = parts[1] ?? "01";
  const day = parts[2] ?? "01";
  return `${parseInt(day, 10)} ${MONTHS[parseInt(month, 10) - 1] ?? ""}`;
}

/**
 * Inline SVG line chart — no chart deps, server-rendered. Plots two series
 * (stamp taps and review clicks) per day over the supplied window. The SVG
 * scales fluidly via its viewBox; strokes stay crisp with non-scaling-stroke.
 */
export function ActivityChart({ points }: Props) {
  const totalStamps = points.reduce((s, p) => s + p.stamps, 0);
  const totalReviews = points.reduce((s, p) => s + p.reviews, 0);
  const hasData = totalStamps + totalReviews > 0;

  const W = 760;
  const H = 240;
  const padL = 8;
  const padR = 8;
  const padT = 16;
  const padB = 28;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const n = points.length;

  const maxVal = Math.max(1, ...points.map((p) => Math.max(p.stamps, p.reviews)));
  const xAt = (i: number) =>
    padL + (n <= 1 ? innerW / 2 : (i / (n - 1)) * innerW);
  const yAt = (v: number) => padT + innerH - (v / maxVal) * innerH;
  const pathFor = (key: "stamps" | "reviews") =>
    points
      .map((p, i) => `${i === 0 ? "M" : "L"} ${xAt(i).toFixed(1)} ${yAt(p[key]).toFixed(1)}`)
      .join(" ");

  const gridYs = [0, maxVal / 2, maxVal];

  return (
    <div className="rounded-xl border border-electric-border bg-electric-surface p-6">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="font-display text-lg font-semibold text-electric-text">
            Activity
          </h3>
          <p className="text-xs text-electric-text-muted">Last {n} days</p>
        </div>
        <div className="flex items-center gap-4 text-xs text-electric-text-muted">
          <span className="flex items-center gap-1.5">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: STAMP_COLOR }}
              aria-hidden="true"
            />
            Stamps
          </span>
          <span className="flex items-center gap-1.5">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: REVIEW_COLOR }}
              aria-hidden="true"
            />
            Reviews
          </span>
        </div>
      </div>

      {hasData ? (
        <svg
          viewBox={`0 0 ${W} ${H}`}
          width="100%"
          className="h-auto w-full"
          role="img"
          aria-label={`Activity over the last ${n} days: ${totalStamps} stamp taps and ${totalReviews} review clicks.`}
        >
          {/* horizontal gridlines + y labels */}
          {gridYs.map((v) => (
            <g key={v}>
              <line
                x1={padL}
                x2={W - padR}
                y1={yAt(v)}
                y2={yAt(v)}
                stroke={GRID_COLOR}
                strokeWidth={1}
                vectorEffect="non-scaling-stroke"
              />
              <text
                x={padL}
                y={yAt(v) - 4}
                fill={AXIS_TEXT}
                fontSize={11}
              >
                {Math.round(v)}
              </text>
            </g>
          ))}

          {/* series */}
          <path
            d={pathFor("reviews")}
            fill="none"
            stroke={REVIEW_COLOR}
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
          />
          <path
            d={pathFor("stamps")}
            fill="none"
            stroke={STAMP_COLOR}
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
          />

          {/* x labels: first, middle, last */}
          {n > 0 && (
            <>
              <text x={padL} y={H - 8} fill={AXIS_TEXT} fontSize={11}>
                {formatLabel(points[0]!.date)}
              </text>
              {n > 2 && (
                <text
                  x={W / 2}
                  y={H - 8}
                  fill={AXIS_TEXT}
                  fontSize={11}
                  textAnchor="middle"
                >
                  {formatLabel(points[Math.floor(n / 2)]!.date)}
                </text>
              )}
              <text
                x={W - padR}
                y={H - 8}
                fill={AXIS_TEXT}
                fontSize={11}
                textAnchor="end"
              >
                {formatLabel(points[n - 1]!.date)}
              </text>
            </>
          )}
        </svg>
      ) : (
        <div className="flex h-40 items-center justify-center text-sm text-electric-text-muted">
          No taps in the last {n} days yet.
        </div>
      )}
    </div>
  );
}
