"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { AuthGuard } from "@/components/guards/auth-guard";
import { PrivateShell } from "@/components/layout/private-shell";
import { PageState } from "@/components/states/page-state";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getApiErrorMessage } from "@/lib/api/client";
import { roadmapsApi } from "@/lib/api/endpoints";
import { formatDate } from "@/lib/formatters";

interface RoadmapPageProps {
  params: {
    roadmapId: string;
  };
}

const finalStatuses = ["completed", "failed", "published", "archived", "draft"];

function getPriorityLabel(risk: string): "alta" | "media" | "baixa" {
  if (risk === "alto") {
    return "alta";
  }
  if (risk === "baixo") {
    return "baixa";
  }
  return "media";
}

export default function RoadmapPage({ params }: RoadmapPageProps): JSX.Element {
  const router = useRouter();
  const roadmapId = params.roadmapId;

  const statusQuery = useQuery({
    queryKey: ["roadmap-status", roadmapId],
    queryFn: () => roadmapsApi.getStatus(roadmapId),
    refetchInterval: (query) => {
      const currentStatus = query.state.data?.status;
      if (currentStatus && finalStatuses.includes(currentStatus)) {
        return false;
      }
      return 3500;
    }
  });

  const detailQuery = useQuery({
    queryKey: ["roadmap-detail", roadmapId],
    queryFn: () => roadmapsApi.getDetail(roadmapId),
    enabled:
      statusQuery.data?.status !== "failed" &&
      statusQuery.data?.status !== "pending" &&
      statusQuery.data?.status !== undefined
  });

  if (statusQuery.isLoading) {
    return (
      <AuthGuard>
        <PrivateShell>
          <PageState
            title="Carregando roadmap"
            description="Buscando status inicial do roadmap para este assessment."
          />
        </PrivateShell>
      </AuthGuard>
    );
  }

  if (statusQuery.isError) {
    return (
      <AuthGuard>
        <PrivateShell>
          <PageState
            title="Erro ao consultar roadmap"
            description={getApiErrorMessage(statusQuery.error)}
            actionLabel="Tentar novamente"
            onAction={() => statusQuery.refetch()}
          />
        </PrivateShell>
      </AuthGuard>
    );
  }

  if (statusQuery.data?.status === "pending") {
    return (
      <AuthGuard>
        <PrivateShell>
          <PageState
            title="Roadmap em processamento"
            description="Estamos gerando passos priorizados com prazo e dependencias."
          />
        </PrivateShell>
      </AuthGuard>
    );
  }

  if (statusQuery.data?.status === "failed") {
    return (
      <AuthGuard>
        <PrivateShell>
          <PageState
            title="Falha na geracao do roadmap"
            description={statusQuery.data.error ?? "O processo terminou com erro."}
            actionLabel="Voltar para resultado"
            onAction={() => router.push("/dashboard")}
          />
        </PrivateShell>
      </AuthGuard>
    );
  }

  if (detailQuery.isLoading) {
    return (
      <AuthGuard>
        <PrivateShell>
          <PageState
            title="Montando checklist"
            description="Carregando estrutura final de passos e dependencias."
          />
        </PrivateShell>
      </AuthGuard>
    );
  }

  if (detailQuery.isError || !detailQuery.data) {
    return (
      <AuthGuard>
        <PrivateShell>
          <PageState
            title="Nao foi possivel carregar o roadmap"
            description={detailQuery.isError ? getApiErrorMessage(detailQuery.error) : "Sem conteudo"}
            actionLabel="Recarregar"
            onAction={() => detailQuery.refetch()}
          />
        </PrivateShell>
      </AuthGuard>
    );
  }

  if (!detailQuery.data.steps.length) {
    return (
      <AuthGuard>
        <PrivateShell>
          <PageState
            title="Roadmap sem passos"
            description="Este roadmap nao retornou etapas executaveis."
          />
        </PrivateShell>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard>
      <PrivateShell>
        <section className="space-y-4 reveal">
          <Card className="bg-gradient-to-r from-brand-soft via-white to-white">
            <p className="text-xs uppercase tracking-[0.18em] text-muted">Roadmap</p>
            <h1 className="mt-2 font-serif text-4xl">{detailQuery.data.roadmap.summary}</h1>
            <p className="mt-2 text-sm text-muted">
              Status: {detailQuery.data.roadmap.status} | Concluido em {" "}
              {formatDate(detailQuery.data.roadmap.completed_at)}
            </p>
          </Card>

          <Card>
            <h2 className="font-serif text-2xl">Checklist de execucao</h2>
            <div className="mt-4 space-y-3">
              {detailQuery.data.steps
                .slice()
                .sort((a, b) => a.step_order - b.step_order)
                .map((step) => (
                  <div
                    key={step.id}
                    className="rounded-xl border border-ink/10 bg-white p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-semibold">
                        {step.step_order}. {step.title}
                      </p>
                      <span className="rounded-full bg-accent-soft px-3 py-1 text-xs font-semibold text-ink">
                        prioridade {getPriorityLabel(step.risk_level)}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-muted">{step.description}</p>

                    <div className="mt-3 grid gap-2 text-xs text-muted md:grid-cols-3">
                      <p>
                        <strong className="text-ink">Prazo:</strong>{" "}
                        {step.eta_weeks ? `${step.eta_weeks} semanas` : "Nao informado"}
                      </p>
                      <p>
                        <strong className="text-ink">Dependencias:</strong>{" "}
                        {step.dependencies_json.length
                          ? step.dependencies_json.join(", ")
                          : "Nenhuma"}
                      </p>
                      <p>
                        <strong className="text-ink">Criterio de conclusao:</strong>{" "}
                        {step.completion_criteria}
                      </p>
                    </div>
                  </div>
                ))}
            </div>
            <Button className="mt-5" variant="ghost" onClick={() => router.push("/dashboard") }>
              Voltar para dashboard
            </Button>
          </Card>
        </section>
      </PrivateShell>
    </AuthGuard>
  );
}
