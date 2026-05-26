/**
 * FAQ entries for the landing accordion. Order matters — top entries
 * are pre-emptive (the questions a skeptical owner thinks BEFORE they
 * ask). Bottom entries are reassurance (cancel, GDPR, setup fee).
 */

export interface FaqItem {
  q: string;
  a: string;
}

export const FAQ_ITEMS: FaqItem[] = [
  {
    q: "Do my customers need to download an app?",
    a: "No. They tap the stand with any modern phone and a page opens in their browser. That's the whole interaction.",
  },
  {
    q: "Does it work on iPhone and Android?",
    a: "Yes — both. NFC works out of the box on iPhones since 2018 and on practically every Android sold today.",
  },
  {
    q: "Are customers forced to give their details?",
    a: "Never. They can leave a review with zero data shared. Stamps and rewards are an opt-in extra they choose themselves.",
  },
  {
    q: "Can I cancel whenever I want?",
    a: "Yes. No contracts, no notice period. Cancel from your dashboard in two clicks and export every customer record on your way out.",
  },
  {
    q: "Who actually owns the customer data?",
    a: "You do. Full stop. We host it on your behalf, you can export it any time, and we never market to your customers ourselves.",
  },
  {
    q: "What if my shop Wi-Fi is patchy?",
    a: "Doesn't matter. The customer's own phone data does the work — your Wi-Fi isn't part of the tap at all.",
  },
  {
    q: "Is this GDPR compliant?",
    a: "Yes. Built for it from day one — explicit consent, EU-hosted data, full customer rights to access, edit and delete. You stay clean.",
  },
  {
    q: "What does the setup fee cover?",
    a: "Your custom 3D-printed stand in your shop's colour, your account fully configured, your Google Reviews link tested, and a short call to walk you through it.",
  },
];
