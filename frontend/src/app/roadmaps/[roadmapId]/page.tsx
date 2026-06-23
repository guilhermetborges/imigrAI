"use client";

import { useRouter } from "next/navigation";

import { AuthGuard } from "@/components/guards/auth-guard";
import { PrivateShell } from "@/components/layout/private-shell";
import { RoadmapChecklist } from "@/components/roadmap/roadmap-checklist";
import { CardSkeleton, ListSkeleton } from "@/components/states/loading-skeletons";
import { PageState } from "@/components/states/page-state";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useRoadmapDetail, useRoadmapStatus } from "@/hooks/use-roadmap";
import { getApiErrorMessage } from "@/lib/api/client";
import { formatDate } from "@/lib/formatters";

interface RoadmapPageProps {
  params: {
    roadmapId: string;
  };
}

export default function RoadmapPage({ params }: Readonly<RoadmapPageProps>): JSX.Element {
  const router = useRouter();
  const roadmapId = params.roadmapId;

  const statusQuery = useRoadmapStatus(roadmapId, true);

  const detailQuery = useRoadmapDetail(
    roadmapId,
    Boolean(statusQuery.data && statusQuery.data.status !== "failed")
  );

  if (statusQuery.isLoading) {
    return (
      <AuthGuard>
        <PrivateShell>
          <CardSkeleton />
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

  if (statusQuery.timedOut) {
    return (
      <AuthGuard>
        <PrivateShell>
          <PageState
            title="Geracao ainda em andamento"
            description="O roadmap ainda nao terminou de processar. Tente novamente em instantes."
            actionLabel="Consultar novamente"
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
            actionLabel="Voltar para dashboard"
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
          <section className="space-y-4">
            <CardSkeleton />
            <ListSkeleton rows={5} />
          </section>
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

          <RoadmapChecklist steps={detailQuery.data.steps} />

          <Button className="mt-1" variant="ghost" onClick={() => router.push("/dashboard")}>
            Voltar para dashboard
          </Button>
        </section>
      </PrivateShell>
    </AuthGuard>
  );
}
