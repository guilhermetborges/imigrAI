export type ApiStatus = "pending" | "running" | "completed" | "failed" | "canceled";
export type JobStatus = "pending" | "running" | "completed" | "failed" | "dead_letter";
export type RoadmapStatus =
  | "pending"
  | "completed"
  | "failed"
  | "draft"
  | "published"
  | "archived";

export interface ApiErrorResponse {
  detail?: string;
}

export interface TokenPairResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface UserResponse {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface CountryRead {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
  created_at: string;
}

export interface ImmigrationProgramRead {
  id: string;
  country_id: string;
  code: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AssessmentCreate {
  program_id: string;
  profile_json: Record<string, unknown>;
  idempotency_key: string;
}

export interface AssessmentQueuedRead {
  assessment_id: string;
  status: ApiStatus;
  job_id: string;
}

export interface AssessmentStatusRead {
  assessment_id: string;
  status: ApiStatus;
  completed_at: string | null;
  job_id: string | null;
}

export interface ProgramVersionUsedRead {
  id: string;
  version: string;
  effective_from: string;
  effective_to: string | null;
}

export interface AssessmentBreakdownEntryRead {
  rule_group_id: string | null;
  rule_group_code: string;
  rule_condition_id: string | null;
  rule_outcome_id: string | null;
  applied: boolean;
  score_delta: number | string;
  is_blocking: boolean;
  explanation_message: string;
  condition_checks: Record<string, unknown>[];
}

export interface AssessmentBreakdownRead {
  assessment_id: string;
  score_final: number | string;
  faixa: string;
  fatores_positivos: string[];
  gaps_criticos: string[];
  program_version_used: ProgramVersionUsedRead;
  algorithm_version: string;
  rules_version_hash: string;
  items: AssessmentBreakdownEntryRead[];
}

export interface RoadmapCreate {
  assessment_id: string;
  idempotency_key?: string;
}

export interface RoadmapQueuedRead {
  roadmap_id: string;
  status: RoadmapStatus;
  roadmap_schema_version: string;
  job_id: string;
}

export interface RoadmapStatusRead {
  roadmap_id: string;
  status: RoadmapStatus;
  completed_at: string | null;
  error: string | null;
  job_id: string | null;
}

export interface RoadmapRead {
  id: string;
  user_id: string;
  assessment_result_id: string;
  roadmap_schema_version: string;
  status: RoadmapStatus;
  summary: string;
  manual_review_required: boolean;
  llm_provider: string | null;
  llm_model: string | null;
  generation_error: string | null;
  trace_id: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface RoadmapStepRead {
  id: string;
  roadmap_id: string;
  step_order: number;
  title: string;
  description: string;
  related_gap_json: Record<string, unknown>;
  is_required: boolean;
  eta_weeks: number | null;
  dependencies_json: number[];
  risk_level: string;
  completion_criteria: string;
  created_at: string;
}

export interface RoadmapDetailRead {
  roadmap: RoadmapRead;
  steps: RoadmapStepRead[];
}

export type PlanInterval = "month" | "year";
export type SubscriptionStatus = "trialing" | "active" | "past_due" | "canceled" | "expired";
export type EntitlementWindow = "daily" | "monthly" | "lifetime";

export interface PlanRead {
  id: string;
  code: string;
  name: string;
  description: string | null;
  price_cents: number;
  currency: string;
  billing_interval: PlanInterval;
  provider: string;
  stripe_price_id: string | null;
  stripe_product_id: string | null;
  is_free: boolean;
  is_active: boolean;
  created_at: string;
}

export interface SubscriptionRead {
  id: string;
  user_id: string;
  plan_id: string;
  status: SubscriptionStatus;
  started_at: string;
  current_period_start: string;
  current_period_end: string;
  canceled_at: string | null;
  provider: string;
  provider_customer_id: string | null;
  provider_subscription_id: string | null;
  cancel_at_period_end: boolean;
  created_at: string;
}

export interface EntitlementRead {
  id: string;
  user_id: string;
  plan_id: string | null;
  subscription_id: string | null;
  feature_key: string;
  limit_value: number | null;
  usage_window: EntitlementWindow;
  is_enabled: boolean;
  valid_from: string;
  valid_to: string | null;
  created_at: string;
}

export interface UsageCounterRead {
  id: string;
  user_id: string;
  feature_key: string;
  window_start: string;
  window_end: string;
  used_count: number;
  created_at: string;
}

export interface EntitlementsMeRead {
  plan: PlanRead | null;
  subscription: SubscriptionRead | null;
  entitlements: EntitlementRead[];
  usage_counters: UsageCounterRead[];
}

export interface CheckoutSessionCreate {
  plan_code: string;
  success_url: string;
  cancel_url: string;
}

export interface CheckoutSessionRead {
  checkout_session_id: string;
  checkout_url: string;
}

export interface JobRead {
  id: string;
  job_type: "score_job" | "roadmap_job";
  idempotency_key: string;
  status: JobStatus;
  assessment_id: string | null;
  roadmap_id: string | null;
  attempts: number;
  last_error: string | null;
  trace_id: string | null;
  duration_ms: number | null;
  queued_at: string;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}
