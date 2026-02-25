import { useQuery, type QueryKey } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

interface BackoffPollingOptions<TData> {
  enabled?: boolean;
  queryKey: QueryKey;
  queryFn: () => Promise<TData>;
  isTerminal: (data: TData | undefined) => boolean;
  timeoutMs?: number;
  initialIntervalMs?: number;
  maxIntervalMs?: number;
}

interface BackoffPollingResult {
  timedOut: boolean;
  elapsedMs: number;
}

export function useBackoffPollingQuery<TData>({
  enabled = true,
  queryKey,
  queryFn,
  isTerminal,
  timeoutMs = 60_000,
  initialIntervalMs = 2_000,
  maxIntervalMs = 15_000
}: BackoffPollingOptions<TData>) {
  const startedAtRef = useRef<number>(Date.now());
  const queryKeySignature = JSON.stringify(queryKey);

  useEffect(() => {
    startedAtRef.current = Date.now();
  }, [enabled, queryKeySignature]);

  const query = useQuery({
    queryKey,
    queryFn,
    enabled,
    refetchInterval: (queryState) => {
      if (!enabled) {
        return false;
      }

      const data = queryState.state.data as TData | undefined;
      if (isTerminal(data)) {
        return false;
      }

      const elapsed = Date.now() - startedAtRef.current;
      const remaining = timeoutMs - elapsed;
      if (remaining <= 0) {
        return false;
      }

      const attempt = Math.max(queryState.state.dataUpdateCount - 1, 0);
      const nextInterval = Math.min(initialIntervalMs * 2 ** attempt, maxIntervalMs);
      return Math.max(1_000, Math.min(nextInterval, remaining));
    }
  });

  const elapsedMs = Date.now() - startedAtRef.current;
  const timedOut =
    Boolean(enabled) &&
    !query.isFetching &&
    !isTerminal(query.data) &&
    elapsedMs >= timeoutMs;

  return {
    ...query,
    timedOut,
    elapsedMs
  } as typeof query & BackoffPollingResult;
}
