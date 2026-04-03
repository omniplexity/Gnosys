/**
 * TypeScript client for Gnosys backend pipeline/multi-agent features
 */

import type { GnosysService } from "../service.js";

export type AgentType = "primary" | "specialist" | "worker" | "coordinator";
export type CoordinationMode = "sequential" | "parallel" | "hierarchical" | "debate";
export type AgentStatus = "pending" | "running" | "completed" | "failed";

export interface AgentProfile {
  id?: string;
  role: string;
  type: AgentType;
  weight?: number;
  context?: Record<string, unknown>;
}

export interface AgentSpawnRequest {
  agent_id?: string;
  role: string;
  agent_type?: AgentType;
  context?: Record<string, unknown>;
  tools?: string[];
  parent_id?: string;
}

export interface AgentSpawnResponse {
  agent_id: string;
  role: string;
  agent_type: AgentType;
  status: AgentStatus;
  created_at: string;
}

export interface TaskDelegateRequest {
  agent_id?: string;
  role: string;
  agent_type?: AgentType;
  context: Record<string, unknown>;
  tools?: string[];
  parent_id?: string;
}

export interface TaskDelegateResponse {
  agent_id: string;
  status: AgentStatus;
  delegated_at: string;
}

export interface PipelineProfile {
  id: string;
  name: string;
  agents: AgentProfile[];
  coordination: CoordinationMode;
}

export interface PipelineExecuteRequest {
  profile_name: string;
  task: string;
  coordinator_id?: string;
}

export interface PipelineExecuteResponse {
  pipeline_id: string;
  profile_name: string;
  agents_spawned: number;
  results: Record<string, unknown>[];
  executed_at: string;
}

export function createPipelineClient(service: GnosysService) {
  return {
    /**
     * Spawn a sub-agent with isolated context
     */
    async spawnAgent(request: AgentSpawnRequest): Promise<AgentSpawnResponse> {
      const response = await service.request("/agents/spawn", {
        method: "POST",
        body: request,
      });
      return response as Promise<AgentSpawnResponse>;
    },

    /**
     * Delegate a task to a sub-agent
     */
    async delegateTask(request: TaskDelegateRequest): Promise<TaskDelegateResponse> {
      const response = await service.request("/agents/delegate", {
        method: "POST",
        body: request,
      });
      return response as Promise<TaskDelegateResponse>;
    },

    /**
     * Get agent by ID
     */
    async getAgent(agentId: string): Promise<AgentSpawnResponse> {
      const response = await service.request(`/agents/${agentId}`, {
        method: "GET",
      });
      return response as Promise<AgentSpawnResponse>;
    },

    /**
     * List active agents
     */
    async listAgents(parentId?: string): Promise<AgentSpawnResponse[]> {
      const url = parentId ? `/agents?parent_id=${encodeURIComponent(parentId)}` : "/agents";
      const response = await service.request(url, {
        method: "GET",
      });
      return response as Promise<AgentSpawnResponse[]>;
    },

    /**
     * Execute a multi-agent pipeline
     */
    async executePipeline(request: PipelineExecuteRequest): Promise<PipelineExecuteResponse> {
      const response = await service.request("/pipeline/execute", {
        method: "POST",
        body: request,
      });
      return response as Promise<PipelineExecuteResponse>;
    },
  };
}
