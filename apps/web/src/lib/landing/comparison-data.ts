/**
 * Comparison table data (Section 6 of the landing). 5 axes max per
 * LANDING-SPEC.md — long tables stop being scannable and start being
 * defensive.
 *
 * Wording stays neutral ("Typical alternatives" not named competitors) —
 * naming names invites the reader to google them. Each row must be
 * factually defensible.
 */

export interface ComparisonRow {
  axis: string;
  smarttap: string;
  others: string;
  /** Marks the SmartTap value as "win" — drives the green check styling.
   * Default true; flip to false only for axes where you want to flag
   * neutral parity (none currently). */
  win?: boolean;
}

export const COMPARISON_ROWS: ComparisonRow[] = [
  {
    axis: "Customer data ownership",
    smarttap: "You own it",
    others: "They own it",
  },
  {
    axis: "App download required",
    smarttap: "No — just tap",
    others: "Yes",
  },
  {
    axis: "Physical stand included",
    smarttap: "Yes, custom 3D-printed",
    others: "Sold separately",
  },
  {
    axis: "Built for your shop",
    smarttap: "White-label, your brand",
    others: "Their logo",
  },
  {
    axis: "Support from Ireland",
    smarttap: "Founder, in Dublin",
    others: "Call centre abroad",
  },
];
