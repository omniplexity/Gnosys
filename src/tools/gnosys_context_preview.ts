import { Type } from "@sinclair/typebox";
import { jsonResult, readNumberParam, readStringParam, type AnyAgentTool } from "openclaw/plugin-sdk/memory-core";

import type { GnosysContextTier } from "../bridge/client.js";
import type { GnosysService } from "../service.js";

const GnosysContextPreviewSchema = Type.Object({
  query: Type.String({ minLength: 1 }),
  maxTokens: Type.Optional(Type.Number({ minimum: 100, maximum: 4000 })),
  includeTiers: Type.Optional(Type.Array(Type.Union([
    Type.Literal("working"),
    Type.Literal("episodic"),
    Type.Literal("semantic"),
    Type.Literal("archive")
  ])))
});

export function createGnosysContextPreviewTool(service: GnosysService): AnyAgentTool {
  return {
    label: "Gnosys Context Preview",
    name: "gnosys_context_preview",
    description: "Preview the backend-ranked retrieval context block that Gnosys would inject for the current prompt.",
    parameters: GnosysContextPreviewSchema,
    execute: async (_toolCallId, params) => {
      const query = readStringParam(params, "query", { required: true });
      const maxTokens = readNumberParam(params, "maxTokens", { integer: true }) ?? service.config.context.maxTokens;
      const includeTiers = Array.isArray(params.includeTiers)
        ? params.includeTiers.filter((entry: unknown): entry is GnosysContextTier => (
          entry === "working" || entry === "episodic" || entry === "semantic" || entry === "archive"
        ))
        : service.config.context.includeTiers;

      const preview = await service.retrieveContext({
        query,
        max_tokens: maxTokens,
        include_tiers: includeTiers
      });

      return jsonResult({
        query: preview.query,
        count: preview.items.length,
        tiersIncluded: preview.tiers_included,
        tokenBudget: preview.token_budget,
        usedTokens: preview.used_tokens,
        remainingTokens: preview.remaining_tokens,
        truncated: preview.truncated,
        droppedCount: preview.dropped_count,
        items: preview.items.map((item) => ({
          rank: item.rank,
          id: item.memory.id,
          tier: item.memory.tier,
          memoryType: item.memory.memory_type,
          score: item.score,
          blendedScore: item.blended_score,
          matchedKeywords: item.matched_keywords,
          estimatedTokens: item.estimated_tokens
        })),
        assemblyText: preview.assembly_text
      });
    }
  };
}
