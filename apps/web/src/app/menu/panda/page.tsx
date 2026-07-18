import type { Metadata } from "next";

// ============================================================
//  CONFIGURAÇÃO DO CLIENTE  —  edite só aqui
// ============================================================
const RESTAURANT_NAME = "Panda Restaurant";
const RESTAURANT_TAGLINE = "Sushi · Burger";

// Link de avaliação do Google (abre direto a caixa de escrever review).
const REVIEW_URL =
  "https://search.google.com/local/writereview?placeid=ChIJW6fecH8NZ0gR6NSvIcYW0AE";

const MENU_PAGES = 10; // nº de imagens em /public/menus/panda/

// URL pública desta página (usada no preview de link do WhatsApp).
const PAGE_URL = "https://www.smarttap.ie/menu/panda";
const OG_IMAGE = "/menus/panda/og.jpg"; // card mostrado no WhatsApp
// ============================================================

export const metadata: Metadata = {
  metadataBase: new URL("https://www.smarttap.ie"),
  title: `${RESTAURANT_NAME} — Menu`,
  description: `${RESTAURANT_NAME} · ${RESTAURANT_TAGLINE} — View our menu.`,
  robots: { index: false }, // menu não precisa aparecer no Google
  openGraph: {
    type: "website",
    url: PAGE_URL,
    siteName: RESTAURANT_NAME,
    title: `${RESTAURANT_NAME} — Menu`,
    description: `${RESTAURANT_TAGLINE} · Coopers Court, Bond Street, Dublin`,
    locale: "en_IE",
    images: [
      { url: OG_IMAGE, width: 1200, height: 630, alt: `${RESTAURANT_NAME} menu` },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: `${RESTAURANT_NAME} — Menu`,
    description: `${RESTAURANT_TAGLINE} · Dublin`,
    images: [OG_IMAGE],
  },
};

export default function PandaMenuPage() {
  const pages = Array.from({ length: MENU_PAGES }, (_, i) =>
    `/menus/panda/menu-${String(i + 1).padStart(2, "0")}.webp`
  );

  return (
    <main className="min-h-screen bg-[#0f0f10] text-white">
      {/* Cabeçalho */}
      <header className="px-6 pt-8 pb-5 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">{RESTAURANT_NAME}</h1>
        <p className="mt-1 text-sm text-white/50">{RESTAURANT_TAGLINE}</p>
      </header>

      {/* Menu (uma imagem embaixo da outra, rolagem natural) */}
      <section className="mx-auto max-w-[560px]">
        {pages.map((src, i) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={src}
            src={src}
            alt={`${RESTAURANT_NAME} menu — página ${i + 1}`}
            loading={i === 0 ? "eager" : "lazy"}
            decoding="async"
            className="block w-full h-auto"
          />
        ))}
      </section>

      {/* Bloco de avaliação */}
      <section className="mx-auto max-w-[560px] px-6 py-10 text-center">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-6 py-8">
          <div className="text-3xl" aria-hidden>⭐⭐⭐⭐⭐</div>
          <h2 className="mt-3 text-lg font-medium">Enjoyed your meal?</h2>
          <p className="mt-1 text-sm text-white/50">
            Your review helps {RESTAURANT_NAME} a lot. Thank you!
          </p>
          <a
            href={REVIEW_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-5 inline-flex w-full items-center justify-center rounded-xl bg-[#00D4FF] px-6 py-4 text-base font-semibold text-black transition active:scale-[0.98]"
          >
            Leave a review on Google
          </a>
        </div>
      </section>

      {/* Rodapé discreto — marketing da SmartTap (remova se o cliente pedir) */}
      <footer className="pb-10 text-center text-xs text-white/25">
        Powered by SmartTap
      </footer>
    </main>
  );
}
