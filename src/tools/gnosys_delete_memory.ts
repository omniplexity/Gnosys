import { Type } from "@sinclair/typebox";
import { jsonResult, readStringParam, type AnyAgentTool } from "openclaw/plugin-sdk/memory-core";

import type { GnosysService } from "../service.js";

const GnosysDeleteMemorySchema = Type.Object({
  memoryId: Type.String({ minLength: 1 })
});

export function createGnosysDeleteMemoryTool(service: GnosysService): AnyAgentTool {
  return {
    label: "Gnosys Delete Memory",
    name: "gnosys_delete_memory",
    description: "Delete a specific memory by its ID from the Gnosys backend.",
    parameters: GnosysDeleteMemorySchema,
    execute: async (_toolCallId, params) => {
      const memoryId = readStringParam(params, "memoryId", { required: true });
      return jsonResult(await service.deleteMemory(memoryId));
    }
  };
}
