"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { getApiErrorMessage, getApiErrorStatus } from "@/lib/api/client";
import { profileMatchApi } from "@/lib/api/endpoints";
import type { ProfileMatchResultRead } from "@/types/api";

const GUEST_SESSION_ID_KEY = "imigrai_guest_session_id";
const PENDING_SUBMISSION_KEY = "imigrai_pending_submission";

const profileFormSchema = z.object({
  age: z.number().int().min(18).max(70),
  education_level: z.enum(["ensino_medio", "tecnico", "graduacao", "mestrado", "doutorado"]),
  experience_years: z.number().int().min(0).max(45),
  english_level: z.enum(["A1", "A2", "B1", "B2", "C1", "C2"]),
  french_level: z.enum(["A1", "A2", "B1", "B2", "C1", "C2"]),
  savings_brl: z.number().min(0).max(10_000_000),
  monthly_income_brl: z.number().min(0).max(1_000_000),
  profession_area: z.enum([
    "tecnologia",
    "engenharia",
    "saude",
    "negocios",
    "educacao",
    "servicos",
    "outros"
  ]),
  has_job_offer: z.boolean(),
  has_family_abroad: z.boolean(),
  willing_to_learn_language: z.boolean(),
  wants_fast_citizenship: z.boolean(),
  preferred_region: z.enum(["americas", "europa", "asia", "indiferente"])
});

type ProfileFormValues = z.infer<typeof profileFormSchema>;

interface PendingSubmission {
  submission_id: string;
  guest_session_id: string;
}

function buildGuestSessionId(): string {
  if (globalThis.window === undefined) {
    return "guest-session-server";
  }

  if (globalThis.window.crypto !== undefined && typeof globalThis.window.crypto.randomUUID === "function") {
    return `guest-${globalThis.window.crypto.randomUUID()}`;
  }

  return `guest-${Math.random().toString(36).slice(2)}-${Date.now()}`;
}

function getOrCreateGuestSessionId(): string {
  if (globalThis.window === undefined) {
    return "guest-session-server";
  }

  const existing = globalThis.window.localStorage.getItem(GUEST_SESSION_ID_KEY);
  if (existing && existing.length >= 8) {
    return existing;
  }

  const created = buildGuestSessionId();
  globalThis.window.localStorage.setItem(GUEST_SESSION_ID_KEY, created);
  return created;
}

function readPendingSubmission(): PendingSubmission | null {
  if (globalThis.window === undefined) {
    return null;
  }

  const raw = globalThis.window.localStorage.getItem(PENDING_SUBMISSION_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as PendingSubmission;
    if (!parsed.submission_id || !parsed.guest_session_id) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function writePendingSubmission(pending: PendingSubmission): void {
  if (globalThis.window === undefined) {
    return;
  }
  globalThis.window.localStorage.setItem(PENDING_SUBMISSION_KEY, JSON.stringify(pending));
}

function clearPendingSubmission(): void {
  if (globalThis.window === undefined) {
    return;
  }
  globalThis.window.localStorage.removeItem(PENDING_SUBMISSION_KEY);
}

const educationOptions = [
  { value: "ensino_medio", label: "Ensino medio" },
  { value: "tecnico", label: "Tecnico" },
  { value: "graduacao", label: "Graduacao" },
  { value: "mestrado", label: "Mestrado" },
  { value: "doutorado", label: "Doutorado" }
];

const levelOptions = [
  { value: "A1", label: "A1 - Basico" },
  { value: "A2", label: "A2 - Basico+" },
  { value: "B1", label: "B1 - Intermediario" },
  { value: "B2", label: "B2 - Intermediario+" },
  { value: "C1", label: "C1 - Avancado" },
  { value: "C2", label: "C2 - Fluente" }
];

const professionOptions = [
  { value: "tecnologia", label: "Tecnologia" },
  { value: "engenharia", label: "Engenharia" },
  { value: "saude", label: "Saude" },
  { value: "negocios", label: "Negocios" },
  { value: "educacao", label: "Educacao" },
  { value: "servicos", label: "Servicos" },
  { value: "outros", label: "Outros" }
];

const regionOptions = [
  { value: "indiferente", label: "Indiferente" },
  { value: "americas", label: "Americas" },
  { value: "europa", label: "Europa" },
  { value: "asia", label: "Asia" }
];

export default function LandingPage(): JSX.Element {
  const { status } = useAuth();
  const [result, setResult] = useState<ProfileMatchResultRead | null>(null);
  const [pendingSubmission, setPendingSubmission] = useState<PendingSubmission | null>(null);
  const [claimError, setClaimError] = useState<string | null>(null);
  const lastClaimAttemptRef = useRef<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileFormSchema),
    defaultValues: {
      age: 29,
      education_level: "graduacao",
      experience_years: 5,
      english_level: "B2",
      french_level: "A1",
      savings_brl: 60000,
      monthly_income_brl: 12000,
      profession_area: "tecnologia",
      has_job_offer: false,
      has_family_abroad: false,
      willing_to_learn_language: true,
      wants_fast_citizenship: false,
      preferred_region: "indiferente"
    }
  });

  const claimMutation = useMutation({
    mutationFn: (payload: PendingSubmission) => profileMatchApi.claim(payload),
    onSuccess: (data) => {
      setResult(data);
      setClaimError(null);
      setPendingSubmission(null);
      clearPendingSubmission();
    },
    onError: (error) => {
      const statusCode = getApiErrorStatus(error);
      if (statusCode === 403 || statusCode === 404) {
        clearPendingSubmission();
        setPendingSubmission(null);
      }
      setClaimError(getApiErrorMessage(error));
    }
  });

  const submitMutation = useMutation({
    mutationFn: async (values: ProfileFormValues) => {
      const guestSessionId = getOrCreateGuestSessionId();
      return profileMatchApi.submit({
        ...values,
        guest_session_id: guestSessionId
      });
    },
    onSuccess: (data) => {
      setClaimError(null);
      if (data.requires_login) {
        const pending = {
          submission_id: data.submission_id,
          guest_session_id: getOrCreateGuestSessionId()
        };
        writePendingSubmission(pending);
        setPendingSubmission(pending);
        setResult(null);
        return;
      }

      clearPendingSubmission();
      setPendingSubmission(null);
      setResult(data.result);
    }
  });

  useEffect(() => {
    const pending = readPendingSubmission();
    setPendingSubmission(pending);
  }, []);

  useEffect(() => {
    if (status !== "authenticated" || !pendingSubmission) {
      return;
    }

    if (lastClaimAttemptRef.current === pendingSubmission.submission_id) {
      return;
    }

    lastClaimAttemptRef.current = pendingSubmission.submission_id;
    claimMutation.mutate(pendingSubmission);
  }, [status, pendingSubmission, claimMutation]);

  return (
    <section className="space-y-6">
      <Card className="reveal overflow-hidden bg-gradient-to-br from-brand-soft via-white to-accent-soft">
        <div className="grid gap-6 md:grid-cols-[1.15fr_1fr] md:items-center">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
              Diagnostico inicial gratuito
            </p>
            <h1 className="mt-2 font-serif text-4xl leading-tight sm:text-5xl">
              Preencha seu perfil e veja os paises mais aderentes para imigracao.
            </h1>
            <p className="mt-3 text-sm text-muted">
              O formulario e livre sem login. O resultado com ranking dos 15 paises fica protegido
              por conta para manter historico e seguranca dos dados.
            </p>
          </div>
          <div className="rounded-2xl border border-brand/20 bg-white/90 p-5">
            <p className="text-sm font-semibold text-muted">Fluxo do plano gratis</p>
            <div className="mt-3 space-y-2 text-sm text-ink">
              <p>1. Envie seus dados no formulario da home.</p>
              <p>2. O perfil e salvo no banco imediatamente.</p>
              <p>3. Login libera o ranking e recomenda os melhores destinos.</p>
            </div>
          </div>
        </div>
      </Card>

      <Card className="reveal">
        <h2 className="font-serif text-3xl">Formulario de perfil migratorio</h2>
        <p className="mt-2 text-sm text-muted">
          Campos relevantes para elegibilidade inicial, aderencia de mercado e viabilidade
          financeira.
        </p>

        <form
          className="mt-6 space-y-5"
          onSubmit={handleSubmit((values) => submitMutation.mutate(values))}
        >
          <div className="grid gap-4 md:grid-cols-2">
            <Input
              label="Idade"
              type="number"
              min={18}
              max={70}
              error={errors.age?.message}
              {...register("age", { valueAsNumber: true })}
            />
            <Select
              label="Escolaridade"
              options={educationOptions}
              error={errors.education_level?.message}
              {...register("education_level")}
            />
            <Input
              label="Anos de experiencia"
              type="number"
              min={0}
              max={45}
              error={errors.experience_years?.message}
              {...register("experience_years", { valueAsNumber: true })}
            />
            <Select
              label="Area profissional"
              options={professionOptions}
              error={errors.profession_area?.message}
              {...register("profession_area")}
            />
            <Select
              label="Ingles"
              options={levelOptions}
              error={errors.english_level?.message}
              {...register("english_level")}
            />
            <Select
              label="Frances"
              options={levelOptions}
              error={errors.french_level?.message}
              {...register("french_level")}
            />
            <Input
              label="Reserva financeira (BRL)"
              type="number"
              min={0}
              error={errors.savings_brl?.message}
              {...register("savings_brl", { valueAsNumber: true })}
            />
            <Input
              label="Renda mensal (BRL)"
              type="number"
              min={0}
              error={errors.monthly_income_brl?.message}
              {...register("monthly_income_brl", { valueAsNumber: true })}
            />
            <Select
              label="Regiao de preferencia"
              options={regionOptions}
              error={errors.preferred_region?.message}
              {...register("preferred_region")}
            />
          </div>

          <div className="grid gap-3 rounded-xl border border-ink/10 bg-white p-4 md:grid-cols-2">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" className="h-4 w-4 accent-[#1993ab]" {...register("has_job_offer")} />{" "}
              Possuo oferta de trabalho
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="h-4 w-4 accent-[#1993ab]"
                {...register("has_family_abroad")}
              />
              {" "}Tenho familia no exterior
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="h-4 w-4 accent-[#1993ab]"
                {...register("willing_to_learn_language")}
              />
              {" "}Tenho disponibilidade para aprender novo idioma
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="h-4 w-4 accent-[#1993ab]"
                {...register("wants_fast_citizenship")}
              />
              {" "}Prioridade em paises com cidadania mais rapida
            </label>
          </div>

          {submitMutation.isError ? (
            <p className="text-sm text-danger">{getApiErrorMessage(submitMutation.error)}</p>
          ) : null}

          <Button type="submit" disabled={submitMutation.isPending}>
            {submitMutation.isPending ? "Calculando aderencia..." : "Calcular paises compativeis"}
          </Button>
        </form>
      </Card>

      {pendingSubmission && status !== "authenticated" ? (
        <Card className="reveal border border-brand/20">
          <h3 className="font-serif text-2xl">Perfil salvo com sucesso</h3>
          <p className="mt-2 text-sm text-muted">
            Seus dados ja foram gravados. Para ver o ranking dos paises, faca login ou crie uma
            conta gratuita.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link href="/login?next=%2F">
              <Button>Entrar para ver resultado</Button>
            </Link>
            <Link href="/register?next=%2F">
              <Button variant="ghost">Criar conta gratuita</Button>
            </Link>
          </div>
        </Card>
      ) : null}

      {claimMutation.isPending ? (
        <Card>
          <p className="text-sm text-muted">
            Recuperando seu resultado salvo para esta conta, aguarde alguns segundos...
          </p>
        </Card>
      ) : null}

      {claimError ? (
        <Card>
          <p className="text-sm text-danger">Nao foi possivel recuperar o resultado: {claimError}</p>
          {pendingSubmission && status === "authenticated" ? (
            <Button className="mt-4" onClick={() => claimMutation.mutate(pendingSubmission)}>
              Tentar novamente
            </Button>
          ) : null}
        </Card>
      ) : null}

      {result ? (
        <Card className="reveal">
          <h2 className="font-serif text-3xl">Ranking de paises mais compativeis</h2>
          <p className="mt-2 text-sm text-muted">
            Algoritmo: {result.algorithm_version}. Resultado gerado em{" "}
            {new Date(result.created_at).toLocaleString("pt-BR")}.
          </p>

          <div className="mt-6 grid gap-4">
            {result.matches.map((country, index) => (
              <article key={country.country_code} className="rounded-xl border border-ink/10 bg-white p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h3 className="text-lg font-semibold">
                    {index + 1}. {country.country_name}
                  </h3>
                  <span className="rounded-lg bg-brand-soft px-3 py-1 text-sm font-semibold text-ink">
                    {country.match_score.toFixed(2)}% de aderencia
                  </span>
                </div>
                <ul className="mt-3 space-y-1 text-sm text-muted">
                  {country.highlights.map((highlight) => (
                    <li key={`${country.country_code}-${highlight}`}>- {highlight}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </Card>
      ) : null}
    </section>
  );
}
