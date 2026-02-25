import type {
  ApiStatus,
  AssessmentStatusRead,
  RoadmapStatus,
  RoadmapStatusRead
} from "@/types/api";

const assessmentStatusMap: Record<string, ApiStatus> = {
  pending: "pending",
  running: "running",
  completed: "completed",
  failed: "failed",
  canceled: "canceled",
  cancelled: "canceled"
};

const roadmapStatusMap: Record<string, RoadmapStatus> = {
  pending: "pending",
  completed: "completed",
  failed: "failed",
  draft: "draft",
  published: "published",
  archived: "archived"
};

export function normalizeAssessmentStatus(status: string | undefined | null): ApiStatus {
  if (!status) {
    return "pending";
  }

  const normalized = status.toLowerCase();
  return assessmentStatusMap[normalized] ?? "pending";
}

export function normalizeRoadmapStatus(status: string | undefined | null): RoadmapStatus {
  if (!status) {
    return "pending";
  }

  const normalized = status.toLowerCase();
  return roadmapStatusMap[normalized] ?? "pending";
}

export function normalizeAssessmentStatusRead(
  raw: Record<string, unknown>,
  fallbackId: string
): AssessmentStatusRead {
  const assessmentId =
    (typeof raw.assessment_id === "string" ? raw.assessment_id : null) ??
    (typeof raw.id === "string" ? raw.id : null) ??
    fallbackId;

  return {
    assessment_id: assessmentId,
    status: normalizeAssessmentStatus(
      typeof raw.status === "string" ? raw.status : undefined
    ),
    completed_at: typeof raw.completed_at === "string" ? raw.completed_at : null,
    job_id: typeof raw.job_id === "string" ? raw.job_id : null,
    created_at: typeof raw.created_at === "string" ? raw.created_at : null,
    program_id: typeof raw.program_id === "string" ? raw.program_id : null
  };
}

export function normalizeRoadmapStatusRead(
  raw: Record<string, unknown>,
  fallbackId: string
): RoadmapStatusRead {
  const roadmapId =
    (typeof raw.roadmap_id === "string" ? raw.roadmap_id : null) ??
    (typeof raw.id === "string" ? raw.id : null) ??
    fallbackId;

  return {
    roadmap_id: roadmapId,
    status: normalizeRoadmapStatus(
      typeof raw.status === "string" ? raw.status : undefined
    ),
    completed_at: typeof raw.completed_at === "string" ? raw.completed_at : null,
    error: typeof raw.error === "string" ? raw.error : null,
    job_id: typeof raw.job_id === "string" ? raw.job_id : null
  };
}

export function isRoadmapDetailShape(value: unknown): value is { roadmap: unknown; steps: unknown } {
  if (!value || typeof value !== "object") {
    return false;
  }

  return "roadmap" in value && "steps" in value;
}
