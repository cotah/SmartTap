import Link from "next/link";

import { getAuthApiClient } from "@/lib/api";
import type { NfcTag } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";
import { publicEnv } from "@/lib/env";

import { COLOR_LABELS, COLOR_SWATCH, FORMAT_LABELS } from "./tag-labels";

export default async function TagsPage() {
  await getDashboardContext();
  const api = getAuthApiClient();
  const { items } = await api.listTags();

  return (
    <main className="space-y-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm text-electric-text-muted">
            <Link href="/dashboard" className="underline">
              Dashboard
            </Link>{" "}
            / NFC tags
          </p>
          <h1 className="font-display text-3xl font-semibold text-electric-text">NFC tags</h1>
          <p className="mt-1 text-sm text-electric-text-muted">
            One row per physical tag — write the public URL onto each one
            with TagWriter.
          </p>
        </div>
        <Link
          href="/dashboard/tags/new"
          className="rounded-full bg-electric-cyan px-5 py-2.5 text-sm font-semibold text-electric-bg transition-colors hover:bg-electric-cyan-deep"
        >
          New tag
        </Link>
      </header>

      {items.length === 0 ? (
        <EmptyState />
      ) : (
        <ul className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {items.map((t) => (
            <li key={t.id}>
              <TagCard tag={t} siteUrl={publicEnv.NEXT_PUBLIC_SITE_URL} />
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
      <p className="font-display text-lg font-semibold text-electric-text">No tags yet</p>
      <p className="mt-1 text-sm text-electric-text-muted">
        Create your first tag, then write its URL to the physical NFC chip
        with TagWriter on your phone.
      </p>
      <Link
        href="/dashboard/tags/new"
        className="mt-4 inline-block rounded-full bg-electric-cyan px-5 py-2 text-sm font-semibold text-electric-bg transition-colors hover:bg-electric-cyan-deep"
      >
        Create your first tag
      </Link>
    </div>
  );
}

function TagCard({ tag, siteUrl }: { tag: NfcTag; siteUrl: string }) {
  const title = tag.location_name?.trim()
    ? tag.location_name
    : `${FORMAT_LABELS[tag.format]} · ${COLOR_LABELS[tag.color]}`;
  return (
    <Link
      href={`/dashboard/tags/${tag.id}`}
      className="block rounded-2xl border border-electric-border bg-electric-surface p-4 transition hover:border-electric-cyan"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          {tag.tag_number != null ? (
            <span className="shrink-0 rounded-md bg-electric-surface-2 px-1.5 py-0.5 font-mono text-xs font-semibold text-electric-cyan">
              #{String(tag.tag_number).padStart(3, "0")}
            </span>
          ) : null}
          <span
            className="inline-block h-5 w-5 rounded-full border border-electric-border"
            style={{ backgroundColor: COLOR_SWATCH[tag.color] }}
            aria-hidden
          />
          <p className="font-display text-lg font-semibold text-electric-text">{title}</p>
        </div>
        {tag.is_active ? (
          <span className="rounded-full bg-electric-cyan/15 px-2.5 py-0.5 text-xs font-semibold text-electric-cyan">
            Active
          </span>
        ) : (
          <span className="rounded-full bg-electric-surface-2 px-2.5 py-0.5 text-xs font-semibold text-electric-text-muted">
            Inactive
          </span>
        )}
      </div>
      <p className="mt-1 text-sm text-electric-text-muted">
        {FORMAT_LABELS[tag.format]} · {COLOR_LABELS[tag.color]}
      </p>
      <p className="mt-2 truncate font-mono text-xs text-electric-text-muted/80">
        {siteUrl}/t/{tag.tag_uuid}
      </p>
    </Link>
  );
}
