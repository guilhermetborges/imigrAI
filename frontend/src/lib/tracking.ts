export type TrackingEventName =
  | "onboarding_started"
  | "assessment_requested"
  | "assessment_completed"
  | "roadmap_upgrade_clicked"
  | "checkout_started"
  | "roadmap_generated";

declare global {
  interface Window {
    dataLayer?: Array<Record<string, unknown>>;
  }
}

export function trackEvent(
  event: TrackingEventName,
  payload: Record<string, unknown> = {}
): void {
  if (globalThis.window === undefined) {
    return;
  }

  const envelope = {
    event,
    at: new Date().toISOString(),
    ...payload
  };

  if (Array.isArray(globalThis.window.dataLayer)) {
    globalThis.window.dataLayer.push(envelope);
  }

  if (process.env.NODE_ENV !== "production") {
    console.info("[tracking]", envelope);
  }
}
