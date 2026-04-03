import { SILENT_REPLY_TOKEN, resolveCronStyleNow, type MemoryFlushPlanResolver } from "openclaw/plugin-sdk/memory-core";

function formatDateStamp(nowMs: number, timezone: string): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).formatToParts(new Date(nowMs));

  const year = parts.find((entry) => entry.type === "year")?.value ?? "1970";
  const month = parts.find((entry) => entry.type === "month")?.value ?? "01";
  const day = parts.find((entry) => entry.type === "day")?.value ?? "01";
  return `${year}-${month}-${day}`;
}

export const buildMemoryFlushPlan: MemoryFlushPlanResolver = ({ cfg, nowMs }) => {
  const resolvedNowMs = typeof nowMs === "number" ? nowMs : Date.now();
  const { timeLine, userTimezone } = resolveCronStyleNow(cfg ?? {}, resolvedNowMs);
  const stamp = formatDateStamp(resolvedNowMs, userTimezone);

  return {
    softThresholdTokens: 4_000,
    forceFlushTranscriptBytes: 2 * 1024 * 1024,
    reserveTokensFloor: 20_000,
    prompt: [
      "Pre-compaction Gnosys memory flush.",
      "Use gnosys_store_memory only for durable facts, preferences, decisions, or project state that should survive restart.",
      "Do not write or edit workspace memory files for this flush.",
      `If nothing is worth saving, reply with ${SILENT_REPLY_TOKEN}.`,
      timeLine
    ].join("\n"),
    systemPrompt: [
      "Pre-compaction memory flush turn.",
      "Store only durable, low-volume memories through gnosys_store_memory.",
      `If nothing is worth saving, prefer ${SILENT_REPLY_TOKEN}.`
    ].join("\n"),
    relativePath: `memory/${stamp}.md`
  };
};
