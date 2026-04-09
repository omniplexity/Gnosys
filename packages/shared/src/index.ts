export type NavSection =
  | 'Chat'
  | 'Tasks'
  | 'Projects'
  | 'Agents'
  | 'Skills'
  | 'Scheduled'
  | 'Sessions'
  | 'Settings';

export type TaskStatus = 'Inbox' | 'Planned' | 'Running' | 'Waiting' | 'Needs Approval' | 'Completed' | 'Failed';
export type AgentStatus = 'Idle' | 'Working' | 'Waiting' | 'Reviewing';
export type ScheduleApprovalPolicy = 'inherit' | 'require_approval' | 'autonomous';
export type ScheduleFailurePolicy = 'retry_once' | 'fail_fast' | 'retry_twice';

export interface Task {
  id: string;
  project_id?: string | null;
  title: string;
  summary: string;
  status: TaskStatus;
  priority: 'Low' | 'Medium' | 'High' | 'Critical';
}

export interface Agent {
  id: string;
  name: string;
  role: string;
  status: AgentStatus;
}

export interface Project {
  id: string;
  name: string;
  summary: string;
  status: 'Active' | 'Planned' | 'Archived';
  owner: string;
  workspace_path: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectThread {
  id: string;
  project_id: string;
  title: string;
  summary: string;
  status: 'Open' | 'Paused' | 'Archived';
  context_path: string;
  created_at: string;
  updated_at: string;
}

export interface ChatSession {
  id: string;
  title: string;
  summary: string;
  status: 'Active' | 'Paused' | 'Archived';
  context_path: string;
  agent_path: string;
  soul_path: string;
  identity_path: string;
  heartbeat_path: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  chat_session_id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  kind: 'message' | 'event' | 'reflection';
  content: string;
  task_run_id?: string | null;
  agent_run_ids: string[];
  metadata?: Record<string, unknown>;
  created_at: string;
}

export type ChatContextMode = 'personal' | 'project' | 'project-thread';

export interface ChatAttachment {
  id: string;
  chat_session_id: string;
  mode: ChatContextMode;
  project_id?: string | null;
  project_thread_id?: string | null;
  original_name: string;
  stored_name: string;
  content_type: string;
  size_bytes: number;
  storage_path: string;
  created_at: string;
}

export interface OrchestrationStep {
  intent: string;
  objective: string;
  assigned_agent: string;
  approval_note: string;
  rationale: string;
  spawn_worker: boolean;
}

export interface OrchestrationDecision {
  intent_classification: string;
  execution_mode: 'answer-only' | 'task-created';
  delegated_specialists: string[];
  invoked_skills: string[];
  candidate_skills?: string[];
  routing_notes?: string[];
  approvals_triggered: boolean;
  synthesis: string;
}

export interface Skill {
  id: string;
  project_id?: string | null;
  parent_skill_id?: string | null;
  promoted_from_skill_id?: string | null;
  latest_test_run_id?: string | null;
  name: string;
  description: string;
  scope: 'workspace' | 'project' | 'session' | 'user';
  version: string;
  source_type: 'authored' | 'learned';
  status: 'draft' | 'candidate' | 'active' | 'deprecated' | 'archived';
  test_status?: 'untested' | 'passed' | 'failed';
  test_score?: number;
  test_summary?: string;
  provenance_summary?: string;
  evidence_count?: number;
  success_signals?: string[];
  invocation_hints?: string[];
  promotion_summary?: string;
  rollback_summary?: string;
  last_promoted_at?: string | null;
  last_rolled_back_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SkillEvidence {
  id: string;
  skill_id: string;
  task_run_id?: string | null;
  agent_run_id?: string | null;
  source_kind: string;
  pattern_signature: string;
  evidence_summary: string;
  success_score: number;
  created_at: string;
}

export interface Schedule {
  id: string;
  project_id?: string | null;
  name: string;
  target_type: 'task' | 'project' | 'skill' | 'orchestration';
  target_ref: string;
  schedule_expression: string;
  timezone: string;
  enabled: boolean;
  approval_policy: ScheduleApprovalPolicy;
  failure_policy: ScheduleFailurePolicy;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskRun {
  id: string;
  task_id: string;
  objective: string;
  requested_by: string;
  project_id: string | null;
  project_thread_id: string | null;
  chat_session_id: string | null;
  mode: string;
  status: string;
  summary: string;
  step_count: number;
  approval_required: boolean;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface AgentRun {
  id: string;
  agent_id: string;
  agent_name: string;
  agent_role: string;
  run_kind: string;
  status: string;
  objective: string;
  summary: string;
  parent_run_id: string | null;
  task_run_id: string;
  recursion_depth: number;
  child_count: number;
  budget_units: number;
  approval_required: boolean;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface MemoryLayer {
  id: string;
  name: string;
  description: string;
  score: number;
}

export type MemoryState = 'candidate' | 'validated' | 'archived';

export interface MemoryItem {
  id: string;
  layer: string;
  scope: 'workspace' | 'project' | 'session' | 'user';
  project_id?: string | null;
  state: MemoryState;
  pinned?: boolean;
  title: string;
  summary: string;
  confidence: number;
  freshness: number;
  provenance: string;
  tags: string[];
}

export interface MemoryRetrievalStep {
  stage: string;
  detail: string;
}

export interface MemoryRetrievalResult {
  query: string;
  scope: string | null;
  role: string;
  items: MemoryItem[];
  trace: MemoryRetrievalStep[];
}

export interface MemoryContradiction {
  signature: string;
  item_count: number;
  item_ids: string[];
  item_titles: string[];
  item_states: string[];
  pinned_item_id: string | null;
  winner_item_id: string | null;
  recommended_resolution: string;
  reason: string;
}

export interface MemoryBrowseResult {
  query: string | null;
  project_id: string | null;
  total_count: number;
  daily_memories: MemoryItem[];
  long_term_memories: MemoryItem[];
  pinned_memories: MemoryItem[];
  candidate_memories: Array<
    MemoryItem & {
      score?: number;
      reason?: string | null;
      recommended_action?: string | null;
      review_reason?: string | null;
      signature?: string | null;
      conflict_count?: number | null;
    }
  >;
  contradictions: MemoryContradiction[];
}

export interface WorkspaceSummary {
  name: string;
  mode: 'Manual' | 'Supervised' | 'Autonomous' | 'Full Access';
  autonomy_mode: 'Manual' | 'Supervised' | 'Autonomous' | 'Full Access';
  kill_switch: boolean;
  approval_bias: string;
  mode_label: string;
  status: 'Bootstrapping' | 'Healthy' | 'Degraded';
  active_project: string;
  phase: string;
}

export const navSections: NavSection[] = [
  'Chat',
  'Tasks',
  'Projects',
  'Agents',
  'Skills',
  'Scheduled',
  'Sessions',
  'Settings'
];

export const scheduleApprovalPolicies: ScheduleApprovalPolicy[] = ['inherit', 'require_approval', 'autonomous'];
export const scheduleFailurePolicies: ScheduleFailurePolicy[] = ['retry_once', 'fail_fast', 'retry_twice'];

export const workspaceSummary: WorkspaceSummary = {
  name: 'Gnosys',
  mode: 'Supervised',
  autonomy_mode: 'Supervised',
  kill_switch: false,
  approval_bias: 'supervised',
  mode_label: 'Global autonomy and approval policy',
  status: 'Bootstrapping',
  active_project: 'Core Console',
  phase: 'Orchestration runtime foundation'
};

export interface ScheduleRun {
  id: string;
  schedule_id: string;
  schedule_name: string;
  target_type: string;
  target_ref: string;
  status: string;
  attempt_number: number;
  retry_of_run_id: string | null;
  task_run_id: string | null;
  requested_by: string;
  result_summary: string;
  last_error: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface TimelineEntry {
  kind: string;
  label: string;
  detail: string;
  created_at: string;
  source_id: string | null;
}

export interface RunComparison {
  previous_task_run_id: string | null;
  status_changed: boolean;
  summary_changed: boolean;
  step_count_delta: number;
  approval_required_changed: boolean;
  task_summary_changed: boolean;
  agent_run_count_delta: number;
  schedule_run_count_delta: number;
  timeline_entry_count_delta: number;
}

export interface ApprovalRequest {
  id: string;
  action: string;
  subject_type: string;
  subject_ref: string;
  sensitivity: string;
  status: string;
  reason: string;
  payload: Record<string, unknown>;
  requested_by: string;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
}

export interface EntityPolicy {
  entity_type: string;
  entity_id: string;
  project_id: string | null;
  autonomy_mode: string;
  kill_switch: boolean;
  approval_bias: string;
  created_at: string;
  updated_at: string;
}

export interface RecentEvent {
  id: number;
  type: string;
  source: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface WorkspaceCounts {
  tasks: number;
  agents: number;
  projects: number;
  project_threads: number;
  chat_sessions: number;
  skills: number;
  schedules: number;
  memory_layers: number;
  memory_items: number;
  skill_test_runs: number;
  task_runs: number;
  agent_runs: number;
  schedule_runs: number;
  approval_requests: number;
  entity_policies: number;
  events: number;
}

export interface WorkspaceSnapshot {
  workspace: WorkspaceSummary;
  tasks: Task[];
  agents: Agent[];
  projects: Project[];
  project_threads: ProjectThread[];
  chat_sessions: ChatSession[];
  skills: Skill[];
  schedules: Schedule[];
  memory_layers: MemoryLayer[];
  memory_items: MemoryItem[];
  task_runs: TaskRun[];
  agent_runs: AgentRun[];
  schedule_runs: ScheduleRun[];
  timeline: TimelineEntry[];
  comparison: RunComparison | null;
  approval_requests: ApprovalRequest[];
  entity_policies: EntityPolicy[];
  recent_events: RecentEvent[];
  counts: WorkspaceCounts;
}

export const seedTasks: Task[] = [
  {
    id: 'task-001',
    title: 'Desktop shell scaffold',
    summary: 'Build the main console layout and navigation.',
    status: 'Running',
    priority: 'Critical'
  },
  {
    id: 'task-002',
    title: 'Backend API scaffold',
    summary: 'Expose health and metadata endpoints.',
    status: 'Planned',
    priority: 'High'
  },
  {
    id: 'task-003',
    title: 'Shared domain models',
    summary: 'Centralize workspace and task definitions.',
    status: 'Waiting',
    priority: 'Medium'
  }
];

export const seedAgents: Agent[] = [
  { id: 'agent-001', name: 'Orchestrator', role: 'Control loop and task routing', status: 'Working' },
  { id: 'agent-002', name: 'Planner', role: 'Task decomposition and sequencing', status: 'Reviewing' },
  { id: 'agent-003', name: 'Research Specialist', role: 'Research and retrieval', status: 'Idle' },
  { id: 'agent-004', name: 'Builder Specialist', role: 'Coding and implementation', status: 'Idle' },
  { id: 'agent-005', name: 'Memory Steward', role: 'Memory policies and write-back', status: 'Idle' },
  { id: 'agent-006', name: 'Critic / Evaluator', role: 'Review and validation', status: 'Idle' },
  { id: 'agent-007', name: 'Operations / Scheduler', role: 'Scheduling and control', status: 'Idle' }
];

export const seedProjects: Project[] = [
  {
    id: 'project-001',
    name: 'Core Console',
    summary: 'Foundation workspace for the desktop, backend, memory, and orchestration layers.',
    status: 'Active',
    owner: 'Gnosys',
    workspace_path: 'C:/Users/storm/Desktop/Gnosys/workspaces/core-console',
    created_at: '2026-04-06T00:00:00Z',
    updated_at: '2026-04-06T00:00:00Z'
  },
  {
    id: 'project-002',
    name: 'Phase 4 CRUD',
    summary: 'Implement editable surfaces for tasks, projects, agents, skills, and schedules.',
    status: 'Planned',
    owner: 'Gnosys',
    workspace_path: 'C:/Users/storm/Desktop/Gnosys/workspaces/phase-4-crud',
    created_at: '2026-04-06T00:00:00Z',
    updated_at: '2026-04-06T00:00:00Z'
  }
];

export const seedProjectThreads: ProjectThread[] = [
  {
    id: 'thread-001',
    project_id: 'project-001',
    title: 'Core runtime planning',
    summary: 'Track execution design and storage work for the core console.',
    status: 'Open',
    context_path: 'C:/Users/storm/Desktop/Gnosys/workspaces/core-console/threads/core-runtime-planning',
    created_at: '2026-04-06T00:00:00Z',
    updated_at: '2026-04-06T00:00:00Z'
  }
];

export const seedChatSessions: ChatSession[] = [
  {
    id: 'session-001',
    title: 'Main agent thread',
    summary: 'Default non-project orchestration conversation.',
    status: 'Active',
    context_path: 'C:/Users/storm/Desktop/Gnosys/agent/main-thread',
    agent_path: 'C:/Users/storm/Desktop/Gnosys/agent/main-thread/AGENT.md',
    soul_path: 'C:/Users/storm/Desktop/Gnosys/agent/main-thread/SOUL.md',
    identity_path: 'C:/Users/storm/Desktop/Gnosys/agent/main-thread/IDENTITY.md',
    heartbeat_path: 'C:/Users/storm/Desktop/Gnosys/agent/main-thread/HEARTBEAT.md',
    created_at: '2026-04-06T00:00:00Z',
    updated_at: '2026-04-06T00:00:00Z'
  }
];

export const seedSkills: Skill[] = [
  {
    id: 'skill-001',
    name: 'Persistence Inspector',
    description: 'Inspect SQLite state, event logs, and runtime runs for consistency.',
    scope: 'workspace',
    version: '0.1.0',
    source_type: 'authored',
    status: 'active',
    test_status: 'passed',
    test_score: 0.97,
    test_summary: 'Stable authored skill in active use.',
    created_at: '2026-04-06T00:00:00Z',
    updated_at: '2026-04-06T00:00:00Z'
  },
  {
    id: 'skill-002',
    name: 'Run Planner',
    description: 'Decompose objectives into bounded steps and specialist responsibilities.',
    scope: 'workspace',
    version: '0.1.0',
    source_type: 'authored',
    status: 'active',
    test_status: 'passed',
    test_score: 0.95,
    test_summary: 'Stable authored skill in active use.',
    created_at: '2026-04-06T00:00:00Z',
    updated_at: '2026-04-06T00:00:00Z'
  }
];

export const seedSchedules: Schedule[] = [
  {
    id: 'schedule-001',
    project_id: 'project-001',
    name: 'Daily integrity check',
    target_type: 'skill',
    target_ref: 'skill-001',
    schedule_expression: 'FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=9;BYMINUTE=0',
    timezone: 'America/New_York',
    enabled: true,
    approval_policy: 'inherit',
    failure_policy: 'retry_once',
    last_run_at: null,
    next_run_at: null,
    created_at: '2026-04-06T00:00:00Z',
    updated_at: '2026-04-06T00:00:00Z'
  }
];

export const seedMemoryLayers: MemoryLayer[] = [
  {
    id: 'memory-active',
    name: 'Active Context',
    description: 'In-flight session context and immediate working state.',
    score: 0.95
  },
  {
    id: 'memory-episodic',
    name: 'Episodic',
    description: 'Task episodes, decisions, and prior runs.',
    score: 0.88
  },
  {
    id: 'memory-semantic',
    name: 'Semantic',
    description: 'Normalized facts and stable workspace knowledge.',
    score: 0.91
  }
];

export const seedMemoryItems: MemoryItem[] = [
  {
    id: 'memory-item-001',
    layer: 'Active Context',
    scope: 'session',
    state: 'validated',
    pinned: true,
    title: 'Phase 1 completed',
    summary: 'SQLite persistence and append-only event logging are live in the backend.',
    confidence: 0.99,
    freshness: 0.96,
    provenance: 'phase-1-commit',
    tags: ['persistence', 'events', 'backend']
  },
  {
    id: 'memory-item-002',
    layer: 'Semantic',
    scope: 'workspace',
    state: 'validated',
    pinned: false,
    title: 'Phase 2 target',
    summary: 'Build the memory engine with scoped retrieval and explanation traces.',
    confidence: 0.94,
    freshness: 0.9,
    provenance: 'roadmap',
    tags: ['memory', 'retrieval', 'trace']
  },
  {
    id: 'memory-item-003',
    layer: 'Episodic',
    scope: 'project',
    state: 'candidate',
    pinned: false,
    title: 'Retrieval audit note',
    summary: 'Inspect why a memory item was surfaced before it becomes durable.',
    confidence: 0.78,
    freshness: 0.84,
    provenance: 'design-note',
    tags: ['inspectability', 'candidate', 'retrieval']
  }
];
