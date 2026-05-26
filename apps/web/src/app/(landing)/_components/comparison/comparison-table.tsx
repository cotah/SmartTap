import { Check, X } from "lucide-react";
import * as React from "react";

import { COMPARISON_ROWS } from "@/lib/landing/comparison-data";
import { cn } from "@/lib/utils";

/**
 * Desktop comparison table — visible on md+ screens. 3 columns: axis,
 * SmartTap (highlighted green column), Typical alternatives.
 *
 * Each row uses a check (SmartTap) or X (alternatives) so the eye can
 * scan green/amber down the SmartTap column. The wording lives in
 * `comparison-data.ts`; the icons are added here per cell.
 *
 * Cal.com-style polish: rounded corners on the wrapper, no inner row
 * borders (just subtle dividers), generous vertical padding per row.
 */
export function ComparisonTable() {
  return (
    <div className="hidden md:block">
      <div className="overflow-hidden rounded-2xl border border-neutral-300 bg-cream">
        <table className="w-full text-left">
          <thead className="bg-cream/50">
            <tr className="border-b border-neutral-300">
              <th
                scope="col"
                className="w-2/5 px-6 py-5 font-mono text-xs font-medium uppercase tracking-[0.12em] text-neutral-600"
              >
                What matters
              </th>
              <th
                scope="col"
                className="w-[30%] bg-green-900/[0.04] px-6 py-5 font-display text-xl tracking-tight text-green-900"
              >
                SmartTap
              </th>
              <th
                scope="col"
                className="w-[30%] px-6 py-5 font-display text-xl tracking-tight text-neutral-600"
              >
                Typical alternatives
              </th>
            </tr>
          </thead>
          <tbody>
            {COMPARISON_ROWS.map((row, i) => (
              <tr
                key={row.axis}
                className={cn(
                  i !== COMPARISON_ROWS.length - 1 && "border-b border-neutral-300/70",
                )}
              >
                <th
                  scope="row"
                  className="px-6 py-5 text-base font-medium text-neutral-900"
                >
                  {row.axis}
                </th>
                <td className="bg-green-900/[0.04] px-6 py-5">
                  <span className="flex items-center gap-2 text-base text-neutral-900">
                    <Check
                      className="h-4 w-4 shrink-0 text-green-900"
                      aria-hidden="true"
                    />
                    <span>{row.smarttap}</span>
                  </span>
                </td>
                <td className="px-6 py-5">
                  <span className="flex items-center gap-2 text-base text-neutral-600">
                    <X
                      className="h-4 w-4 shrink-0 text-neutral-600"
                      aria-hidden="true"
                    />
                    <span>{row.others}</span>
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
