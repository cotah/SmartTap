import Link from "next/link";
import { notFound } from "next/navigation";

import { ApiError, getAuthApiClient } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";
import { publicEnv } from "@/lib/env";

import { TagForm } from "../tag-form";
import { FORMAT_LABELS } from "../tag-labels";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function EditTagPage({ params }: Props) {
  await getDashboardContext();
  const { id } = await params;
  const api = getAuthApiClient();

  // No single-tag GET endpoint — list and find. Tenant typically has a
  // small handful of tags; avoids adding a route just for this page
  // (mirrors the campaigns/segments edit-page pattern).
  let items;
  try {
    ({ items } = await api.listTags());
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }
  const tag = items.find((t) => t.id === id);
  if (!tag) notFound();

  const title = tag.location_name?.trim()
    ? tag.location_name
    : FORMAT_LABELS[tag.format];

  return (
    <main className="space-y-6">
      <header>
        <p className="text-sm text-electric-text-muted">
          <Link href="/dashboard/tags" className="underline">
            NFC tags
          </Link>{" "}
          / {title}
        </p>
        <h1 className="font-display text-3xl">{title}</h1>
      </header>

      <TagForm
        mode="edit"
        tagId={tag.id}
        tagUuid={tag.tag_uuid}
        initialFormat={tag.format}
        initialColor={tag.color}
        initialLocationName={tag.location_name ?? ""}
        initialIsActive={tag.is_active}
        siteUrl={publicEnv.NEXT_PUBLIC_SITE_URL}
      />
    </main>
  );
}
