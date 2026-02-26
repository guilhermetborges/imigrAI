import { expect, test } from "@playwright/test";

import {
  E2E_ASSESSMENT_ID,
  bootstrapAuthenticatedSession,
  mockAssessmentFlow,
  mockEntitlements
} from "./support/api-mocks";

test("onboarding -> score", async ({ context, page }) => {
  await bootstrapAuthenticatedSession(context, page);
  await mockAssessmentFlow(page);
  await mockEntitlements(page, () => false);

  await page.goto("/onboarding");
  await expect(page.getByRole("heading", { name: /Idade e escolaridade/i })).toBeVisible();

  await page.getByRole("spinbutton", { name: /^Idade$/ }).fill("29");
  await page.getByLabel("Escolaridade").selectOption("graduacao");
  await page.getByRole("button", { name: "Proximo" }).click();
  await expect(page.getByRole("heading", { name: /Profissao e experiencia/i })).toBeVisible();

  await page.getByLabel("Profissao").fill("Software Engineer");
  await page.getByRole("button", { name: "Proximo" }).click();
  await expect(page.getByRole("heading", { name: /Idiomas e nivel/i })).toBeVisible();

  await page.getByLabel("Nivel predominante").selectOption("B2");
  await page.getByRole("button", { name: "Proximo" }).click();
  await expect(page.getByRole("heading", { name: /Renda e paises de interesse/i })).toBeVisible();

  await page.getByLabel("Renda atual (BRL/mensal)").fill("12000");
  await page.locator("form").evaluate((form: HTMLFormElement) => form.requestSubmit());

  await expect(page).toHaveURL(new RegExp(`/results/${E2E_ASSESSMENT_ID}`));
  await expect(page.getByRole("heading", { name: /Breakdown por criterio/i })).toBeVisible();
  await expect(page.getByText(/^AGE$/)).toBeVisible();
  await expect(page.getByRole("button", { name: /Fazer upgrade para gerar roadmap/i })).toBeVisible();
});
