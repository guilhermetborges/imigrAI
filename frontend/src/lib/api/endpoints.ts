import axios from "axios";

import { apiClient } from "@/lib/api/client";
import {
  isRoadmapDetailShape,
  normalizeAssessmentStatusRead,
  normalizeRoadmapStatusRead
} from "@/lib/api/normalizers";
import type {
  AssessmentBreakdownRead,
  AssessmentCreate,
  AssessmentQueuedRead,
  AssessmentStatusRead,
  CheckoutSessionCreate,
  CheckoutSessionRead,
  EntitlementsMeRead,
  ImmigrationProgramRead,
  JobRead,
  LoginRequest,
  PlanRead,
  ProfileCreateRequest,
  RegisterRequest,
  RoadmapCreate,
  RoadmapDetailRead,
  RoadmapQueuedRead,
  RoadmapStatusRead,
  RoadmapStepRead,
  TokenPairResponse,
  UserResponse
} from "@/types/api";

const fallbackPlans: PlanRead[] = [
  {
    id: "plan-free",
    code: "free",
    name: "Free",
    description: "Plano gratuito com limite mensal de assessments.",
    price_cents: 0,
    currency: "BRL",
    billing_interval: "month",
    provider: "stripe",
    stripe_price_id: null,
    stripe_product_id: null,
    is_free: true,
    is_active: true,
    created_at: new Date(0).toISOString()
  },
  {
    id: "plan-pro",
    code: "pro",
    name: "Pro Monthly",
    description: "Plano com assessments ilimitados e roadmap IA.",
    price_cents: 14900,
    currency: "BRL",
    billing_interval: "month",
    provider: "stripe",
    stripe_price_id: null,
    stripe_product_id: null,
    is_free: false,
    is_active: true,
    created_at: new Date(0).toISOString()
  }
];

function isNotFoundError(error: unknown): boolean {
  return axios.isAxiosError(error) && error.response?.status === 404;
}

function readPlansPayload(payload: unknown): PlanRead[] {
  if (Array.isArray(payload)) {
    return payload as PlanRead[];
  }

  if (payload && typeof payload === "object") {
    if ("plans" in payload && Array.isArray((payload as { plans: unknown }).plans)) {
      return (payload as { plans: PlanRead[] }).plans;
    }

    if ("items" in payload && Array.isArray((payload as { items: unknown }).items)) {
      return (payload as { items: PlanRead[] }).items;
    }
  }

  return [];
}

export const authApi = {
  async register(payload: RegisterRequest): Promise<TokenPairResponse> {
    const { data } = await apiClient.post<TokenPairResponse>("/auth/register", payload);
    return data;
  },

  async login(payload: LoginRequest): Promise<TokenPairResponse> {
    const { data } = await apiClient.post<TokenPairResponse>("/auth/login", payload);
    return data;
  },

  async me(): Promise<UserResponse> {
    const { data } = await apiClient.get<UserResponse>("/auth/me");
    return data;
  }
};

export const profilesApi = {
  async create(payload: ProfileCreateRequest): Promise<Record<string, unknown> | null> {
    try {
      const { data } = await apiClient.post<Record<string, unknown>>("/profiles", payload);
      return data;
    } catch (error) {
      if (isNotFoundError(error)) {
        return null;
      }
      throw error;
    }
  }
};

export const immigrationApi = {
  async listPrograms(): Promise<ImmigrationProgramRead[]> {
    const { data } = await apiClient.get<ImmigrationProgramRead[]>("/immigration-rules/programs");
    return data.filter((program) => program.is_active);
  }
};

export const assessmentsApi = {
  async create(payload: AssessmentCreate): Promise<AssessmentQueuedRead> {
    const { data } = await apiClient.post<AssessmentQueuedRead>("/assessments", payload);
    return data;
  },

  async getById(assessmentId: string): Promise<AssessmentStatusRead> {
    try {
      const { data } = await apiClient.get<Record<string, unknown>>(`/assessments/${assessmentId}`);
      return normalizeAssessmentStatusRead(data, assessmentId);
    } catch (error) {
      if (!isNotFoundError(error)) {
        throw error;
      }

      const { data } = await apiClient.get<Record<string, unknown>>(
        `/assessments/${assessmentId}/status`
      );
      return normalizeAssessmentStatusRead(data, assessmentId);
    }
  },

  async list(): Promise<AssessmentStatusRead[]> {
    try {
      const { data } = await apiClient.get<Array<Record<string, unknown>> | { items: Array<Record<string, unknown>> }>(
        "/assessments"
      );

      const rows = Array.isArray(data) ? data : data.items ?? [];
      return rows.map((row) => {
        const fallbackId =
          (typeof row.assessment_id === "string" && row.assessment_id) ||
          (typeof row.id === "string" && row.id) ||
          "unknown";
        return normalizeAssessmentStatusRead(row, fallbackId);
      });
    } catch (error) {
      if (isNotFoundError(error)) {
        return [];
      }
      throw error;
    }
  },

  async getBreakdown(assessmentId: string): Promise<AssessmentBreakdownRead> {
    const { data } = await apiClient.get<AssessmentBreakdownRead>(
      `/assessments/${assessmentId}/breakdown`
    );
    return data;
  }
};

export const roadmapsApi = {
  async create(payload: RoadmapCreate): Promise<RoadmapQueuedRead> {
    const { data } = await apiClient.post<RoadmapQueuedRead>("/roadmaps", payload);
    return data;
  },

  async getStatus(roadmapId: string): Promise<RoadmapStatusRead> {
    try {
      const { data } = await apiClient.get<Record<string, unknown>>(`/roadmaps/${roadmapId}/status`);
      return normalizeRoadmapStatusRead(data, roadmapId);
    } catch (error) {
      if (!isNotFoundError(error)) {
        throw error;
      }

      const { data } = await apiClient.get<Record<string, unknown>>(`/roadmaps/${roadmapId}`);
      const rawRoadmap =
        data && typeof data === "object" && "roadmap" in data
          ? ((data as { roadmap: Record<string, unknown> }).roadmap ?? {})
          : data;

      return normalizeRoadmapStatusRead(rawRoadmap, roadmapId);
    }
  },

  async getSteps(roadmapId: string): Promise<RoadmapStepRead[]> {
    try {
      const { data } = await apiClient.get<RoadmapStepRead[] | { steps: RoadmapStepRead[] }>(
        `/roadmaps/${roadmapId}/steps`
      );

      if (Array.isArray(data)) {
        return data;
      }

      return Array.isArray(data.steps) ? data.steps : [];
    } catch (error) {
      if (!isNotFoundError(error)) {
        throw error;
      }

      const { data } = await apiClient.get<unknown>(`/roadmaps/${roadmapId}`);
      if (isRoadmapDetailShape(data) && Array.isArray(data.steps)) {
        return data.steps as RoadmapStepRead[];
      }

      return [];
    }
  },

  async getDetail(roadmapId: string): Promise<RoadmapDetailRead> {
    const { data } = await apiClient.get<unknown>(`/roadmaps/${roadmapId}`);

    if (isRoadmapDetailShape(data)) {
      return data as RoadmapDetailRead;
    }

    const steps = await roadmapsApi.getSteps(roadmapId);
    return {
      roadmap: data as RoadmapDetailRead["roadmap"],
      steps
    };
  }
};

export const billingApi = {
  async getMyEntitlements(): Promise<EntitlementsMeRead> {
    const { data } = await apiClient.get<EntitlementsMeRead>("/entitlements/me");
    return data;
  },

  async listPlans(): Promise<PlanRead[]> {
    try {
      const { data } = await apiClient.get<unknown>("/plans");
      const plans = readPlansPayload(data).filter((plan) => plan.is_active);
      return plans.length ? plans : fallbackPlans;
    } catch (error) {
      if (isNotFoundError(error)) {
        return fallbackPlans;
      }

      throw error;
    }
  },

  async createCheckoutSession(payload: CheckoutSessionCreate): Promise<CheckoutSessionRead> {
    const { data } = await apiClient.post<CheckoutSessionRead>(
      "/billing/checkout-session",
      payload
    );
    return data;
  }
};

export const jobsApi = {
  async getStatus(jobId: string): Promise<JobRead> {
    const { data } = await apiClient.get<JobRead>(`/jobs/${jobId}`);
    return data;
  }
};
