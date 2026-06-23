"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { type FieldPath, useForm } from "react-hook-form";
import { z } from "zod";

import { AuthGuard } from "@/components/guards/auth-guard";
import { PrivateShell } from "@/components/layout/private-shell";
import { UpgradeModal } from "@/components/modals/upgrade-modal";
import { CardSkeleton } from "@/components/states/loading-skeletons";
import { PageState } from "@/components/states/page-state";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Select } from "@/components/ui/select";
import { useCreateAssessment } from "@/hooks/use-assessment";
import { getApiErrorMessage, isUpgradeRequiredError } from "@/lib/api/client";
import { immigrationApi } from "@/lib/api/endpoints";
import { trackEvent } from "@/lib/tracking";

const educationOptions = [
  { value: "", label: "Selecione" },
  { value: "ensino_medio", label: "Ensino medio" },
  { value: "tecnico", label: "Tecnico" },
  { value: "graduacao", label: "Graduacao" },
  { value: "pos", label: "Pos-graduacao" },
  { value: "mestrado", label: "Mestrado" },
  { value: "doutorado", label: "Doutorado" }
] as const;

const levelOptions = [
  { value: "", label: "Selecione" },
  { value: "A1", label: "A1" },
  { value: "A2", label: "A2" },
  { value: "B1", label: "B1" },
  { value: "B2", label: "B2" },
  { value: "C1", label: "C1" },
  { value: "C2", label: "C2" }
] as const;

const onboardingSchema = z.object({
  age: z.coerce.number().min(18, "Idade minima: 18").max(80, "Idade maxima: 80"),
  education: z.string().min(1, "Selecione a escolaridade"),
  occupation: z.string().min(2, "Profissao obrigatoria"),
  yearsExperience: z.coerce
    .number()
    .min(0, "Anos de experiencia nao pode ser negativo")
    .max(50, "Valor muito alto"),
  languages: z.string().min(2, "Informe ao menos um idioma"),
  languageLevel: z.string().min(1, "Selecione o nivel"),
  income: z.coerce.number().min(0, "Renda deve ser positiva"),
  countriesInterest: z.string().min(2, "Informe ao menos um pais"),
  programId: z.string().uuid("Selecione um programa valido")
});

type OnboardingValues = z.infer<typeof onboardingSchema>;

const steps = [
  {
    title: "Step 1",
    subtitle: "Idade e escolaridade"
  },
  {
    title: "Step 2",
    subtitle: "Profissao e experiencia"
  },
  {
    title: "Step 3",
    subtitle: "Idiomas e nivel"
  },
  {
    title: "Step 4",
    subtitle: "Renda e paises de interesse"
  }
] as const;

function toProfileJson(values: OnboardingValues): Record<string, unknown> {
  return {
    age: values.age,
    education: values.education,
    occupation: values.occupation,
    years_experience: values.yearsExperience,
    languages: values.languages.split(",").map((item) => item.trim()),
    language_level: values.languageLevel,
    income_current: values.income,
    countries_interest: values.countriesInterest.split(",").map((item) => item.trim())
  };
}

export default function OnboardingPage(): JSX.Element {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);

  const {
    register,
    handleSubmit,
    trigger,
    setValue,
    getValues,
    formState: { errors }
  } = useForm<OnboardingValues>({
    resolver: zodResolver(onboardingSchema),
    defaultValues: {
      age: 29,
      education: "",
      occupation: "",
      yearsExperience: 3,
      languages: "Ingles",
      languageLevel: "",
      income: 0,
      countriesInterest: "Canada, Portugal",
      programId: ""
    }
  });

  useEffect(() => {
    trackEvent("onboarding_started");
  }, []);

  const programsQuery = useQuery({
    queryKey: ["programs"],
    queryFn: immigrationApi.listPrograms
  });

  useEffect(() => {
    if (!programsQuery.data?.length) {
      return;
    }

    setValue("programId", programsQuery.data[0].id);
  }, [programsQuery.data, setValue]);

  const programOptions = useMemo(() => {
    const options = [{ value: "", label: "Selecione um programa" }];

    if (!programsQuery.data) {
      return options;
    }

    return [
      ...options,
      ...programsQuery.data.map((program) => ({
        value: program.id,
        label: `${program.name} (${program.code})`
      }))
    ];
  }, [programsQuery.data]);

  const createAssessmentMutation = useCreateAssessment();

  const stepFields: FieldPath<OnboardingValues>[][] = [
    ["age", "education"],
    ["occupation", "yearsExperience"],
    ["languages", "languageLevel"],
    ["income", "countriesInterest", "programId"]
  ];

  const advanceStep = async (): Promise<void> => {
    const isStepValid = await trigger(stepFields[step], { shouldFocus: true });
    if (!isStepValid) {
      return;
    }

    setStep((current) => Math.min(current + 1, steps.length - 1));
  };

  const retreatStep = (): void => {
    setStep((current) => Math.max(current - 1, 0));
  };

  const submit = (values: OnboardingValues): void => {
    createAssessmentMutation.mutate(
      {
        programId: values.programId,
        profileJson: toProfileJson(values)
      },
      {
        onSuccess: (data) => {
          router.push(`/results/${data.assessment_id}`);
        },
        onError: (error) => {
          if (isUpgradeRequiredError(error)) {
            setShowUpgradeModal(true);
          }
        }
      }
    );
  };

  const hasNoPrograms = programsQuery.data?.length === 0;
  const hasPrograms = (programsQuery.data?.length ?? 0) > 0;
  const submitLabel = createAssessmentMutation.isPending
    ? "Enviando avaliacao..."
    : "Finalizar e calcular score";

  return (
    <AuthGuard>
      <PrivateShell>
        <Card className="reveal">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">Onboarding</p>
              <h1 className="mt-2 font-serif text-4xl">{steps[step].subtitle}</h1>
            </div>
            <p className="rounded-lg bg-brand-soft px-3 py-1 text-xs font-medium text-brand">
              {steps[step].title}
            </p>
          </div>

          <div className="mt-5">
            <Progress value={((step + 1) / steps.length) * 100} />
          </div>

          {programsQuery.isLoading ? (
            <div className="mt-8">
              <CardSkeleton />
            </div>
          ) : null}

          {programsQuery.isError ? (
            <div className="mt-8">
              <PageState
                title="Erro ao buscar programas"
                description={getApiErrorMessage(programsQuery.error)}
                actionLabel="Tentar novamente"
                onAction={() => programsQuery.refetch()}
              />
            </div>
          ) : null}

          {hasNoPrograms ? (
            <div className="mt-8">
              <PageState
                title="Nenhum programa ativo"
                description="O backend nao retornou programas ativos. Rode seed e tente novamente."
              />
            </div>
          ) : null}

          {hasPrograms ? (
            <form className="mt-8 space-y-5" onSubmit={handleSubmit(submit)}>
              {step === 0 ? (
                <div className="grid gap-4 md:grid-cols-2">
                  <Input
                    label="Idade"
                    type="number"
                    min={18}
                    max={80}
                    error={errors.age?.message}
                    {...register("age")}
                  />
                  <Select
                    label="Escolaridade"
                    options={educationOptions.map((item) => ({ ...item }))}
                    error={errors.education?.message}
                    {...register("education")}
                  />
                </div>
              ) : null}

              {step === 1 ? (
                <div className="grid gap-4 md:grid-cols-2">
                  <Input
                    label="Profissao"
                    placeholder="Ex: Engenheiro de Software"
                    error={errors.occupation?.message}
                    {...register("occupation")}
                  />
                  <Input
                    label="Anos de experiencia"
                    type="number"
                    min={0}
                    max={50}
                    error={errors.yearsExperience?.message}
                    {...register("yearsExperience")}
                  />
                </div>
              ) : null}

              {step === 2 ? (
                <div className="grid gap-4 md:grid-cols-2">
                  <Input
                    label="Idiomas"
                    placeholder="Ex: Ingles, Frances"
                    error={errors.languages?.message}
                    {...register("languages")}
                  />
                  <Select
                    label="Nivel predominante"
                    options={levelOptions.map((item) => ({ ...item }))}
                    error={errors.languageLevel?.message}
                    {...register("languageLevel")}
                  />
                </div>
              ) : null}

              {step === 3 ? (
                <div className="grid gap-4 md:grid-cols-2">
                  <Input
                    label="Renda atual (BRL/mensal)"
                    type="number"
                    min={0}
                    error={errors.income?.message}
                    {...register("income")}
                  />
                  <Input
                    label="Paises de interesse"
                    placeholder="Ex: Canada, Portugal"
                    error={errors.countriesInterest?.message}
                    {...register("countriesInterest")}
                  />
                  <div className="md:col-span-2">
                    <Select
                      label="Programa alvo"
                      options={programOptions}
                      error={errors.programId?.message}
                      {...register("programId")}
                    />
                  </div>
                </div>
              ) : null}

              {createAssessmentMutation.isError ? (
                <div className="space-y-2 rounded-xl border border-danger/30 bg-danger/5 p-3">
                  <p className="text-sm text-danger">{getApiErrorMessage(createAssessmentMutation.error)}</p>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => submit(getValues())}
                    >
                      Tentar novamente
                    </Button>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={() => setShowUpgradeModal(true)}
                    >
                      Fazer upgrade
                    </Button>
                  </div>
                </div>
              ) : null}

              <div className="flex flex-wrap gap-3">
                <Button type="button" variant="ghost" onClick={retreatStep} disabled={step === 0}>
                  Voltar
                </Button>

                {step < steps.length - 1 ? (
                  <Button type="button" onClick={advanceStep}>
                    Proximo
                  </Button>
                ) : (
                  <Button type="submit" disabled={createAssessmentMutation.isPending}>
                    {submitLabel}
                  </Button>
                )}
              </div>
            </form>
          ) : null}
        </Card>

        <UpgradeModal
          isOpen={showUpgradeModal}
          onClose={() => setShowUpgradeModal(false)}
          onUpgrade={() => {
            setShowUpgradeModal(false);
            router.push("/pricing");
          }}
        />
      </PrivateShell>
    </AuthGuard>
  );
}
