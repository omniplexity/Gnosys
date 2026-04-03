import type { PluginLogger } from "openclaw/plugin-sdk/plugin-entry";

import type { NormalizedGnosysPluginConfig } from "./config.js";
import { GnosysBackendClient, type GnosysHealthResponse, type GnosysMemoryResponse, type GnosysDeleteResponse, type GnosysSearchResponse, type GnosysStatsResponse, type GnosysStoreMemoryRequest, type GnosysStoreMemoryResponse, type GnosysRetrieveContextRequest, type GnosysRetrieveContextResponse, type GnosysSemanticSearchRequest, type GnosysSemanticSearchResponse } from "./bridge/client.js";
import { GnosysBackendProcessManager } from "./bridge/process.js";

export type GnosysSearchSnapshot = {
  results: Array<{
    id: string;
    content: string;
    score: number;
    matchedKeywords: string[];
    tier: string;
    memoryType: string;
  }>;
  raw: GnosysSearchResponse;
};

export type GnosysSemanticSearchSnapshot = {
  results: Array<{
    id: string;
    content: string;
    score: number;
    semanticScore?: number;
    keywordScore?: number;
    matchedKeywords: string[];
    tier: string;
    memoryType: string;
  }>;
  raw: GnosysSemanticSearchResponse;
  usedSemanticSearch: boolean;
  truncated: boolean;
};

export type GnosysService = ReturnType<typeof createGnosysService>;

export function createGnosysService(params: {
  config: NormalizedGnosysPluginConfig;
  logger: PluginLogger;
}) {
  const client = new GnosysBackendClient(params.config);
  const processManager = new GnosysBackendProcessManager(params.config, client, params.logger);
  const ensureReady = async (): Promise<void> => {
    if (params.config.mode === "spawn-local-python-backend") {
      await processManager.ensureStarted();
    }
    await client.health();
  };

  return {
    config: params.config,
    ensureReady,
    async stop(): Promise<void> {
      await processManager.stop();
    },
    async health(): Promise<GnosysHealthResponse> {
      await ensureReady();
      return client.health();
    },
    async stats(): Promise<GnosysStatsResponse> {
      await ensureReady();
      return client.stats();
    },
    async storeMemory(payload: GnosysStoreMemoryRequest): Promise<GnosysStoreMemoryResponse> {
      await ensureReady();
      return client.storeMemory(payload);
    },
    async search(params: { query: string; limit?: number; memoryType?: string; tier?: string }): Promise<GnosysSearchSnapshot> {
      await ensureReady();
      const raw = await client.searchMemories(params);
      return {
        raw,
        results: raw.results.map((result) => ({
          id: result.memory.id,
          content: result.memory.content,
          score: result.score,
          matchedKeywords: result.matched_keywords,
          tier: result.memory.tier,
          memoryType: result.memory.memory_type
        }))
      };
    },
    async semanticSearch(params: { query: string; limit?: number; memoryType?: string; tier?: string; semanticWeight?: number }): Promise<GnosysSemanticSearchSnapshot> {
      await ensureReady();
      const raw = await client.semanticSearch({
        query: params.query,
        limit: params.limit,
        memory_type: params.memoryType,
        tier: params.tier,
        semantic_weight: params.semanticWeight
      });
      return {
        raw,
        usedSemanticSearch: raw.used_semantic_search,
        truncated: raw.truncated,
        results: raw.results.map((result) => ({
          id: result.memory.id,
          content: result.memory.content,
          score: result.score,
          semanticScore: result.semantic_score ?? undefined,
          keywordScore: result.keyword_score ?? undefined,
          matchedKeywords: result.matched_keywords,
          tier: result.memory.tier,
          memoryType: result.memory.memory_type
        }))
      };
    },
    async getMemory(memoryId: string): Promise<GnosysMemoryResponse> {
      await ensureReady();
      return client.getMemory(memoryId);
    },
    async deleteMemory(memoryId: string): Promise<GnosysDeleteResponse> {
      await ensureReady();
      return client.deleteMemory(memoryId);
    },
    async getStatusReport(options?: { includeStats?: boolean }) {
      try {
        if (params.config.mode === "spawn-local-python-backend") {
          await processManager.ensureStarted();
        }
        const health = await client.health();
        const stats = options?.includeStats ? await client.stats() : undefined;
        return {
          healthy: true,
          config: {
            mode: params.config.mode,
            backendUrl: params.config.backendUrl,
            requestTimeoutMs: params.config.requestTimeoutMs,
            healthcheckTimeoutMs: params.config.healthcheckTimeoutMs
          },
          health,
          stats,
          process: processManager.getDiagnostics()
        };
      } catch (error) {
        return {
          healthy: false,
          config: {
            mode: params.config.mode,
            backendUrl: params.config.backendUrl,
            requestTimeoutMs: params.config.requestTimeoutMs,
            healthcheckTimeoutMs: params.config.healthcheckTimeoutMs
          },
          error: error instanceof Error ? error.message : String(error),
          process: processManager.getDiagnostics()
        };
      }
    },
    async retrieveContext(req: GnosysRetrieveContextRequest): Promise<GnosysRetrieveContextResponse> {
      await ensureReady();
      return client.retrieveContext(req);
    },
    async request(pathname: string, init?: { method?: string; body?: unknown }): Promise<unknown> {
      await ensureReady();
      const requestInit: RequestInit = {
        method: init?.method ?? "GET",
        headers: {
          "content-type": "application/json"
        }
      };
      if (init?.body) {
        requestInit.body = JSON.stringify(init.body);
      }
      return client.request(pathname, requestInit);
    }
  };
}
