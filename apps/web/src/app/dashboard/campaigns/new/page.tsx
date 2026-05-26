import Link from "next/link";

import { getDashboardContext } from "@/lib/dashboard-data";

import { CampaignForm } from "../campaign-form";

export default async function NewCampaignPage() {
  await getDashboardContext();

  // Sensible default window: starts tomorrow at 09:00, lasts a week.
  // The owner almost always edits these, but the defaults remove a chore.
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 9, 0);
  const end = new Date(start);
  end.setDate(end.getDate() + 7);

  return (
    <main className="space-y-6">
      <header>
        <p className="text-sm text-brand-black/60">
          <Link href="/dashboard/campaigns" className="underline">
            Campaigns
          </Link>{" "}
          / New
        </p>
        <h1 className="font-display text-3xl">New campaign</h1>
        <p className="mt-1 text-sm text-brand-black/60">
          Double-stamp campaigns multiply stamps awarded during a time window.
          You can only run one at a time.
        </p>
      </header>

      <CampaignForm
        mode="create"
        initial={{
          name: "",
          multiplier: 2,
          starts_at: toDatetimeLocal(start),
          ends_at: toDatetimeLocal(end),
          status: "draft",
        }}
      />
    </main>
  );
}

function toDatetimeLocal(date: Date): string {
  // Format compatible with <input type="datetime-local">: YYYY-MM-DDTHH:mm
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}
