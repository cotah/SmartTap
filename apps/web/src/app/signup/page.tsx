import { SignupForm } from "./signup-form";

interface PageProps {
  searchParams: Promise<{ next?: string }>;
}

export default async function SignupPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const next = params.next ?? "/dashboard";

  return (
    <main className="container flex min-h-dvh items-center justify-center py-12">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <p className="text-xs tracking-[0.3em] text-brand-green">SMARTTAP</p>
          <h1 className="font-display text-3xl">Create your account</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Free 30-day trial. No credit card required.
          </p>
        </div>

        <SignupForm next={next} />
      </div>
    </main>
  );
}
