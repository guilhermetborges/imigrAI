"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { GapsList } from "@/components/assessment/gaps-list";
import { ScoreCard } from "@/components/assessment/score-card";
import { AuthGuard } from "@/components/guards/auth-guard";
import { PrivateShell } from "@/components/layout/private-shell";
import { UpgradeModal } from "@/components/modals/upgrade-modal";
import { CardSkeleton, ListSkeleton } from "@/components/states/loading-skeletons";
import { PageState } from "@/components/states/page-state";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useAssessmentBreakdown, useAssessmentStatus } from "@/hooks/use-assessment";
import { useCreateRoadmap } from "@/hooks/use-roadmap";
import { useSubscription } from "@/hooks/use-subscription";
import { getApiErrorMessage, isUpgradeRequiredError } from "@/lib/api/client";
import { trackEvent } from "@/lib/tracking";
import { toNumber } from "@/lib/formatters";

interface ResultsPageProps {
  params: {
    assessmentId: string;
  };
}

const terminalStatuses = new Set(["completed", "failed", "canceled"]);

function getRoadmapDescription(hasRoadmapAccess: boolean): string {
  return hasRoadmapAccess
    ? "Voce tem acesso Pro para gerar roadmap contextual deste score."
    : "Roadmap completo disponivel no plano Pro.";
}

function renderLoadingShell(children: JSX.Element): JSX.Element {
  return (
    <AuthGuard>
      <PrivateShell>
        {children}
      </PrivateShell>
    </AuthGuard>
  );
}

function renderPageState(title: string, description: string, actionLabel?: string, onAction?: () => void): JSX.Element {
  return renderLoadingShell(
    <PageState title={title} description={description} actionLabel={actionLabel} onAction={onAction} />
  );
}

function getRoadmapLabel(hasAccess: boolean, isPending: boolean): string {
  if (!hasAccess) return "Fazer upgrade para gerar roadmap";
  return isPending ? "Gerando roadmap..." : "Gerar roadmap Pro";
}

function getButtonVariant(hasAccess: boolean): "primary" | "secondary" {
  return hasAccess ? "primary" : "secondary";
}

function renderBreakdownLoading(): JSX.Element {
  return renderLoadingShell(
    <section className="space-y-4">
      <CardSkeleton />
      <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
        <ListSkeleton rows={5} />
        <div className="space-y-4">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </div>
    </section>
  );
}

export default function ResultsPage({ params }: Readonly<ResultsPageProps>): JSX.Element {
  const router = useRouter();
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const assessmentId = params.assessmentId;

  const assessmentStatusQuery = useAssessmentStatus(assessmentId, true);

  const breakdownQuery = useAssessmentBreakdown(
    assessmentId,
    assessmentStatusQuery.data?.status === "completed"
  );

  const { hasRoadmapAccess } = useSubscription();
  const createRoadmapMutation = useCreateRoadmap();

  const groupedBreakdown = useMemo(() => {
    if (!breakdownQuery.data) {
      return [];
    }

    const map = new Map<string, { code: string; score: number; applied: number; blocking: number }>();

    for (const item of breakdownQuery.data.items) {
      const current = map.get(item.rule_group_code) ?? {
        code: item.rule_group_code,
        score: 0,
        applied: 0,
        blocking: 0
      };

      current.score += toNumber(item.score_delta);
      current.applied += item.applied ? 1 : 0;
      current.blocking += item.is_blocking ? 1 : 0;
      map.set(item.rule_group_code, current);
    }

    return Array.from(map.values()).sort((a, b) => b.score - a.score);
  }, [breakdownQuery.data]);

  const handleRoadmapAction = (): void => {
    if (!hasRoadmapAccess) {
      trackEvent("roadmap_upgrade_clicked", {
        source: "results_cta",
        assessment_id: assessmentId
      });
      setShowUpgradeModal(true);
      return;
    }

    createRoadmapMutation.mutate(
      { assessmentId },
      {
        onSuccess: (data) => {
          router.push(`/roadmaps/${data.roadmap_id}`);
        },
        onError: (error) => {
          if (isUpgradeRequiredError(error)) {
            trackEvent("roadmap_upgrade_clicked", {
              source: "results_error",
              assessment_id: assessmentId
            });
            setShowUpgradeModal(true);
          }
        }
      }
    );
  };

  if (assessmentStatusQuery.isLoading) {
    return renderLoadingShell(<CardSkeleton />);
  }

  if (assessmentStatusQuery.isError) {
    return renderPageState(
      "Falha ao carregar status",
      getApiErrorMessage(assessmentStatusQuery.error),
      "Tentar novamente",
      () => assessmentStatusQuery.refetch()
    );
  }

  if (assessmentStatusQuery.timedOut) {
    return renderPageState(
      "Processamento demorando mais que o esperado",
      "Ainda estamos processando seu score. Voce pode tentar novamente agora ou voltar ao dashboard.",
      "Tentar novamente",
      () => assessmentStatusQuery.refetch()
    );
  }

  const status = assessmentStatusQuery.data?.status;

  if (status && !terminalStatuses.has(status)) {
    return renderPageState(
      "Score em processamento",
      `Status atual: ${status}. Polling ativo com backoff progressivo.`
    );
  }

  if (status === "failed" || status === "canceled") {
    return renderPageState(
      "Avaliacao nao concluida",
      `Status final: ${status}. Revise o onboarding e tente novamente.`,
      "Refazer onboarding",
      () => router.push("/onboarding")
    );
  }

  if (breakdownQuery.isLoading) {
    return renderBreakdownLoading();
  }

  if (breakdownQuery.isError || !breakdownQuery.data) {
    return renderPageState(
      "Nao foi possivel carregar o resultado",
      breakdownQuery.isError ? getApiErrorMessage(breakdownQuery.error) : "Sem dados",
      "Atualizar",
      () => breakdownQuery.refetch()
    );
  }

  if (groupedBreakdown.length === 0) {
    return renderPageState(
      "Resultado vazio",
      "A avaliacao foi concluida, mas nao retornou itens de breakdown."
    );
  }

  const score = Math.max(0, Math.min(100, toNumber(breakdownQuery.data.score_final)));
  const roadmapCtaLabel = getRoadmapLabel(hasRoadmapAccess, createRoadmapMutation.isPending);

  return (
    <AuthGuard>
      <PrivateShell>
        <section className="space-y-4 reveal">
          <ScoreCard
            score={score}
            faixa={breakdownQuery.data.faixa}
            completedAt={assessmentStatusQuery.data?.completed_at ?? null}
          />

          <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
            <Card>
              <h2 className="font-serif text-2xl">Breakdown por criterio</h2>
              <div className="mt-4 space-y-3">
                {groupedBreakdown.map((criterion) => (
                  <div key={criterion.code} className="rounded-xl border border-ink/10 bg-white p-4 text-sm">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-semibold">{criterion.code}</p>
                      <p className="text-brand">{criterion.score.toFixed(2)} pts</p>
                    </div>
                    <p className="mt-1 text-xs text-muted">
                      Regras aplicadas: {criterion.applied} | Bloqueios: {criterion.blocking}
                    </p>
                  </div>
                ))}
              </div>
            </Card>

            <div className="space-y-4">
              <GapsList gaps={breakdownQuery.data.gaps_criticos} />

              <Card>
                <h3 className="font-semibold">Proxima acao</h3>
                <p className="mt-2 text-sm text-muted">
                  {getRoadmapDescription(hasRoadmapAccess)}
                </p>

                <Button
                  className="mt-4"
                  fullWidth
                  variant={getButtonVariant(hasRoadmapAccess)}
                  disabled={createRoadmapMutation.isPending}
                  onClick={handleRoadmapAction}
                >
                  {roadmapCtaLabel}
                </Button>

                {createRoadmapMutation.isError ? (
                  <div className="mt-2 rounded-lg border border-danger/30 bg-danger/5 p-2 text-xs text-danger">
                    <p>{getApiErrorMessage(createRoadmapMutation.error)}</p>
                    <Button
                      className="mt-2"
                      size="sm"
                      variant="ghost"
                      onClick={handleRoadmapAction}
                    >
                      Tentar novamente
                    </Button>
                  </div>
                ) : null}
              </Card>
            </div>
          </div>
        </section>

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
