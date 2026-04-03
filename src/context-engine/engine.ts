import type { AgentMessage } from "@mariozechner/pi-agent-core";
import type { ContextEngine } from "openclaw/plugin-sdk";
import { delegateCompactionToRuntime } from "openclaw/plugin-sdk/core";

import type { NormalizedGnosysPluginConfig } from "../config.js";
import type { GnosysService } from "../service.js";
import { buildConversationMemoryPayload, buildRetrievalQuery, estimateMessagesTokens } from "./message-utils.js";

const CONTEXT_ENGINE_ID = "gnosys";
const MIN_RETRIEVAL_TOKENS = 100;

function resolveRetrievalTokenBudget(config: NormalizedGnosysPluginConfig, tokenBudget?: number): number {
  if (typeof tokenBudget === "number" && Number.isFinite(tokenBudget) && tokenBudget > 0) {
    const fractionBudget = Math.floor(tokenBudget * config.context.budgetFraction);
    return Math.max(MIN_RETRIEVAL_TOKENS, Math.min(config.context.maxTokens, fractionBudget));
  }
  return config.context.maxTokens;
}

function buildSystemPromptAddition(params: {
  assemblyText: string;
  truncated: boolean;
  droppedCount: number;
}): string | undefined {
  const assemblyText = params.assemblyText.trim();
  if (!assemblyText) {
    return undefined;
  }

  const header = params.truncated || params.droppedCount > 0
    ? "Use the retrieved Gnosys context below when it materially helps. Lower-ranked context was omitted to stay within budget."
    : "Use the retrieved Gnosys context below only when it materially helps answer the current prompt.";

  return `${header}\n\n${assemblyText}`;
}

async function ingestMessages(params: {
  service: GnosysService;
  sessionId: string;
  sessionKey?: string;
  messages: AgentMessage[];
  isHeartbeat?: boolean;
}): Promise<number> {
  let ingestedCount = 0;

  for (const message of params.messages) {
    const payload = buildConversationMemoryPayload({
      sessionId: params.sessionId,
      sessionKey: params.sessionKey,
      isHeartbeat: params.isHeartbeat,
      message
    });

    if (!payload) {
      continue;
    }

    await params.service.storeMemory(payload);
    ingestedCount += 1;
  }

  return ingestedCount;
}

export function createGnosysContextEngine(service: GnosysService, config: NormalizedGnosysPluginConfig): ContextEngine {
  return {
    info: {
      id: CONTEXT_ENGINE_ID,
      name: "Gnosys Context Engine",
      version: "0.5.0",
      ownsCompaction: false
    },
    async ingest(params) {
      const ingestedCount = await ingestMessages({
        service,
        sessionId: params.sessionId,
        sessionKey: params.sessionKey,
        messages: [params.message],
        isHeartbeat: params.isHeartbeat
      });
      return { ingested: ingestedCount > 0 };
    },
    async ingestBatch(params) {
      const ingestedCount = await ingestMessages({
        service,
        sessionId: params.sessionId,
        sessionKey: params.sessionKey,
        messages: params.messages,
        isHeartbeat: params.isHeartbeat
      });
      return { ingestedCount };
    },
    async assemble(params) {
      const baseEstimatedTokens = estimateMessagesTokens(params.messages);
      if (!config.context.enabled) {
        return {
          messages: params.messages,
          estimatedTokens: baseEstimatedTokens
        };
      }

      const query = buildRetrievalQuery({
        prompt: params.prompt,
        messages: params.messages,
        maxChars: config.context.maxQueryChars
      });

      if (!query) {
        return {
          messages: params.messages,
          estimatedTokens: baseEstimatedTokens
        };
      }

      const retrieval = await service.retrieveContext({
        query,
        max_tokens: resolveRetrievalTokenBudget(config, params.tokenBudget),
        include_tiers: config.context.includeTiers
      });

      if (retrieval.items.length === 0) {
        return {
          messages: params.messages,
          estimatedTokens: baseEstimatedTokens
        };
      }

      const systemPromptAddition = buildSystemPromptAddition({
        assemblyText: retrieval.assembly_text,
        truncated: retrieval.truncated,
        droppedCount: retrieval.dropped_count
      });

      return {
        messages: params.messages,
        estimatedTokens: baseEstimatedTokens + retrieval.used_tokens,
        ...(systemPromptAddition ? { systemPromptAddition } : {})
      };
    },
    async compact(params) {
      return delegateCompactionToRuntime(params);
    },
    async dispose() {
      await service.stop();
    }
  };
}

export { CONTEXT_ENGINE_ID };
