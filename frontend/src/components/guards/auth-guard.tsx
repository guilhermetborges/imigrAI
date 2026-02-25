"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { PageState } from "@/components/states/page-state";
import { useAuth } from "@/hooks/use-auth";

export function AuthGuard({ children }: { children: React.ReactNode }): JSX.Element {
  const { status } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      const next = encodeURIComponent(pathname || "/dashboard");
      router.replace(`/login?next=${next}`);
    }
  }, [status, pathname, router]);

  if (status === "loading") {
    return (
      <PageState
        title="Validando sessao"
        description="Estamos confirmando seu acesso para abrir esta pagina."
      />
    );
  }

  if (status === "unauthenticated") {
    return (
      <PageState
        title="Redirecionando para login"
        description="Esta area exige autenticacao ativa."
      />
    );
  }

  return <>{children}</>;
}
