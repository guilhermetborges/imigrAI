"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";

const publicLinks = [
  { href: "/", label: "Home" },
  { href: "/pricing", label: "Pricing" }
];

const authLinks = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/onboarding", label: "Onboarding" }
];

export function SiteHeader(): JSX.Element {
  const pathname = usePathname();
  const { status, logout } = useAuth();
  const isAuthenticated = status === "authenticated";

  return (
    <header className="sticky top-0 z-40 border-b border-ink/10 bg-canvas/90 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
        <Link href="/" className="font-serif text-2xl font-semibold tracking-tight text-ink">
          imigrAI
        </Link>
        <nav className="hidden items-center gap-1 md:flex">
          {[...publicLinks, ...(isAuthenticated ? authLinks : [])].map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "rounded-lg px-3 py-2 text-sm text-muted transition hover:text-ink",
                pathname === link.href && "bg-brand/10 text-ink"
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          {isAuthenticated ? (
            <Button variant="ghost" size="sm" onClick={logout}>
              Sair
            </Button>
          ) : (
            <>
              <Link href="/login">
                <Button variant="ghost" size="sm">
                  Login
                </Button>
              </Link>
              <Link href="/register">
                <Button size="sm">Criar conta</Button>
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
