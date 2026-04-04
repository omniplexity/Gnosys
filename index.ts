import { definePluginEntry, type PluginCommandContext } from "openclaw/plugin-sdk/plugin-entry";

import { GnosysPluginConfigSchema, normalizeGnosysConfig } from "./src/config.js";
import { buildMemoryFlushPlan } from "./src/memory/flush-plan.js";
import { buildMemoryPromptSection } from "./src/memory/prompt-section.js";
import { createGnosysMemoryRuntime } from "./src/memory/runtime.js";
import { createGnosysService } from "./src/service.js";
import { createGnosysStatusTool } from "./src/tools/gnosys_status.js";
import { createGnosysStoreMemoryTool } from "./src/tools/gnosys_store_memory.js";
import { createGnosysMemorySearchTool } from "./src/tools/memory_search.js";
import { createGnosysSemanticSearchTool } from "./src/tools/gnosys_semantic_search.js";
import { createGnosysSkillsTool } from "./src/tools/gnosys_skills.js";
import { createGnosysSchedulerTool } from "./src/tools/gnosys_scheduler.js";
import { createGnosysBackupTool } from "./src/tools/gnosys_backup.js";
import { createGnosysMigrateTool } from "./src/tools/gnosys_migrate.js";

async function handleGnosysCommand(ctx: PluginCommandContext, service: ReturnType<typeof createGnosysService>): Promise<{ text: string }> {
  const action = (ctx.args ?? "status").trim().toLowerCase();
  if (action !== "" && action !== "status") {
    return {
      text: "Usage: /gnosys status"
    };
  }

  const status = await service.getStatusReport({ includeStats: true });
  const lines = [
    `Gnosys status: ${status.healthy ? "healthy" : "degraded"}`,
    `- mode: ${status.config.mode}`,
    `- backendUrl: ${status.config.backendUrl}`,
    `- backend: ${status.health?.service ?? "unreachable"}`
  ];

  if (status.health?.database) {
    lines.push(`- database: ${status.health.database}`);
  }
  if (status.stats) {
    lines.push(`- memories: ${status.stats.total_memories}`);
  }
  if (status.error) {
    lines.push(`- error: ${status.error}`);
  }

  return { text: lines.join("\n") };
}

export default definePluginEntry({
  id: "gnosys",
  name: "Gnosys",
  description: "HTTP-bridged memory plugin for a local Python Gnosys backend",
  kind: "memory",
  configSchema: GnosysPluginConfigSchema,
  register(api) {
    const config = normalizeGnosysConfig(api.pluginConfig, api.resolvePath);
    const service = createGnosysService({
      config,
      logger: api.logger
    });

    api.registerMemoryPromptSection(buildMemoryPromptSection);
    api.registerMemoryFlushPlan(buildMemoryFlushPlan);
    api.registerMemoryRuntime(createGnosysMemoryRuntime(service));

    api.registerTool((ctx) => createGnosysMemorySearchTool(ctx, service), { names: ["memory_search"] });
    api.registerTool(() => createGnosysStatusTool(service), { names: ["gnosys_status"] });
    api.registerTool(() => createGnosysStoreMemoryTool(service), { names: ["gnosys_store_memory"] });
    api.registerTool((ctx) => createGnosysSemanticSearchTool(ctx, service), { names: ["gnosys_semantic_search"] });
    api.registerTool(() => createGnosysSkillsTool(service), { names: ["gnosys_skills"] });
    api.registerTool(() => createGnosysSchedulerTool(service), { names: ["gnosys_scheduler"] });
    api.registerTool(() => createGnosysBackupTool(service), { names: ["gnosys_backup"] });
    api.registerTool(() => createGnosysMigrateTool(service), { names: ["gnosys_migrate"] });

    api.registerCommand({
      name: "gnosys",
      description: "Show Gnosys backend status.",
      acceptsArgs: true,
      handler: async (ctx) => handleGnosysCommand(ctx, service)
    });

    api.registerCli(({ program }) => {
      const gnosys = program.command("gnosys").description("Inspect the Gnosys memory plugin");
      gnosys.command("status").description("Show backend health and config").option("--json", "Print JSON").action(async (opts) => {
        const status = await service.getStatusReport({ includeStats: true });
        if (opts.json) {
          process.stdout.write(`${JSON.stringify(status, null, 2)}\n`);
          return;
        }
        const payload = await handleGnosysCommand({
          channel: "cli",
          isAuthorizedSender: true,
          commandBody: "gnosys status",
          args: "status",
          config: api.config,
          requestConversationBinding: async () => ({ status: "error", message: "Conversation binding unavailable from CLI." }),
          detachConversationBinding: async () => ({ removed: false }),
          getCurrentConversationBinding: async () => null
        }, service);
        process.stdout.write(`${payload.text}\n`);
      });
    }, {
      descriptors: [
        {
          name: "gnosys",
          description: "Inspect the Gnosys memory plugin",
          hasSubcommands: true
        }
      ]
    });

    api.on("gateway_start", async () => {
      if (config.mode === "spawn-local-python-backend") {
        try {
          await service.ensureReady();
        } catch (error) {
          const message = error instanceof Error ? error.message : String(error);
          api.logger.error(`Gnosys backend start failed: ${message}`);
          // Throw to fail the gateway start - the plugin cannot function without the backend
          throw new Error(`Gnosys backend failed to start: ${message}`);
        }
      }
    });

    api.on("gateway_stop", async () => {
      await service.stop();
    });
  }
});
