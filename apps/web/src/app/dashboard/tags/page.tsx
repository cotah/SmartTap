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
          <p className="text-sm text-brand-black/60">
            <Link href="/dashboard" className="underline">
              Dashboard
            </Link>{" "}
            / NFC tags
          </p>
          <h1 className="font-display text-3xl">NFC tags</h1>
          <p className="mt-1 text-sm text-brand-black/60">
            One row per physical tag — write the public URL onto each one
            with TagWriter.
          </p>
        </div>
        <Link
          href="/dashboard/tags/new"
          className="rounded-full bg-brand-green px-5 py-2.5 text-sm font-semibold text-brand-off-white"
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
    <div className="rounded-2xl border border-dashed border-brand-black/20 bg-white p-8 text-center">
      <p className="font-display text-lg">No tags yet</p>
      <p className="mt-1 text-sm text-brand-black/60">
        Create your first tag, then write its URL to the physical NFC chip
        with TagWriter on your phone.
      </p>
      <Link
        href="/dashboard/tags/new"
        className="mt-4 inline-block rounded-full bg-brand-green px-5 py-2 text-sm font-semibold text-brand-off-white"
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
      className="block rounded-2xl border border-brand-black/10 bg-white p-4 shadow-sm transition hover:border-brand-green"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className="inline-block h-5 w-5 rounded-full border border-brand-black/10"
            style={{ backgroundColor: COLOR_SWATCH[tag.color] }}
            aria-hidden
          />
          <p className="font-display text-lg">{title}</p>
        </div>
        {tag.is_active ? (
          <span className="rounded-full bg-brand-green/10 px-2.5 py-0.5 text-xs font-semibold text-brand-green">
            Active
          </span>
        ) : (
          <span className="rounded-full bg-brand-black/5 px-2.5 py-0.5 text-xs font-semibold text-brand-black/60">
            Inactive
          </span>
        )}
      </div>
      <p className="mt-1 text-sm text-brand-black/60">
        {FORMAT_LABELS[tag.format]} · {COLOR_LABELS[tag.color]}
      </p>
      <p className="mt-2 truncate font-mono text-xs text-brand-black/50">
        {siteUrl}/t/{tag.tag_uuid}
      </p>
    </Link>
  );
}
