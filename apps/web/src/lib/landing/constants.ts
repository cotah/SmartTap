/**
 * Tunable landing-page constants. Update these as the world changes —
 * specifically `FOUNDING_SPOTS_REMAINING` after each founding member
 * signs, and `BOOK_CALL_URL` once the Cal.com account is live.
 */

/** Founding member spots still open. 5 → 4 → 3 → ... → 0. When 0, the
 * top banner and CTA Final switch to "Founding offer closed" copy. */
export const FOUNDING_SPOTS_REMAINING = 5;
export const FOUNDING_TOTAL = 5;

/** Cal.com booking URL for "15 minutes with the founder".
 *
 * Empty string = mailto fallback (Dialog opens with prefilled email
 * compose). Set this once the Cal.com account is created.
 *
 * Format expected by @calcom/embed-react: "username/event-type"
 * (e.g. "henrique/15min"). NOT a full URL. */
export const BOOK_CALL_URL = "";

/** Mailto destination when BOOK_CALL_URL is empty. */
export const BOOK_CALL_MAILTO = "henrique@smarttap.ie";

/** Hero microtrust line copy — kept here so adjusting it doesn't require
 * touching JSX. */
export const FOUNDER_MICROTRUST = "Built by Henrique in Dublin";

/** Used by the layout metadata. The runtime SITE_URL env var still
 * controls links inside emails, but these are baked at build time for
 * SEO/OG generation. */
export const PUBLIC_SITE_URL = "https://smarttap.ie";
