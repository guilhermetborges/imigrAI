const RECENT_ASSESSMENTS_KEY = "imigrai_recent_assessments";
const RECENT_ROADMAPS_KEY = "imigrai_recent_roadmaps";

function readList(key: string): string[] {
  if (typeof globalThis.window === "undefined") {
    return [];
  }

  const raw = globalThis.window.localStorage.getItem(key);
  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter((item): item is string => typeof item === "string");
  } catch {
    return [];
  }
}

function writeList(key: string, values: string[]): void {
  if (typeof globalThis.window === "undefined") {
    return;
  }

  globalThis.window.localStorage.setItem(key, JSON.stringify(values.slice(0, 25)));
}

function addUniqueItem(key: string, item: string): void {
  const existing = readList(key);
  const next = [item, ...existing.filter((value) => value !== item)];
  writeList(key, next);
}

export function addRecentAssessmentId(id: string): void {
  addUniqueItem(RECENT_ASSESSMENTS_KEY, id);
}

export function getRecentAssessmentIds(): string[] {
  return readList(RECENT_ASSESSMENTS_KEY);
}

export function addRecentRoadmapId(id: string): void {
  addUniqueItem(RECENT_ROADMAPS_KEY, id);
}

export function getRecentRoadmapIds(): string[] {
  return readList(RECENT_ROADMAPS_KEY);
}
