import { getDashboardContext } from "@/lib/dashboard-data";

import { DashboardShell } from "./shell";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const ctx = await getDashboardContext();

  return (
    <DashboardShell
      tenantName={ctx.tenant.name}
      email={ctx.email}
      trialStatus={ctx.tenant.trial_status}
      trialEndsAt={ctx.tenant.trial_ends_at}
    >
      {children}
    </DashboardShell>
  );
}
