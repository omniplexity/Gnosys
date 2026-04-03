import { Type } from "@sinclair/typebox";
import { jsonResult, readStringParam, type AnyAgentTool } from "openclaw/plugin-sdk/memory-core";

import type { GnosysService } from "../service.js";

const GnosysStoreMemorySchema = Type.Object({
  content: Type.String({ minLength: 1 }),
  memoryType: Type.Optional(Type.String()),
  tier: Type.Optional(Type.Union([
    Type.Literal("working"),
    Type.Literal("episodic"),
    Type.Literal("semantic"),
    Type.Literal("archive")
  ])),
  tags: Type.Optional(Type.Array(Type.String())),
  metadata: Type.Optional(Type.Object({}, { additionalProperties: true }))
});

export function createGnosysStoreMemoryTool(service: GnosysService): AnyAgentTool {
  return {
    label: "Gnosys Store Memory",
    name: "gnosys_store_memory",
    description: "Persist a durable memory through the Gnosys backend. Use sparingly for facts that should survive restart.",
    parameters: GnosysStoreMemorySchema,
    execute: async (_toolCallId, params) => {
      const content = readStringParam(params, "content", { required: true });
      const memoryType = readStringParam(params, "memoryType");
      const tier = readStringParam(params, "tier") as "working" | "episodic" | "semantic" | "archive" | undefined;
      const tags = Array.isArray(params.tags) ? params.tags.filter((entry: unknown): entry is string => typeof entry === "string") : undefined;
      const metadata = params.metadata && typeof params.metadata === "object" && !Array.isArray(params.metadata)
        ? params.metadata as Record<string, unknown>
        : undefined;

      return jsonResult(await service.storeMemory({
        content,
        memory_type: memoryType,
        tier,
        tags,
        metadata
      }));
    }
  };
}
