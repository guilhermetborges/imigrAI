import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ScoreCard } from "@/components/assessment/score-card";

describe("ScoreCard", () => {
  it("renderiza score e faixa", () => {
    render(<ScoreCard score={87.2} faixa="alta" completedAt="2026-02-25T10:00:00Z" />);

    expect(screen.getByText("87.2")).toBeInTheDocument();
    expect(screen.getByText(/Faixa: alta/)).toBeInTheDocument();
  });

  it("limita score acima de 100", () => {
    render(<ScoreCard score={132} faixa="max" completedAt={null} />);

    expect(screen.getByText("100.0")).toBeInTheDocument();
  });
});
