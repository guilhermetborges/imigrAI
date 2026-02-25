import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RoadmapChecklist } from "@/components/roadmap/roadmap-checklist";
import type { RoadmapStepRead } from "@/types/api";

const steps: RoadmapStepRead[] = [
  {
    id: "2",
    roadmap_id: "roadmap-1",
    step_order: 2,
    title: "Aplicar",
    description: "Enviar aplicacao",
    related_gap_json: {},
    is_required: true,
    eta_weeks: 4,
    dependencies_json: [1],
    risk_level: "alto",
    completion_criteria: "Documento enviado",
    created_at: "2026-02-25T10:00:00Z"
  },
  {
    id: "1",
    roadmap_id: "roadmap-1",
    step_order: 1,
    title: "Prova de idioma",
    description: "Fazer exame",
    related_gap_json: {},
    is_required: true,
    eta_weeks: 6,
    dependencies_json: [],
    risk_level: "medio",
    completion_criteria: "Pontuacao minima",
    created_at: "2026-02-25T10:00:00Z"
  }
];

describe("RoadmapChecklist", () => {
  it("ordena e renderiza passos", () => {
    render(<RoadmapChecklist steps={steps} />);

    const firstStep = screen.getByText("1. Prova de idioma");
    const secondStep = screen.getByText("2. Aplicar");

    expect(firstStep).toBeInTheDocument();
    expect(secondStep).toBeInTheDocument();
    expect(
      screen.getByText((_, element) => element?.textContent === "Dependencias: 1")
    ).toBeInTheDocument();
  });
});
