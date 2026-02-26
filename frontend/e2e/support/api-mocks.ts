import type { BrowserContext, Page, Route } from "@playwright/test";

const fakeAccessToken = "e2e-access-token";
const fakeRefreshToken = "e2e-refresh-token";
export const E2E_ASSESSMENT_ID = "73135d0f-2271-4a6c-8da8-b5dca0898a8a";
export const E2E_ROADMAP_ID = "9e844fe2-087f-44a2-8f49-f28cccf64b22";

const authProfile = {
  id: "6cd4d623-dc40-4502-a9ea-019765ec0942",
  email: "e2e-user@example.com",
  role: "member",
  is_active: true,
  created_at: "2026-02-25T00:00:00Z"
};

const completedAssessmentStatus = {
  assessment_id: E2E_ASSESSMENT_ID,
  status: "completed",
  completed_at: "2026-02-25T00:00:01Z",
  job_id: "job-e2e"
};

const assessmentBreakdown = {
  assessment_id: E2E_ASSESSMENT_ID,
  score_final: 78.4,
  faixa: "alto",
  fatores_positivos: ["Idiomas acima do baseline"],
  gaps_criticos: ["Pontuar experiencia internacional"],
  program_version_used: {
    id: "1ba5e53f-a4be-4f21-b58a-f748e31e1468",
    version: "2026.01",
    effective_from: "2026-01-01T00:00:00Z",
    effective_to: null
  },
  algorithm_version: "score-engine-v1",
  rules_version_hash: "2f4aee7e6c056f95d2f56f94f58e007f45f0d5966f3c2ecb5cf975f44dbf1f04",
  items: [
    {
      rule_group_id: "6ccab8a0-08e2-4d89-9edb-b94da57110b3",
      rule_group_code: "AGE",
      rule_condition_id: null,
      rule_outcome_id: null,
      applied: true,
      score_delta: 20,
      is_blocking: false,
      explanation_message: "Faixa etaria favoravel",
      condition_checks: []
    }
  ]
};

const freeEntitlementsPayload = {
  plan: {
    id: "plan-free",
    code: "free",
    name: "Free",
    description: "Plano gratuito",
    price_cents: 0,
    currency: "BRL",
    billing_interval: "month",
    provider: "stripe",
    stripe_price_id: null,
    stripe_product_id: null,
    is_free: true,
    is_active: true,
    created_at: "2026-02-25T00:00:00Z"
  },
  subscription: null,
  entitlements: [
    {
      id: "ent-free-assessment",
      user_id: authProfile.id,
      plan_id: "plan-free",
      subscription_id: null,
      feature_key: "assessments.monthly",
      limit_value: 3,
      usage_window: "monthly",
      is_enabled: true,
      valid_from: "2026-02-01T00:00:00Z",
      valid_to: null,
      created_at: "2026-02-01T00:00:00Z"
    }
  ],
  usage_counters: []
};

const proEntitlementsPayload = {
  ...freeEntitlementsPayload,
  plan: {
    id: "plan-pro",
    code: "pro",
    name: "Pro Monthly",
    description: "Plano pago",
    price_cents: 14900,
    currency: "BRL",
    billing_interval: "month",
    provider: "stripe",
    stripe_price_id: "price_e2e",
    stripe_product_id: null,
    is_free: false,
    is_active: true,
    created_at: "2026-02-25T00:00:00Z"
  },
  subscription: {
    id: "sub-e2e",
    user_id: authProfile.id,
    plan_id: "plan-pro",
    status: "active",
    started_at: "2026-02-25T00:00:00Z",
    current_period_start: "2026-02-25T00:00:00Z",
    current_period_end: "2026-03-25T00:00:00Z",
    canceled_at: null,
    provider: "stripe",
    provider_customer_id: "cus-e2e",
    provider_subscription_id: "sub-e2e",
    cancel_at_period_end: false,
    created_at: "2026-02-25T00:00:00Z"
  },
  entitlements: [
    ...freeEntitlementsPayload.entitlements,
    {
      id: "ent-pro-roadmap",
      user_id: authProfile.id,
      plan_id: "plan-pro",
      subscription_id: "sub-e2e",
      feature_key: "roadmap.pro",
      limit_value: null,
      usage_window: "lifetime",
      is_enabled: true,
      valid_from: "2026-02-25T00:00:00Z",
      valid_to: null,
      created_at: "2026-02-25T00:00:00Z"
    }
  ]
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body)
  });
}

export async function bootstrapAuthenticatedSession(
  context: BrowserContext,
  page: Page
): Promise<void> {
  await context.addCookies([
    {
      name: "imigrai_access_token",
      value: fakeAccessToken,
      domain: "127.0.0.1",
      path: "/",
      httpOnly: false,
      secure: false,
      sameSite: "Lax"
    }
  ]);

  await context.addInitScript(
    ({ access, refresh }) => {
      window.localStorage.setItem("imigrai_access_token", access);
      window.localStorage.setItem("imigrai_refresh_token", refresh);
    },
    { access: fakeAccessToken, refresh: fakeRefreshToken }
  );

  await page.route("**/api/v1/auth/me", (route) => json(route, authProfile));
  await page.route("**/api/v1/profiles", (route) =>
    route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Not Found" })
    })
  );
}

export async function mockAssessmentFlow(page: Page): Promise<void> {
  await page.route("**/api/v1/immigration-rules/programs", (route) =>
    json(route, [
      {
        id: "5a34dc3d-0f33-4ec8-ac72-34618dd3e27d",
        country_id: "8fda844d-4f46-4f88-b7ca-4f127fdce2d6",
        code: "CA-EXPRESS",
        name: "Express Entry",
        description: "Programa teste",
        is_active: true,
        created_at: "2026-02-25T00:00:00Z"
      }
    ])
  );

  await page.route("**/api/v1/assessments", async (route, request) => {
    if (request.method() !== "POST") {
      return route.fallback();
    }
    return json(route, {
      assessment_id: E2E_ASSESSMENT_ID,
      status: "pending",
      job_id: "job-e2e"
    }, 202);
  });

  await page.route(`**/api/v1/assessments/${E2E_ASSESSMENT_ID}/status`, (route) =>
    json(route, completedAssessmentStatus)
  );

  await page.route(`**/api/v1/assessments/${E2E_ASSESSMENT_ID}`, (route) =>
    json(route, completedAssessmentStatus)
  );

  await page.route(`**/api/v1/assessments/${E2E_ASSESSMENT_ID}/breakdown`, (route) =>
    json(route, assessmentBreakdown)
  );
}

export async function mockEntitlements(page: Page, isProProvider: () => boolean): Promise<void> {
  await page.route("**/api/v1/entitlements/me", (route) =>
    json(route, isProProvider() ? proEntitlementsPayload : freeEntitlementsPayload)
  );
}

export async function mockUpgradeAndRoadmap(page: Page, setPro: () => void): Promise<void> {
  await page.route("**/api/v1/plans", (route) =>
    json(route, [
      freeEntitlementsPayload.plan,
      proEntitlementsPayload.plan
    ])
  );

  await page.route("**/api/v1/billing/checkout-session", async (route, request) => {
    if (request.method() !== "POST") {
      return route.fallback();
    }
    setPro();
    return json(route, {
      checkout_session_id: "cs-e2e",
      checkout_url: `http://127.0.0.1:3000/results/${E2E_ASSESSMENT_ID}?success=1`
    }, 201);
  });

  await page.route("**/api/v1/roadmaps", async (route, request) => {
    if (request.method() !== "POST") {
      return route.fallback();
    }
    return json(route, {
      roadmap_id: E2E_ROADMAP_ID,
      status: "pending",
      roadmap_schema_version: "roadmap.v1",
      job_id: "job-roadmap-e2e"
    }, 202);
  });

  await page.route(`**/api/v1/roadmaps/${E2E_ROADMAP_ID}/status`, (route) =>
    json(route, {
      roadmap_id: E2E_ROADMAP_ID,
      status: "completed",
      completed_at: "2026-02-25T00:00:02Z",
      error: null,
      job_id: "job-roadmap-e2e"
    })
  );

  await page.route(`**/api/v1/roadmaps/${E2E_ROADMAP_ID}`, (route) =>
    json(route, {
      roadmap: {
        id: E2E_ROADMAP_ID,
        user_id: authProfile.id,
        assessment_result_id: "assessment-result-e2e",
        roadmap_schema_version: "roadmap.v1",
        status: "completed",
        summary: "Plano de 90 dias para elevar score",
        manual_review_required: false,
        llm_provider: "openai",
        llm_model: "gpt-4o-mini",
        generation_error: null,
        trace_id: "trace-e2e",
        completed_at: "2026-02-25T00:00:02Z",
        created_at: "2026-02-25T00:00:00Z"
      },
      steps: [
        {
          id: "step-1",
          roadmap_id: E2E_ROADMAP_ID,
          step_order: 1,
          title: "Fechar gap de idioma",
          description: "Aumentar proficiencia em ingles para C1.",
          related_gap_json: { gap: "Pontuar experiencia internacional" },
          is_required: true,
          eta_weeks: 8,
          dependencies_json: [],
          risk_level: "medio",
          completion_criteria: "Teste oficial com nota alvo.",
          created_at: "2026-02-25T00:00:02Z"
        }
      ]
    })
  );
}
