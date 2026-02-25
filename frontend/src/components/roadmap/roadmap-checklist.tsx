import { Card } from "@/components/ui/card";
import type { RoadmapStepRead } from "@/types/api";

function getPriorityLabel(risk: string): "alta" | "media" | "baixa" {
  if (risk === "alto") {
    return "alta";
  }
  if (risk === "baixo") {
    return "baixa";
  }
  return "media";
}

interface RoadmapChecklistProps {
  steps: RoadmapStepRead[];
}

export function RoadmapChecklist({ steps }: RoadmapChecklistProps): JSX.Element {
  return (
    <Card>
      <h2 className="font-serif text-2xl">Checklist de execucao</h2>
      <div className="mt-4 space-y-3">
        {steps
          .slice()
          .sort((a, b) => a.step_order - b.step_order)
          .map((step) => (
            <div key={step.id} className="rounded-xl border border-ink/10 bg-white p-4">
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
                  {step.dependencies_json.length ? step.dependencies_json.join(", ") : "Nenhuma"}
                </p>
                <p>
                  <strong className="text-ink">Criterio de conclusao:</strong>{" "}
                  {step.completion_criteria}
                </p>
              </div>
            </div>
          ))}
      </div>
    </Card>
  );
}
