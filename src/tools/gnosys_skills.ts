import { Type } from "@sinclair/typebox";
import { jsonResult, type AnyAgentTool } from "openclaw/plugin-sdk/memory-core";

import type { GnosysService } from "../service.js";

const GnosysSkillsListSchema = Type.Object({
  filter: Type.Optional(Type.String())
});

const GnosysSkillCreateSchema = Type.Object({
  name: Type.String({ minLength: 1 }),
  triggers: Type.Optional(Type.Array(Type.String())),
  workflow: Type.Array(Type.String()),
  tools: Type.Optional(Type.Array(Type.String())),
  parameters: Type.Optional(Type.Record(Type.String(), Type.Any())),
  description: Type.Optional(Type.String()),
  compoundsFrom: Type.Optional(Type.Array(Type.String()))
});

const GnosysSkillMatchSchema = Type.Object({
  task: Type.String({ minLength: 1 }),
  context: Type.Optional(Type.Record(Type.String(), Type.Any()))
});

const GnosysSkillRefineSchema = Type.Object({
  skillId: Type.String({ minLength: 1 }),
  feedback: Type.String({ minLength: 1 }),
  success: Type.Boolean(),
  improvements: Type.Optional(Type.Array(Type.String()))
});

export function createGnosysSkillsTool(service: GnosysService): AnyAgentTool {
  return {
    label: "Gnosys Skills",
    name: "gnosys_skills",
    description: "Manage and match skills - list skills, create skills, match tasks to skills, and refine skill performance.",
    parameters: Type.Union([
      // List skills
      Type.Object({
        action: Type.Literal("list"),
        filter: Type.Optional(Type.String())
      }),
      // Create skill
      Type.Object({
        action: Type.Literal("create"),
        name: Type.String({ minLength: 1 }),
        triggers: Type.Optional(Type.Array(Type.String())),
        workflow: Type.Array(Type.String()),
        tools: Type.Optional(Type.Array(Type.String())),
        parameters: Type.Optional(Type.Record(Type.String(), Type.Any())),
        description: Type.Optional(Type.String()),
        compoundsFrom: Type.Optional(Type.Array(Type.String()))
      }),
      // Match skill
      Type.Object({
        action: Type.Literal("match"),
        task: Type.String({ minLength: 1 }),
        context: Type.Optional(Type.Record(Type.String(), Type.Any()))
      }),
      // Refine skill
      Type.Object({
        action: Type.Literal("refine"),
        skillId: Type.String({ minLength: 1 }),
        feedback: Type.String({ minLength: 1 }),
        success: Type.Boolean(),
        improvements: Type.Optional(Type.Array(Type.String()))
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
          const result = await service.request("/skills") as { count: number; skills: Array<{
            id: string; name: string; version: string; triggers: string[];
            workflow: string[]; tools: string[]; use_count: number; success_rate: number;
          }>};
          return jsonResult({
            total_skills: result.count,
            skills: result.skills.map(s => ({
              id: s.id,
              name: s.name,
              version: s.version,
              triggers: s.triggers,
              workflow: s.workflow,
              tools: s.tools,
              use_count: s.use_count,
              success_rate: s.success_rate
            }))
          });
        }
        case "create": {
          const p = params as {
            name: string;
            triggers?: string[];
            workflow: string[];
            tools?: string[];
            parameters?: Record<string, unknown>;
            description?: string;
            compoundsFrom?: string[];
          };
          const result = await service.request("/skills", {
            method: "POST",
            body: {
              name: p.name,
              triggers: p.triggers || [],
              workflow: p.workflow,
              tools: p.tools || [],
              parameters: p.parameters || {},
              description: p.description,
              compounds_from: p.compoundsFrom || []
            }
          }) as { id: string; name: string; version: string };
          return jsonResult({ created: true, skill_id: result.id, name: result.name, version: result.version });
        }
        case "match": {
          const p = params as { task: string; context?: Record<string, unknown> };
          const result = await service.request("/skills/match", {
            method: "POST",
            body: { task: p.task, context: p.context }
          }) as { matched: boolean; skill?: { id: string; name: string; version: string; workflow: string[] }; confidence: number };
          if (result.matched && result.skill) {
            return jsonResult({
              matched: true,
              skill: result.skill,
              confidence: result.confidence,
              workflow: result.skill.workflow
            });
          }
          return jsonResult({ matched: false, confidence: result.confidence });
        }
        case "refine": {
          const p = params as { skillId: string; feedback: string; success: boolean; improvements?: string[] };
          const result = await service.request(`/skills/${p.skillId}/refine`, {
            method: "POST",
            body: { feedback: p.feedback, success: p.success, improvements: p.improvements || [] }
          }) as { skill: { id: string; version: string }; previous_version: string; new_version: string };
          return jsonResult({
            refined: true,
            skill_id: result.skill.id,
            previous_version: result.previous_version,
            new_version: result.new_version
          });
        }
        case "stats": {
          const result = await service.request("/skills/stats") as {
            total_skills: number;
            total_uses: number;
            avg_success_rate: number;
            top_skills: Array<{ name: string; use_count: number; success_rate: number }>;
          };
          return jsonResult(result);
        }
        default:
          return jsonResult({ error: `Unknown action: ${action}` });
      }
    }
  };
}
