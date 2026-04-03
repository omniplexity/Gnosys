import { Type } from "@sinclair/typebox";
import { jsonResult, type AnyAgentTool } from "openclaw/plugin-sdk/memory-core";

import type { GnosysService } from "../service.js";

const GnosysStatusSchema = Type.Object({
  includeStats: Type.Optional(Type.Boolean())
});

export function createGnosysStatusTool(service: GnosysService): AnyAgentTool {
  return {
    label: "Gnosys Status",
    name: "gnosys_status",
    description: "Diagnose Gnosys backend connectivity, active plugin mode, and optional backend stats.",
    parameters: GnosysStatusSchema,
    execute: async (_toolCallId, params) => {
      const includeStats = typeof params.includeStats === "boolean" ? params.includeStats : true;
      return jsonResult(await service.getStatusReport({ includeStats }));
    }
  };
}
