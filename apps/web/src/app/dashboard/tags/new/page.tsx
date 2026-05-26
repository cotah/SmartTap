import Link from "next/link";

import { getDashboardContext } from "@/lib/dashboard-data";
import { publicEnv } from "@/lib/env";

import { TagForm } from "../tag-form";

export default async function NewTagPage() {
  await getDashboardContext();

  return (
    <main className="space-y-6">
      <header>
        <p className="text-sm text-brand-black/60">
          <Link href="/dashboard" className="underline">
            Dashboard
          </Link>{" "}
          /{" "}
          <Link href="/dashboard/tags" className="underline">
            NFC tags
          </Link>{" "}
          / New
        </p>
        <h1 className="font-display text-3xl">New NFC tag</h1>
        <p className="mt-1 text-sm text-brand-black/60">
          Once saved, the next screen shows the URL to write onto the
          physical tag.
        </p>
      </header>

      <TagForm mode="create" siteUrl={publicEnv.NEXT_PUBLIC_SITE_URL} />
    </main>
  );
}
