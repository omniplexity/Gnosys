import { Type } from "@sinclair/typebox";
import { jsonResult, readStringParam, type AnyAgentTool } from "openclaw/plugin-sdk/memory-core";

import type { GnosysService } from "../service.js";

const GnosysGetMemorySchema = Type.Object({
  memoryId: Type.String({ minLength: 1 })
});

export function createGnosysGetMemoryTool(service: GnosysService): AnyAgentTool {
  return {
    label: "Gnosys Get Memory",
    name: "gnosys_get_memory",
    description: "Fetch a specific memory by its ID from the Gnosys backend.",
    parameters: GnosysGetMemorySchema,
    execute: async (_toolCallId, params) => {
      const memoryId = readStringParam(params, "memoryId", { required: true });
      return jsonResult(await service.getMemory(memoryId));
    }
  };
}
