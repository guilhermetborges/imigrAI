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

export function AppProviders({ children }: { children: React.ReactNode }): JSX.Element {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        queryCache: new QueryCache({
          onError: (error) => {
            console.error("React Query error:", getApiErrorMessage(error));
          }
        }),
        mutationCache: new MutationCache({
          onError: (error) => {
            console.error("React Query mutation error:", getApiErrorMessage(error));
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
