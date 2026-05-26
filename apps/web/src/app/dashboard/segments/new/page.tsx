import Link from "next/link";

import { getDashboardContext } from "@/lib/dashboard-data";

import { SegmentForm } from "../segment-form";

export default async function NewSegmentPage() {
  await getDashboardContext();

  return (
    <main className="space-y-6">
      <header>
        <p className="text-sm text-brand-black/60">
          <Link href="/dashboard" className="underline">
            Dashboard
          </Link>{" "}
          /{" "}
          <Link href="/dashboard/segments" className="underline">
            Segments
          </Link>{" "}
          / New
        </p>
        <h1 className="font-display text-3xl">New segment</h1>
        <p className="mt-1 text-sm text-brand-black/60">
          Combine filters with AND. Leave anything blank to ignore it.
        </p>
      </header>

      <SegmentForm mode="create" />
    </main>
  );
}
