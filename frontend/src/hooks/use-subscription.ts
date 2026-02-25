import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { billingApi } from "@/lib/api/endpoints";
import { trackEvent } from "@/lib/tracking";

interface StartCheckoutInput {
  planCode?: string;
  successUrl: string;
  cancelUrl: string;
}

interface UseSubscriptionOptions {
  includePlans?: boolean;
}

export function useSubscription({ includePlans = false }: UseSubscriptionOptions = {}) {
  const plansQuery = useQuery({
    queryKey: ["plans"],
    queryFn: billingApi.listPlans,
    enabled: includePlans
  });

  const entitlementsQuery = useQuery({
    queryKey: ["entitlements", "me"],
    queryFn: billingApi.getMyEntitlements
  });

  const checkoutMutation = useMutation({
    mutationFn: async ({
      planCode = "pro",
      successUrl,
      cancelUrl
    }: StartCheckoutInput) => {
      trackEvent("checkout_started", {
        plan_code: planCode
      });

      return billingApi.createCheckoutSession({
        plan_code: planCode,
        success_url: successUrl,
        cancel_url: cancelUrl
      });
    }
  });

  const hasRoadmapAccess = useMemo(
    () =>
      Boolean(
        entitlementsQuery.data?.entitlements.some(
          (entitlement) => entitlement.feature_key === "roadmap.pro" && entitlement.is_enabled
        )
      ),
    [entitlementsQuery.data]
  );

  const assessmentUsage = useMemo(
    () =>
      entitlementsQuery.data?.usage_counters.find(
        (counter) => counter.feature_key === "assessments.monthly"
      ) ?? null,
    [entitlementsQuery.data]
  );

  return {
    plansQuery,
    entitlementsQuery,
    checkoutMutation,
    hasRoadmapAccess,
    assessmentUsage,
    isPro:
      entitlementsQuery.data?.plan?.code === "pro" ||
      entitlementsQuery.data?.plan?.is_free === false
  };
}
