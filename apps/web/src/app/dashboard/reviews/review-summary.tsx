import type { ReviewStats } from "@/lib/api";

interface Props {
  stats: ReviewStats;
}

// Sentiment-graded bars: 5–4★ emerald, 3★ amber, 2–1★ red. Literal strings so
// Tailwind's JIT keeps them.
function barColor(rating: number): string {
  if (rating >= 4) return "bg-emerald-400";
  if (rating === 3) return "bg-amber-400";
  return "bg-red-400";
}

/**
 * Summary header for the reviews dashboard: average rating, a 5★→1★
 * distribution, and the total count. Server-rendered, no interactivity.
 * Renders nothing when the tenant has no reviews yet.
 */
export function ReviewSummary({ stats }: Props) {
  if (stats.total === 0) return null;

  const averageLabel = stats.average !== null ? stats.average.toFixed(1) : "—";
  const filledStars = Math.round(stats.average ?? 0);

  return (
    <section
      className="rounded-2xl border border-electric-border bg-electric-surface p-5"
      aria-label="Review summary"
    >
      <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
        {/* Average */}
        <div className="flex flex-col items-center sm:w-44 sm:border-r sm:border-electric-border sm:pr-6">
          <p className="font-display text-5xl font-semibold leading-none text-electric-text">
            {averageLabel}
          </p>
          <p
            className="mt-2 text-base text-electric-cyan"
            aria-label={`Average ${averageLabel} out of 5 stars`}
          >
            {"★".repeat(filledStars)}
            <span className="text-electric-text-muted">
              {"★".repeat(Math.max(0, 5 - filledStars))}
            </span>
          </p>
          <p className="mt-1 text-xs text-electric-text-muted">
            {stats.total} review{stats.total === 1 ? "" : "s"}
          </p>
        </div>

        {/* Distribution */}
        <div className="flex-1 space-y-1.5">
          {stats.distribution.map((bucket) => {
            const pct =
              stats.rated_count > 0
                ? (bucket.count / stats.rated_count) * 100
                : 0;
            return (
              <div
                key={bucket.rating}
                className="flex items-center gap-3 text-xs text-electric-text-muted"
              >
                <span className="w-7 shrink-0 tabular-nums">{bucket.rating}★</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-electric-surface-2">
                  <div
                    className={`h-full rounded-full ${barColor(bucket.rating)}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="w-8 shrink-0 text-right tabular-nums">
                  {bucket.count}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
