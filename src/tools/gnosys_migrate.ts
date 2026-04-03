import { Type } from "@sinclair/typebox";
import { jsonResult, type AnyAgentTool } from "openclaw/plugin-sdk/memory-core";

import type { GnosysService } from "../service.js";

// Migration action schemas
const GnosysMigrateExportSchema = Type.Object({
  action: Type.Literal("export"),
  format: Type.Optional(Type.Union([Type.Literal("json"), Type.Literal("markdown")])),
  outputPath: Type.Optional(Type.String())
});

const GnosysMigrateImportSchema = Type.Object({
  action: Type.Literal("import"),
  inputPath: Type.String(),
  format: Type.Optional(Type.Union([Type.Literal("json"), Type.Literal("jsonl"), Type.Literal("markdown"), Type.Literal("mem0"), Type.Literal("zep"), Type.Literal("chroma")])),
});

export function createGnosysMigrateTool(service: GnosysService): AnyAgentTool {
  return {
    label: "Gnosys Migration",
    name: "gnosys_migrate",
    description: "Import and export data - migrate memories from/to external formats like Mem0, Zep, Chroma, or OpenClaw.",
    parameters: Type.Union([
      GnosysMigrateExportSchema,
      GnosysMigrateImportSchema
    ]),
    execute: async (_toolCallId, params) => {
      const action = (params as { action: string }).action;

      switch (action) {
        case "export": {
          const p = params as {
            format?: "json" | "markdown";
            outputPath?: string;
          };
          const format = p.format || "json";
          const output = p.outputPath || `./data/gnosys_export_${Date.now()}`;
          const result = await service.request(`/migrate/export?format=${format}&output=${output}`) as {
            exported_to: string;
            count: number;
          };
          return jsonResult({
            exported: true,
            exported_to: result.exported_to,
            memories_exported: result.count,
            format: format
          });
        }
        case "import": {
          const p = params as {
            inputPath: string;
            format?: "json" | "jsonl" | "markdown" | "mem0" | "zep" | "chroma";
          };
          const format = p.format || "json";
          const result = await service.request(`/migrate/import?input_path=${encodeURIComponent(p.inputPath)}&format=${format}`, {
            method: "POST"
          }) as {
            imported: number;
            total: number;
          };
          return jsonResult({
            imported: true,
            memories_imported: result.imported,
            total_found: result.total,
            format: format
          });
        }
        default:
          return jsonResult({ error: `Unknown action: ${action}` });
      }
    }
  };
}