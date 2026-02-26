import { expect, test } from "@playwright/test";

import {
  E2E_ASSESSMENT_ID,
  E2E_ROADMAP_ID,
  bootstrapAuthenticatedSession,
  mockAssessmentFlow,
  mockEntitlements,
  mockUpgradeAndRoadmap
} from "./support/api-mocks";

test("upgrade -> roadmap", async ({ context, page }) => {
  let isPro = false;

  await bootstrapAuthenticatedSession(context, page);
  await mockAssessmentFlow(page);
  await mockEntitlements(page, () => isPro);
  await mockUpgradeAndRoadmap(page, () => {
    isPro = true;
  });

  await page.goto(`/results/${E2E_ASSESSMENT_ID}`);
  await expect(page.getByRole("heading", { name: /Breakdown por criterio/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Fazer upgrade para gerar roadmap/i })).toBeVisible();

  await page.getByRole("button", { name: /Fazer upgrade para gerar roadmap/i }).click();
  await expect(page.getByRole("heading", { name: /Upgrade necessario/i })).toBeVisible();
  await page.getByRole("button", { name: /^Fazer upgrade$/ }).click();

  await expect(page).toHaveURL(/\/pricing/);
  await page.getByRole("button", { name: /Assinar Pro/i }).click();

  await expect(page).toHaveURL(new RegExp(`/results/${E2E_ASSESSMENT_ID}`));
  await expect(page.getByRole("button", { name: /Gerar roadmap Pro/i })).toBeVisible();
  await page.getByRole("button", { name: /Gerar roadmap Pro/i }).click();

  await expect(page).toHaveURL(new RegExp(`/roadmaps/${E2E_ROADMAP_ID}`));
  await expect(page.getByRole("heading", { name: /Plano de 90 dias para elevar score/i })).toBeVisible();
  await expect(page.getByText(/Fechar gap de idioma/i)).toBeVisible();
});
