import type { AgentRun, ChatAttachment, ChatContextMode, ChatMessage, ChatSession, MemoryBrowseResult, MemoryItem, OrchestrationDecision, OrchestrationStep, ProjectThread, Skill, Task, TaskRun, WorkspaceSnapshot } from '@gnosys/shared';
import { readErrorDetail } from './lib/errors';

export type MemoryRetrievalResult = {
  query: string;
  scope: string | null;
  role: string;
  items: Array<
    MemoryItem & {
      score: number;
      reason: string;
    }
  >;
  trace: Array<{ stage: string; detail: string }>;
};

export type LaunchResponse = {
  task: Task;
  task_run: TaskRun;
  agent_runs: AgentRun[];
  steps: OrchestrationStep[];
  approvals_required: string[];
  summary: string;
  decision: OrchestrationDecision;
};

export type ChatSendResponse = {
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  generated_messages: ChatMessage[];
  task_run: TaskRun | null;
  agent_runs: AgentRun[];
  approval_request: {
    id: string;
    action: string;
    status: string;
    reason: string;
  } | null;
  decision: OrchestrationDecision;
};

export type PolicyUpdateResponse = {
  autonomy_mode: string;
  kill_switch: boolean;
  approval_bias: string;
  mode_label: string;
};

export type EntityPolicyRecord = {
  entity_type: string;
  entity_id: string;
  autonomy_mode: string;
  kill_switch: boolean;
  approval_bias: string;
  created_at: string;
  updated_at: string;
};

export type ReplayResponse = {
  task_run: TaskRun;
  agent_runs: AgentRun[];
  events: Array<{
    id: number;
    type: string;
    source: string;
    payload: Record<string, unknown>;
    created_at: string;
  }>;
  timeline: WorkspaceSnapshot['timeline'];
  comparison: WorkspaceSnapshot['comparison'];
  schedule_runs: WorkspaceSnapshot['schedule_runs'];
};

export type DiagnosticsRunListResponse = {
  task_runs: TaskRun[];
  query: string | null;
  status: string | null;
  approval_required: boolean | null;
  total_count: number;
  filtered_count: number;
  metrics: {
    total_task_runs: number;
    filtered_task_runs: number;
    total_agent_runs: number;
    total_schedule_runs: number;
    completed_task_runs: number;
    failed_task_runs: number;
    approval_required_task_runs: number;
  };
};

export type MemoryReviewResponse = {
  candidate_count: number;
  pinned_count: number;
  contradiction_count: number;
  items: Array<
    MemoryItem & {
      score: number;
      reason: string;
      recommended_action: string | null;
      review_reason: string | null;
      signature: string | null;
      conflict_count: number | null;
    }
  >;
  contradictions: Array<{
    signature: string;
    item_count: number;
    item_ids: string[];
    item_titles: string[];
    item_states: string[];
    pinned_item_id: string | null;
    winner_item_id: string | null;
    recommended_resolution: string;
    reason: string;
  }>;
};

export type MemoryBrowserResponse = MemoryBrowseResult;

export type SkillTestRunResponse = {
  id: string;
  skill_id: string;
  scenario: string;
  expected_outcome: string;
  observed_outcome: string;
  passed: boolean;
  score: number;
  summary: string;
  requested_by: string;
  created_at: string;
};

export type SkillLifecycleResponse = {
  skill: Skill;
  parent_skill: Skill | null;
  related_skills: Skill[];
  evidence: Array<{
    id: string;
    skill_id: string;
    task_run_id: string | null;
    agent_run_id: string | null;
    source_kind: string;
    pattern_signature: string;
    evidence_summary: string;
    success_score: number;
    created_at: string;
  }>;
  test_runs: SkillTestRunResponse[];
  lifecycle_state: string;
  ready_for_promotion: boolean;
};

export type SkillLearnResponse = {
  created_skills: Skill[];
  analyzed_runs: number;
  repeated_patterns: number;
  skipped_patterns: number;
};

async function requestJson<T>(url: string, fallback: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, fallback));
  }
  return (await response.json()) as T;
}

export function loadSnapshot(): Promise<WorkspaceSnapshot> {
  return requestJson<WorkspaceSnapshot>('/api/state', 'Failed to load state');
}

export async function retrieveMemory(query: string, role: string, scope: string | null, projectId: string | null): Promise<MemoryRetrievalResult> {
  const params = new URLSearchParams({ query, role });
  if (scope) {
    params.set('scope', scope);
  }
  if (projectId) {
    params.set('project_id', projectId);
  }
  return requestJson<MemoryRetrievalResult>(`/api/memory/retrieve?${params.toString()}`, 'Failed to retrieve memory');
}

export async function loadMemoryBrowser(query: string, projectId: string | null, limit = 12): Promise<MemoryBrowserResponse> {
  const params = new URLSearchParams();
  if (query.trim()) {
    params.set('query', query.trim());
  }
  if (projectId) {
    params.set('project_id', projectId);
  }
  params.set('limit', String(limit));
  return requestJson<MemoryBrowserResponse>(`/api/memory/browser?${params.toString()}`, 'Failed to load memory browser');
}

export function launchOrchestration(
  objective: string,
  mode: string,
  taskId?: string,
  context?: { project_id?: string | null; project_thread_id?: string | null; chat_session_id?: string | null }
): Promise<LaunchResponse> {
  return requestJson<LaunchResponse>('/api/orchestration/launch', 'Failed to launch orchestration', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      objective,
      task_title: objective.slice(0, 48),
      task_summary: objective,
      task_id: taskId,
      project_id: context?.project_id ?? null,
      project_thread_id: context?.project_thread_id ?? null,
      chat_session_id: context?.chat_session_id ?? null,
      requested_by: 'desktop',
      mode,
      priority: 'High'
    })
  });
}

export function createProjectThread(payload: {
  project_id: string;
  title: string;
  summary?: string;
  status?: string;
}): Promise<ProjectThread> {
  return requestJson<ProjectThread>('/api/project-threads', 'Failed to create project thread', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
}

export function createChatSession(payload: {
  title: string;
  summary?: string;
  status?: string;
}): Promise<ChatSession> {
  return requestJson<ChatSession>('/api/chat-sessions', 'Failed to create chat session', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
}

export function loadChatMessages(sessionId: string): Promise<ChatMessage[]> {
  return requestJson<ChatMessage[]>(`/api/chat-sessions/${sessionId}/messages`, 'Failed to load chat messages');
}

export function sendChatMessage(
  sessionId: string,
  payload: {
    content: string;
    selected_model?: string;
    reasoning_strength?: string;
    requested_by?: string;
    mode?: ChatContextMode;
    project_id?: string | null;
    project_thread_id?: string | null;
    attachment_ids?: string[];
  }
): Promise<ChatSendResponse> {
  return requestJson<ChatSendResponse>(`/api/chat-sessions/${sessionId}/send`, 'Failed to send chat message', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      content: payload.content,
      selected_model: payload.selected_model ?? null,
      reasoning_strength: payload.reasoning_strength ?? null,
      requested_by: payload.requested_by ?? 'desktop',
      mode: payload.mode ?? 'personal',
      project_id: payload.project_id ?? null,
      project_thread_id: payload.project_thread_id ?? null,
      attachment_ids: payload.attachment_ids ?? [],
    })
  });
}

export function loadChatAttachments(sessionId: string): Promise<ChatAttachment[]> {
  return requestJson<ChatAttachment[]>(`/api/chat-sessions/${sessionId}/attachments`, 'Failed to load chat attachments');
}

export async function uploadChatAttachment(
  sessionId: string,
  payload: {
    file: File;
    mode?: ChatContextMode;
    project_id?: string | null;
    project_thread_id?: string | null;
  }
): Promise<ChatAttachment> {
  const formData = new FormData();
  formData.set('file', payload.file);
  formData.set('mode', payload.mode ?? 'personal');
  if (payload.project_id) {
    formData.set('project_id', payload.project_id);
  }
  if (payload.project_thread_id) {
    formData.set('project_thread_id', payload.project_thread_id);
  }
  const response = await fetch(`/api/chat-sessions/${sessionId}/attachments`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, 'Failed to upload chat attachment'));
  }
  return (await response.json()) as ChatAttachment;
}

export function updatePolicy(payload: {
  autonomy_mode?: string;
  kill_switch?: boolean;
  approval_bias?: string;
}): Promise<PolicyUpdateResponse> {
  return requestJson<PolicyUpdateResponse>('/api/policy', 'Failed to update policy', {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
}

export function updateEntityPolicy(entityType: string, entityId: string, payload: {
  autonomy_mode?: string;
  kill_switch?: boolean;
  approval_bias?: string;
}): Promise<EntityPolicyRecord> {
  return requestJson<EntityPolicyRecord>(`/api/policies/entities/${entityType}/${entityId}`, 'Failed to update entity policy', {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
}

export function runSchedule(scheduleId: string): Promise<{ id: string }> {
  return requestJson<{ id: string }>(`/api/schedules/${scheduleId}/run`, 'Failed to run schedule', { method: 'POST' });
}

export function retryScheduleRun(runId: string): Promise<{ id: string }> {
  return requestJson<{ id: string }>(`/api/schedule-runs/${runId}/retry`, 'Failed to retry schedule run', { method: 'POST' });
}

export function loadReplay(taskRunId: string): Promise<ReplayResponse> {
  return requestJson<ReplayResponse>(`/api/diagnostics/replay/${taskRunId}`, 'Failed to load replay');
}

export async function loadDiagnosticsRuns(filters: {
  query?: string;
  status?: string;
  approvalRequired?: string;
  projectId?: string;
  projectThreadId?: string;
  chatSessionId?: string;
  limit?: number;
} = {}): Promise<DiagnosticsRunListResponse> {
  const params = new URLSearchParams();
  if (filters.query) {
    params.set('query', filters.query);
  }
  if (filters.status) {
    params.set('status', filters.status);
  }
  if (filters.approvalRequired === 'true') {
    params.set('approval_required', 'true');
  } else if (filters.approvalRequired === 'false') {
    params.set('approval_required', 'false');
  }
  if (filters.projectId) {
    params.set('project_id', filters.projectId);
  }
  if (filters.projectThreadId) {
    params.set('project_thread_id', filters.projectThreadId);
  }
  if (filters.chatSessionId) {
    params.set('chat_session_id', filters.chatSessionId);
  }
  params.set('limit', String(filters.limit ?? 20));
  return requestJson<DiagnosticsRunListResponse>(`/api/diagnostics/runs?${params.toString()}`, 'Failed to load diagnostics runs');
}

export function loadMemoryReview(): Promise<MemoryReviewResponse> {
  return requestJson<MemoryReviewResponse>('/api/memory/review', 'Failed to load memory review');
}

export function loadSkillLifecycle(skillId: string): Promise<SkillLifecycleResponse> {
  return requestJson<SkillLifecycleResponse>(`/api/skills/${skillId}/lifecycle`, 'Failed to load skill lifecycle');
}

export function createSkillDraft(skillId: string): Promise<Skill> {
  return requestJson<Skill>(`/api/skills/${skillId}/draft?requested_by=desktop`, 'Failed to create skill draft', {
    method: 'POST'
  });
}

export function learnSkills(limit = 12): Promise<SkillLearnResponse> {
  return requestJson<SkillLearnResponse>('/api/skills/learn', 'Failed to derive learned skills', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      limit,
      requested_by: 'desktop'
    })
  });
}

export function testSkill(skillId: string, payload: { scenario: string; expected_outcome: string; requested_by?: string }): Promise<SkillTestRunResponse> {
  return requestJson<SkillTestRunResponse>(`/api/skills/${skillId}/test`, 'Failed to test skill', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      scenario: payload.scenario,
      expected_outcome: payload.expected_outcome,
      requested_by: payload.requested_by ?? 'desktop'
    })
  });
}

export function promoteSkill(skillId: string): Promise<Skill> {
  return requestJson<Skill>(`/api/skills/${skillId}/promote?requested_by=desktop`, 'Failed to promote skill', {
    method: 'POST'
  });
}

export function rollbackSkill(skillId: string): Promise<Skill> {
  return requestJson<Skill>(`/api/skills/${skillId}/rollback?requested_by=desktop`, 'Failed to roll back skill', {
    method: 'POST'
  });
}

export function promoteMemoryItem(itemId: string): Promise<MemoryItem> {
  return requestJson<MemoryItem>(`/api/memory/items/${itemId}/promote`, 'Failed to promote memory item', { method: 'POST' });
}

export function archiveMemoryItem(itemId: string): Promise<MemoryItem> {
  return requestJson<MemoryItem>(`/api/memory/items/${itemId}/archive`, 'Failed to archive memory item', { method: 'POST' });
}

export function pinMemoryItem(itemId: string): Promise<MemoryItem> {
  return requestJson<MemoryItem>(`/api/memory/items/${itemId}/pin`, 'Failed to pin memory item', { method: 'POST' });
}

export function forgetMemoryItem(itemId: string): Promise<MemoryItem> {
  return requestJson<MemoryItem>(`/api/memory/items/${itemId}/forget`, 'Failed to forget memory item', { method: 'POST' });
}

export function resolveApproval(approvalId: string, status: 'approved' | 'rejected'): Promise<{ id: string; status: string }> {
  return requestJson<{ id: string; status: string }>(`/api/approvals/${approvalId}/resolve`, 'Failed to resolve approval', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ status, resolved_by: 'desktop' })
  });
}

export function saveCrudResource(endpoint: string, selectionId: string, payload: Record<string, unknown>, creating: boolean): Promise<{ id: string }> {
  const requestUrl = creating ? endpoint : `${endpoint}/${selectionId}`;
  return requestJson<{ id: string }>(requestUrl, 'Failed to save resource', {
    method: creating ? 'POST' : 'PATCH',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
}

export async function deleteCrudResource(endpoint: string, selectionId: string): Promise<void> {
  const response = await fetch(`${endpoint}/${selectionId}`, {
    method: 'DELETE'
  });
  if (!response.ok && response.status !== 204) {
    throw new Error(await readErrorDetail(response, 'Failed to delete resource'));
  }
}

export async function appendEvent(payload: {
  type: string;
  source: string;
  payload: Record<string, unknown>;
}): Promise<void> {
  const response = await fetch('/api/events', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(`Failed to record event: ${response.status}`);
  }
}
