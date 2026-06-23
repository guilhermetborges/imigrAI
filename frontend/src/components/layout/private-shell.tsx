"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const links = [
  { href: "/dashboard", label: "Visao geral" },
  { href: "/onboarding", label: "Novo score" },
  { href: "/pricing", label: "Planos" },
  { href: "/settings/subscription", label: "Assinatura" }
];

export function PrivateShell({ children }: Readonly<{ children: React.ReactNode }>): JSX.Element {
  const pathname = usePathname();

  return (
    <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
      <aside className="rounded-2xl border border-ink/10 bg-white/80 p-3 shadow-card">
        <p className="px-3 pb-2 text-xs uppercase tracking-[0.16em] text-muted">Workspace</p>
        <nav className="flex flex-col gap-1">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "rounded-lg px-3 py-2 text-sm transition",
                pathname === link.href
                  ? "bg-brand text-brand-contrast"
                  : "text-muted hover:bg-ink/5 hover:text-ink"
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </aside>
      <div>{children}</div>
    </div>
  );
}
