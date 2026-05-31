import Link from "next/link";

import { getAuthApiClient } from "@/lib/api";
import type { Segment, SegmentCriteria } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";

export default async function SegmentsPage() {
  await getDashboardContext();
  const api = getAuthApiClient();
  const { items } = await api.listSegments();

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
  return (
    <Link
      href={`/dashboard/segments/${segment.id}`}
      className="block rounded-2xl border border-electric-border bg-electric-surface p-4 transition hover:border-electric-cyan"
    >
      <p className="font-display text-lg font-semibold text-electric-text">{segment.name}</p>
      <p className="mt-1 text-sm text-electric-text-muted">
        {summariseCriteria(segment.criteria)}
      </p>
    </Link>
  );
}

/** One-line human summary of a criteria block — what the merchant sees on
 * the card. Order tries to match a natural reading: counts → recency →
 * cohort → channels. Returns "No filters — all customers" when empty so
 * the card never blanks out. */
function summariseCriteria(c: SegmentCriteria): string {
  const parts: string[] = [];
  if (c.visits_min != null || c.visits_max != null) {
    parts.push(rangeLabel("visits", c.visits_min, c.visits_max));
  }
  if (c.stamps_min != null || c.stamps_max != null) {
    parts.push(rangeLabel("stamps", c.stamps_min, c.stamps_max));
  }
  if (c.last_visit_after_days != null) {
    parts.push(`visited in last ${c.last_visit_after_days}d`);
  }
  if (c.last_visit_before_days != null) {
    parts.push(`inactive ${c.last_visit_before_days}d+`);
  }
  if (c.created_after_days != null) {
    parts.push(`new in ${c.created_after_days}d`);
  }
  if (c.has_email === true) parts.push("has email");
  if (c.has_email === false) parts.push("no email");
  if (c.has_phone === true) parts.push("has phone");
  if (c.has_phone === false) parts.push("no phone");
  if (c.gdpr_consent_only === true) parts.push("GDPR ok");
  return parts.length > 0 ? parts.join(" · ") : "No filters — all customers";
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
