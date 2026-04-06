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

export interface Task {
  id: string;
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
  state: MemoryState;
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

export interface WorkspaceSummary {
  name: string;
  mode: 'Manual' | 'Supervised' | 'Autonomous';
  status: 'Bootstrapping' | 'Healthy' | 'Degraded';
  activeProject: string;
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

export const workspaceSummary: WorkspaceSummary = {
  name: 'Gnosys',
  mode: 'Supervised',
  status: 'Bootstrapping',
  activeProject: 'Core Console'
};

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
  { id: 'agent-003', name: 'Memory Steward', role: 'Memory policies and write-back', status: 'Idle' }
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
    title: 'Retrieval audit note',
    summary: 'Inspect why a memory item was surfaced before it becomes durable.',
    confidence: 0.78,
    freshness: 0.84,
    provenance: 'design-note',
    tags: ['inspectability', 'candidate', 'retrieval']
  }
];
