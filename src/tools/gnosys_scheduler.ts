import { Type } from "@sinclair/typebox";
import { jsonResult, type AnyAgentTool } from "openclaw/plugin-sdk/memory-core";

import type { GnosysService } from "../service.js";

export function createGnosysSchedulerTool(service: GnosysService): AnyAgentTool {
  return {
    label: "Gnosys Scheduler",
    name: "gnosys_scheduler",
    description: "Manage scheduled tasks - list, create, run, and view history of scheduled tasks.",
    parameters: Type.Union([
      // List tasks
      Type.Object({
        action: Type.Literal("list"),
        enabledOnly: Type.Optional(Type.Boolean())
      }),
      // Create task
      Type.Object({
        action: Type.Literal("create"),
        name: Type.String({ minLength: 1 }),
        schedule: Type.String({ minLength: 1 }),
        taskType: Type.Union([Type.Literal("query"), Type.Literal("action"), Type.Literal("report"), Type.Literal("check")]),
        enabled: Type.Optional(Type.Boolean()),
        description: Type.Optional(Type.String()),
        taskAction: Type.Optional(Type.Record(Type.String(), Type.Any())),
        delivery: Type.Optional(Type.Record(Type.String(), Type.Any()))
      }),
      // Run task immediately
      Type.Object({
        action: Type.Literal("run"),
        taskId: Type.String({ minLength: 1 })
      }),
      // Get history
      Type.Object({
        action: Type.Literal("history"),
        taskId: Type.String({ minLength: 1 }),
        limit: Type.Optional(Type.Integer({ minimum: 1, maximum: 100 }))
      }),
      // Get stats
      Type.Object({
        action: Type.Literal("stats")
      })
    ]),
    execute: async (_toolCallId, params) => {
      const action = (params as { action?: string }).action || "list";
      
      switch (action) {
        case "list": {
          const p = params as { enabledOnly?: boolean };
          const result = await service.request(`/scheduled${p.enabledOnly ? "?enabled_only=true" : ""}`) as {
            count: number;
            tasks: Array<{
              id: string; name: string; schedule: string; task_type: string;
              enabled: boolean; description?: string; last_run_at?: string;
              next_run_at?: string; run_count: number;
            }>;
          };
          return jsonResult({
            total_tasks: result.count,
            tasks: result.tasks.map(t => ({
              id: t.id,
              name: t.name,
              schedule: t.schedule,
              task_type: t.task_type,
              enabled: t.enabled,
              description: t.description,
              last_run_at: t.last_run_at,
              next_run_at: t.next_run_at,
              run_count: t.run_count
            }))
          });
        }
        case "create": {
          const p = params as {
            name: string;
            schedule: string;
            taskType: string;
            enabled?: boolean;
            description?: string;
            taskAction?: Record<string, unknown>;
            delivery?: Record<string, unknown>;
          };
          const result = await service.request("/scheduled", {
            method: "POST",
            body: {
              name: p.name,
              schedule: p.schedule,
              task_type: p.taskType,
              enabled: p.enabled ?? true,
              description: p.description,
              action: p.taskAction || {},
              delivery: p.delivery || {}
            }
          }) as { id: string; name: string; schedule: string };
          return jsonResult({
            created: true,
            task_id: result.id,
            name: result.name,
            schedule: result.schedule
          });
        }
        case "run": {
          const p = params as { taskId: string };
          const result = await service.request(`/scheduled/${p.taskId}/run`, {
            method: "POST"
          }) as { task_id: string; executed: boolean; result?: Record<string, unknown>; executed_at: string };
          return jsonResult({
            task_id: result.task_id,
            executed: result.executed,
            result: result.result,
            executed_at: result.executed_at
          });
        }
        case "history": {
          const p = params as { taskId: string; limit?: number };
          const result = await service.request(`/scheduled/${p.taskId}/history?limit=${p.limit || 50}`) as {
            count: number;
            executions: Array<{
              id: string; executed_at: string; success: boolean;
              result?: Record<string, unknown>; error?: string; duration_ms: number;
            }>;
          };
          return jsonResult({
            task_id: p.taskId,
            total_executions: result.count,
            executions: result.executions
          });
        }
        case "stats": {
          const result = await service.request("/scheduler/stats") as {
            total_tasks: number;
            active_tasks: number;
            due_now: number;
            executions_24h: number;
            success_rate_24h: number;
          };
          return jsonResult(result);
        }
        default:
          return jsonResult({ error: `Unknown action: ${action}` });
      }
    }
  };
}
