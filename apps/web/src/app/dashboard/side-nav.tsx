"use client";

import {
  CreditCard,
  Gift,
  type LucideIcon,
  LayoutDashboard,
  Layers,
  Megaphone,
  Settings,
  Star,
  Tag,
  Ticket,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavLink {
  href: string;
  label: string;
  icon: LucideIcon;
}

const NAV_LINKS: NavLink[] = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/customers", label: "Customers", icon: Users },
  { href: "/dashboard/segments", label: "Segments", icon: Layers },
  { href: "/dashboard/tags", label: "NFC tags", icon: Tag },
  { href: "/dashboard/reward", label: "Reward", icon: Gift },
  { href: "/dashboard/campaigns", label: "Campaigns", icon: Megaphone },
  { href: "/dashboard/reviews", label: "Reviews", icon: Star },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
  { href: "/dashboard/billing", label: "Billing", icon: CreditCard },
];

interface Props {
  mobileOpen: boolean;
  onClose: () => void;
}

export function SideNav({ mobileOpen, onClose }: Props) {
  const pathname = usePathname();

  function isActive(href: string): boolean {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  return (
    <nav
      aria-label="Dashboard navigation"
      className={`fixed left-0 top-0 z-40 flex h-full w-64 flex-col border-r border-neutral-300/40 bg-white transition-transform duration-300 md:translate-x-0 ${
        mobileOpen ? "translate-x-0" : "-translate-x-full"
      }`}
    >
      <div className="flex items-start justify-between border-b border-neutral-300/40 p-6">
        <div>
          <h2 className="font-display text-2xl leading-tight text-brand-green">
            SmartTap
          </h2>
          <p className="mt-1 text-xs text-neutral-600">Business Dashboard</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close menu"
          className="p-1 text-neutral-600 hover:text-brand-green md:hidden"
        >
          <X className="h-5 w-5" aria-hidden="true" />
        </button>
      </div>

      <div className="flex-1 space-y-1 overflow-y-auto px-3 py-6">
        {NAV_LINKS.map((link) => {
          const Icon = link.icon;
          const active = isActive(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              onClick={onClose}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-bold tracking-wide transition-all ${
                active
                  ? "translate-x-1 bg-brand-green text-white shadow-sm"
                  : "text-neutral-600 hover:bg-brand-green/5 hover:text-brand-green"
              }`}
            >
              <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
              {link.label}
            </Link>
          );
        })}
      </div>

      <div className="border-t border-neutral-300/40 p-4">
        <Link
          href="/dashboard/redeem"
          onClick={onClose}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-green px-4 py-3 text-sm font-bold uppercase tracking-wider text-white shadow-sm transition-colors hover:bg-green-800"
        >
          <Ticket className="h-5 w-5" aria-hidden="true" />
          Redeem reward
        </Link>
      </div>
    </nav>
  );
}
