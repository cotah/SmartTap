import type { DashboardOverview } from "@/lib/api";

interface Props {
  overview: DashboardOverview;
}

const CARDS: Array<{
  key: keyof DashboardOverview;
  label: string;
  hint: string;
}> = [
  { key: "customers_total", label: "Customers", hint: "All-time signups" },
  { key: "taps_week", label: "Taps this week", hint: "Last 7 days" },
  { key: "reviews_month", label: "Reviews", hint: "Last 30 days" },
  { key: "customers_at_risk", label: "At risk", hint: ">30 days no visit" },
  { key: "active_stamps_total", label: "Active stamps", hint: "Across all customers" },
];

export function OverviewCards({ overview }: Props) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
      {CARDS.map((card) => (
        <div
          key={card.key}
          className="rounded-2xl border border-brand-black/10 bg-white p-4 shadow-sm"
        >
          <p className="text-xs uppercase tracking-wide text-brand-black/60">{card.label}</p>
          <p className="mt-2 font-display text-4xl">{overview[card.key]}</p>
          <p className="mt-1 text-xs text-brand-black/50">{card.hint}</p>
        </div>
      ))}
    </div>
  );
}
