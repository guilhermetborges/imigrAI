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

const registerSchema = z
  .object({
    email: z.string().email("Email invalido"),
    password: z.string().min(8, "Senha deve ter no minimo 8 caracteres"),
    confirmPassword: z.string().min(8, "Confirme sua senha")
  })
  .refine((value) => value.password === value.confirmPassword, {
    message: "As senhas devem ser iguais",
    path: ["confirmPassword"]
  });

type RegisterValues = z.infer<typeof registerSchema>;

export default function RegisterPage(): JSX.Element {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextParam = searchParams.get("next");
  const nextUrl =
    nextParam && nextParam.startsWith("/") && !nextParam.startsWith("//")
      ? nextParam
      : "/onboarding";
  const loginHref = nextUrl === "/onboarding" ? "/login" : `/login?next=${encodeURIComponent(nextUrl)}`;
  const { register: registerAccount, status } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: "",
      password: "",
      confirmPassword: ""
    }
  });

  const registerMutation = useMutation({
    mutationFn: async (payload: RegisterValues) =>
      registerAccount({ email: payload.email, password: payload.password }),
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
        description="Validando se ja existe autenticacao ativa para este navegador."
      />
    );
  }

  return (
    <div className="mx-auto max-w-md reveal">
      <Card>
        <h1 className="font-serif text-4xl">Criar conta</h1>
        <p className="mt-2 text-sm text-muted">Em menos de 2 minutos voce ja calcula seu score.</p>

        <form
          className="mt-6 space-y-4"
          onSubmit={handleSubmit((payload) => registerMutation.mutate(payload))}
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
          <Input
            label="Confirmar senha"
            type="password"
            placeholder="********"
            error={errors.confirmPassword?.message}
            {...register("confirmPassword")}
          />

          {registerMutation.isError ? (
            <p className="text-sm text-danger">{getApiErrorMessage(registerMutation.error)}</p>
          ) : null}

          <Button fullWidth type="submit" disabled={registerMutation.isPending}>
            {registerMutation.isPending ? "Criando conta..." : "Criar conta"}
          </Button>
        </form>

        <p className="mt-4 text-sm text-muted">
          Ja possui acesso?{" "}
          <Link href={loginHref} className="font-semibold text-brand hover:underline">
            Entrar
          </Link>
        </p>
      </Card>
    </div>
  );
}
