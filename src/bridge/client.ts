import type { NormalizedGnosysPluginConfig } from "../config.js";

export type GnosysContextTier = "working" | "episodic" | "semantic" | "archive";

export type GnosysContextItem = {
  rank: number;
  memory: GnosysMemoryRecord;
  score: number;
  blended_score?: number;
  matched_keywords: string[];
  estimated_tokens: number;
};

export type GnosysRetrieveContextRequest = {
  query: string;
  max_tokens?: number;
  include_tiers?: GnosysContextTier[];
};

export type GnosysRetrieveContextResponse = {
  query: string;
  items: GnosysContextItem[];
  tiers_included: GnosysContextTier[];
  token_budget: number;
  used_tokens: number;
  remaining_tokens: number;
  truncated: boolean;
  dropped_count: number;
  assembly_text: string;
};

export type GnosysHealthResponse = {
  status: string;
  service: string;
  version: string;
  database: string;
};

export type GnosysMemoryRecord = {
  id: string;
  content: string;
  memory_type: string;
  tier: "working" | "episodic" | "semantic" | "archive";
  tags: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  last_accessed_at?: string | null;
  expires_at?: string | null;
};

export type GnosysStoreMemoryRequest = {
  content: string;
  memory_type?: string;
  tier?: GnosysMemoryRecord["tier"];
  tags?: string[];
  metadata?: Record<string, unknown>;
  created_at?: string;
  expires_at?: string;
};

export type GnosysStoreMemoryResponse = {
  memory: GnosysMemoryRecord;
};

export type GnosysSearchResponse = {
  query: string;
  count: number;
  results: Array<{
    memory: GnosysMemoryRecord;
    score: number;
    matched_keywords: string[];
  }>;
};

export type GnosysStatsResponse = {
  total_memories: number;
  counts_by_type: Record<string, number>;
  counts_by_tier: Record<string, number>;
  newest_memory_at?: string | null;
  oldest_memory_at?: string | null;
  database_path: string;
};

export type GnosysMemoryResponse = {
  memory: GnosysMemoryRecord;
};

export type GnosysDeleteResponse = {
  deleted: string;
  success: boolean;
};

export type GnosysSemanticSearchRequest = {
  query: string;
  limit?: number;
  memory_type?: string;
  tier?: string;
  semantic_weight?: number;
  include_entities?: boolean;
};

export type GnosysSemanticSearchResult = {
  memory: GnosysMemoryRecord;
  score: number;
  semantic_score?: number | null;
  keyword_score?: number | null;
  matched_keywords: string[];
};

export type GnosysSemanticSearchResponse = {
  query: string;
  count: number;
  results: GnosysSemanticSearchResult[];
  used_semantic_search: boolean;
  truncated: boolean;
};

export class GnosysBackendError extends Error {
  readonly status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "GnosysBackendError";
    this.status = status;
  }
}

export class GnosysBackendClient {
  readonly baseUrl: string;

  constructor(private readonly config: Pick<NormalizedGnosysPluginConfig, "backendUrl" | "requestTimeoutMs" | "healthcheckTimeoutMs">) {
    this.baseUrl = config.backendUrl.replace(/\/+$/, "");
  }

  async health(): Promise<GnosysHealthResponse> {
    return this.request<GnosysHealthResponse>("/health", undefined, this.config.healthcheckTimeoutMs);
  }

  async stats(): Promise<GnosysStatsResponse> {
    return this.request<GnosysStatsResponse>("/stats");
  }

  async storeMemory(payload: GnosysStoreMemoryRequest): Promise<GnosysStoreMemoryResponse> {
    return this.request<GnosysStoreMemoryResponse>("/memories", {
      method: "POST",
      headers: {
        "content-type": "application/json"
      },
      body: JSON.stringify(payload)
    });
  }

  async searchMemories(params: {
    query: string;
    limit?: number;
    memoryType?: string;
    tier?: string;
  }): Promise<GnosysSearchResponse> {
    const searchParams = new URLSearchParams({ q: params.query });
    if (typeof params.limit === "number") {
      searchParams.set("limit", String(params.limit));
    }
    if (params.memoryType) {
      searchParams.set("memory_type", params.memoryType);
    }
    if (params.tier) {
      searchParams.set("tier", params.tier);
    }
    return this.request<GnosysSearchResponse>(`/memories/search?${searchParams.toString()}`);
  }

  async getMemory(memoryId: string): Promise<GnosysMemoryResponse> {
    return this.request<GnosysMemoryResponse>(`/memories/${memoryId}`);
  }

  async deleteMemory(memoryId: string): Promise<GnosysDeleteResponse> {
    return this.request<GnosysDeleteResponse>(`/memories/${memoryId}`, {
      method: "DELETE"
    });
  }

  async semanticSearch(params: GnosysSemanticSearchRequest): Promise<GnosysSemanticSearchResponse> {
    return this.request<GnosysSemanticSearchResponse>("/memories/semantic-search", {
      method: "POST",
      headers: {
        "content-type": "application/json"
      },
      body: JSON.stringify(params)
    });
  }

  async retrieveContext(params: GnosysRetrieveContextRequest): Promise<GnosysRetrieveContextResponse> {
    const body: Record<string, unknown> = { query: params.query };
    if (typeof params.max_tokens === "number") {
      body.max_tokens = params.max_tokens;
    }
    if (Array.isArray(params.include_tiers)) {
      body.include_tiers = params.include_tiers;
    }
    return this.request<GnosysRetrieveContextResponse>("/context/retrieve", {
      method: "POST",
      headers: {
        "content-type": "application/json"
      },
      body: JSON.stringify(body)
    });
  }

  async request<T>(pathname: string, init?: RequestInit, timeoutMs = this.config.requestTimeoutMs): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(`${this.baseUrl}${pathname}`, {
        ...init,
        signal: controller.signal
      });

      const text = await response.text();
      let payload: unknown = null;
      
      if (text) {
        try {
          payload = JSON.parse(text);
        } catch (parseError) {
          throw new GnosysBackendError(`Backend returned invalid JSON response: ${parseError instanceof Error ? parseError.message : String(parseError)}`, response.status);
        }
      }

      if (!response.ok) {
        throw new GnosysBackendError(this.extractErrorMessage(payload, response.status, response.statusText), response.status);
      }

      return payload as T;
    } catch (error) {
      if (error instanceof GnosysBackendError) {
        throw error;
      }
      if (error instanceof Error && error.name === "AbortError") {
        throw new GnosysBackendError(`Timed out waiting for Gnosys backend at ${this.baseUrl}${pathname}`);
      }
      throw new GnosysBackendError(error instanceof Error ? error.message : String(error));
    } finally {
      clearTimeout(timer);
    }
  }

  private extractErrorMessage(payload: unknown, status: number, statusText: string): string {
    if (payload && typeof payload === "object") {
      const detail = (payload as { detail?: unknown }).detail;
      if (typeof detail === "string" && detail.trim()) {
        return detail;
      }
    }
    return `Gnosys backend request failed (${status} ${statusText})`;
  }
}
