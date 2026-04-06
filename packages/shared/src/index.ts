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
