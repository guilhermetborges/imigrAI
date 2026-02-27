"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { PageState } from "@/components/states/page-state";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage } from "@/lib/api/client";

const loginSchema = z.object({
  email: z.string().email("Email invalido"),
  password: z.string().min(8, "Senha deve ter pelo menos 8 caracteres")
});

type LoginValues = z.infer<typeof loginSchema>;

export default function LoginPage(): JSX.Element {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextParam = searchParams.get("next");
  const nextUrl =
    nextParam && nextParam.startsWith("/") && !nextParam.startsWith("//")
      ? nextParam
      : "/dashboard";
  const registerHref =
    nextUrl === "/dashboard" ? "/register" : `/register?next=${encodeURIComponent(nextUrl)}`;
  const { login, status } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: ""
    }
  });

  const loginMutation = useMutation({
    mutationFn: (payload: LoginValues) => login(payload),
    onSuccess: () => {
      router.push(nextUrl);
    }
  });

  useEffect(() => {
    if (status === "authenticated") {
      router.replace(nextUrl);
    }
  }, [status, router, nextUrl]);

  if (status === "loading") {
    return (
      <PageState
        title="Checando sessao"
        description="Estamos validando se voce ja possui autenticacao ativa."
      />
    );
  }

  return (
    <div className="mx-auto max-w-md reveal">
      <Card>
        <h1 className="font-serif text-4xl">Entrar</h1>
        <p className="mt-2 text-sm text-muted">Acesse seu painel e continue sua avaliacao.</p>

        <form
          className="mt-6 space-y-4"
          onSubmit={handleSubmit((payload) => loginMutation.mutate(payload))}
        >
          <Input
            label="Email"
            type="email"
            placeholder="voce@email.com"
            error={errors.email?.message}
            {...register("email")}
          />
          <Input
            label="Senha"
            type="password"
            placeholder="********"
            error={errors.password?.message}
            {...register("password")}
          />

          {loginMutation.isError ? (
            <p className="text-sm text-danger">{getApiErrorMessage(loginMutation.error)}</p>
          ) : null}

          <Button fullWidth type="submit" disabled={loginMutation.isPending}>
            {loginMutation.isPending ? "Entrando..." : "Entrar"}
          </Button>
        </form>

        <p className="mt-4 text-sm text-muted">
          Nao possui conta?{" "}
          <Link href={registerHref} className="font-semibold text-brand hover:underline">
            Crie agora
          </Link>
        </p>
      </Card>
    </div>
  );
}
