import type { MemoryPromptSectionBuilder } from "openclaw/plugin-sdk/memory-core";

export const buildMemoryPromptSection: MemoryPromptSectionBuilder = ({ availableTools, citationsMode }) => {
  if (!availableTools.has("memory_search")) {
    return [];
  }

  const lines = [
    "## Memory Recall",
    "Before answering questions about prior work, preferences, people, dates, or decisions, run memory_search against Gnosys memory.",
    "Treat gnosys_store_memory as a sparse durability tool: store only facts that should survive restart or be recalled later."
  ];

  if (citationsMode !== "off") {
    lines.push("When useful, mention the returned Gnosys memory id in the reply for traceability.");
  }

  lines.push("");
  return lines;
};
