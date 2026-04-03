import type { AgentMessage } from "@mariozechner/pi-agent-core";

import type { GnosysStoreMemoryRequest } from "../bridge/client.js";

const TOKEN_CHAR_RATIO = 4;
const DEFAULT_STORAGE_TEXT_LIMIT = 2_000;

type MessageRecord = AgentMessage & Record<string, unknown>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function clampText(input: string, maxChars: number): string {
  if (input.length <= maxChars) {
    return input;
  }
  return `${input.slice(0, Math.max(0, maxChars - 1)).trimEnd()}...`;
}

function normalizeWhitespace(input: string): string {
  return input.replace(/\s+/g, " ").trim();
}

function extractTextParts(value: unknown, parts: string[]): void {
  if (typeof value === "string") {
    const normalized = normalizeWhitespace(value);
    if (normalized) {
      parts.push(normalized);
    }
    return;
  }

  if (Array.isArray(value)) {
    for (const entry of value) {
      extractTextParts(entry, parts);
    }
    return;
  }

  if (!isRecord(value)) {
    return;
  }

  if (value.type === "text" && typeof value.text === "string") {
    extractTextParts(value.text, parts);
    return;
  }

  if (typeof value.content === "string" || Array.isArray(value.content)) {
    extractTextParts(value.content, parts);
  }

  if (typeof value.text === "string") {
    extractTextParts(value.text, parts);
  }
}

export function stringifyMessageForStorage(message: AgentMessage, maxChars = DEFAULT_STORAGE_TEXT_LIMIT): string {
  const record = message as MessageRecord;
  const parts: string[] = [];
  const role = typeof record.role === "string" ? record.role : "";

  switch (role) {
    case "user": {
      extractTextParts(record.content, parts);
      break;
    }
    case "assistant": {
      extractTextParts(record.content, parts);
      break;
    }
    case "toolResult": {
      if (typeof record.toolName === "string" && record.toolName.trim()) {
        parts.push(`tool=${record.toolName.trim()}`);
      }
      extractTextParts(record.content, parts);
      break;
    }
    case "bashExecution": {
      if (record.excludeFromContext === true) {
        return "";
      }
      if (typeof record.command === "string" && record.command.trim()) {
        parts.push(`command=${normalizeWhitespace(record.command)}`);
      }
      if (typeof record.output === "string" && record.output.trim()) {
        parts.push(`output=${normalizeWhitespace(record.output)}`);
      }
      break;
    }
    case "branchSummary": {
      if (typeof record.summary === "string") {
        parts.push(normalizeWhitespace(record.summary));
      }
      break;
    }
    case "compactionSummary": {
      if (typeof record.summary === "string") {
        parts.push(normalizeWhitespace(record.summary));
      }
      break;
    }
    case "custom": {
      extractTextParts(record.content, parts);
      break;
    }
    default: {
      extractTextParts(record.content, parts);
      if (typeof record.summary === "string") {
        parts.push(normalizeWhitespace(record.summary));
      }
    }
  }

  return clampText(parts.join("\n"), maxChars);
}

export function buildConversationMemoryPayload(params: {
  sessionId: string;
  sessionKey?: string;
  isHeartbeat?: boolean;
  message: AgentMessage;
}): GnosysStoreMemoryRequest | undefined {
  const body = stringifyMessageForStorage(params.message);
  if (!body) {
    return undefined;
  }

  const record = params.message as MessageRecord;
  const createdAt = toIsoTimestamp(record.timestamp);
  const tags = ["conversation", "context-engine", typeof record.role === "string" ? record.role : "unknown"];
  if (params.isHeartbeat) {
    tags.push("heartbeat");
  }

  return {
    content: `[${String(record.role ?? "message")}] ${body}`,
    memory_type: "conversational",
    tier: "episodic",
    tags,
    metadata: {
      source: "openclaw-context-engine",
      sessionId: params.sessionId,
      ...(params.sessionKey ? { sessionKey: params.sessionKey } : {}),
      role: record.role ?? "unknown",
      ...(typeof record.toolName === "string" ? { toolName: record.toolName } : {}),
      ...(typeof record.model === "string" ? { model: record.model } : {}),
      isHeartbeat: params.isHeartbeat === true
    },
    ...(createdAt ? { created_at: createdAt } : {})
  };
}

export function estimateTextTokens(text: string): number {
  const normalized = normalizeWhitespace(text);
  if (!normalized) {
    return 0;
  }
  return Math.max(1, Math.ceil(normalized.length / TOKEN_CHAR_RATIO));
}

export function estimateMessagesTokens(messages: AgentMessage[]): number {
  return messages.reduce((total, message) => {
    const text = stringifyMessageForStorage(message, 8_000);
    const role = (message as MessageRecord).role;
    return total + estimateTextTokens(text) + (typeof role === "string" ? estimateTextTokens(role) : 0) + 8;
  }, 0);
}

export function buildRetrievalQuery(params: {
  prompt?: string;
  messages: AgentMessage[];
  maxChars: number;
}): string | undefined {
  const directPrompt = normalizeWhitespace(params.prompt ?? "");
  if (directPrompt) {
    return clampText(directPrompt, params.maxChars);
  }

  for (let index = params.messages.length - 1; index >= 0; index -= 1) {
    const message = params.messages[index] as MessageRecord;
    if (message.role !== "user") {
      continue;
    }
    const text = normalizeWhitespace(stringifyMessageForStorage(params.messages[index], params.maxChars));
    if (text) {
      return clampText(text, params.maxChars);
    }
  }

  return undefined;
}

function toIsoTimestamp(value: unknown): string | undefined {
  if (typeof value === "number" && Number.isFinite(value)) {
    return new Date(value).toISOString();
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Date.parse(value);
    if (!Number.isNaN(parsed)) {
      return new Date(parsed).toISOString();
    }
  }
  return undefined;
}
