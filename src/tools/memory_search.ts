import { Type } from "@sinclair/typebox";
import { jsonResult, readNumberParam, readStringParam, type AnyAgentTool } from "openclaw/plugin-sdk/memory-core";
import type { OpenClawPluginToolContext } from "openclaw/plugin-sdk/plugin-entry";

import type { GnosysService } from "../service.js";

const MemorySearchSchema = Type.Object({
  query: Type.String({ minLength: 1 }),
  maxResults: Type.Optional(Type.Number({ minimum: 1, maximum: 100 })),
  memoryType: Type.Optional(Type.String()),
  tier: Type.Optional(Type.String())
});

export function createGnosysMemorySearchTool(ctx: OpenClawPluginToolContext, service: GnosysService): AnyAgentTool {
  return {
    label: "Memory Search",
    name: "memory_search",
    description: "Search Gnosys long-term memory before answering questions about prior work, preferences, facts, or decisions.",
    parameters: MemorySearchSchema,
    execute: async (_toolCallId, params) => {
      const query = readStringParam(params, "query", { required: true });
      const maxResults = readNumberParam(params, "maxResults", { integer: true }) ?? service.config.retention.defaultSearchLimit;
      const memoryType = readStringParam(params, "memoryType");
      const tier = readStringParam(params, "tier");
      const result = await service.search({
        query,
        limit: maxResults,
        memoryType,
        tier
      });

      return jsonResult({
        query,
        count: result.raw.count,
        results: result.raw.results.map((entry) => ({
          id: entry.memory.id,
          memoryType: entry.memory.memory_type,
          tier: entry.memory.tier,
          score: entry.score,
          matchedKeywords: entry.matched_keywords,
          snippet: entry.memory.content,
          metadata: {
            ...entry.memory.metadata,
            sessionKey: ctx.sessionKey
          },
          citation: `gnosys:${entry.memory.id}`
        }))
      });
    }
  };
}
