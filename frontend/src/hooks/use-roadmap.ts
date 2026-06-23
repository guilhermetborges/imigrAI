import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { useBackoffPollingQuery } from "@/hooks/use-backoff-polling-query";
import { roadmapsApi } from "@/lib/api/endpoints";
import { addRecentRoadmapId } from "@/lib/recent-items";
import { trackEvent } from "@/lib/tracking";
import { generateIdempotencyKey } from "@/lib/utils";
import type { RoadmapDetailRead, RoadmapQueuedRead, RoadmapStatusRead } from "@/types/api";

const terminalRoadmapStatuses = new Set([
  "completed",
  "failed",
  "draft",
  "published",
  "archived"
]);

interface CreateRoadmapInput {
  assessmentId: string;
  idempotencyKey?: string;
}

export function useCreateRoadmap() {
  return useMutation({
    mutationFn: async ({
      assessmentId,
      idempotencyKey = generateIdempotencyKey()
    }: CreateRoadmapInput): Promise<RoadmapQueuedRead> => {
      const roadmap = await roadmapsApi.create({
        assessment_id: assessmentId,
        idempotency_key: idempotencyKey
      });

      addRecentRoadmapId(roadmap.roadmap_id);
      return roadmap;
    }
  });
}

export function useRoadmapStatus(roadmapId: string, enabled = true) {
  return useBackoffPollingQuery<RoadmapStatusRead>({
    queryKey: ["roadmap-status", roadmapId],
    queryFn: () => roadmapsApi.getStatus(roadmapId),
    enabled,
    timeoutMs: 120_000,
    initialIntervalMs: 2_000,
    maxIntervalMs: 15_000,
    isTerminal: (data) =>
      Boolean(data && terminalRoadmapStatuses.has(data.status))
  });
}

export function useRoadmapDetail(roadmapId: string, enabled = true) {
  const trackedRef = useRef(false);

  const query = useQuery<RoadmapDetailRead>({
    queryKey: ["roadmap-detail", roadmapId],
    queryFn: () => roadmapsApi.getDetail(roadmapId),
    enabled
  });

  useEffect(() => {
    if (!query.data || trackedRef.current) {
      return;
    }

    trackedRef.current = true;
    trackEvent("roadmap_generated", {
      roadmap_id: query.data.roadmap.id,
      steps_count: query.data.steps.length
    });
  }, [query.data]);

  return query;
}
