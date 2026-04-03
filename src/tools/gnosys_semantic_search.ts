import { Type } from "@sinclair/typebox";
import { jsonResult, readNumberParam, readStringParam, type AnyAgentTool } from "openclaw/plugin-sdk/memory-core";
import type { OpenClawPluginToolContext } from "openclaw/plugin-sdk/plugin-entry";

import type { GnosysService } from "../service.js";

const SemanticSearchSchema = Type.Object({
  query: Type.String({ minLength: 1 }),
  maxResults: Type.Optional(Type.Number({ minimum: 1, maximum: 100 })),
  memoryType: Type.Optional(Type.String()),
  tier: Type.Optional(Type.String()),
  semanticWeight: Type.Optional(Type.Number({ minimum: 0, maximum: 1 }))
});

export function createGnosysSemanticSearchTool(ctx: OpenClawPluginToolContext, service: GnosysService): AnyAgentTool {
  return {
    label: "Semantic Memory Search",
    name: "gnosys_semantic_search",
    description: "Search Gnosys memory using semantic similarity with embeddings. Provides better results for conceptual queries but requires embeddings provider to be configured.",
    parameters: SemanticSearchSchema,
    execute: async (_toolCallId, params) => {
      const query = readStringParam(params, "query", { required: true });
      const maxResults = readNumberParam(params, "maxResults", { integer: true }) ?? service.config.retention.defaultSearchLimit;
      const memoryType = readStringParam(params, "memoryType");
      const tier = readStringParam(params, "tier");
      const semanticWeight = readNumberParam(params, "semanticWeight") ?? 0.7;

      const result = await service.semanticSearch({
        query,
        limit: maxResults,
        memoryType,
        tier,
        semanticWeight
      });

      return jsonResult({
        query,
        count: result.raw.count,
        usedSemanticSearch: result.usedSemanticSearch,
        truncated: result.truncated,
        results: await Promise.all(result.results.map(async (entry) => ({
          id: entry.id,
          memoryType: entry.memoryType,
          tier: entry.tier,
          score: entry.score,
          semanticScore: entry.semanticScore,
          keywordScore: entry.keywordScore,
          matchedKeywords: entry.matchedKeywords,
          snippet: entry.content,
          metadata: {
            ...(await service.getMemory(entry.id)).memory.metadata,
            sessionKey: ctx.sessionKey
          },
          citation: `gnosys:${entry.id}`
        })))
      });
    }
  };
}