"use client";

import {
  QueryClient,
  QueryClientProvider,
  QueryCache,
  MutationCache
} from "@tanstack/react-query";
import { useState } from "react";

import { getApiErrorMessage } from "@/lib/api/client";
import { AuthProvider } from "@/providers/auth-provider";

function reportQueryError(scope: string, error: unknown): void {
  if (process.env.NODE_ENV !== "production") {
    console.error(`${scope}:`, getApiErrorMessage(error));
  }
}

export function AppProviders({ children }: Readonly<{ children: React.ReactNode }>): JSX.Element {
  const [queryClient] = useState(
    () =>
        new QueryClient({
          queryCache: new QueryCache({
            onError: (error) => {
              reportQueryError("React Query error", error);
            }
          }),
          mutationCache: new MutationCache({
            onError: (error) => {
              reportQueryError("React Query mutation error", error);
            }
          }),
        defaultOptions: {
          queries: {
            staleTime: 20_000,
            retry: 1,
            refetchOnWindowFocus: false
          }
        }
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
}
