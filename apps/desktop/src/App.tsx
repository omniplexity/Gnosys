import {
  navSections,
  seedAgents,
  seedMemoryItems,
  seedMemoryLayers,
  seedProjects,
  seedSchedules,
  seedSkills,
  seedTasks,
  workspaceSummary,
  type Agent,
  type AgentRun,
  type MemoryItem,
  type MemoryLayer,
  type Project,
  type Schedule,
  type Skill,
  type Task,
  type TaskRun
} from '@gnosys/shared';
import { useEffect, useMemo, useState } from 'react';

const bottomTabs = ['Logs', 'Timeline', 'Trace'] as const;

type WorkspaceSnapshot = {
  workspace: {
    name: string;
    mode: string;
    autonomy_mode: string;
    kill_switch: boolean;
    approval_bias: string;
    mode_label: string;
    status: string;
    active_project: string;
    phase: string;
  };
  tasks: Task[];
  agents: Agent[];
  projects: Project[];
  skills: Skill[];
  schedules: Schedule[];
  memory_layers: MemoryLayer[];
  memory_items: MemoryItem[];
  task_runs: TaskRun[];
  agent_runs: AgentRun[];
  schedule_runs: Array<{
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
  }>;
  approval_requests: Array<{
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
  }>;
  entity_policies: Array<{
    entity_type: string;
    entity_id: string;
    autonomy_mode: string;
    kill_switch: boolean;
    approval_bias: string;
    created_at: string;
    updated_at: string;
  }>;
  recent_events: Array<{
    id: number;
    type: string;
    source: string;
    payload: Record<string, unknown>;
    created_at: string;
  }>;
  counts: {
    tasks: number;
    agents: number;
    projects: number;
    skills: number;
    schedules: number;
    memory_layers: number;
    memory_items: number;
    task_runs: number;
    agent_runs: number;
    schedule_runs: number;
    approval_requests: number;
    entity_policies: number;
    events: number;
  };
};

type MemoryRetrievalResult = {
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

type LaunchResponse = {
  task: Task;
  task_run: TaskRun;
  agent_runs: AgentRun[];
  steps: Array<{ intent: string; objective: string; assigned_agent: string; approval_note: string }>;
  approvals_required: string[];
  summary: string;
};

type CrudDraft = Record<string, string | boolean>;

type PolicyUpdateResponse = {
  autonomy_mode: string;
  kill_switch: boolean;
  approval_bias: string;
  mode_label: string;
};

type EntityPolicyRecord = {
  entity_type: string;
  entity_id: string;
  autonomy_mode: string;
  kill_switch: boolean;
  approval_bias: string;
  created_at: string;
  updated_at: string;
};

type ReplayResponse = {
  task_run: TaskRun;
  agent_runs: AgentRun[];
  events: Array<{
    id: number;
    type: string;
    source: string;
    payload: Record<string, unknown>;
    created_at: string;
  }>;
  schedule_runs: WorkspaceSnapshot['schedule_runs'];
};

const fallbackSnapshot: WorkspaceSnapshot = {
  workspace: {
    name: workspaceSummary.name,
    mode: workspaceSummary.mode,
    autonomy_mode: 'Supervised',
    kill_switch: false,
    approval_bias: 'supervised',
    mode_label: 'Global autonomy and approval policy',
    status: workspaceSummary.status,
    active_project: workspaceSummary.activeProject,
    phase: 'Orchestration runtime foundation'
  },
  tasks: seedTasks,
  agents: seedAgents,
  projects: seedProjects,
  skills: seedSkills,
  schedules: seedSchedules,
  memory_layers: seedMemoryLayers,
  memory_items: seedMemoryItems,
  task_runs: [],
  agent_runs: [],
  schedule_runs: [],
  approval_requests: [],
  entity_policies: [],
  recent_events: [],
  counts: {
    tasks: seedTasks.length,
    agents: seedAgents.length,
    projects: seedProjects.length,
    skills: seedSkills.length,
    schedules: seedSchedules.length,
    memory_layers: seedMemoryLayers.length,
    memory_items: seedMemoryItems.length,
    task_runs: 0,
    agent_runs: 0,
    schedule_runs: 0,
    approval_requests: 0,
    entity_policies: 0,
    events: 0
  }
};

type CrudKind = 'tasks' | 'projects' | 'agents' | 'skills' | 'schedules';
const NEW_ITEM_SENTINEL = '__new__';

const crudKinds: CrudKind[] = ['tasks', 'projects', 'agents', 'skills', 'schedules'];

async function loadSnapshot(): Promise<WorkspaceSnapshot> {
  const response = await fetch('/api/state');
  if (!response.ok) {
    throw new Error(`Failed to load state: ${response.status}`);
  }
  return (await response.json()) as WorkspaceSnapshot;
}

async function retrieveMemory(query: string, role: string, scope: string | null, projectId: string | null): Promise<MemoryRetrievalResult> {
  const params = new URLSearchParams({
    query,
    role
  });
  if (scope) {
    params.set('scope', scope);
  }
  if (projectId) {
    params.set('project_id', projectId);
  }

  const response = await fetch(`/api/memory/retrieve?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`Failed to retrieve memory: ${response.status}`);
  }
  return (await response.json()) as MemoryRetrievalResult;
}

async function launchOrchestration(objective: string, mode: string): Promise<LaunchResponse> {
  const response = await fetch('/api/orchestration/launch', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      objective,
      task_title: objective.slice(0, 48),
      task_summary: objective,
      requested_by: 'desktop',
      mode,
      priority: 'High'
    })
  });

  if (!response.ok) {
    throw new Error(await readErrorDetail(response, `Failed to launch orchestration: ${response.status}`));
  }

  return (await response.json()) as LaunchResponse;
}

async function readErrorDetail(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: { message?: string } | string };
    if (typeof body.detail === 'string') {
      return body.detail;
    }
    if (body.detail && typeof body.detail.message === 'string') {
      return body.detail.message;
    }
  } catch {
    return fallback;
  }
  return fallback;
}

async function updatePolicy(payload: {
  autonomy_mode?: string;
  kill_switch?: boolean;
  approval_bias?: string;
}): Promise<PolicyUpdateResponse> {
  const response = await fetch('/api/policy', {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await readErrorDetail(response, `Failed to update policy: ${response.status}`));
  }

  return (await response.json()) as PolicyUpdateResponse;
}

async function updateEntityPolicy(entityType: string, entityId: string, payload: {
  autonomy_mode?: string;
  kill_switch?: boolean;
  approval_bias?: string;
}): Promise<EntityPolicyRecord> {
  const response = await fetch(`/api/policies/entities/${entityType}/${entityId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await readErrorDetail(response, `Failed to update entity policy: ${response.status}`));
  }

  return (await response.json()) as EntityPolicyRecord;
}

async function runSchedule(scheduleId: string): Promise<{ id: string }> {
  const response = await fetch(`/api/schedules/${scheduleId}/run`, {
    method: 'POST'
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, `Failed to run schedule: ${response.status}`));
  }
  return (await response.json()) as { id: string };
}

async function retryScheduleRun(runId: string): Promise<{ id: string }> {
  const response = await fetch(`/api/schedule-runs/${runId}/retry`, {
    method: 'POST'
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, `Failed to retry schedule run: ${response.status}`));
  }
  return (await response.json()) as { id: string };
}

async function loadReplay(taskRunId: string): Promise<ReplayResponse> {
  const response = await fetch(`/api/diagnostics/replay/${taskRunId}`);
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, `Failed to load replay: ${response.status}`));
  }
  return (await response.json()) as ReplayResponse;
}

function buildRunTree(agentRuns: AgentRun[]): AgentRun[] {
  return agentRuns.slice().sort((left, right) => {
    if (left.recursion_depth !== right.recursion_depth) {
      return left.recursion_depth - right.recursion_depth;
    }
    return left.created_at.localeCompare(right.created_at);
  });
}

function getCrudItems(snapshot: WorkspaceSnapshot, kind: CrudKind): Array<Record<string, unknown> & { id: string }> {
  switch (kind) {
    case 'tasks':
      return snapshot.tasks as unknown as Array<Record<string, unknown> & { id: string }>;
    case 'projects':
      return snapshot.projects as unknown as Array<Record<string, unknown> & { id: string }>;
    case 'agents':
      return snapshot.agents as unknown as Array<Record<string, unknown> & { id: string }>;
    case 'skills':
      return snapshot.skills as unknown as Array<Record<string, unknown> & { id: string }>;
    case 'schedules':
      return snapshot.schedules as unknown as Array<Record<string, unknown> & { id: string }>;
  }
}

function buildCrudDraft(kind: CrudKind, item: unknown): CrudDraft {
  if (!item || typeof item !== 'object') {
    return {};
  }
  return { ...item } as CrudDraft;
}

function normalizeCrudDraft(kind: CrudKind, draft: CrudDraft): Record<string, unknown> {
  switch (kind) {
    case 'tasks':
      return {
        title: String(draft.title ?? ''),
        summary: String(draft.summary ?? ''),
        status: String(draft.status ?? 'Inbox'),
        priority: String(draft.priority ?? 'Medium'),
        project_id: draft.project_id ? String(draft.project_id) : null
      };
    case 'projects':
      return {
        name: String(draft.name ?? ''),
        summary: String(draft.summary ?? ''),
        status: String(draft.status ?? 'Planned'),
        owner: String(draft.owner ?? 'Gnosys')
      };
    case 'agents':
      return {
        name: String(draft.name ?? ''),
        role: String(draft.role ?? ''),
        status: String(draft.status ?? 'Idle')
      };
    case 'skills':
      return {
        name: String(draft.name ?? ''),
        description: String(draft.description ?? ''),
        scope: String(draft.scope ?? 'workspace'),
        version: String(draft.version ?? '0.1.0'),
        source_type: String(draft.source_type ?? 'authored'),
        status: String(draft.status ?? 'draft'),
        project_id: draft.project_id ? String(draft.project_id) : null
      };
    case 'schedules':
      return {
        name: String(draft.name ?? ''),
        target_type: String(draft.target_type ?? 'skill'),
        target_ref: String(draft.target_ref ?? ''),
        schedule_expression: String(draft.schedule_expression ?? ''),
        timezone: String(draft.timezone ?? 'America/New_York'),
        enabled: Boolean(draft.enabled),
        last_run_at: draft.last_run_at ? String(draft.last_run_at) : null,
        next_run_at: draft.next_run_at ? String(draft.next_run_at) : null,
        project_id: draft.project_id ? String(draft.project_id) : null
      };
  }
}

function crudConfig(kind: CrudKind) {
  switch (kind) {
    case 'tasks':
      return {
        title: 'Tasks',
        createLabel: 'Create task',
        endpoint: '/api/tasks'
      };
    case 'projects':
      return {
        title: 'Projects',
        createLabel: 'Create project',
        endpoint: '/api/projects'
      };
    case 'agents':
      return {
        title: 'Agents',
        createLabel: 'Create agent',
        endpoint: '/api/agents'
      };
    case 'skills':
      return {
        title: 'Skills',
        createLabel: 'Create skill',
        endpoint: '/api/skills'
      };
    case 'schedules':
      return {
        title: 'Schedules',
        createLabel: 'Create schedule',
        endpoint: '/api/schedules'
      };
  }
}

export default function App() {
  const [activeSection, setActiveSection] = useState(navSections[0]);
  const [activeTask, setActiveTask] = useState(seedTasks[0].id);
  const [activeTab, setActiveTab] = useState<(typeof bottomTabs)[number]>('Logs');
  const [snapshot, setSnapshot] = useState<WorkspaceSnapshot>(fallbackSnapshot);
  const [loadingState, setLoadingState] = useState<'idle' | 'loading' | 'ready' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [eventDraft, setEventDraft] = useState('desktop.checkpoint');
  const [memoryQuery, setMemoryQuery] = useState('persistence event log');
  const [memoryScope, setMemoryScope] = useState('workspace');
  const [memoryRole, setMemoryRole] = useState('orchestrator');
  const [memoryProjectId, setMemoryProjectId] = useState('project-001');
  const [retrieval, setRetrieval] = useState<MemoryRetrievalResult | null>(null);
  const [memoryError, setMemoryError] = useState<string | null>(null);
  const [memoryState, setMemoryState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [launchObjective, setLaunchObjective] = useState('Implement phase 3 orchestration runtime for Gnosys');
  const [launchMode, setLaunchMode] = useState('Supervised');
  const [launchState, setLaunchState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [launchError, setLaunchError] = useState<string | null>(null);
  const [launchResponse, setLaunchResponse] = useState<LaunchResponse | null>(null);
  const [policyState, setPolicyState] = useState<'idle' | 'saving' | 'error'>('idle');
  const [policyError, setPolicyError] = useState<string | null>(null);
  const [crudKind, setCrudKind] = useState<CrudKind>('tasks');
  const [crudSelectionId, setCrudSelectionId] = useState<string>('');
  const [crudDraft, setCrudDraft] = useState<CrudDraft>({});
  const [crudState, setCrudState] = useState<'idle' | 'saving' | 'error'>('idle');
  const [crudError, setCrudError] = useState<string | null>(null);
  const [policyEntityType, setPolicyEntityType] = useState<'task' | 'project' | 'skill' | 'schedule'>('project');
  const [policyEntityId, setPolicyEntityId] = useState('project-001');
  const [policyEntityMode, setPolicyEntityMode] = useState('Supervised');
  const [policyEntityKillSwitch, setPolicyEntityKillSwitch] = useState(false);
  const [policyEntityBias, setPolicyEntityBias] = useState('supervised');
  const [policyEntityState, setPolicyEntityState] = useState<'idle' | 'saving' | 'error'>('idle');
  const [policyEntityError, setPolicyEntityError] = useState<string | null>(null);
  const [replayRunId, setReplayRunId] = useState('');
  const [replay, setReplay] = useState<ReplayResponse | null>(null);
  const [replayState, setReplayState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [replayError, setReplayError] = useState<string | null>(null);

  async function refreshSnapshot() {
    const state = await loadSnapshot();
    setSnapshot(state);
    return state;
  }

  async function runMemorySearch(query = memoryQuery, role = memoryRole, scope = memoryScope, projectId = memoryProjectId) {
    setMemoryState('loading');
    setMemoryError(null);
    try {
      const result = await retrieveMemory(query, role, scope || null, projectId || null);
      setRetrieval(result);
      setMemoryState('ready');
      setActiveTab('Trace');
    } catch (error) {
      setMemoryError(error instanceof Error ? error.message : 'Failed to retrieve memory');
      setMemoryState('error');
    }
  }

  async function runLaunch(objective = launchObjective, mode = launchMode) {
    setLaunchState('loading');
    setLaunchError(null);
    try {
      const result = await launchOrchestration(objective, mode);
      setLaunchResponse(result);
      await refreshSnapshot();
      setLaunchState('ready');
      setActiveTab('Trace');
    } catch (error) {
      setLaunchError(error instanceof Error ? error.message : 'Failed to launch orchestration');
      setLaunchState('error');
    }
  }

  async function savePolicyMode(nextMode: string, nextKillSwitch: boolean) {
    setPolicyState('saving');
    setPolicyError(null);
    try {
      const updated = await updatePolicy({ autonomy_mode: nextMode, kill_switch: nextKillSwitch });
      setLaunchMode(updated.autonomy_mode);
      await refreshSnapshot();
      setPolicyState('idle');
      setActiveTab('Logs');
    } catch (error) {
      setPolicyError(error instanceof Error ? error.message : 'Failed to update policy');
      setPolicyState('error');
    }
  }

  async function resolveApproval(approvalId: string, status: 'approved' | 'rejected') {
    setPolicyState('saving');
    setPolicyError(null);
    try {
      const response = await fetch(`/api/approvals/${approvalId}/resolve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status, resolved_by: 'desktop' })
      });
      if (!response.ok) {
        throw new Error(await readErrorDetail(response, `Failed to resolve approval: ${response.status}`));
      }
      await refreshSnapshot();
      setPolicyState('idle');
    } catch (error) {
      setPolicyError(error instanceof Error ? error.message : 'Failed to resolve approval');
      setPolicyState('error');
    }
  }

  async function saveEntityPolicy() {
    setPolicyEntityState('saving');
    setPolicyEntityError(null);
    try {
      const updated = await updateEntityPolicy(policyEntityType, policyEntityId, {
        autonomy_mode: policyEntityMode,
        kill_switch: policyEntityKillSwitch,
        approval_bias: policyEntityBias
      });
      setPolicyEntityMode(updated.autonomy_mode);
      setPolicyEntityKillSwitch(updated.kill_switch);
      setPolicyEntityBias(updated.approval_bias);
      await refreshSnapshot();
      setPolicyEntityState('idle');
    } catch (error) {
      setPolicyEntityError(error instanceof Error ? error.message : 'Failed to update entity policy');
      setPolicyEntityState('error');
    }
  }

  async function executeSchedule(scheduleId: string) {
    try {
      await runSchedule(scheduleId);
      await refreshSnapshot();
      await runMemorySearch(memoryQuery, memoryRole, memoryScope, memoryProjectId);
      setActiveTab('Logs');
    } catch (error) {
      setPolicyError(error instanceof Error ? error.message : 'Failed to run schedule');
    }
  }

  async function retryRun(runId: string) {
    try {
      await retryScheduleRun(runId);
      await refreshSnapshot();
      setActiveTab('Logs');
    } catch (error) {
      setPolicyError(error instanceof Error ? error.message : 'Failed to retry schedule');
    }
  }

  async function loadRunReplay(runId: string) {
    setReplayState('loading');
    setReplayError(null);
    try {
      const result = await loadReplay(runId);
      setReplay(result);
      setReplayRunId(runId);
      setReplayState('ready');
      setActiveTab('Trace');
    } catch (error) {
      setReplayError(error instanceof Error ? error.message : 'Failed to load replay');
      setReplayState('error');
    }
  }

  async function saveCrudItem() {
    const endpoint = crudConfig(crudKind).endpoint;
    const normalized = normalizeCrudDraft(crudKind, crudDraft);
    const creating = crudSelectionId === '' || crudSelectionId === NEW_ITEM_SENTINEL;
    const method = creating ? 'POST' : 'PATCH';
    const requestUrl = creating ? endpoint : `${endpoint}/${crudSelectionId}`;
    setCrudState('saving');
    setCrudError(null);

    try {
      const response = await fetch(requestUrl, {
        method,
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(normalized)
      });

      if (!response.ok) {
        throw new Error(await readErrorDetail(response, `Failed to save ${crudKind}: ${response.status}`));
      }

      const saved = (await response.json()) as { id: string };
      const nextSnapshot = await refreshSnapshot();
      const items = getCrudItems(nextSnapshot, crudKind) as Array<{ id: string }>;
      const nextSelection = saved.id || items[0]?.id || '';
      setCrudSelectionId(nextSelection);
      setCrudDraft(buildCrudDraft(crudKind, items.find((item) => item.id === nextSelection) ?? items[0] ?? {}));
      setCrudState('idle');
      setActiveTab('Logs');
    } catch (error) {
      setCrudError(error instanceof Error ? error.message : 'Failed to save item');
      setCrudState('error');
    }
  }

  async function deleteCrudItem() {
    if (!crudSelectionId || crudSelectionId === NEW_ITEM_SENTINEL) {
      return;
    }
    const endpoint = crudConfig(crudKind).endpoint;
    setCrudState('saving');
    setCrudError(null);

    try {
      const response = await fetch(`${endpoint}/${crudSelectionId}`, {
        method: 'DELETE'
      });
      if (!response.ok && response.status !== 204) {
        throw new Error(await readErrorDetail(response, `Failed to delete ${crudKind}: ${response.status}`));
      }
      const nextSnapshot = await refreshSnapshot();
      const items = getCrudItems(nextSnapshot, crudKind) as Array<{ id: string }>;
      const nextSelection = items[0]?.id || '';
      setCrudSelectionId(nextSelection);
      setCrudDraft(buildCrudDraft(crudKind, items[0] ?? {}));
      setCrudState('idle');
    } catch (error) {
      setCrudError(error instanceof Error ? error.message : 'Failed to delete item');
      setCrudState('error');
    }
  }

  function startNewCrudItem() {
    setCrudSelectionId(NEW_ITEM_SENTINEL);
    setCrudDraft({});
    setCrudError(null);
    setCrudState('idle');
  }

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setLoadingState('loading');
      try {
        const state = await refreshSnapshot();
        if (cancelled) {
          return;
        }
        setSnapshot(state);
        setLoadingState('ready');
        setErrorMessage(null);
        const firstRun = state.task_runs[0];
        if (firstRun) {
          setLaunchResponse({
            task: state.tasks.find((task) => task.id === firstRun.task_id) ?? state.tasks[0] ?? seedTasks[0],
            task_run: firstRun,
            agent_runs: state.agent_runs.filter((run) => run.task_run_id === firstRun.id)
          } as LaunchResponse);
        }
      } catch (error) {
        if (cancelled) {
          return;
        }
        setSnapshot(fallbackSnapshot);
        setLoadingState('error');
        setErrorMessage(error instanceof Error ? error.message : 'Failed to load backend state');
      }
    }

    void run();
    void runMemorySearch('persistence event log', 'orchestrator', 'workspace', memoryProjectId);

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setLaunchMode(snapshot.workspace.autonomy_mode);
  }, [snapshot.workspace.autonomy_mode]);

  useEffect(() => {
    if (!memoryProjectId || !snapshot.projects.some((project) => project.id === memoryProjectId)) {
      setMemoryProjectId(snapshot.projects[0]?.id ?? '');
    }
  }, [memoryProjectId, snapshot.projects]);

  useEffect(() => {
    if (!policyEntityId) {
      return;
    }
    const existing = snapshot.entity_policies.find(
      (policy) => policy.entity_type === policyEntityType && policy.entity_id === policyEntityId
    );
    if (existing) {
      setPolicyEntityMode(existing.autonomy_mode);
      setPolicyEntityKillSwitch(existing.kill_switch);
      setPolicyEntityBias(existing.approval_bias);
      return;
    }

    const defaultsByType = {
      task: snapshot.tasks.find((task) => task.id === policyEntityId),
      project: snapshot.projects.find((project) => project.id === policyEntityId),
      skill: snapshot.skills.find((skill) => skill.id === policyEntityId),
      schedule: snapshot.schedules.find((schedule) => schedule.id === policyEntityId)
    };
    if (!defaultsByType[policyEntityType]) {
      return;
    }
    setPolicyEntityMode(snapshot.workspace.autonomy_mode);
    setPolicyEntityKillSwitch(snapshot.workspace.kill_switch);
    setPolicyEntityBias(snapshot.workspace.approval_bias);
  }, [
    policyEntityId,
    policyEntityType,
    snapshot.entity_policies,
    snapshot.projects,
    snapshot.schedules,
    snapshot.skills,
    snapshot.tasks,
    snapshot.workspace.autonomy_mode,
    snapshot.workspace.approval_bias,
    snapshot.workspace.kill_switch
  ]);

  useEffect(() => {
    if (crudSelectionId === NEW_ITEM_SENTINEL) {
      return;
    }
    const items = getCrudItems(snapshot, crudKind) as Array<{ id: string }>;
    const nextSelection = items.find((item) => item.id === crudSelectionId)?.id ?? items[0]?.id ?? '';
    if (nextSelection !== crudSelectionId) {
      setCrudSelectionId(nextSelection);
    }
    const selectedItem = items.find((item) => item.id === nextSelection) ?? items[0];
    setCrudDraft(selectedItem ? buildCrudDraft(crudKind, selectedItem) : {});
  }, [crudKind, snapshot, crudSelectionId]);

  const selectedTask = useMemo(
    () => snapshot.tasks.find((task) => task.id === activeTask) ?? snapshot.tasks[0] ?? fallbackSnapshot.tasks[0],
    [activeTask, snapshot.tasks]
  );

  const selectedAgent = snapshot.agents[0] ?? fallbackSnapshot.agents[0];
  const activeMemoryLayer = snapshot.memory_layers[0] ?? fallbackSnapshot.memory_layers[0];
  const pendingApprovals = snapshot.approval_requests.filter((request) => request.status === 'pending');
  const currentRun = launchResponse?.task_run ?? snapshot.task_runs[0] ?? null;
  const currentRunTree = currentRun ? buildRunTree(snapshot.agent_runs.filter((run) => run.task_run_id === currentRun.id)) : [];
  const selectedProject = snapshot.projects.find((project) => project.id === memoryProjectId) ?? snapshot.projects[0] ?? null;
  const selectedSchedule = snapshot.schedules[0] ?? null;
  const latestScheduleRun = snapshot.schedule_runs[0] ?? null;
  const replayTaskRunId = replayRunId || currentRun?.id || snapshot.task_runs[0]?.id || '';
  const policyEntityItems: Array<{ id: string; name: string }> = (() => {
    switch (policyEntityType) {
      case 'task':
        return snapshot.tasks.map((item) => ({ id: item.id, name: item.title }));
      case 'project':
        return snapshot.projects.map((item) => ({ id: item.id, name: item.name }));
      case 'skill':
        return snapshot.skills.map((item) => ({ id: item.id, name: item.name }));
      case 'schedule':
        return snapshot.schedules.map((item) => ({ id: item.id, name: item.name }));
    }
  })();
  const activeCrudItems = getCrudItems(snapshot, crudKind);
  const activeCrudItem = crudSelectionId && crudSelectionId !== NEW_ITEM_SENTINEL
    ? activeCrudItems.find((item) => item.id === crudSelectionId) ?? null
    : null;

  async function appendCheckpointEvent() {
    const response = await fetch('/api/events', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        type: eventDraft,
        source: 'desktop-shell',
        payload: {
          section: activeSection,
          task_id: selectedTask.id,
          agent_id: selectedAgent.id
        }
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to record event: ${response.status}`);
    }

    const nextSnapshot = await refreshSnapshot();
    setSnapshot(nextSnapshot);
    setActiveTab('Logs');
    await runMemorySearch(memoryQuery, memoryRole, memoryScope, memoryProjectId);
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="eyebrow">Gnosys scaffold</div>
          <h1>{snapshot.workspace.name}</h1>
          <p>{snapshot.workspace.active_project}</p>
        </div>

        <nav className="nav" aria-label="Primary navigation">
          {navSections.map((section) => (
            <button
              key={section}
              className={section === activeSection ? 'nav-item active' : 'nav-item'}
              onClick={() => setActiveSection(section)}
            >
              {section}
            </button>
          ))}
        </nav>
      </aside>

      <main className="main">
        <header className="hero">
          <div>
            <div className="eyebrow">Orchestration runtime</div>
            <h2>Memory, delegation, and bounded worker runs now sit on the same local foundation.</h2>
          </div>
          <div className="status-pill">
            {snapshot.workspace.autonomy_mode} · {snapshot.workspace.status} · {loadingState}
          </div>
        </header>

        <section className="metrics">
          <article>
            <span>Task</span>
            <strong>{selectedTask.title}</strong>
          </article>
          <article>
            <span>Agent</span>
            <strong>{selectedAgent.name}</strong>
          </article>
          <article>
            <span>Memory</span>
            <strong>{activeMemoryLayer.name}</strong>
          </article>
            <article>
              <span>Runs</span>
              <strong>{snapshot.counts.task_runs}</strong>
            </article>
            <article>
              <span>Approvals</span>
              <strong>{snapshot.counts.approval_requests}</strong>
            </article>
          </section>

        <section className="content-grid">
          <section className="panel panel-wide">
            <div className="panel-title">Workspace surface</div>
            <div className="stack">
              {snapshot.tasks.map((task) => (
                <button
                  key={task.id}
                  className={task.id === activeTask ? 'row active' : 'row'}
                  onClick={() => setActiveTask(task.id)}
                >
                  <div>
                    <strong>{task.title}</strong>
                    <span>{task.summary}</span>
                  </div>
                  <div className="row-meta">
                    <span>{task.priority}</span>
                    <span>{task.status}</span>
                  </div>
                </button>
              ))}
            </div>
          </section>

          <aside className="panel inspector">
            <div className="panel-title">Inspector</div>
            <div className="detail">
              <strong>Current section</strong>
              <p>{activeSection}</p>
            </div>
            <div className="detail">
              <strong>Execution phase</strong>
              <p>{snapshot.workspace.phase}</p>
            </div>
            <div className="detail">
              <strong>Autonomy mode</strong>
              <p>{snapshot.workspace.autonomy_mode}</p>
            </div>
            <div className="detail">
              <strong>Approval bias</strong>
              <p>{snapshot.workspace.approval_bias}</p>
            </div>
            <div className="detail">
              <strong>Memory</strong>
              <p>{activeMemoryLayer.description}</p>
            </div>
            <div className="detail">
              <strong>Live counts</strong>
              <p>
                {snapshot.counts.tasks} tasks, {snapshot.counts.agents} agents, {snapshot.counts.memory_layers} layers, {snapshot.counts.memory_items} memories
              </p>
            </div>
            <div className="detail">
              <strong>Run status</strong>
              <p>{launchState}</p>
            </div>
            <div className="detail">
              <strong>Kill switch</strong>
              <p>{snapshot.workspace.kill_switch ? 'Enabled' : 'Disabled'}</p>
            </div>
            <div className="detail">
              <strong>Pending approvals</strong>
              <p>{pendingApprovals.length}</p>
            </div>
          </aside>
        </section>

        <section className="panel orchestration-panel">
          <div className="panel-title">Launch orchestration</div>
          <div className="orchestration-controls">
            <input
              value={launchObjective}
              onChange={(event) => setLaunchObjective(event.target.value)}
              aria-label="Launch objective"
            />
            <select value={launchMode} onChange={(event) => setLaunchMode(event.target.value)}>
              <option>Manual</option>
              <option>Supervised</option>
              <option>Autonomous</option>
              <option>Full Access</option>
            </select>
            <button className="primary-action" onClick={() => void runLaunch()}>
              Launch run
            </button>
          </div>
          <p className="event-hint">The backend applies the active autonomy policy before execution. The launch selector records the requested run mode, but policy can still gate the request.</p>
          {launchError && <p className="error-banner">{launchError}</p>}
          {launchResponse && (
            <div className="launch-summary">
              <strong>{launchResponse.summary}</strong>
              <p>{launchResponse.task_run.status} · {launchResponse.agent_runs.length} runs created · {launchResponse.steps.length} steps</p>
            </div>
          )}
        </section>

        <section className="panel orchestration-panel">
          <div className="panel-title">Autonomy controls</div>
          <div className="orchestration-controls">
            <select value={snapshot.workspace.autonomy_mode} onChange={(event) => void savePolicyMode(event.target.value, snapshot.workspace.kill_switch)}>
              <option>Manual</option>
              <option>Supervised</option>
              <option>Autonomous</option>
              <option>Full Access</option>
            </select>
            <button
              className={snapshot.workspace.kill_switch ? 'primary-action danger' : 'tab'}
              onClick={() => void savePolicyMode(snapshot.workspace.autonomy_mode, !snapshot.workspace.kill_switch)}
            >
              {snapshot.workspace.kill_switch ? 'Disable kill switch' : 'Enable kill switch'}
            </button>
          </div>
          <p className="event-hint">
            {snapshot.workspace.mode_label} · current mode: {snapshot.workspace.autonomy_mode} · kill switch {snapshot.workspace.kill_switch ? 'armed' : 'clear'} · full access mode bypasses approval gates unless the kill switch is armed
          </p>
          {policyError && <p className="error-banner">{policyError}</p>}
          <div className="launch-summary">
            <strong>{pendingApprovals.length} pending approval request{pendingApprovals.length === 1 ? '' : 's'}</strong>
            <p>{snapshot.workspace.approval_bias} gating is enforced in the backend before writes or launches proceed.</p>
          </div>
        </section>

        <section className="panel orchestration-panel">
          <div className="panel-title">Entity policy controls</div>
          <div className="orchestration-controls">
            <select
              value={policyEntityType}
              onChange={(event) => {
                const nextType = event.target.value as typeof policyEntityType;
                setPolicyEntityType(nextType);
                const nextId =
                  nextType === 'task'
                    ? snapshot.tasks[0]?.id ?? ''
                    : nextType === 'project'
                      ? snapshot.projects[0]?.id ?? ''
                      : nextType === 'skill'
                        ? snapshot.skills[0]?.id ?? ''
                        : snapshot.schedules[0]?.id ?? '';
                setPolicyEntityId(nextId);
              }}
            >
              <option value="project">Project</option>
              <option value="task">Task</option>
              <option value="skill">Skill</option>
              <option value="schedule">Schedule</option>
            </select>
            <select
              value={policyEntityId}
              onChange={(event) => setPolicyEntityId(event.target.value)}
            >
              {policyEntityItems.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
            <select value={policyEntityMode} onChange={(event) => setPolicyEntityMode(event.target.value)}>
              <option>Manual</option>
              <option>Supervised</option>
              <option>Autonomous</option>
              <option>Full Access</option>
            </select>
            <select value={policyEntityBias} onChange={(event) => setPolicyEntityBias(event.target.value)}>
              <option value="manual">manual</option>
              <option value="supervised">supervised</option>
              <option value="autonomous">autonomous</option>
              <option value="full-access">full-access</option>
            </select>
            <label className="toggle-row">
              Kill switch
              <input
                type="checkbox"
                checked={policyEntityKillSwitch}
                onChange={(event) => setPolicyEntityKillSwitch(event.target.checked)}
              />
            </label>
            <button className="primary-action" onClick={() => void saveEntityPolicy()}>
              Save entity policy
            </button>
          </div>
          <p className="event-hint">
            {policyEntityType} policies override workspace policy for that entity scope. Current selection follows the active project, task, skill, or schedule. Status: {policyEntityState}.
          </p>
          {policyEntityError && <p className="error-banner">{policyEntityError}</p>}
          <div className="stack compact">
            {snapshot.entity_policies.slice(0, 6).map((policy) => (
              <article key={`${policy.entity_type}:${policy.entity_id}`} className="run-node">
                <div className="run-node-top">
                  <strong>{policy.entity_type}</strong>
                  <span>{policy.entity_id}</span>
                </div>
                <p>
                  {policy.autonomy_mode} · {policy.approval_bias} · {policy.kill_switch ? 'kill switch enabled' : 'kill switch clear'}
                </p>
                <div className="run-node-meta">
                  <span>{policy.updated_at}</span>
                  <span>
                    <button
                      className="tab"
                      onClick={() => {
                        setPolicyEntityType(policy.entity_type as typeof policyEntityType);
                        setPolicyEntityId(policy.entity_id);
                        setPolicyEntityMode(policy.autonomy_mode);
                        setPolicyEntityKillSwitch(policy.kill_switch);
                        setPolicyEntityBias(policy.approval_bias);
                      }}
                    >
                      Edit
                    </button>
                  </span>
                </div>
              </article>
            ))}
            {snapshot.entity_policies.length === 0 && <p>No entity-specific policies have been created yet.</p>}
          </div>
        </section>

        <section className="panel orchestration-panel">
          <div className="panel-title">Approval queue</div>
          <div className="stack compact">
            {pendingApprovals.map((request) => (
              <article key={request.id} className="run-node">
                <div className="run-node-top">
                  <strong>{request.action}</strong>
                  <span>{request.sensitivity} · {request.subject_type}</span>
                </div>
                <p>{request.reason}</p>
                <div className="run-node-meta">
                  <span>{request.subject_ref}</span>
                  <span>{request.requested_by}</span>
                  <span>{request.created_at}</span>
                </div>
                <div className="crud-actions">
                  <button className="primary-action" onClick={() => void resolveApproval(request.id, 'approved')}>
                    Approve
                  </button>
                  <button className="tab" onClick={() => void resolveApproval(request.id, 'rejected')}>
                    Reject
                  </button>
                </div>
              </article>
            ))}
            {pendingApprovals.length === 0 && <p>No pending approval requests.</p>}
          </div>
        </section>

        <section className="panel orchestration-panel">
          <div className="panel-title">Run tree</div>
          <div className="run-history">
            <div className="run-list">
              {snapshot.task_runs.map((run) => (
                <button
                  key={run.id}
                  className={currentRun?.id === run.id ? 'run-row active' : 'run-row'}
                  onClick={() =>
                    setLaunchResponse({
                      task: snapshot.tasks.find((task) => task.id === run.task_id) ?? selectedTask,
                      task_run: run,
                      agent_runs: snapshot.agent_runs.filter((agentRun) => agentRun.task_run_id === run.id),
                      steps: [],
                      approvals_required: [],
                      summary: run.summary
                    })
                  }
                >
                  <strong>{run.objective}</strong>
                  <span>{run.status} · {run.step_count} steps</span>
                </button>
              ))}
              {snapshot.task_runs.length === 0 && <p>No orchestration runs yet.</p>}
            </div>
            <div className="run-tree">
              <div className="panel-title">Selected run</div>
              {currentRun ? (
                <>
                  <div className="detail">
                    <strong>{currentRun.objective}</strong>
                    <p>{currentRun.summary}</p>
                  </div>
                  <div className="stack compact">
                    {currentRunTree.map((run) => (
                      <article key={run.id} className="run-node" style={{ marginLeft: `${run.recursion_depth * 18}px` }}>
                        <div className="run-node-top">
                          <strong>{run.agent_name}</strong>
                          <span>{run.run_kind} · {run.status}</span>
                        </div>
                        <p>{run.summary}</p>
                        <div className="run-node-meta">
                          <span>budget {run.budget_units}</span>
                          <span>children {run.child_count}</span>
                          <span>approval {run.approval_required ? 'required' : 'not required'}</span>
                        </div>
                      </article>
                    ))}
                  </div>
                </>
              ) : (
                <p>Run details will appear here after launch.</p>
              )}
            </div>
          </div>
        </section>

        <section className="panel orchestration-panel">
          <div className="panel-title">Schedule execution</div>
          <div className="stack compact">
            {snapshot.schedules.map((schedule) => (
              <article key={schedule.id} className="run-node">
                <div className="run-node-top">
                  <strong>{schedule.name}</strong>
                  <span>{schedule.target_type} · {schedule.enabled ? 'enabled' : 'disabled'}</span>
                </div>
                <p>{schedule.schedule_expression}</p>
                <div className="run-node-meta">
                  <span>{schedule.target_ref}</span>
                  <span>{schedule.timezone}</span>
                  <span>{schedule.project_id ?? 'workspace'}</span>
                </div>
                <div className="crud-actions">
                  <button className="primary-action" onClick={() => void executeSchedule(schedule.id)}>
                    Run now
                  </button>
                </div>
              </article>
            ))}
            {snapshot.schedules.length === 0 && <p>No schedules are defined yet.</p>}
          </div>
          {snapshot.schedule_runs.length > 0 && (
            <div className="stack compact" style={{ marginTop: '1rem' }}>
              {snapshot.schedule_runs.slice(0, 4).map((run) => (
                <article key={run.id} className="run-node">
                  <div className="run-node-top">
                    <strong>{run.schedule_name}</strong>
                    <span>{run.status} · attempt {run.attempt_number}</span>
                  </div>
                  <p>{run.result_summary}</p>
                  <div className="run-node-meta">
                    <span>{run.target_type}</span>
                    <span>{run.task_run_id ?? 'no task run'}</span>
                    <span>{run.requested_by}</span>
                  </div>
                  <div className="crud-actions">
                    <button className="tab" onClick={() => void retryRun(run.id)}>
                      Retry
                    </button>
                    <button className="tab" onClick={() => run.task_run_id && setReplayRunId(run.task_run_id)}>
                      Inspect
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
          {selectedSchedule && latestScheduleRun && (
            <p className="event-hint">
              Latest run for {selectedSchedule.name}: {latestScheduleRun.status} · {latestScheduleRun.result_summary}
            </p>
          )}
        </section>

        <section className="panel crud-panel">
          <div className="panel-title">CRUD workspace</div>
          <div className="crud-tabs">
            {crudKinds.map((kind) => (
              <button key={kind} className={kind === crudKind ? 'tab active' : 'tab'} onClick={() => setCrudKind(kind)}>
                {crudConfig(kind).title}
              </button>
            ))}
          </div>
          <div className="crud-grid">
            <div className="crud-list">
              {activeCrudItems.map((item) => (
                <button
                  key={item.id}
                  className={item.id === crudSelectionId ? 'run-row active' : 'run-row'}
                  onClick={() => {
                    setCrudSelectionId(item.id);
                    setCrudDraft(buildCrudDraft(crudKind, item));
                  }}
                >
                  <strong>{String(item.name ?? item.title ?? item.id)}</strong>
                  <span>{String(item.status ?? '')}</span>
                </button>
              ))}
              {activeCrudItems.length === 0 && <p>No {crudConfig(crudKind).title.toLowerCase()} yet.</p>}
            </div>
            <div className="crud-editor">
              <div className="panel-title">{activeCrudItem ? 'Edit item' : 'Create item'}</div>
              <div className="crud-form">
                {crudKind === 'tasks' && (
                  <>
                    <label>
                      Title
                      <input value={String(crudDraft.title ?? '')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, title: event.target.value }))} />
                    </label>
                    <label>
                      Summary
                      <textarea value={String(crudDraft.summary ?? '')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, summary: event.target.value }))} />
                    </label>
                    <label>
                      Status
                      <select value={String(crudDraft.status ?? 'Inbox')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, status: event.target.value }))}>
                        <option>Inbox</option>
                        <option>Planned</option>
                        <option>Running</option>
                        <option>Waiting</option>
                        <option>Needs Approval</option>
                        <option>Completed</option>
                        <option>Failed</option>
                      </select>
                    </label>
                    <label>
                      Priority
                      <select value={String(crudDraft.priority ?? 'Medium')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, priority: event.target.value }))}>
                        <option>Low</option>
                        <option>Medium</option>
                        <option>High</option>
                        <option>Critical</option>
                      </select>
                    </label>
                    <label>
                      Project
                      <select value={String(crudDraft.project_id ?? '')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, project_id: event.target.value }))}>
                        <option value="">Workspace</option>
                        {snapshot.projects.map((project) => (
                          <option key={project.id} value={project.id}>
                            {project.name}
                          </option>
                        ))}
                      </select>
                    </label>
                  </>
                )}
                {crudKind === 'projects' && (
                  <>
                    <label>
                      Name
                      <input value={String(crudDraft.name ?? '')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, name: event.target.value }))} />
                    </label>
                    <label>
                      Summary
                      <textarea value={String(crudDraft.summary ?? '')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, summary: event.target.value }))} />
                    </label>
                    <label>
                      Status
                      <select value={String(crudDraft.status ?? 'Planned')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, status: event.target.value }))}>
                        <option>Active</option>
                        <option>Planned</option>
                        <option>Archived</option>
                      </select>
                    </label>
                    <label>
                      Owner
                      <input value={String(crudDraft.owner ?? '')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, owner: event.target.value }))} />
                    </label>
                  </>
                )}
                {crudKind === 'agents' && (
                  <>
                    <label>
                      Name
                      <input value={String(crudDraft.name ?? '')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, name: event.target.value }))} />
                    </label>
                    <label>
                      Role
                      <input value={String(crudDraft.role ?? '')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, role: event.target.value }))} />
                    </label>
                    <label>
                      Status
                      <select value={String(crudDraft.status ?? 'Idle')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, status: event.target.value }))}>
                        <option>Idle</option>
                        <option>Working</option>
                        <option>Waiting</option>
                        <option>Reviewing</option>
                      </select>
                    </label>
                  </>
                )}
                {crudKind === 'skills' && (
                  <>
                    <label>
                      Name
                      <input value={String(crudDraft.name ?? '')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, name: event.target.value }))} />
                    </label>
                    <label>
                      Description
                      <textarea value={String(crudDraft.description ?? '')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, description: event.target.value }))} />
                    </label>
                    <label>
                      Scope
                      <select value={String(crudDraft.scope ?? 'workspace')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, scope: event.target.value }))}>
                        <option>workspace</option>
                        <option>project</option>
                        <option>session</option>
                        <option>user</option>
                      </select>
                    </label>
                    <label>
                      Version
                      <input value={String(crudDraft.version ?? '0.1.0')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, version: event.target.value }))} />
                    </label>
                    <label>
                      Source type
                      <select value={String(crudDraft.source_type ?? 'authored')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, source_type: event.target.value }))}>
                        <option>authored</option>
                        <option>learned</option>
                      </select>
                    </label>
                    <label>
                      Status
                      <select value={String(crudDraft.status ?? 'draft')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, status: event.target.value }))}>
                        <option>draft</option>
                        <option>active</option>
                        <option>archived</option>
                      </select>
                    </label>
                    <label>
                      Project
                      <select value={String(crudDraft.project_id ?? '')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, project_id: event.target.value }))}>
                        <option value="">Workspace</option>
                        {snapshot.projects.map((project) => (
                          <option key={project.id} value={project.id}>
                            {project.name}
                          </option>
                        ))}
                      </select>
                    </label>
                  </>
                )}
                {crudKind === 'schedules' && (
                  <>
                    <label>
                      Name
                      <input value={String(crudDraft.name ?? '')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, name: event.target.value }))} />
                    </label>
                    <label>
                      Target type
                      <select value={String(crudDraft.target_type ?? 'skill')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, target_type: event.target.value }))}>
                        <option>task</option>
                        <option>project</option>
                        <option>skill</option>
                        <option>orchestration</option>
                      </select>
                    </label>
                    <label>
                      Target ref
                      <input value={String(crudDraft.target_ref ?? '')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, target_ref: event.target.value }))} />
                    </label>
                    <label>
                      Schedule expression
                      <input value={String(crudDraft.schedule_expression ?? '')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, schedule_expression: event.target.value }))} />
                    </label>
                    <label>
                      Timezone
                      <input value={String(crudDraft.timezone ?? 'America/New_York')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, timezone: event.target.value }))} />
                    </label>
                    <label className="toggle-row">
                      Enabled
                      <input
                        type="checkbox"
                        checked={Boolean(crudDraft.enabled)}
                        onChange={(event) => setCrudDraft((prev) => ({ ...prev, enabled: event.target.checked }))}
                      />
                    </label>
                    <label>
                      Project
                      <select value={String(crudDraft.project_id ?? '')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, project_id: event.target.value }))}>
                        <option value="">Workspace</option>
                        {snapshot.projects.map((project) => (
                          <option key={project.id} value={project.id}>
                            {project.name}
                          </option>
                        ))}
                      </select>
                    </label>
                  </>
                )}
              </div>
              <div className="crud-actions">
                <button className="tab" onClick={() => startNewCrudItem()}>
                  New item
                </button>
                <button className="primary-action" onClick={() => void saveCrudItem()}>
                  {crudSelectionId && crudSelectionId !== NEW_ITEM_SENTINEL ? 'Save changes' : crudConfig(crudKind).createLabel}
                </button>
                <button
                  className="tab"
                  onClick={() => void deleteCrudItem()}
                  disabled={!crudSelectionId || crudSelectionId === NEW_ITEM_SENTINEL}
                >
                  Delete
                </button>
              </div>
              {crudError && <p className="error-banner">{crudError}</p>}
              <p className="event-hint">
                {crudState === 'saving'
                  ? 'Saving...'
                  : crudSelectionId && crudSelectionId !== NEW_ITEM_SENTINEL
                    ? `Editing ${crudSelectionId}`
                    : 'Creating a new item'}
              </p>
            </div>
          </div>
        </section>

        <section className="panel event-panel">
          <div className="panel-title">Memory retrieval</div>
          <div className="memory-controls">
            <input value={memoryQuery} onChange={(event) => setMemoryQuery(event.target.value)} aria-label="Memory query" />
            <select value={memoryScope} onChange={(event) => setMemoryScope(event.target.value)}>
              <option value="">All scopes</option>
              <option value="workspace">Workspace</option>
              <option value="project">Project</option>
              <option value="session">Session</option>
              <option value="user">User</option>
            </select>
            <select value={memoryProjectId} onChange={(event) => setMemoryProjectId(event.target.value)}>
              <option value="">All projects</option>
              {snapshot.projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
            <select value={memoryRole} onChange={(event) => setMemoryRole(event.target.value)}>
              <option value="orchestrator">Orchestrator</option>
              <option value="planner">Planner</option>
              <option value="memory_steward">Memory Steward</option>
              <option value="critic">Critic</option>
            </select>
            <button className="primary-action" onClick={() => void runMemorySearch()}>
              Search memory
            </button>
          </div>
          <div className="retrieval-grid">
            <div>
              <p className="event-hint">Memory results are ranked against confidence, freshness, scope, role bias, and project scope when selected.</p>
              {memoryError && <p className="error-banner">{memoryError}</p>}
              {retrieval && (
                <div className="stack compact">
                  {retrieval.items.map((item) => (
                    <article key={item.id} className="memory-card">
                      <div className="memory-card-top">
                        <strong>{item.title}</strong>
                        <span>{item.layer} · {item.state}</span>
                      </div>
                      <p>{item.summary}</p>
                      <div className="memory-meta">
                        <span>score {item.score.toFixed(2)}</span>
                        <span>{item.reason}</span>
                      </div>
                    </article>
                  ))}
                  {retrieval.items.length === 0 && <p>No memory items matched this query.</p>}
                </div>
              )}
            </div>
            <aside className="trace-panel">
              <div className="panel-title">Retrieval trace</div>
              <div className="stack compact">
                {retrieval?.trace.map((step) => (
                  <div key={step.stage} className="trace-step">
                    <strong>{step.stage}</strong>
                    <span>{step.detail}</span>
                  </div>
                ))}
              </div>
            </aside>
          </div>
        </section>

        <section className="panel event-panel">
          <div className="panel-title">Write to event log</div>
          <div className="event-controls">
            <input value={eventDraft} onChange={(event) => setEventDraft(event.target.value)} aria-label="Event type" />
            <button className="primary-action" onClick={() => void appendCheckpointEvent()}>
              Record event
            </button>
          </div>
          <p className="event-hint">This writes a durable row into the local SQLite event log and refreshes the UI.</p>
          {errorMessage && <p className="error-banner">{errorMessage}</p>}
        </section>

        <section className="panel event-panel">
          <div className="panel-title">Diagnostics replay</div>
          <div className="event-controls">
            <select value={replayRunId} onChange={(event) => setReplayRunId(event.target.value)}>
              <option value="">Select task run</option>
              {snapshot.task_runs.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.id} · {run.status}
                </option>
              ))}
            </select>
            <button className="primary-action" onClick={() => void loadRunReplay(replayRunId || replayTaskRunId)}>
              Load replay
            </button>
          </div>
          <p className="event-hint">Replay pulls the task run, agent runs, related events, and schedule runs that point at the same task run.</p>
          <p className="event-hint">Replay status: {replayState}. Active project for memory routing: {selectedProject?.name ?? 'none'}.</p>
          {replayError && <p className="error-banner">{replayError}</p>}
          {replay && (
            <div className="retrieval-grid">
              <div className="stack compact">
                <article className="memory-card">
                  <div className="memory-card-top">
                    <strong>{replay.task_run.objective}</strong>
                    <span>{replay.task_run.status}</span>
                  </div>
                  <p>{replay.task_run.summary}</p>
                  <div className="memory-meta">
                    <span>{replay.task_run.mode}</span>
                    <span>{replay.task_run.step_count} steps</span>
                    <span>{replay.task_run.approval_required ? 'approval required' : 'no approval required'}</span>
                  </div>
                </article>
                {replay.agent_runs.map((run) => (
                  <article key={run.id} className="memory-card">
                    <div className="memory-card-top">
                      <strong>{run.agent_name}</strong>
                      <span>{run.run_kind} · {run.status}</span>
                    </div>
                    <p>{run.summary}</p>
                    <div className="memory-meta">
                      <span>depth {run.recursion_depth}</span>
                      <span>budget {run.budget_units}</span>
                      <span>{run.task_run_id}</span>
                    </div>
                  </article>
                ))}
                {replay.schedule_runs.map((run) => (
                  <article key={run.id} className="memory-card">
                    <div className="memory-card-top">
                      <strong>{run.schedule_name}</strong>
                      <span>{run.status} · attempt {run.attempt_number}</span>
                    </div>
                    <p>{run.result_summary}</p>
                    <div className="memory-meta">
                      <span>{run.target_type}</span>
                      <span>{run.target_ref}</span>
                      <span>{run.requested_by}</span>
                    </div>
                  </article>
                ))}
              </div>
              <aside className="trace-panel">
                <div className="panel-title">Replay events</div>
                <div className="stack compact">
                  {replay.events.map((event) => (
                    <div key={event.id} className="trace-step">
                      <strong>{event.type}</strong>
                      <span>{event.created_at}</span>
                    </div>
                  ))}
                  {replay.events.length === 0 && <p>No replay events were found for this run.</p>}
                </div>
              </aside>
            </div>
          )}
        </section>

        <section className="bottom">
          <div className="tabs">
            {bottomTabs.map((tab) => (
              <button
                key={tab}
                className={tab === activeTab ? 'tab active' : 'tab'}
                onClick={() => setActiveTab(tab)}
              >
                {tab}
              </button>
            ))}
          </div>
          <div className="bottom-content">
            {activeTab === 'Logs' && (
              <div className="log">
                {snapshot.recent_events.slice(0, 5).map((event) => (
                  <span key={event.id}>
                    {event.created_at} {event.type} via {event.source}
                  </span>
                ))}
                {snapshot.recent_events.length === 0 && <span>No events yet.</span>}
              </div>
            )}
            {activeTab === 'Timeline' && (
              <p>Task runs, specialist delegation, and worker spawning now sit on the same local event trail.</p>
            )}
            {activeTab === 'Trace' && (
              <p>request → task run → planner → specialist → bounded worker → event log → inspectable tree</p>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
