import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { useBackoffPollingQuery } from "@/hooks/use-backoff-polling-query";
import { assessmentsApi, profilesApi } from "@/lib/api/endpoints";
import { addRecentAssessmentId, getRecentAssessmentIds } from "@/lib/recent-items";
import { trackEvent } from "@/lib/tracking";
import { generateIdempotencyKey } from "@/lib/utils";
import type {
  AssessmentBreakdownRead,
  AssessmentQueuedRead,
  AssessmentStatusRead
} from "@/types/api";

const terminalAssessmentStatuses = new Set(["completed", "failed", "canceled"]);

interface CreateAssessmentInput {
  programId: string;
  profileJson: Record<string, unknown>;
  idempotencyKey?: string;
}

export function useCreateAssessment() {
  return useMutation({
    mutationFn: async ({
      programId,
      profileJson,
      idempotencyKey = generateIdempotencyKey()
    }: CreateAssessmentInput): Promise<AssessmentQueuedRead> => {
      trackEvent("assessment_requested", { program_id: programId });

      await profilesApi.create({
        profile_json: profileJson
      });

      const assessment = await assessmentsApi.create({
        program_id: programId,
        profile_json: profileJson,
        idempotency_key: idempotencyKey
      });

      addRecentAssessmentId(assessment.assessment_id);
      return assessment;
    }
  });
}

export function useAssessmentStatus(assessmentId: string, enabled = true) {
  const completionTrackedRef = useRef(false);

  const query = useBackoffPollingQuery<AssessmentStatusRead>({
    queryKey: ["assessment-status", assessmentId],
    queryFn: () => assessmentsApi.getById(assessmentId),
    enabled,
    timeoutMs: 90_000,
    initialIntervalMs: 1_500,
    maxIntervalMs: 12_000,
    isTerminal: (data) =>
      Boolean(data && terminalAssessmentStatuses.has(data.status))
  });

  useEffect(() => {
    if (!query.data || completionTrackedRef.current) {
      return;
    }

    if (query.data.status === "completed") {
      completionTrackedRef.current = true;
      trackEvent("assessment_completed", {
        assessment_id: query.data.assessment_id
      });
    }
  }, [query.data]);

  return query;
}

export function useAssessmentBreakdown(assessmentId: string, enabled = true) {
  return useQuery<AssessmentBreakdownRead>({
    queryKey: ["assessment-breakdown", assessmentId],
    queryFn: () => assessmentsApi.getBreakdown(assessmentId),
    enabled
  });
}

function mergeAndSortAssessments(items: AssessmentStatusRead[]): AssessmentStatusRead[] {
  const merged = new Map<string, AssessmentStatusRead>();

  for (const item of items) {
    merged.set(item.assessment_id, item);
  }

  return Array.from(merged.values()).sort((a, b) => {
    const left = a.created_at ? new Date(a.created_at).getTime() : 0;
    const right = b.created_at ? new Date(b.created_at).getTime() : 0;
    return right - left;
  });
}

export function useAssessmentHistory() {
  return useQuery({
    queryKey: ["assessments", "history"],
    queryFn: async () => {
      const apiAssessments = await assessmentsApi.list();
      const recentIds = getRecentAssessmentIds();

      if (!recentIds.length) {
        return mergeAndSortAssessments(apiAssessments);
      }

      const recentAssessments = await Promise.all(
        recentIds.map(async (assessmentId) => {
          try {
            return await assessmentsApi.getById(assessmentId);
          } catch {
            return null;
          }
        })
      );

      return mergeAndSortAssessments([
        ...apiAssessments,
        ...recentAssessments.filter((item): item is AssessmentStatusRead => Boolean(item))
      ]);
    }
  });
}
