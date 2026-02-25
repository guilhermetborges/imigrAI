import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { GapsList } from "@/components/assessment/gaps-list";

describe("GapsList", () => {
  it("renderiza gaps recebidos", () => {
    render(<GapsList gaps={["Idioma", "Renda"]} />);

    expect(screen.getByText("- Idioma")).toBeInTheDocument();
    expect(screen.getByText("- Renda")).toBeInTheDocument();
  });

  it("renderiza estado vazio", () => {
    render(<GapsList gaps={[]} />);

    expect(screen.getByText(/Nenhum gap critico detectado/)).toBeInTheDocument();
  });
});
