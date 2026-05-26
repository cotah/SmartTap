import Link from "next/link";
import { notFound } from "next/navigation";

import { ApiError, getAuthApiClient } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";

import { SegmentForm } from "../segment-form";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function EditSegmentPage({ params }: Props) {
  await getDashboardContext();
  const { id } = await params;
  const api = getAuthApiClient();

  // No single-segment GET endpoint — list and find. Tenant typically has a
  // handful of segments; avoids adding a route just for this page (same
  // pattern as the campaigns edit page).
  let items;
  try {
    ({ items } = await api.listSegments());
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }
  const segment = items.find((s) => s.id === id);
  if (!segment) notFound();

  return (
    <main className="space-y-6">
      <header>
        <p className="text-sm text-brand-black/60">
          <Link href="/dashboard/segments" className="underline">
            Segments
          </Link>{" "}
          / {segment.name}
        </p>
        <h1 className="font-display text-3xl">{segment.name}</h1>
      </header>

      <SegmentForm
        mode="edit"
        segmentId={segment.id}
        initialName={segment.name}
        initialCriteria={segment.criteria}
      />
    </main>
  );
}
