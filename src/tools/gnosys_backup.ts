import { Type } from "@sinclair/typebox";
import { jsonResult, type AnyAgentTool } from "openclaw/plugin-sdk/memory-core";

import type { GnosysService } from "../service.js";

// Backup action schemas
const GnosysBackupCreateSchema = Type.Object({
  action: Type.Literal("create"),
  backupType: Type.Optional(Type.Union([Type.Literal("full"), Type.Literal("selective")])),
  components: Type.Optional(Type.Array(Type.String()))
});

const GnosysBackupListSchema = Type.Object({
  action: Type.Literal("list")
});

const GnosysBackupVerifySchema = Type.Object({
  action: Type.Literal("verify"),
  backupId: Type.String()
});

const GnosysBackupRestoreSchema = Type.Object({
  action: Type.Literal("restore"),
  backupPath: Type.String(),
  targetDir: Type.String(),
  components: Type.Optional(Type.Array(Type.String())),
  overwrite: Type.Optional(Type.Boolean())
});

export function createGnosysBackupTool(service: GnosysService): AnyAgentTool {
  return {
    label: "Gnosys Backup",
    name: "gnosys_backup",
    description: "Manage backups - create, list, verify, and restore from backups.",
    parameters: Type.Union([
      GnosysBackupCreateSchema,
      GnosysBackupListSchema,
      GnosysBackupVerifySchema,
      GnosysBackupRestoreSchema
    ]),
    execute: async (_toolCallId, params) => {
      const action = (params as { action: string }).action;

      switch (action) {
        case "create": {
          const p = params as {
            backupType?: "full" | "selective";
            components?: string[];
          };
          const result = await service.request("/backup", {
            method: "POST",
            body: {
              backup_type: p.backupType || "full",
              components: p.components
            }
          }) as {
            id: string;
            backup_type: string;
            file_path: string;
            checksum: string;
            size_bytes: number;
            created_at: string;
          };
          return jsonResult({
            created: true,
            backup_id: result.id,
            backup_type: result.backup_type,
            file_path: result.file_path,
            checksum: result.checksum,
            size_bytes: result.size_bytes,
            created_at: result.created_at
          });
        }
        case "list": {
          const result = await service.request("/backup") as {
            backups: Array<{
              id: string;
              backup_type: string;
              file_path: string;
              size_bytes: number;
              created_at: string;
            }>;
          };
          return jsonResult({
            total_backups: result.backups.length,
            backups: result.backups
          });
        }
        case "verify": {
          const p = params as { backupId: string };
          const result = await service.request(`/backup/verify/${p.backupId}`) as {
            backup_id: string;
            valid: boolean;
          };
          return jsonResult({
            backup_id: result.backup_id,
            valid: result.valid,
            status: result.valid ? "valid" : "invalid"
          });
        }
        case "restore": {
          const p = params as {
            backupPath: string;
            targetDir: string;
            components?: string[];
            overwrite?: boolean;
          };
          const result = await service.request("/restore", {
            method: "POST",
            body: {
              backup_path: p.backupPath,
              target_dir: p.targetDir,
              components: p.components,
              overwrite: p.overwrite || false
            }
          }) as { restored: Record<string, string> };
          return jsonResult({
            restored: true,
            components: result.restored
          });
        }
        default:
          return jsonResult({ error: `Unknown action: ${action}` });
      }
    }
  };
}