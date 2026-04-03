import type { MemoryPluginRuntime } from "openclaw/plugin-sdk/memory-core";
import type { MemoryEmbeddingProbeResult, MemoryProviderStatus, MemorySearchManager, MemorySearchResult } from "openclaw/plugin-sdk/memory-core-host-engine-storage";

import type { GnosysService } from "../service.js";

function toSearchResult(record: {
  id: string;
  content: string;
  score: number;
  tier: string;
  matchedKeywords: string[];
  memoryType: string;
}): MemorySearchResult {
  const lineCount = Math.max(1, record.content.split(/\r?\n/).length);
  return {
    path: `gnosys:${record.id}`,
    startLine: 1,
    endLine: lineCount,
    score: record.score,
    snippet: record.content,
    source: "memory",
    citation: `gnosys:${record.id}`
  };
}

export function createGnosysMemoryRuntime(service: GnosysService): MemoryPluginRuntime {
  const manager: MemorySearchManager = {
    async search(query, opts) {
      const status = await service.search({
        query,
        limit: opts?.maxResults
      });
      return status.results.map(toSearchResult);
    },
    async readFile(params) {
      return {
        path: params.relPath,
        text: "Gnosys does not expose raw file-backed memory reads in v0.1. Use memory_search results directly."
      };
    },
    status(): MemoryProviderStatus {
      return {
        backend: "qmd",
        provider: "gnosys-http",
        model: "keyword-search",
        custom: {
          plugin: "gnosys",
          searchMode: "keyword-http-bridge",
          backendUrl: service.config.backendUrl,
          mode: service.config.mode
        }
      };
    },
    async sync() {
      await service.ensureReady();
    },
    async probeEmbeddingAvailability(): Promise<MemoryEmbeddingProbeResult> {
      await service.ensureReady();
      return { ok: true };
    },
    async probeVectorAvailability(): Promise<boolean> {
      return false;
    },
    async close() {
      await service.stop();
    }
  };

  return {
    async getMemorySearchManager() {
      try {
        await service.ensureReady();
        return { manager };
      } catch (error) {
        return {
          manager: null,
          error: error instanceof Error ? error.message : String(error)
        };
      }
    },
    resolveMemoryBackendConfig() {
      return {
        backend: "qmd",
        qmd: {
          command: "gnosys-http"
        }
      };
    },
    async closeAllMemorySearchManagers() {
      await service.stop();
    }
  };
}
