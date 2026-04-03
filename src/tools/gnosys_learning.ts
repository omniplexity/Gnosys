/**
 * TypeScript client for Gnosys backend learning features
 */

import type { GnosysService } from "../service.js";

export interface LearningConfig {
  enabled: boolean;
  pattern_detection: {
    trajectory_limit: number;
    min_sequence_length: number;
    min_frequency: number;
  };
  dataset_generation: {
    success_threshold: number;
    min_trajectories: number;
  };
}

export interface PatternRecord {
  id: string;
  pattern_type: string;
  description: string;
  frequency: number;
  success_rate: number;
  tools: string[];
  metadata: Record<string, unknown>;
}

export interface PatternDetectResponse {
  patterns: PatternRecord[];
  total_analyzed: number;
  generated_at: string;
}

export interface DatasetGenerateRequest {
  dataset_type: "task_response" | "tool_workflow" | "context_relevance" | "agent_decision";
  min_success_rate?: number;
}

export interface DatasetGenerateResponse {
  dataset_type: string;
  records: Record<string, unknown>[];
  total_records: number;
  generated_at: string;
}

export interface LearningMetrics {
  patterns_detected: number;
  total_trajectories: number;
  learning_enabled: boolean;
}

export function createLearningClient(service: GnosysService) {
  return {
    /**
     * Detect patterns from recent trajectories
     */
    async detectPatterns(trajectoryLimit: number = 100): Promise<PatternDetectResponse> {
      const response = await service.request("/learning/detect-patterns", {
        method: "POST",
        body: { trajectory_limit: trajectoryLimit },
      });
      return response as Promise<PatternDetectResponse>;
    },

    /**
     * Generate training dataset from successful trajectories
     */
    async generateDataset(request: DatasetGenerateRequest): Promise<DatasetGenerateResponse> {
      const response = await service.request("/learning/generate-dataset", {
        method: "POST",
        body: request,
      });
      return response as Promise<DatasetGenerateResponse>;
    },

    /**
     * Get learning system metrics
     */
    async getMetrics(): Promise<LearningMetrics> {
      const response = await service.request("/learning/metrics", {
        method: "GET",
      });
      return response as Promise<LearningMetrics>;
    },
  };
}
