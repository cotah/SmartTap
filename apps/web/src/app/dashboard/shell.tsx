"use client";

import { useState } from "react";

import type { TrialStatus } from "@/lib/api";

import { SideNav } from "./side-nav";
import { TopBar } from "./top-bar";
import { TrialBanner } from "./trial-banner";

interface Props {
  tenantName: string;
  email: string | null;
  trialStatus: TrialStatus;
  trialEndsAt: string | null;
  children: React.ReactNode;
}

/**
 * Client shell around every /dashboard/* page. Owns the drawer state for
 * the mobile slide-in navigation. The layout.tsx (server) feeds context
 * props in via `getDashboardContext()`.
 *
 * Layout:
 *  - SideNav (fixed left, w-64 desktop / slide-in drawer mobile)
 *  - Right pane (md:pl-64): TopBar → TrialBanner → main content
 *
 * TrialBanner stays inside the right pane (not at the very top of the
 * body) so the fixed sidenav doesn't slice its content on the left edge.
 */
export function DashboardShell({
  tenantName,
  email,
  trialStatus,
  trialEndsAt,
  children,
}: Props) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="min-h-dvh bg-brand-off-white text-brand-black">
      <SideNav
        mobileOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
      {drawerOpen ? (
        <button
          type="button"
          aria-label="Close menu"
          onClick={() => setDrawerOpen(false)}
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
        />
      ) : null}
      <div className="md:pl-64">
        <TopBar
          tenantName={tenantName}
          email={email}
          trialStatus={trialStatus}
          trialEndsAt={trialEndsAt}
          onMenuClick={() => setDrawerOpen(true)}
        />
        <TrialBanner status={trialStatus} trialEndsAt={trialEndsAt} />
        <main className="px-4 py-8 md:px-10">{children}</main>
      </div>
    </div>
  );
}
