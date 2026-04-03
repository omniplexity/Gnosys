import path from "node:path";

import type { OpenClawPluginConfigSchema } from "openclaw/plugin-sdk/plugin-entry";
import type { GnosysContextTier } from "./bridge/client.js";

export type RawGnosysPluginConfig = {
  mode?: "backend-url" | "spawn-local-python-backend";
  backendUrl?: string;
  requestTimeoutMs?: number;
  healthcheckTimeoutMs?: number;
  spawn?: {
    command?: string;
    args?: string[];
    cwd?: string;
    host?: string;
    port?: number;
    dbPath?: string;
    vectorsPath?: string;
    startupTimeoutMs?: number;
    env?: Record<string, string>;
  };
  retention?: {
    episodicDays?: number;
    archiveDays?: number;
    defaultSearchLimit?: number;
  };
  context?: {
    enabled?: boolean;
    budgetFraction?: number;
    maxTokens?: number;
    maxQueryChars?: number;
    includeTiers?: GnosysContextTier[];
  };
  embeddings?: {
    provider?: string;
    model?: string;
    dimension?: number;
    openaiModel?: string;
    batchSize?: number;
  };
};

export type NormalizedGnosysPluginConfig = {
  mode: "backend-url" | "spawn-local-python-backend";
  backendUrl: string;
  requestTimeoutMs: number;
  healthcheckTimeoutMs: number;
  retention: {
    episodicDays: number;
    archiveDays: number;
    defaultSearchLimit: number;
  };
  spawn: {
    command: string;
    args: string[];
    cwd: string;
    host: string;
    port: number;
    dbPath: string;
    vectorsPath: string;
    startupTimeoutMs: number;
    env: Record<string, string>;
  };
  context: {
    enabled: boolean;
    budgetFraction: number;
    maxTokens: number;
    maxQueryChars: number;
    includeTiers: GnosysContextTier[];
  };
  embeddings: {
    provider: string;
    model: string;
    dimension: number;
    openaiModel: string;
    batchSize: number;
  };
};

export const GnosysPluginConfigJsonSchema: Record<string, unknown> = {
  type: "object",
  additionalProperties: false,
  properties: {
    mode: {
      type: "string",
      enum: ["backend-url", "spawn-local-python-backend"]
    },
    backendUrl: {
      type: "string"
    },
    requestTimeoutMs: {
      type: "number",
      minimum: 100
    },
    healthcheckTimeoutMs: {
      type: "number",
      minimum: 100
    },
    spawn: {
      type: "object",
      additionalProperties: false,
      properties: {
        command: { type: "string" },
        args: {
          type: "array",
          items: { type: "string" }
        },
        cwd: { type: "string" },
        host: { type: "string" },
        port: {
          type: "number",
          minimum: 1,
          maximum: 65535
        },
        dbPath: { type: "string" },
        vectorsPath: { type: "string" },
        startupTimeoutMs: {
          type: "number",
          minimum: 100
        },
        env: {
          type: "object",
          additionalProperties: { type: "string" }
        }
      }
    },
    retention: {
      type: "object",
      additionalProperties: false,
      properties: {
        episodicDays: {
          type: "number",
          minimum: 1
        },
        archiveDays: {
          type: "number",
          minimum: 1
        },
        defaultSearchLimit: {
          type: "number",
          minimum: 1,
          maximum: 100
        }
      }
    },
    context: {
      type: "object",
      additionalProperties: false,
      properties: {
        enabled: { type: "boolean" },
        budgetFraction: { type: "number", minimum: 0, maximum: 1 },
        maxTokens: { type: "number", minimum: 100 },
        maxQueryChars: { type: "number", minimum: 10 },
        includeTiers: {
          type: "array",
          items: { type: "string", enum: ["working", "episodic", "semantic", "archive"] }
        }
      }
    },
    embeddings: {
      type: "object",
      additionalProperties: false,
      properties: {
        provider: { type: "string", enum: ["local", "openai", "disabled"] },
        model: { type: "string" },
        dimension: { type: "number", minimum: 1 },
        openaiModel: { type: "string" },
        batchSize: { type: "number", minimum: 1 }
      }
    }
  }
};

function asRecord(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }
  return value as Record<string, unknown>;
}

function asString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function asNumber(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function asStringArray(value: unknown): string[] | undefined {
  if (!Array.isArray(value) || !value.every((entry) => typeof entry === "string")) {
    return undefined;
  }
  return [...value];
}

function asStringMap(value: unknown): Record<string, string> {
  const input = asRecord(value);
  const output: Record<string, string> = {};
  for (const [key, raw] of Object.entries(input)) {
    if (typeof raw === "string") {
      output[key] = raw;
    }
  }
  return output;
}

function validateGnosysConfig(value: unknown): { ok: true } | { ok: false; errors: string[] } {
  const errors: string[] = [];
  const raw = asRecord(value);
  const allowedTopLevel = new Set(["mode", "backendUrl", "requestTimeoutMs", "healthcheckTimeoutMs", "spawn", "retention", "context", "embeddings"]);
  for (const key of Object.keys(raw)) {
    if (!allowedTopLevel.has(key)) {
      errors.push(`Unknown config key: ${key}`);
    }
  }

  if (raw.mode !== undefined && raw.mode !== "backend-url" && raw.mode !== "spawn-local-python-backend") {
    errors.push("mode must be 'backend-url' or 'spawn-local-python-backend'");
  }
  if (raw.backendUrl !== undefined && typeof raw.backendUrl !== "string") {
    errors.push("backendUrl must be a string");
  }
  if (raw.requestTimeoutMs !== undefined && (typeof raw.requestTimeoutMs !== "number" || raw.requestTimeoutMs < 100)) {
    errors.push("requestTimeoutMs must be a number >= 100");
  }
  if (raw.healthcheckTimeoutMs !== undefined && (typeof raw.healthcheckTimeoutMs !== "number" || raw.healthcheckTimeoutMs < 100)) {
    errors.push("healthcheckTimeoutMs must be a number >= 100");
  }

  const spawn = raw.spawn;
  if (spawn !== undefined && (!spawn || typeof spawn !== "object" || Array.isArray(spawn))) {
    errors.push("spawn must be an object");
  }
  const rawSpawn = asRecord(spawn);
  const allowedSpawn = new Set(["command", "args", "cwd", "host", "port", "dbPath", "vectorsPath", "startupTimeoutMs", "env"]);
  for (const key of Object.keys(rawSpawn)) {
    if (!allowedSpawn.has(key)) {
      errors.push(`Unknown spawn config key: ${key}`);
    }
  }
  if (rawSpawn.command !== undefined && typeof rawSpawn.command !== "string") {
    errors.push("spawn.command must be a string");
  }
  if (rawSpawn.args !== undefined && !asStringArray(rawSpawn.args)) {
    errors.push("spawn.args must be an array of strings");
  }
  if (rawSpawn.cwd !== undefined && typeof rawSpawn.cwd !== "string") {
    errors.push("spawn.cwd must be a string");
  }
  if (rawSpawn.host !== undefined && typeof rawSpawn.host !== "string") {
    errors.push("spawn.host must be a string");
  }
  if (rawSpawn.port !== undefined && (typeof rawSpawn.port !== "number" || rawSpawn.port < 1 || rawSpawn.port > 65535)) {
    errors.push("spawn.port must be a number between 1 and 65535");
  }
  if (rawSpawn.dbPath !== undefined && typeof rawSpawn.dbPath !== "string") {
    errors.push("spawn.dbPath must be a string");
  }
  if (rawSpawn.vectorsPath !== undefined && typeof rawSpawn.vectorsPath !== "string") {
    errors.push("spawn.vectorsPath must be a string");
  }
  if (rawSpawn.startupTimeoutMs !== undefined && (typeof rawSpawn.startupTimeoutMs !== "number" || rawSpawn.startupTimeoutMs < 100)) {
    errors.push("spawn.startupTimeoutMs must be a number >= 100");
  }
  if (rawSpawn.env !== undefined) {
    const env = asRecord(rawSpawn.env);
    if (Object.keys(env).some((key) => typeof env[key] !== "string")) {
      errors.push("spawn.env must be an object with string values");
    }
  }

  const retention = raw.retention;
  if (retention !== undefined && (!retention || typeof retention !== "object" || Array.isArray(retention))) {
    errors.push("retention must be an object");
  }
  const rawRetention = asRecord(retention);
  const allowedRetention = new Set(["episodicDays", "archiveDays", "defaultSearchLimit"]);
  for (const key of Object.keys(rawRetention)) {
    if (!allowedRetention.has(key)) {
      errors.push(`Unknown retention config key: ${key}`);
    }
  }
  if (rawRetention.episodicDays !== undefined && (typeof rawRetention.episodicDays !== "number" || rawRetention.episodicDays < 1)) {
    errors.push("retention.episodicDays must be a number >= 1");
  }
  if (rawRetention.archiveDays !== undefined && (typeof rawRetention.archiveDays !== "number" || rawRetention.archiveDays < 1)) {
    errors.push("retention.archiveDays must be a number >= 1");
  }
  if (rawRetention.defaultSearchLimit !== undefined && (typeof rawRetention.defaultSearchLimit !== "number" || rawRetention.defaultSearchLimit < 1 || rawRetention.defaultSearchLimit > 100)) {
    errors.push("retention.defaultSearchLimit must be a number between 1 and 100");
  }

  const rawContext = asRecord(raw.context);
  const allowedContext = new Set(["enabled", "budgetFraction", "maxTokens", "maxQueryChars", "includeTiers"]);
  for (const key of Object.keys(rawContext)) {
    if (!allowedContext.has(key)) {
      errors.push(`Unknown context config key: ${key}`);
    }
  }
  const validTiers = new Set(["working", "episodic", "semantic", "archive"]);
  if (rawContext.includeTiers !== undefined) {
    if (!Array.isArray(rawContext.includeTiers) || !rawContext.includeTiers.every((t: string) => validTiers.has(t))) {
      errors.push("context.includeTiers must be an array of 'working', 'episodic', 'semantic', or 'archive'");
    }
  }
  if (rawContext.enabled !== undefined && typeof rawContext.enabled !== "boolean") {
    errors.push("context.enabled must be a boolean");
  }
  if (rawContext.budgetFraction !== undefined && (typeof rawContext.budgetFraction !== "number" || rawContext.budgetFraction <= 0 || rawContext.budgetFraction > 1)) {
    errors.push("context.budgetFraction must be a number between 0 and 1");
  }
  if (rawContext.maxTokens !== undefined && (typeof rawContext.maxTokens !== "number" || rawContext.maxTokens < 100)) {
    errors.push("context.maxTokens must be a number >= 100");
  }
  if (rawContext.maxQueryChars !== undefined && (typeof rawContext.maxQueryChars !== "number" || rawContext.maxQueryChars < 10)) {
    errors.push("context.maxQueryChars must be a number >= 10");
  }

  const rawEmbeddings = asRecord(raw.embeddings);
  const allowedEmbeddings = new Set(["provider", "model", "dimension", "openaiModel", "batchSize"]);
  for (const key of Object.keys(rawEmbeddings)) {
    if (!allowedEmbeddings.has(key)) {
      errors.push(`Unknown embeddings config key: ${key}`);
    }
  }
  const embeddingsProvider = asString(rawEmbeddings.provider);
  if (embeddingsProvider !== undefined && !["local", "openai", "disabled"].includes(embeddingsProvider)) {
    errors.push("embeddings.provider must be 'local', 'openai', or 'disabled'");
  }
  if (rawEmbeddings.model !== undefined && typeof rawEmbeddings.model !== "string") {
    errors.push("embeddings.model must be a string");
  }
  if (rawEmbeddings.dimension !== undefined && (typeof rawEmbeddings.dimension !== "number" || rawEmbeddings.dimension < 1)) {
    errors.push("embeddings.dimension must be a number >= 1");
  }
  if (rawEmbeddings.openaiModel !== undefined && typeof rawEmbeddings.openaiModel !== "string") {
    errors.push("embeddings.openaiModel must be a string");
  }
  if (rawEmbeddings.batchSize !== undefined && (typeof rawEmbeddings.batchSize !== "number" || rawEmbeddings.batchSize < 1)) {
    errors.push("embeddings.batchSize must be a number >= 1");
  }

  if (errors.length > 0) {
    return { ok: false, errors };
  }
  return { ok: true };
}

export const GnosysPluginConfigSchema: OpenClawPluginConfigSchema = {
  jsonSchema: GnosysPluginConfigJsonSchema,
  validate: validateGnosysConfig
};

export function normalizeGnosysConfig(rawConfig: unknown, resolvePath: (input: string) => string): NormalizedGnosysPluginConfig {
  const raw = asRecord(rawConfig);
  const rawSpawn = asRecord(raw.spawn);
  const rawRetention = asRecord(raw.retention);
  const rawContext = asRecord(raw.context);
  const rawEmbeddings = asRecord(raw.embeddings);
  const mode = raw.mode === "backend-url" || raw.mode === "spawn-local-python-backend"
    ? raw.mode
    : asString(raw.backendUrl)
      ? "backend-url"
      : "spawn-local-python-backend";

  const host = asString(rawSpawn.host) ?? "127.0.0.1";
  const port = asNumber(rawSpawn.port) ?? 8766;
  const backendUrl = asString(raw.backendUrl) ?? `http://${host}:${port}`;
  const pythonRoot = resolvePath("python");
  const rawCwd = asString(rawSpawn.cwd);
  const resolvedCwd = rawCwd ? resolvePath(rawCwd) : pythonRoot;
  const rawDbPath = asString(rawSpawn.dbPath);
  const dbPath = rawDbPath
    ? path.isAbsolute(rawDbPath)
      ? rawDbPath
      : resolvePath(rawDbPath)
    : path.join(pythonRoot, "data", "gnosys.db");

  const rawVectorsPath = asString(rawSpawn.vectorsPath);
  const vectorsPath = rawVectorsPath
    ? path.isAbsolute(rawVectorsPath)
      ? rawVectorsPath
      : resolvePath(rawVectorsPath)
    : path.join(pythonRoot, "data", "vectors.db");

  return {
    mode,
    backendUrl,
    requestTimeoutMs: asNumber(raw.requestTimeoutMs) ?? 10_000,
    healthcheckTimeoutMs: asNumber(raw.healthcheckTimeoutMs) ?? 3_000,
    retention: {
      episodicDays: asNumber(rawRetention.episodicDays) ?? 30,
      archiveDays: asNumber(rawRetention.archiveDays) ?? 365,
      defaultSearchLimit: asNumber(rawRetention.defaultSearchLimit) ?? 10
    },
    spawn: {
      command: asString(rawSpawn.command) ?? "python",
      args: asStringArray(rawSpawn.args) ?? ["-m", "gnosys_backend.app"],
      cwd: resolvedCwd,
      host,
      port,
      dbPath,
      vectorsPath,
      startupTimeoutMs: asNumber(rawSpawn.startupTimeoutMs) ?? 10_000,
      env: asStringMap(rawSpawn.env)
    },
    context: {
      enabled: rawContext.enabled === true,
      budgetFraction: asNumber(rawContext.budgetFraction) ?? 0.3,
      maxTokens: asNumber(rawContext.maxTokens) ?? 2000,
      maxQueryChars: asNumber(rawContext.maxQueryChars) ?? 500,
      includeTiers: (Array.isArray(rawContext.includeTiers) ? rawContext.includeTiers : ["working", "episodic", "semantic"]) as GnosysContextTier[]
    },
    embeddings: {
      provider: asString(rawEmbeddings?.provider) ?? "local",
      model: asString(rawEmbeddings?.model) ?? "sentence-transformers/all-MiniLM-L6-v2",
      dimension: asNumber(rawEmbeddings?.dimension) ?? 384,
      openaiModel: asString(rawEmbeddings?.openaiModel) ?? "text-embedding-3-small",
      batchSize: asNumber(rawEmbeddings?.batchSize) ?? 32
    }
  };
}
