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
      enabledModules={ctx.tenant.enabled_modules ?? ["loyalty", "reviews"]}
      tenants={ctx.tenants.map((t) => ({ id: t.id, name: t.name }))}
      activeTenantId={ctx.tenant.id}
    >
      {children}
    </DashboardShell>
  );
}
