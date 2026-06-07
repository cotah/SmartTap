import { Layers, Users } from "lucide-react";
import Link from "next/link";

import { getAuthApiClient } from "@/lib/api";
import type { Segment, SegmentCriteria } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";

export default async function SegmentsPage() {
  await getDashboardContext();
  const api = getAuthApiClient();
  const { items } = await api.listSegments();

  const totalMatches = items.reduce((sum, s) => sum + (s.member_count ?? 0), 0);

  return (
    <main className="space-y-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm text-electric-text-muted">
            <Link href="/dashboard" className="underline">
              Dashboard
            </Link>{" "}
            / Segments
          </p>
          <h1 className="font-display text-3xl font-semibold text-electric-text">Segments</h1>
          <p className="mt-1 text-sm text-electric-text-muted">
            Group customers by visit history, stamps and contact channel.
          </p>
        </div>
        <Link
          href="/dashboard/segments/new"
          className="rounded-full bg-electric-cyan px-5 py-2.5 text-sm font-semibold text-electric-bg transition-colors hover:bg-electric-cyan-deep"
        >
          New segment
        </Link>
      </header>

      {items.length > 0 ? (
        <div className="flex flex-wrap gap-3">
          <SummaryStat label="Segments" value={items.length} />
          <SummaryStat
            label="Matches across segments"
            value={totalMatches}
            hint="customers may appear in more than one"
          />
        </div>
      ) : null}

      {items.length === 0 ? (
        <EmptyState />
      ) : (
        <ul className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {items.map((s) => (
            <li key={s.id}>
              <SegmentCard segment={s} />
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

function SummaryStat({
  label,
  value,
  hint,
}: {
  label: string;
  value: number;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-electric-border bg-electric-surface px-4 py-3">
      <p className="text-xs font-bold uppercase tracking-wider text-electric-text-muted">
        {label}
      </p>
      <p className="mt-1 font-display text-2xl font-semibold text-electric-text">
        {value.toLocaleString()}
      </p>
      {hint ? (
        <p className="mt-0.5 text-[11px] text-electric-text-muted">{hint}</p>
      ) : null}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-electric-border bg-electric-surface p-8 text-center">
      <p className="font-display text-lg font-semibold text-electric-text">No segments yet</p>
      <p className="mt-1 text-sm text-electric-text-muted">
        Build a reusable group — like &ldquo;loyal regulars&rdquo; or
        &ldquo;new this week&rdquo; — then use it to target campaigns later.
      </p>
      <Link
        href="/dashboard/segments/new"
        className="mt-4 inline-block rounded-full bg-electric-cyan px-5 py-2 text-sm font-semibold text-electric-bg transition-colors hover:bg-electric-cyan-deep"
      >
        Create your first segment
      </Link>
    </div>
  );
}

function SegmentCard({ segment }: { segment: Segment }) {
  const chips = criteriaChips(segment.criteria);
  return (
    <Link
      href={`/dashboard/segments/${segment.id}`}
      className="flex h-full flex-col gap-3 rounded-2xl border border-electric-border bg-electric-surface p-4 transition hover:border-electric-cyan hover:bg-electric-surface-2"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-electric-cyan/15 text-electric-cyan">
            <Layers className="h-4 w-4" aria-hidden="true" />
          </span>
          <p className="truncate font-display text-lg font-semibold text-electric-text">
            {segment.name}
          </p>
        </div>
        {segment.member_count != null ? (
          <span className="flex shrink-0 items-center gap-1 rounded-full bg-electric-surface-2 px-2.5 py-1 text-xs font-semibold text-electric-text">
            <Users className="h-3.5 w-3.5 text-electric-text-muted" aria-hidden="true" />
            {segment.member_count.toLocaleString()}
          </span>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-1.5">
        {chips.length > 0 ? (
          chips.map((chip) => (
            <span
              key={chip}
              className="rounded-full bg-electric-surface-2 px-2 py-0.5 text-xs text-electric-text-muted"
            >
              {chip}
            </span>
          ))
        ) : (
          <span className="text-xs text-electric-text-muted">
            No filters — all customers
          </span>
        )}
      </div>
    </Link>
  );
}

/** Human-readable chips for a criteria block, in a natural reading order:
 * counts → recency → cohort → channels. */
function criteriaChips(c: SegmentCriteria): string[] {
  const chips: string[] = [];
  if (c.visits_min != null || c.visits_max != null) {
    chips.push(rangeLabel("visits", c.visits_min, c.visits_max));
  }
  if (c.stamps_min != null || c.stamps_max != null) {
    chips.push(rangeLabel("stamps", c.stamps_min, c.stamps_max));
  }
  if (c.last_visit_after_days != null) {
    chips.push(`visited in last ${c.last_visit_after_days}d`);
  }
  if (c.last_visit_before_days != null) {
    chips.push(`inactive ${c.last_visit_before_days}d+`);
  }
  if (c.created_after_days != null) {
    chips.push(`new in ${c.created_after_days}d`);
  }
  if (c.has_email === true) chips.push("has email");
  if (c.has_email === false) chips.push("no email");
  if (c.has_phone === true) chips.push("has phone");
  if (c.has_phone === false) chips.push("no phone");
  if (c.gdpr_consent_only === true) chips.push("GDPR ok");
  return chips;
}

function rangeLabel(
  noun: string,
  min: number | null | undefined,
  max: number | null | undefined,
): string {
  if (min != null && max != null) return `${min}–${max} ${noun}`;
  if (min != null) return `≥${min} ${noun}`;
  if (max != null) return `≤${max} ${noun}`;
  return noun;
}
