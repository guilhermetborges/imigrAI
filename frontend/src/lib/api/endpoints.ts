import { apiClient } from "@/lib/api/client";
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
  RegisterRequest,
  RoadmapCreate,
  RoadmapDetailRead,
  RoadmapQueuedRead,
  RoadmapStatusRead,
  TokenPairResponse,
  UserResponse
} from "@/types/api";

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

  async getStatus(assessmentId: string): Promise<AssessmentStatusRead> {
    const { data } = await apiClient.get<AssessmentStatusRead>(
      `/assessments/${assessmentId}/status`
    );
    return data;
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
    const { data } = await apiClient.get<RoadmapStatusRead>(`/roadmaps/${roadmapId}/status`);
    return data;
  },

  async getDetail(roadmapId: string): Promise<RoadmapDetailRead> {
    const { data } = await apiClient.get<RoadmapDetailRead>(`/roadmaps/${roadmapId}`);
    return data;
  }
};

export const billingApi = {
  async getMyEntitlements(): Promise<EntitlementsMeRead> {
    const { data } = await apiClient.get<EntitlementsMeRead>("/entitlements/me");
    return data;
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
