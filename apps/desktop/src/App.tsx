import {
  navSections,
  scheduleApprovalPolicies,
  scheduleFailurePolicies,
  seedAgents,
  seedMemoryItems,
  seedMemoryLayers,
  seedProjects,
  seedProjectThreads,
  seedSchedules,
  seedSkills,
  seedTasks,
  seedChatSessions,
  workspaceSummary,
  type Agent,
  type AgentRun,
  type ChatAttachment,
  type ChatMessage,
  type MemoryBrowseResult,
  type MemoryItem,
  type MemoryLayer,
  type Project,
  type Schedule,
  type Skill,
  type Task,
  type TaskRun,
  type WorkspaceSnapshot
} from '@gnosys/shared';
import {
  appendEvent,
  archiveMemoryItem,
  createSkillDraft,
  createProjectThread,
  deleteCrudResource,
  forgetMemoryItem,
  launchOrchestration,
  loadChatAttachments,
  loadChatMessages,
  loadDiagnosticsRuns,
  loadMemoryBrowser,
  loadMemoryReview,
  loadReplay,
  loadSkillLifecycle,
  loadSnapshot,
  pinMemoryItem,
  promoteMemoryItem,
  promoteSkill,
  resolveApproval as resolveApprovalRequest,
  retrieveMemory,
  retryScheduleRun,
  rollbackSkill,
  runSchedule,
  saveCrudResource,
  sendChatMessage,
  testSkill,
  uploadChatAttachment,
  updateEntityPolicy,
  updatePolicy,
  type DiagnosticsRunListResponse,
  type EntityPolicyRecord,
  type LaunchResponse,
  type MemoryBrowserResponse,
  type MemoryRetrievalResult,
  type MemoryReviewResponse,
  type ReplayResponse,
  type SkillLifecycleResponse,
  type SkillTestRunResponse
} from './api';
import { AgentsWorkspace } from './modules/AgentsWorkspace';
import { ChatWorkspace } from './modules/ChatWorkspace';
import { DiagnosticsPanel } from './modules/DiagnosticsPanel';
import { ProjectsWorkspace } from './modules/ProjectsWorkspace';
import { SchedulesPanel } from './modules/SchedulesPanel';
import { ScheduledWorkspace } from './modules/ScheduledWorkspace';
import { SessionsWorkspace } from './modules/SessionsWorkspace';
import { SettingsWorkspace } from './modules/SettingsWorkspace';
import { SkillsWorkspace } from './modules/SkillsWorkspace';
import { TasksWorkspace } from './modules/TasksWorkspace';
import { useEffect, useMemo, useState } from 'react';

const bottomTabs = ['Logs', 'Timeline', 'Trace'] as const;

type CrudDraft = Record<string, string | boolean>;

  const fallbackSnapshot: WorkspaceSnapshot = {
    workspace: {
      name: workspaceSummary.name,
      mode: workspaceSummary.mode,
      autonomy_mode: 'Supervised',
      kill_switch: false,
      approval_bias: 'supervised',
      mode_label: 'Global autonomy and approval policy',
      status: workspaceSummary.status,
      active_project: workspaceSummary.active_project,
      phase: workspaceSummary.phase
    },
    tasks: seedTasks,
    agents: seedAgents,
    projects: seedProjects,
    project_threads: seedProjectThreads,
    chat_sessions: seedChatSessions,
    skills: seedSkills,
    schedules: seedSchedules,
    memory_layers: seedMemoryLayers,
    memory_items: seedMemoryItems,
    task_runs: [],
    agent_runs: [],
    schedule_runs: [],
    timeline: [],
    comparison: null,
    approval_requests: [],
    entity_policies: [],
  recent_events: [],
  counts: {
    tasks: seedTasks.length,
    agents: seedAgents.length,
    projects: seedProjects.length,
    project_threads: seedProjectThreads.length,
    chat_sessions: seedChatSessions.length,
    skills: seedSkills.length,
    schedules: seedSchedules.length,
    memory_layers: seedMemoryLayers.length,
    memory_items: seedMemoryItems.length,
    skill_test_runs: 0,
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
type AdvancedSection = 'Launch' | 'Policy' | 'Approvals' | 'Runs' | 'More' | 'Schedules' | 'Skills' | 'Memory' | 'Diagnostics' | 'CRUD';

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
        approval_policy: String(draft.approval_policy ?? 'inherit'),
        failure_policy: String(draft.failure_policy ?? 'retry_once'),
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

const advancedSections: Array<{ label: AdvancedSection; description: string }> = [
  { label: 'Policy', description: 'Workspace and entity policy controls' },
  { label: 'Launch', description: 'Objective entry and execution preview' },
  { label: 'Approvals', description: 'Pending approvals and resolution actions' },
  { label: 'Runs', description: 'Run trees and recent execution history' },
  { label: 'More', description: 'Skills, memory, diagnostics, and entity editing tools' }
];

const sectionModules: Record<(typeof navSections)[number], AdvancedSection[]> = {
  Chat: ['Launch', 'Approvals', 'Runs', 'Memory'],
  Tasks: ['CRUD'],
  Projects: ['CRUD'],
  Agents: ['CRUD'],
  Skills: ['Skills', 'CRUD'],
  Scheduled: ['Schedules', 'Diagnostics'],
  Sessions: ['Runs', 'Diagnostics'],
  Settings: ['Policy']
};

const defaultModuleBySection: Record<(typeof navSections)[number], AdvancedSection> = {
  Chat: 'Launch',
  Tasks: 'CRUD',
  Projects: 'CRUD',
  Agents: 'CRUD',
  Skills: 'Skills',
  Scheduled: 'Schedules',
  Sessions: 'Diagnostics',
  Settings: 'Policy'
};

const sectionLabels: Record<(typeof navSections)[number], string> = {
  Chat: 'Conversation',
  Tasks: 'Tasks',
  Projects: 'Projects',
  Agents: 'Agents',
  Skills: 'Skills',
  Scheduled: 'Automations',
  Sessions: 'Sessions',
  Settings: 'Settings'
};

const workflowSections: Array<{
  section: (typeof navSections)[number];
  stage: string;
  title: string;
  description: string;
}> = [
  { section: 'Chat', stage: '01', title: 'Define work', description: 'Start from intent, requests, and operator prompts.' },
  { section: 'Tasks', stage: '02', title: 'Shape scope', description: 'Turn intent into tracked work with clear status and priority.' },
  { section: 'Projects', stage: '03', title: 'Anchor context', description: 'Bind work to initiative, threads, and workspace paths.' },
  { section: 'Agents', stage: '04', title: 'Assign execution', description: 'Tune specialists and keep delegation understandable.' },
  { section: 'Skills', stage: '05', title: 'Build capability', description: 'Author, test, and promote reusable learned behavior.' },
  { section: 'Scheduled', stage: '06', title: 'Automate flow', description: 'Run work on a schedule with recovery and visibility.' },
  { section: 'Sessions', stage: '07', title: 'Inspect runs', description: 'Search, replay, and compare execution history.' },
  { section: 'Settings', stage: '08', title: 'Govern safely', description: 'Apply policy, overrides, and kill-switch controls.' }
];

function describeWorkspacePolicy(workspace: WorkspaceSnapshot['workspace'], pendingApprovals: number): string {
  if (workspace.kill_switch) {
    return 'Kill switch armed. Mutations stay gated until it is cleared.';
  }
  if (workspace.autonomy_mode === 'Manual') {
    return 'Manual mode routes all mutations through approvals.';
  }
  if (workspace.autonomy_mode === 'Supervised') {
    return pendingApprovals > 0
      ? `${pendingApprovals} pending approval${pendingApprovals === 1 ? '' : 's'} will be resolved before the next gated action.`
      : 'Supervised mode allows routine work while sensitive changes are gated.';
  }
  if (workspace.autonomy_mode === 'Autonomous') {
    return 'Autonomous mode allows most work to proceed, but critical changes still gate.';
  }
  return 'Full Access allows automated execution unless the kill switch is armed.';
}

export default function App() {
  const [activeSection, setActiveSection] = useState(navSections[0]);
  const [activeTask, setActiveTask] = useState(seedTasks[0].id);
  const [activeChatSessionId, setActiveChatSessionId] = useState(seedChatSessions[0]?.id ?? '');
  const [chatDraft, setChatDraft] = useState('');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatAttachments, setChatAttachments] = useState<ChatAttachment[]>([]);
  const [pendingAttachmentIds, setPendingAttachmentIds] = useState<string[]>([]);
  const [chatThreadState, setChatThreadState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [chatThreadError, setChatThreadError] = useState<string | null>(null);
  const [chatSendState, setChatSendState] = useState<'idle' | 'sending' | 'error'>('idle');
  const [chatSendError, setChatSendError] = useState<string | null>(null);
  const [activeProjectThreadId, setActiveProjectThreadId] = useState(seedProjectThreads[0]?.id ?? '');
  const [activeTab, setActiveTab] = useState<(typeof bottomTabs)[number]>('Logs');
  const [snapshot, setSnapshot] = useState<WorkspaceSnapshot>(fallbackSnapshot);
  const [loadingState, setLoadingState] = useState<'idle' | 'loading' | 'ready' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [advancedSection, setAdvancedSection] = useState<AdvancedSection>('Launch');
  const [eventDraft, setEventDraft] = useState('desktop.checkpoint');
  const [memoryQuery, setMemoryQuery] = useState('persistence event log');
  const [memoryScope, setMemoryScope] = useState('workspace');
  const [memoryRole, setMemoryRole] = useState('orchestrator');
  const [memoryProjectId, setMemoryProjectId] = useState('project-001');
  const [retrieval, setRetrieval] = useState<MemoryRetrievalResult | null>(null);
  const [memoryError, setMemoryError] = useState<string | null>(null);
  const [memoryState, setMemoryState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [memoryBrowser, setMemoryBrowser] = useState<MemoryBrowserResponse | null>(null);
  const [memoryBrowserState, setMemoryBrowserState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [memoryBrowserError, setMemoryBrowserError] = useState<string | null>(null);
  const [memoryReview, setMemoryReview] = useState<MemoryReviewResponse | null>(null);
  const [memoryReviewState, setMemoryReviewState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [memoryReviewError, setMemoryReviewError] = useState<string | null>(null);
  const [launchObjective, setLaunchObjective] = useState('Implement phase 3 orchestration runtime for Gnosys');
  const [launchMode, setLaunchMode] = useState('Supervised');
  const [selectedModel, setSelectedModel] = useState('GPT-5.4');
  const [reasoningStrength, setReasoningStrength] = useState('medium');
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
  const [skillLifecycle, setSkillLifecycle] = useState<SkillLifecycleResponse | null>(null);
  const [skillLifecycleState, setSkillLifecycleState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [skillLifecycleError, setSkillLifecycleError] = useState<string | null>(null);
  const [skillTestScenario, setSkillTestScenario] = useState('Inspect the selected skill against a realistic workflow.');
  const [skillTestExpectedOutcome, setSkillTestExpectedOutcome] = useState('The skill produces a clear, actionable result and passes the lifecycle check.');
  const [policyEntityType, setPolicyEntityType] = useState<'task' | 'project' | 'skill' | 'schedule'>('project');
  const [policyEntityId, setPolicyEntityId] = useState('project-001');
  const [policyEntityMode, setPolicyEntityMode] = useState('Supervised');
  const [policyEntityKillSwitch, setPolicyEntityKillSwitch] = useState(false);
  const [policyEntityBias, setPolicyEntityBias] = useState('supervised');
  const [policyEntityState, setPolicyEntityState] = useState<'idle' | 'saving' | 'error'>('idle');
  const [policyEntityError, setPolicyEntityError] = useState<string | null>(null);
  const [diagnosticsQuery, setDiagnosticsQuery] = useState('replay');
  const [diagnosticsStatus, setDiagnosticsStatus] = useState('Running');
  const [diagnosticsApprovalRequired, setDiagnosticsApprovalRequired] = useState('any');
  const [diagnosticsProjectId, setDiagnosticsProjectId] = useState('');
  const [diagnosticsProjectThreadId, setDiagnosticsProjectThreadId] = useState('');
  const [diagnosticsChatSessionId, setDiagnosticsChatSessionId] = useState('');
  const [diagnosticsRuns, setDiagnosticsRuns] = useState<DiagnosticsRunListResponse | null>(null);
  const [diagnosticsState, setDiagnosticsState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [diagnosticsError, setDiagnosticsError] = useState<string | null>(null);
  const [replayRunId, setReplayRunId] = useState('');
  const [replay, setReplay] = useState<ReplayResponse | null>(null);
  const [replayState, setReplayState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [replayError, setReplayError] = useState<string | null>(null);

  async function refreshSnapshot() {
    const state = await loadSnapshot();
    setSnapshot(state);
    return state;
  }

  async function refreshChatThread(sessionId = activeChatSessionId) {
    if (!sessionId) {
      setChatMessages([]);
      setChatThreadState('idle');
      setChatThreadError(null);
      return [];
    }
    setChatThreadState('loading');
    setChatThreadError(null);
    try {
      const messages = await loadChatMessages(sessionId);
      setChatMessages(messages);
      setChatThreadState('ready');
      return messages;
    } catch (error) {
      setChatMessages([]);
      setChatThreadError(error instanceof Error ? error.message : 'Failed to load chat thread');
      setChatThreadState('error');
      return [];
    }
  }

  async function refreshChatAttachments(sessionId = activeChatSessionId) {
    if (!sessionId) {
      setChatAttachments([]);
      setPendingAttachmentIds([]);
      return [];
    }
    try {
      const attachments = await loadChatAttachments(sessionId);
      setChatAttachments(attachments);
      return attachments;
    } catch {
      setChatAttachments([]);
      return [];
    }
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

  async function refreshMemoryBrowser(query = memoryQuery, projectId = memoryProjectId) {
    setMemoryBrowserState('loading');
    setMemoryBrowserError(null);
    try {
      const browser = await loadMemoryBrowser(query, projectId || null, 12);
      setMemoryBrowser(browser);
      setMemoryBrowserState('ready');
    } catch (error) {
      setMemoryBrowserError(error instanceof Error ? error.message : 'Failed to load memory browser');
      setMemoryBrowserState('error');
    }
  }

  async function refreshMemoryReview() {
    setMemoryReviewState('loading');
    setMemoryReviewError(null);
    try {
      const review = await loadMemoryReview();
      setMemoryReview(review);
      setMemoryReviewState('ready');
    } catch (error) {
      setMemoryReviewError(error instanceof Error ? error.message : 'Failed to load memory review');
      setMemoryReviewState('error');
    }
  }

  async function sendCurrentChatMessage() {
    const sessionId = activeChatSessionId || snapshot.chat_sessions[0]?.id || '';
    const content = chatDraft.trim();
    if (!sessionId || !content) {
      return;
    }
    setChatSendState('sending');
    setChatSendError(null);
    try {
      await sendChatMessage(sessionId, {
        content,
        selected_model: selectedModel,
        reasoning_strength: reasoningStrength,
        requested_by: 'desktop',
        mode: 'personal',
        attachment_ids: pendingAttachmentIds,
      });
      setChatDraft('');
      setPendingAttachmentIds([]);
      await Promise.all([refreshSnapshot(), refreshChatThread(sessionId), refreshChatAttachments(sessionId)]);
      setChatSendState('idle');
    } catch (error) {
      setChatSendError(error instanceof Error ? error.message : 'Failed to send chat message');
      setChatSendState('error');
    }
  }

  async function runLaunch(objective = launchObjective, mode = launchMode) {
    setLaunchState('loading');
    setLaunchError(null);
    try {
      const result = await launchOrchestration(objective, mode, selectedTask.id, {
        project_id: activeSection === 'Projects' ? selectedProject?.id ?? null : null,
        project_thread_id: activeSection === 'Projects' ? activeProjectThreadId || null : null,
        chat_session_id: activeSection === 'Chat' ? activeChatSessionId || null : null,
      });
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
      await resolveApprovalRequest(approvalId, status);
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

  async function refreshSkillLifecycle(skillId: string) {
    setSkillLifecycleState('loading');
    setSkillLifecycleError(null);
    try {
      const lifecycle = await loadSkillLifecycle(skillId);
      setSkillLifecycle(lifecycle);
      setSkillLifecycleState('ready');
      return lifecycle;
    } catch (error) {
      setSkillLifecycleError(error instanceof Error ? error.message : 'Failed to load skill lifecycle');
      setSkillLifecycleState('error');
      return null;
    }
  }

  async function createLearnedSkillDraft(skillId: string) {
    setSkillLifecycleState('loading');
    setSkillLifecycleError(null);
    try {
      await createSkillDraft(skillId);
      const nextSnapshot = await refreshSnapshot();
      const refreshedSkill = nextSnapshot.skills.find((skill) => skill.parent_skill_id === skillId) ?? nextSnapshot.skills[0] ?? null;
      if (refreshedSkill) {
        setCrudSelectionId(refreshedSkill.id);
        setCrudDraft(buildCrudDraft('skills', refreshedSkill));
        await refreshSkillLifecycle(refreshedSkill.id);
      }
      setCrudState('idle');
      return true;
    } catch (error) {
      setSkillLifecycleError(error instanceof Error ? error.message : 'Failed to create learned skill draft');
      setSkillLifecycleState('error');
      return false;
    }
  }

  async function runSkillTest(skillId: string) {
    setSkillLifecycleState('loading');
    setSkillLifecycleError(null);
    try {
      await testSkill(skillId, {
        scenario: skillTestScenario,
        expected_outcome: skillTestExpectedOutcome,
        requested_by: 'desktop'
      });
      await refreshSnapshot();
      await refreshSkillLifecycle(skillId);
      return true;
    } catch (error) {
      setSkillLifecycleError(error instanceof Error ? error.message : 'Failed to run skill test');
      setSkillLifecycleState('error');
      return false;
    }
  }

  async function promoteSelectedSkill(skillId: string) {
    setSkillLifecycleState('loading');
    setSkillLifecycleError(null);
    try {
      await promoteSkill(skillId);
      const nextSnapshot = await refreshSnapshot();
      const current = nextSnapshot.skills.find((skill) => skill.id === skillId) ?? null;
      if (current) {
        setCrudDraft(buildCrudDraft('skills', current));
        await refreshSkillLifecycle(skillId);
      }
      return true;
    } catch (error) {
      setSkillLifecycleError(error instanceof Error ? error.message : 'Failed to promote skill');
      setSkillLifecycleState('error');
      return false;
    }
  }

  async function rollbackSelectedSkill(skillId: string) {
    setSkillLifecycleState('loading');
    setSkillLifecycleError(null);
    try {
      const restored = await rollbackSkill(skillId);
      const nextSnapshot = await refreshSnapshot();
      const current = nextSnapshot.skills.find((skill) => skill.id === restored.id) ?? restored;
      setCrudSelectionId(current.id);
      setCrudDraft(buildCrudDraft('skills', current));
      await refreshSkillLifecycle(current.id);
      return true;
    } catch (error) {
      setSkillLifecycleError(error instanceof Error ? error.message : 'Failed to roll back skill');
      setSkillLifecycleState('error');
      return false;
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

  async function refreshDiagnosticsRuns(
    query = diagnosticsQuery,
    status = diagnosticsStatus,
    approvalRequired = diagnosticsApprovalRequired,
    projectId = diagnosticsProjectId,
    projectThreadId = diagnosticsProjectThreadId,
    chatSessionId = diagnosticsChatSessionId
  ) {
    setDiagnosticsState('loading');
    setDiagnosticsError(null);
    try {
      const result = await loadDiagnosticsRuns({
        query: query.trim() || undefined,
        status: status === 'Any' ? undefined : status,
        approvalRequired: approvalRequired === 'any' ? undefined : approvalRequired,
        projectId: projectId || undefined,
        projectThreadId: projectThreadId || undefined,
        chatSessionId: chatSessionId || undefined,
        limit: 12
      });
      setDiagnosticsRuns(result);
      if (!replayRunId && result.task_runs[0]) {
        setReplayRunId(result.task_runs[0].id);
      }
      setDiagnosticsState('ready');
    } catch (error) {
      setDiagnosticsError(error instanceof Error ? error.message : 'Failed to load diagnostics runs');
      setDiagnosticsState('error');
    }
  }

  async function promoteReviewItem(itemId: string) {
    try {
      await promoteMemoryItem(itemId);
      await refreshSnapshot();
      await refreshMemoryBrowser(memoryQuery, memoryProjectId);
      await refreshMemoryReview();
      await runMemorySearch(memoryQuery, memoryRole, memoryScope, memoryProjectId);
      setActiveTab('Logs');
    } catch (error) {
      setMemoryReviewError(error instanceof Error ? error.message : 'Failed to promote memory item');
      setMemoryReviewState('error');
    }
  }

  async function archiveReviewItem(itemId: string) {
    try {
      await archiveMemoryItem(itemId);
      await refreshSnapshot();
      await refreshMemoryBrowser(memoryQuery, memoryProjectId);
      await refreshMemoryReview();
      await runMemorySearch(memoryQuery, memoryRole, memoryScope, memoryProjectId);
      setActiveTab('Logs');
    } catch (error) {
      setMemoryReviewError(error instanceof Error ? error.message : 'Failed to archive memory item');
      setMemoryReviewState('error');
    }
  }

  async function pinReviewItem(itemId: string) {
    try {
      await pinMemoryItem(itemId);
      await refreshSnapshot();
      await refreshMemoryBrowser(memoryQuery, memoryProjectId);
      await refreshMemoryReview();
      await runMemorySearch(memoryQuery, memoryRole, memoryScope, memoryProjectId);
      setActiveTab('Logs');
    } catch (error) {
      setMemoryReviewError(error instanceof Error ? error.message : 'Failed to pin memory item');
      setMemoryReviewState('error');
    }
  }

  async function forgetReviewItem(itemId: string) {
    try {
      await forgetMemoryItem(itemId);
      await refreshSnapshot();
      await refreshMemoryBrowser(memoryQuery, memoryProjectId);
      await refreshMemoryReview();
      await runMemorySearch(memoryQuery, memoryRole, memoryScope, memoryProjectId);
      setActiveTab('Logs');
    } catch (error) {
      setMemoryReviewError(error instanceof Error ? error.message : 'Failed to forget memory item');
      setMemoryReviewState('error');
    }
  }

  async function saveCrudItem() {
    const endpoint = crudConfig(crudKind).endpoint;
    const normalized = normalizeCrudDraft(crudKind, crudDraft);
    const creating = crudSelectionId === '' || crudSelectionId === NEW_ITEM_SENTINEL;
    setCrudState('saving');
    setCrudError(null);

    try {
      const saved = await saveCrudResource(endpoint, crudSelectionId, normalized, creating);
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
      await deleteCrudResource(endpoint, crudSelectionId);
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
            agent_runs: state.agent_runs.filter((run) => run.task_run_id === firstRun.id),
            steps: [],
            approvals_required: [],
            summary: firstRun.summary,
            decision: {
              intent_classification: 'general',
              execution_mode: 'task-created',
              delegated_specialists: [],
              invoked_skills: [],
              approvals_triggered: firstRun.approval_required,
              synthesis: firstRun.summary,
            }
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
    void refreshMemoryBrowser('persistence event log', memoryProjectId);
    void runMemorySearch('persistence event log', 'orchestrator', 'workspace', memoryProjectId);
    void refreshMemoryReview();
    void refreshDiagnosticsRuns('replay', 'Running', 'any');

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
    if (!activeChatSessionId || !snapshot.chat_sessions.some((session) => session.id === activeChatSessionId)) {
      setActiveChatSessionId(snapshot.chat_sessions[0]?.id ?? '');
    }
  }, [activeChatSessionId, snapshot.chat_sessions]);

  useEffect(() => {
    let cancelled = false;
    if (!activeChatSessionId) {
      setChatMessages([]);
      setChatThreadState('idle');
      setChatThreadError(null);
      return () => {
        cancelled = true;
      };
    }

    async function loadThread() {
      setChatThreadState('loading');
      setChatThreadError(null);
      try {
        const messages = await loadChatMessages(activeChatSessionId);
        if (cancelled) {
          return;
        }
        setChatMessages(messages);
        setChatThreadState('ready');
      } catch (error) {
        if (cancelled) {
          return;
        }
        setChatMessages([]);
        setChatThreadError(error instanceof Error ? error.message : 'Failed to load chat thread');
        setChatThreadState('error');
      }
    }

    void loadThread();

    return () => {
      cancelled = true;
    };
  }, [activeChatSessionId]);

  useEffect(() => {
    setPendingAttachmentIds([]);
    void refreshChatAttachments();
  }, [activeChatSessionId]);

  async function uploadChatFiles(files: FileList | null) {
    const sessionId = activeChatSessionId || snapshot.chat_sessions[0]?.id || '';
    if (!sessionId || !files || files.length === 0) {
      return;
    }
    setChatSendError(null);
    try {
      const uploaded = await Promise.all(
        Array.from(files).map((file) =>
          uploadChatAttachment(sessionId, {
            file,
            mode: 'personal',
          })
        )
      );
      setChatAttachments((prev) => [...uploaded, ...prev]);
      setPendingAttachmentIds((prev) => [...prev, ...uploaded.map((item) => item.id)]);
    } catch (error) {
      setChatSendError(error instanceof Error ? error.message : 'Failed to upload attachment');
      setChatSendState('error');
    }
  }

  useEffect(() => {
    const selectedProjectId = memoryProjectId || snapshot.projects[0]?.id || '';
    const threadsForProject = snapshot.project_threads.filter((thread) => thread.project_id === selectedProjectId);
    if (!threadsForProject.some((thread) => thread.id === activeProjectThreadId)) {
      setActiveProjectThreadId(threadsForProject[0]?.id ?? '');
    }
  }, [activeProjectThreadId, memoryProjectId, snapshot.project_threads, snapshot.projects]);

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

  useEffect(() => {
    const nextModule = defaultModuleBySection[activeSection];
    if (advancedSection !== nextModule && !sectionModules[activeSection].includes(advancedSection)) {
      setAdvancedSection(nextModule);
    }

    if (activeSection === 'Tasks' && crudKind !== 'tasks') {
      setCrudKind('tasks');
    } else if (activeSection === 'Projects' && crudKind !== 'projects') {
      setCrudKind('projects');
    } else if (activeSection === 'Agents' && crudKind !== 'agents') {
      setCrudKind('agents');
    } else if (activeSection === 'Skills' && crudKind !== 'skills') {
      setCrudKind('skills');
    } else if (activeSection === 'Scheduled' && crudKind !== 'schedules') {
      setCrudKind('schedules');
    }
  }, [activeSection, advancedSection, crudKind]);

  const selectedTask = useMemo(
    () => snapshot.tasks.find((task) => task.id === activeTask) ?? snapshot.tasks[0] ?? fallbackSnapshot.tasks[0],
    [activeTask, snapshot.tasks]
  );

  const selectedAgent = snapshot.agents[0] ?? fallbackSnapshot.agents[0];
  const activeMemoryLayer = snapshot.memory_layers[0] ?? fallbackSnapshot.memory_layers[0];
  const pendingApprovals = snapshot.approval_requests.filter((request) => request.status === 'pending');
  const currentRun = launchResponse?.task_run ?? snapshot.task_runs[0] ?? null;
  const currentRunTree = currentRun ? buildRunTree(snapshot.agent_runs.filter((run) => run.task_run_id === currentRun.id)) : [];
  const availableProjects = snapshot.projects.length > 0 ? snapshot.projects : fallbackSnapshot.projects;
  const selectedProject = availableProjects.find((project) => project.id === memoryProjectId) ?? availableProjects[0] ?? null;
  const activeChatSession = snapshot.chat_sessions.find((session) => session.id === activeChatSessionId) ?? snapshot.chat_sessions[0] ?? null;
  const selectedSchedule = snapshot.schedules[0] ?? null;
  const latestScheduleRun = snapshot.schedule_runs[0] ?? null;
  const replayTaskRunId = replayRunId || currentRun?.id || snapshot.task_runs[0]?.id || '';
  const selectedProjectPolicy = selectedProject
    ? snapshot.entity_policies.find((policy) => policy.entity_type === 'project' && policy.entity_id === selectedProject.id) ?? null
    : null;
  const activeEntityPolicy = snapshot.entity_policies.find(
    (policy) => policy.entity_type === policyEntityType && policy.entity_id === policyEntityId
  ) ?? null;
  const effectivePolicy = activeEntityPolicy ?? selectedProjectPolicy ?? null;
  const policySummary = describeWorkspacePolicy(snapshot.workspace, pendingApprovals.length);
  const policyScopeLabel =
    activeEntityPolicy !== null
      ? `${policyEntityType} override active`
      : policyEntityType === 'project'
        ? `Project scope follows ${snapshot.workspace.active_project}`
        : 'Workspace scope';
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
  const workspaceTaskSelectionId =
    crudKind === 'tasks' && crudSelectionId && crudSelectionId !== NEW_ITEM_SENTINEL
      ? crudSelectionId
      : selectedTask.id;
  const workspaceProjectSelectionId =
    crudKind === 'projects' && crudSelectionId && crudSelectionId !== NEW_ITEM_SENTINEL
      ? crudSelectionId
      : selectedProject?.id ?? snapshot.projects[0]?.id ?? '';
  const workspaceAgentSelectionId =
    crudKind === 'agents' && crudSelectionId && crudSelectionId !== NEW_ITEM_SENTINEL
      ? crudSelectionId
      : snapshot.agents[0]?.id ?? fallbackSnapshot.agents[0].id;
  const selectedSkill = crudKind === 'skills' && crudSelectionId && crudSelectionId !== NEW_ITEM_SENTINEL
    ? snapshot.skills.find((skill) => skill.id === crudSelectionId) ?? null
    : null;
  const workspaceSkillSelectionId =
    crudKind === 'skills' && crudSelectionId && crudSelectionId !== NEW_ITEM_SENTINEL
      ? crudSelectionId
      : selectedSkill?.id ?? snapshot.skills[0]?.id ?? '';
  const selectedSkillId = selectedSkill?.id ?? null;
  const selectedSkillName = selectedSkill?.name ?? '';
  const replayHistoryRuns = diagnosticsRuns?.task_runs ?? snapshot.task_runs;
  const replayAgentGroups = replay
    ? Object.values(
      replay.agent_runs.reduce<Record<string, { agent_id: string; agent_name: string; runs: AgentRun[] }>>(
        (groups, run) => {
          const key = run.agent_id;
          if (!groups[key]) {
            groups[key] = { agent_id: run.agent_id, agent_name: run.agent_name, runs: [] };
          }
          groups[key].runs.push(run);
          return groups;
        },
        {}
      )
    )
    : [];
  const currentSectionTabs = sectionModules[activeSection]
    .map((moduleLabel) => advancedSections.find((section) => section.label === moduleLabel))
    .filter((section): section is { label: AdvancedSection; description: string } => section !== undefined);
  const projectSwitcherOptions = availableProjects;
  const activeWorkflowIndex = workflowSections.findIndex((item) => item.section === activeSection);
  const activeWorkflow = workflowSections[activeWorkflowIndex] ?? workflowSections[0];
  const nextWorkflow = workflowSections[activeWorkflowIndex + 1] ?? null;
  const dockSummary =
    activeSection === 'Chat'
      ? launchResponse?.summary ?? 'Use the conversation surface to define or refine the next step.'
      : activeSection === 'Tasks'
        ? `${snapshot.tasks.filter((task) => task.status !== 'Completed').length} active tasks remain in the flow.`
        : activeSection === 'Projects'
          ? `${snapshot.project_threads.length} project threads are available to carry context forward.`
          : activeSection === 'Agents'
            ? `${snapshot.agent_runs.length} agent runs recorded across the current workspace.`
            : activeSection === 'Skills'
              ? `${snapshot.skills.length} skills available, ${snapshot.skills.filter((skill) => skill.status === 'active').length} active.`
              : activeSection === 'Scheduled'
                ? `${snapshot.schedules.filter((schedule) => schedule.enabled).length} automations are enabled.`
                : activeSection === 'Sessions'
                  ? `${replayHistoryRuns.length} runs visible for replay and inspection.`
                  : `${pendingApprovals.length} approvals pending under ${snapshot.workspace.autonomy_mode}.`;

  useEffect(() => {
    const lifecycleSkillId = selectedSkillId;
    if (crudKind !== 'skills' || !lifecycleSkillId) {
      setSkillLifecycle(null);
      setSkillLifecycleState('idle');
      setSkillLifecycleError(null);
      return;
    }

    let cancelled = false;
    async function run() {
      setSkillLifecycleState('loading');
      setSkillLifecycleError(null);
      try {
        const skillId = lifecycleSkillId;
        if (!skillId) {
          return;
        }
        const lifecycle = await loadSkillLifecycle(skillId);
        if (cancelled) {
          return;
        }
        setSkillLifecycle(lifecycle);
        setSkillLifecycleState('ready');
      } catch (error) {
        if (cancelled) {
          return;
        }
        setSkillLifecycleError(error instanceof Error ? error.message : 'Failed to load skill lifecycle');
        setSkillLifecycleState('error');
      }
    }

    void run();
    setSkillTestScenario(`Inspect ${selectedSkillName} against its described workflow.`);
    setSkillTestExpectedOutcome(`The ${selectedSkillName} skill should resolve the workflow with a passing lifecycle score.`);

    return () => {
      cancelled = true;
    };
  }, [crudKind, selectedSkillId, selectedSkillName]);

  async function appendCheckpointEvent() {
    await appendEvent({
      type: eventDraft,
      source: 'desktop-shell',
      payload: {
        section: activeSection,
        task_id: selectedTask.id,
        agent_id: selectedAgent.id
      }
    });

    const nextSnapshot = await refreshSnapshot();
    setSnapshot(nextSnapshot);
    setActiveTab('Logs');
    await runMemorySearch(memoryQuery, memoryRole, memoryScope, memoryProjectId);
  }

  function renderMemoryBrowserCards(
    title: string,
    hint: string,
    items: Array<
      MemoryItem & {
        score?: number;
        reason?: string | null;
        recommended_action?: string | null;
        review_reason?: string | null;
      }
    >,
    emptyMessage: string,
  ) {
    return (
      <section className="memory-browser-group">
        <div className="memory-browser-head">
          <strong>{title}</strong>
          <span>{items.length} items</span>
        </div>
        <p className="event-hint">{hint}</p>
        <div className="stack compact">
          {items.map((item) => (
            <article key={item.id} className="memory-card">
              <div className="memory-card-top">
                <strong>{item.title}</strong>
                <span>{item.layer} · {item.state}{item.pinned ? ' · pinned' : ''}</span>
              </div>
              <p>{item.summary}</p>
              <div className="memory-meta">
                <span>{item.scope}</span>
                <span>{item.project_id ?? 'workspace'}</span>
                <span>{item.confidence.toFixed(2)}</span>
                <span>{item.freshness.toFixed(2)}</span>
                {typeof item.score === 'number' ? <span>score {item.score.toFixed(2)}</span> : null}
              </div>
              {(item.review_reason || item.reason) && <p className="event-hint">{item.review_reason ?? item.reason}</p>}
              <div className="crud-actions">
                {item.state === 'candidate' ? (
                  <button className="primary-action" onClick={() => void promoteReviewItem(item.id)}>
                    Promote
                  </button>
                ) : null}
                <button className="tab" onClick={() => void pinReviewItem(item.id)}>
                  Pin
                </button>
                <button className="tab" onClick={() => void archiveReviewItem(item.id)}>
                  Archive
                </button>
                <button className="tab" onClick={() => void forgetReviewItem(item.id)}>
                  Forget
                </button>
              </div>
            </article>
          ))}
          {items.length === 0 && <p>{emptyMessage}</p>}
        </div>
      </section>
    );
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="eyebrow">Workflow console</div>
          <h1>{snapshot.workspace.name}</h1>
          <p>{snapshot.workspace.phase}</p>
          <label className="sidebar-switcher">
            <span className="sidebar-switcher-head">
              <span>Project</span>
              <button
                className="sidebar-add"
                aria-label="Create project"
                title="Create project"
                onClick={() => {
                  setActiveSection('Projects');
                  setCrudKind('projects');
                  startNewCrudItem();
                }}
              >
                +
              </button>
            </span>
            <select
              value={selectedProject?.id ?? ''}
              onChange={(event) => {
                const nextProjectId = event.target.value;
                setMemoryProjectId(nextProjectId);
                setPolicyEntityType('project');
                setPolicyEntityId(nextProjectId);
              }}
            >
              {projectSwitcherOptions.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </label>
        </div>

        <section className="workflow-rail" aria-label="Workflow stages">
          <div className="workflow-rail-head">
            <span className="eyebrow">Flow</span>
            <span>{activeWorkflow.stage}/08</span>
          </div>
          <div className="workflow-list">
            {workflowSections.map((item, index) => {
              const state =
                item.section === activeSection ? 'active' : index < activeWorkflowIndex ? 'complete' : 'upcoming';
              return (
                <button
                  key={item.section}
                  className={`workflow-step workflow-step-${state}`}
                  onClick={() => setActiveSection(item.section)}
                >
                  <span className="workflow-step-stage">{item.stage}</span>
                  <span className="workflow-step-copy">
                    <strong>{item.title}</strong>
                    <span>{item.description}</span>
                  </span>
                </button>
              );
            })}
          </div>
        </section>

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

      <main className={activeSection === 'Chat' ? 'main main-section-chat' : 'main'}>
        {activeSection !== 'Chat' && (
          <section className="shell-topbar">
            <div className="shell-topbar-copy">
              <div className="eyebrow">{activeWorkflow.stage} · {activeWorkflow.title}</div>
              <strong>{sectionLabels[activeSection]} in the active workflow</strong>
              <p>{activeWorkflow.description}</p>
            </div>
            <div className="shell-topbar-meta">
              <span className="status-chip">{snapshot.workspace.autonomy_mode}</span>
              <span>{selectedProject?.name ?? snapshot.workspace.active_project}</span>
              <span>{pendingApprovals.length} approvals</span>
              <span>{snapshot.workspace.kill_switch ? 'kill switch armed' : 'kill switch clear'}</span>
            </div>
            <div className="shell-topbar-next">
              <span className="eyebrow">Next transition</span>
              <strong>{nextWorkflow?.title ?? 'Workflow complete'}</strong>
              <span>{nextWorkflow?.description ?? 'The current section is the final control layer in the flow.'}</span>
            </div>
          </section>
        )}
        {activeSection === 'Chat' ? (
          <>
            <ChatWorkspace
              chatSessions={snapshot.chat_sessions}
              activeChatSessionId={activeChatSessionId}
              messages={chatMessages}
              attachments={chatAttachments}
              pendingAttachmentIds={pendingAttachmentIds}
              threadState={chatThreadState}
              threadError={chatThreadError}
              draft={chatDraft}
              selectedModel={selectedModel}
              reasoningStrength={reasoningStrength}
              sendState={chatSendState}
              sendError={chatSendError}
              onDraftChange={setChatDraft}
              onUploadFiles={(files) => void uploadChatFiles(files)}
              onModelChange={setSelectedModel}
              onReasoningStrengthChange={setReasoningStrength}
              onSend={() => void sendCurrentChatMessage()}
            />
          </>
        ) : activeSection === 'Tasks' ? (
          <TasksWorkspace
            tasks={snapshot.tasks}
            projects={snapshot.projects}
            selectedTaskId={workspaceTaskSelectionId}
            taskDraft={crudKind === 'tasks' ? crudDraft : buildCrudDraft('tasks', selectedTask)}
            crudState={crudState}
            crudError={crudKind === 'tasks' ? crudError : null}
            onSelectTask={(taskId) => {
              setCrudKind('tasks');
              setCrudSelectionId(taskId);
              setActiveTask(taskId);
            }}
            onCreateTask={() => {
              setCrudKind('tasks');
              setActiveTask(snapshot.tasks[0]?.id ?? fallbackSnapshot.tasks[0].id);
              startNewCrudItem();
            }}
            onTaskDraftChange={(field, value) => setCrudDraft((prev) => ({ ...prev, [field]: value }))}
            onSaveTask={() => void saveCrudItem()}
            onDeleteTask={() => void deleteCrudItem()}
            onOpenChat={(prompt) => {
              setActiveSection('Chat');
              setLaunchObjective(prompt);
              setLaunchMode('Supervised');
            }}
            taskRuns={snapshot.task_runs}
          />
        ) : activeSection === 'Projects' ? (
          <ProjectsWorkspace
            projects={snapshot.projects}
            tasks={snapshot.tasks}
            skills={snapshot.skills}
            schedules={snapshot.schedules}
            projectThreads={snapshot.project_threads}
            entityPolicies={snapshot.entity_policies}
            selectedProjectId={workspaceProjectSelectionId}
            activeThreadId={activeProjectThreadId}
            projectDraft={crudKind === 'projects' ? crudDraft : buildCrudDraft('projects', selectedProject)}
            crudState={crudState}
            crudError={crudKind === 'projects' ? crudError : null}
            onSelectProject={(projectId) => {
              setCrudKind('projects');
              setCrudSelectionId(projectId);
              setMemoryProjectId(projectId);
              setPolicyEntityType('project');
              setPolicyEntityId(projectId);
            }}
            onCreateProject={() => {
              setCrudKind('projects');
              startNewCrudItem();
            }}
            onSelectThread={(threadId) => setActiveProjectThreadId(threadId)}
            onCreateThread={() => {
              if (!workspaceProjectSelectionId) {
                return;
              }
              void (async () => {
                const created = await createProjectThread({
                  project_id: workspaceProjectSelectionId,
                  title: `Thread ${snapshot.project_threads.filter((thread) => thread.project_id === workspaceProjectSelectionId).length + 1}`,
                  summary: 'Project-scoped execution thread',
                  status: 'Open'
                });
                const nextSnapshot = await refreshSnapshot();
                setSnapshot(nextSnapshot);
                setActiveProjectThreadId(created.id);
              })();
            }}
            onProjectDraftChange={(field, value) => setCrudDraft((prev) => ({ ...prev, [field]: value }))}
            onSaveProject={() => void saveCrudItem()}
            onDeleteProject={() => void deleteCrudItem()}
          />
        ) : activeSection === 'Sessions' ? (
          <SessionsWorkspace
            recentRuns={replayHistoryRuns}
            currentReplayId={replayRunId || replayTaskRunId}
            replayState={replayState}
            diagnosticsQuery={diagnosticsQuery}
            diagnosticsStatus={diagnosticsStatus}
            diagnosticsApprovalRequired={diagnosticsApprovalRequired}
            diagnosticsProjectId={diagnosticsProjectId}
            diagnosticsProjectThreadId={diagnosticsProjectThreadId}
            diagnosticsChatSessionId={diagnosticsChatSessionId}
            diagnosticsRuns={diagnosticsRuns}
            diagnosticsState={diagnosticsState}
            diagnosticsError={diagnosticsError}
            replayRunId={replayRunId}
            replayTaskRunId={replayTaskRunId}
            replayHistoryRuns={replayHistoryRuns}
            replay={replay}
            replayError={replayError}
            replayAgentGroups={replayAgentGroups}
            selectedProjectName={selectedProject?.name ?? null}
            projects={snapshot.projects}
            projectThreads={snapshot.project_threads}
            chatSessions={snapshot.chat_sessions}
            onDiagnosticsQueryChange={setDiagnosticsQuery}
            onDiagnosticsStatusChange={setDiagnosticsStatus}
            onDiagnosticsApprovalRequiredChange={setDiagnosticsApprovalRequired}
            onDiagnosticsProjectIdChange={setDiagnosticsProjectId}
            onDiagnosticsProjectThreadIdChange={setDiagnosticsProjectThreadId}
            onDiagnosticsChatSessionIdChange={setDiagnosticsChatSessionId}
            onReplayRunIdChange={setReplayRunId}
            onRefreshDiagnosticsRuns={() => void refreshDiagnosticsRuns()}
            onLoadReplay={(runId) => void loadRunReplay(runId)}
          />
        ) : activeSection === 'Agents' ? (
          <AgentsWorkspace
            agents={snapshot.agents}
            agentRuns={snapshot.agent_runs}
            selectedAgentId={workspaceAgentSelectionId}
            agentDraft={crudKind === 'agents' ? crudDraft : buildCrudDraft('agents', snapshot.agents[0] ?? fallbackSnapshot.agents[0])}
            crudState={crudState}
            crudError={crudKind === 'agents' ? crudError : null}
            onSelectAgent={(agentId) => {
              setCrudKind('agents');
              setCrudSelectionId(agentId);
            }}
            onCreateAgent={() => {
              setCrudKind('agents');
              startNewCrudItem();
            }}
            onAgentDraftChange={(field, value) => setCrudDraft((prev) => ({ ...prev, [field]: value }))}
            onSaveAgent={() => void saveCrudItem()}
            onDeleteAgent={() => void deleteCrudItem()}
          />
        ) : activeSection === 'Skills' ? (
          <SkillsWorkspace
            skills={snapshot.skills}
            projects={snapshot.projects}
            selectedSkillId={workspaceSkillSelectionId}
            skillDraft={crudKind === 'skills' ? crudDraft : buildCrudDraft('skills', selectedSkill)}
            crudState={crudState}
            crudError={crudKind === 'skills' ? crudError : null}
            lifecycle={skillLifecycle}
            lifecycleError={skillLifecycleError}
            skillTestScenario={skillTestScenario}
            skillTestExpectedOutcome={skillTestExpectedOutcome}
            onSelectSkill={(skillId) => {
              setCrudKind('skills');
              setCrudSelectionId(skillId);
            }}
            onCreateSkill={() => {
              setCrudKind('skills');
              startNewCrudItem();
            }}
            onSkillDraftChange={(field, value) => setCrudDraft((prev) => ({ ...prev, [field]: value }))}
            onSaveSkill={() => void saveCrudItem()}
            onDeleteSkill={() => void deleteCrudItem()}
            onRefreshLifecycle={() => {
              if (workspaceSkillSelectionId) {
                void refreshSkillLifecycle(workspaceSkillSelectionId);
              }
            }}
            onCreateLearnedDraft={() => {
              if (workspaceSkillSelectionId) {
                void createLearnedSkillDraft(workspaceSkillSelectionId);
              }
            }}
            onRunTest={() => {
              if (workspaceSkillSelectionId) {
                void runSkillTest(workspaceSkillSelectionId);
              }
            }}
            onPromote={() => {
              if (workspaceSkillSelectionId) {
                void promoteSelectedSkill(workspaceSkillSelectionId);
              }
            }}
            onRollback={() => {
              if (workspaceSkillSelectionId) {
                void rollbackSelectedSkill(workspaceSkillSelectionId);
              }
            }}
            onSkillTestScenarioChange={setSkillTestScenario}
            onSkillTestExpectedOutcomeChange={setSkillTestExpectedOutcome}
          />
        ) : activeSection === 'Scheduled' ? (
          <ScheduledWorkspace
            schedules={snapshot.schedules}
            scheduleRuns={snapshot.schedule_runs}
            taskRuns={snapshot.task_runs}
            projects={snapshot.projects}
            projectThreads={snapshot.project_threads}
            chatSessions={snapshot.chat_sessions}
            selectedSchedule={selectedSchedule}
            latestScheduleRun={latestScheduleRun}
            onRunSchedule={(scheduleId) => void executeSchedule(scheduleId)}
            onRetryRun={(runId) => void retryRun(runId)}
            onInspectRun={(runId) => void loadRunReplay(runId)}
          />
        ) : activeSection === 'Settings' ? (
          <SettingsWorkspace
            workspace={snapshot.workspace}
            selectedProject={selectedProject}
            selectedProjectPolicy={selectedProjectPolicy}
            effectivePolicy={effectivePolicy}
            pendingApprovals={pendingApprovals}
            policyState={policyState}
            policyError={policyError}
            workspaceMode={snapshot.workspace.autonomy_mode}
            workspaceKillSwitch={snapshot.workspace.kill_switch}
            onWorkspaceModeChange={(value) => void savePolicyMode(value, snapshot.workspace.kill_switch)}
            onWorkspaceKillSwitchToggle={() => void savePolicyMode(snapshot.workspace.autonomy_mode, !snapshot.workspace.kill_switch)}
            policyEntityType={policyEntityType}
            policyEntityId={policyEntityId}
            policyEntityItems={policyEntityItems}
            policyEntityMode={policyEntityMode}
            policyEntityBias={policyEntityBias}
            policyEntityKillSwitch={policyEntityKillSwitch}
            policyEntityState={policyEntityState}
            policyEntityError={policyEntityError}
            onPolicyEntityTypeChange={(nextType) => {
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
            onPolicyEntityIdChange={setPolicyEntityId}
            onPolicyEntityModeChange={setPolicyEntityMode}
            onPolicyEntityBiasChange={setPolicyEntityBias}
            onPolicyEntityKillSwitchChange={setPolicyEntityKillSwitch}
            onSaveEntityPolicy={() => void saveEntityPolicy()}
          />
        ) : (
          <>
        <header className="hero">
          <div className="hero-copy">
            <div className="eyebrow">Orchestration runtime</div>
            <h2>{sectionLabels[activeSection]} keeps its own working surface.</h2>
            <p>
              {snapshot.workspace.phase}. Each sidebar section now owns its own interface, with nested tools only where that section needs them.
            </p>
          </div>
          <div className="status-pill status-stack">
            <div className="status-pill-head">
              <strong>{snapshot.workspace.autonomy_mode}</strong>
              <span>{snapshot.workspace.status} · {loadingState}</span>
            </div>
            <span>{policyScopeLabel}</span>
            <span>{policySummary}</span>
            <div className="hero-tags" aria-label="Workspace summary">
              <span>{selectedProject?.name ?? snapshot.workspace.active_project}</span>
              <span>{activeMemoryLayer.name}</span>
              <span>{snapshot.counts.task_runs} runs</span>
            </div>
          </div>
        </header>

        <section className="metrics">
          <article>
            <span>Task</span>
            <strong>{selectedTask.title}</strong>
            <p>{selectedTask.summary}</p>
          </article>
          <article>
            <span>Agent</span>
            <strong>{selectedAgent.name}</strong>
            <p>{selectedAgent.role}</p>
          </article>
          <article>
            <span>Memory</span>
            <strong>{activeMemoryLayer.name}</strong>
            <p>{snapshot.counts.memory_items} items available for retrieval.</p>
          </article>
          <article>
            <span>Runs</span>
            <strong>{snapshot.counts.task_runs}</strong>
            <p>{snapshot.counts.agent_runs} agent runs and {snapshot.counts.schedule_runs} schedule runs recorded.</p>
          </article>
          <article>
            <span>Approvals</span>
            <strong>{snapshot.counts.approval_requests}</strong>
            <p>{pendingApprovals.length} requests waiting in the queue.</p>
          </article>
        </section>

        <section className="panel automation-cockpit">
          <div className="panel-title">Automation cockpit</div>
          <div className="automation-grid">
            <div className="automation-card">
              <span>Section</span>
              <strong>{sectionLabels[activeSection]}</strong>
            </div>
            <div className="automation-card">
              <span>Current mode</span>
              <strong>{snapshot.workspace.autonomy_mode}</strong>
            </div>
            <div className="automation-card">
              <span>Pending approvals</span>
              <strong>{pendingApprovals.length}</strong>
            </div>
            <div className="automation-card">
              <span>Selection</span>
              <strong>{selectedProject?.name ?? snapshot.workspace.active_project}</strong>
            </div>
          </div>
          <p className="event-hint">
            Section-level tools stay local to the current surface. This keeps the shell calmer while preserving the underlying orchestration depth.
          </p>

          <div className="advanced-shell">
            <section className="panel advanced-switcher">
              <div className="panel-title">{sectionLabels[activeSection]}</div>
              <div className="advanced-tabs">
                {currentSectionTabs.map((section) => (
                  <button
                    key={section.label}
                    className={section.label === advancedSection ? 'tab active' : 'tab'}
                    onClick={() => setAdvancedSection(section.label)}
                  >
                    {section.label}
                  </button>
                ))}
              </div>
              <p className="event-hint">
                {advancedSections.find((section) => section.label === advancedSection)?.description}
              </p>
            </section>
            <div className="advanced-workspace" data-advanced-section={advancedSection}>
        <section className="panel orchestration-panel" data-pane="Launch">
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

        <section className="panel orchestration-panel" data-pane="Policy">
          <div className="panel-title">Autonomy controls</div>
          <div className="policy-rail">
            <article className="policy-layer">
              <span>Workspace default</span>
              <strong>{snapshot.workspace.autonomy_mode}</strong>
              <p>{snapshot.workspace.approval_bias} approval bias · {snapshot.workspace.kill_switch ? 'kill switch armed' : 'kill switch clear'}</p>
            </article>
            <article className="policy-layer">
              <span>Selected project</span>
              <strong>{selectedProject?.name ?? 'No project selected'}</strong>
              <p>
                {selectedProjectPolicy
                  ? `${selectedProjectPolicy.autonomy_mode} · ${selectedProjectPolicy.approval_bias} · ${selectedProjectPolicy.kill_switch ? 'kill switch armed' : 'kill switch clear'}`
                  : 'Inherits the workspace default.'}
              </p>
            </article>
            <article className="policy-layer">
              <span>Effective policy</span>
              <strong>{effectivePolicy?.autonomy_mode ?? snapshot.workspace.autonomy_mode}</strong>
              <p>
                {effectivePolicy
                  ? (activeEntityPolicy
                    ? `${policyEntityType} override applies to this selection.`
                    : 'Project override applies to this selection.'
                  )
                  : 'Workspace policy applies until a project or entity override is created.'}
              </p>
            </article>
          </div>
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

        <section className="panel orchestration-panel" data-pane="Policy">
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
            Use the selector to edit a project, task, skill, or schedule override. The editor follows the selected project by default, so policy inheritance stays readable.
          </p>
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
                  <span>{policy.project_id ?? 'workspace'}</span>
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

        <section className="panel orchestration-panel" data-pane="Approvals">
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

        <section className="panel orchestration-panel" data-pane="Runs">
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
                      summary: run.summary,
                      decision: {
                        intent_classification: 'general',
                        execution_mode: 'task-created',
                        delegated_specialists: [],
                        invoked_skills: [],
                        approvals_triggered: run.approval_required,
                        synthesis: run.summary,
                      }
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

        <SchedulesPanel
          schedules={snapshot.schedules}
          scheduleRuns={snapshot.schedule_runs}
          taskRuns={snapshot.task_runs}
          projects={snapshot.projects}
          projectThreads={snapshot.project_threads}
          chatSessions={snapshot.chat_sessions}
          selectedSchedule={selectedSchedule}
          latestScheduleRun={latestScheduleRun}
          onRunSchedule={(scheduleId) => void executeSchedule(scheduleId)}
          onRetryRun={(runId) => void retryRun(runId)}
          onInspectRun={(taskRunId) => setReplayRunId(taskRunId)}
        />

        <section className="panel orchestration-panel" data-pane="More">
          <div className="panel-title">More tools</div>
          <p className="event-hint">
            Use these only when you need a deeper surface. They stay out of the main advanced tabs so the normal flow remains compact.
          </p>
          <div className="more-tools-grid">
            <button className="tab" onClick={() => setAdvancedSection('Skills')}>
              Skills
            </button>
            <button className="tab" onClick={() => setAdvancedSection('Memory')}>
              Memory
            </button>
            <button className="tab" onClick={() => setAdvancedSection('Diagnostics')}>
              Diagnostics
            </button>
            <button className="tab" onClick={() => setAdvancedSection('CRUD')}>
              Entity editor
            </button>
          </div>
          <div className="more-tools-grid" style={{ marginTop: '0.75rem' }}>
            <button className="tab" onClick={() => setAdvancedSection('Schedules')}>
              Schedules
            </button>
            <button className="tab" onClick={() => setActiveSection('Chat')}>
              Back to chat
            </button>
          </div>
        </section>

        <section className="panel crud-panel" data-pane="CRUD">
          <div className="panel-title">{crudConfig(crudKind).title} workspace</div>
          <div className="crud-tabs">
            {crudKinds.map((kind) => (
              <button key={kind} className={kind === crudKind ? 'tab active' : 'tab'} onClick={() => setCrudKind(kind)}>
                {crudConfig(kind).title}
              </button>
            ))}
          </div>
          <div className="policy-rail">
            <article className="policy-layer">
              <span>Selected item</span>
              <strong>{activeCrudItem ? String(activeCrudItem.name ?? activeCrudItem.title ?? activeCrudItem.id) : 'Create a new item'}</strong>
              <p>{activeCrudItems.length} {crudConfig(crudKind).title.toLowerCase()} available</p>
            </article>
            <article className="policy-layer">
              <span>Workspace scope</span>
              <strong>{crudConfig(crudKind).title}</strong>
              <p>Each section edits one object at a time so the interface stays readable and intentional.</p>
            </article>
            <article className="policy-layer">
              <span>Project context</span>
              <strong>{selectedProject?.name ?? 'No project selected'}</strong>
              <p>{selectedProjectPolicy ? 'Project policy override is active.' : 'Project context inherits workspace policy.'}</p>
            </article>
          </div>
          <div className="crud-editor single-inspector">
            <div className="crud-form">
              <label>
                Selected {crudConfig(crudKind).title.slice(0, -1).toLowerCase()}
                <select
                  value={crudSelectionId}
                  onChange={(event) => {
                    const nextSelection = event.target.value;
                    setCrudSelectionId(nextSelection);
                    if (nextSelection === NEW_ITEM_SENTINEL) {
                      setCrudDraft({});
                      return;
                    }
                    const nextItem = activeCrudItems.find((item) => item.id === nextSelection);
                    setCrudDraft(nextItem ? buildCrudDraft(crudKind, nextItem) : {});
                  }}
                >
                  <option value={NEW_ITEM_SENTINEL}>Create new</option>
                  {activeCrudItems.map((item) => (
                    <option key={item.id} value={item.id}>
                      {String(item.name ?? item.title ?? item.id)}
                    </option>
                  ))}
                </select>
              </label>
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
                    Approval policy
                    <select value={String(crudDraft.approval_policy ?? 'inherit')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, approval_policy: event.target.value }))}>
                      {scheduleApprovalPolicies.map((policy) => (
                        <option key={policy} value={policy}>
                          {policy}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Failure policy
                    <select value={String(crudDraft.failure_policy ?? 'retry_once')} onChange={(event) => setCrudDraft((prev) => ({ ...prev, failure_policy: event.target.value }))}>
                      {scheduleFailurePolicies.map((policy) => (
                        <option key={policy} value={policy}>
                          {policy}
                        </option>
                      ))}
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
        </section>

        {crudKind === 'skills' && (
          <section className="panel event-panel" data-pane="Skills">
            <div className="panel-title">Skill lifecycle</div>
            <div className="event-controls">
              <button className="primary-action" onClick={() => selectedSkill && void createLearnedSkillDraft(selectedSkill.id)} disabled={!selectedSkill}>
                Create learned draft
              </button>
              <button className="tab" onClick={() => selectedSkill && void refreshSkillLifecycle(selectedSkill.id)} disabled={!selectedSkill}>
                Refresh lifecycle
              </button>
            </div>
            <div className="crud-form" style={{ marginTop: '0.75rem' }}>
              <label>
                Test scenario
                <textarea value={skillTestScenario} onChange={(event) => setSkillTestScenario(event.target.value)} />
              </label>
              <label>
                Expected outcome
                <textarea value={skillTestExpectedOutcome} onChange={(event) => setSkillTestExpectedOutcome(event.target.value)} />
              </label>
            </div>
            <p className="event-hint">
              {selectedSkill
                ? `${selectedSkill.name} is the active selection. ${skillLifecycle?.ready_for_promotion ? 'Ready for promotion.' : 'Not ready for promotion yet.'}`
                : 'Select a skill to inspect drafts, tests, promotion, and rollback.'}
            </p>
            {skillLifecycleError && <p className="error-banner">{skillLifecycleError}</p>}
            {skillLifecycle && selectedSkill && (
              <div className="retrieval-grid">
                <div className="stack compact">
                  <article className="memory-card">
                    <div className="memory-card-top">
                      <strong>{skillLifecycle.skill.name}</strong>
                      <span>{skillLifecycle.lifecycle_state} · {skillLifecycle.ready_for_promotion ? 'ready' : 'not ready'}</span>
                    </div>
                    <p>{skillLifecycle.skill.description}</p>
                    <div className="memory-meta">
                      <span>{skillLifecycle.skill.scope}</span>
                      <span>{skillLifecycle.skill.source_type}</span>
                      <span>{skillLifecycle.skill.version}</span>
                      <span>{skillLifecycle.skill.status}</span>
                      <span>{skillLifecycle.skill.test_status}</span>
                      <span>{(skillLifecycle.skill.test_score ?? 0).toFixed(2)}</span>
                    </div>
                    <p className="event-hint">{skillLifecycle.skill.test_summary || 'No skill test summary recorded yet.'}</p>
                  </article>
                  <article className="memory-card">
                    <div className="memory-card-top">
                      <strong>Lineage</strong>
                      <span>{skillLifecycle.related_skills.length} related skills</span>
                    </div>
                    <p>
                      Parent: {skillLifecycle.parent_skill?.name ?? 'none'}
                    </p>
                    <div className="memory-meta">
                      <span>selected {skillLifecycle.skill.id}</span>
                      <span>parent {skillLifecycle.skill.parent_skill_id ?? 'none'}</span>
                      <span>promoted from {skillLifecycle.skill.promoted_from_skill_id ?? 'none'}</span>
                      <span>latest test {skillLifecycle.skill.latest_test_run_id ?? 'none'}</span>
                    </div>
                  </article>
                </div>
                <aside className="trace-panel">
                  <div className="panel-title">Skill test runs</div>
                  <div className="stack compact">
                    {skillLifecycle.test_runs.map((testRun) => (
                      <div key={testRun.id} className="trace-step">
                        <strong>{testRun.passed ? 'passed' : 'failed'}</strong>
                        <span>{testRun.scenario}</span>
                        <span>{testRun.expected_outcome}</span>
                        <span>{testRun.score.toFixed(2)}</span>
                        <span>{testRun.summary}</span>
                      </div>
                    ))}
                    {skillLifecycle.test_runs.length === 0 && <p>No test runs have been recorded for this skill.</p>}
                  </div>
                </aside>
              </div>
            )}
            <div className="crud-actions">
              <button className="primary-action" onClick={() => selectedSkill && void runSkillTest(selectedSkill.id)} disabled={!selectedSkill}>
                Run test
              </button>
              <button className="tab" onClick={() => selectedSkill && void promoteSelectedSkill(selectedSkill.id)} disabled={!selectedSkill}>
                Promote
              </button>
              <button className="tab" onClick={() => selectedSkill && void rollbackSelectedSkill(selectedSkill.id)} disabled={!selectedSkill}>
                Roll back
              </button>
            </div>
          </section>
        )}

        <section className="panel event-panel" data-pane="Memory">
          <div className="panel-title">Memory browser</div>
          <div className="memory-controls">
            <input
              value={memoryQuery}
              onChange={(event) => setMemoryQuery(event.target.value)}
              aria-label="Memory browser query"
              placeholder="Search memories, sessions, goals, or context"
            />
            <select value={memoryProjectId} onChange={(event) => setMemoryProjectId(event.target.value)}>
              <option value="">All projects</option>
              {snapshot.projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
            <button className="primary-action" onClick={() => void refreshMemoryBrowser()}>
              Refresh browser
            </button>
          </div>
          <p className="event-hint">
            Browse durable memory by layer instead of reconstructing it from diagnostics. {memoryBrowserState === 'ready'
              ? `${memoryBrowser?.total_count ?? 0} items matched, ${memoryBrowser?.daily_memories.length ?? 0} daily, ${memoryBrowser?.long_term_memories.length ?? 0} long-term, ${memoryBrowser?.pinned_memories.length ?? 0} pinned.`
              : `State: ${memoryBrowserState}.`}
          </p>
          {memoryBrowserError && <p className="error-banner">{memoryBrowserError}</p>}
          {memoryBrowserState === 'ready' && memoryBrowser && (
            <div className="memory-browser-grid">
              {renderMemoryBrowserCards(
                'Daily memories',
                'Recent daily rollups from personal sessions and short-term continuity.',
                memoryBrowser.daily_memories,
                'No daily memories matched this filter.',
              )}
              {renderMemoryBrowserCards(
                'Long-term memory',
                'Validated memories the agent can rely on across sessions and workflows.',
                memoryBrowser.long_term_memories,
                'No long-term memories matched this filter.',
              )}
              {renderMemoryBrowserCards(
                'Pinned memory',
                'Protected memories that should stay easy to retrieve and hard to lose.',
                memoryBrowser.pinned_memories,
                'No pinned memories matched this filter.',
              )}
              {renderMemoryBrowserCards(
                'Candidate queue',
                'New or uncertain memories waiting for promotion, curation, or removal.',
                memoryBrowser.candidate_memories,
                'No candidate memories matched this filter.',
              )}
              <section className="memory-browser-group memory-browser-group-wide">
                <div className="memory-browser-head">
                  <strong>Contradictions</strong>
                  <span>{memoryBrowser.contradictions.length} groups</span>
                </div>
                <p className="event-hint">Conflicting memory signatures that need a durable winner.</p>
                <div className="stack compact">
                  {memoryBrowser.contradictions.map((contradiction) => (
                    <article key={contradiction.signature} className="memory-card">
                      <div className="memory-card-top">
                        <strong>{contradiction.signature}</strong>
                        <span>{contradiction.recommended_resolution}</span>
                      </div>
                      <p>{contradiction.reason}</p>
                      <div className="memory-meta">
                        <span>{contradiction.item_count} items</span>
                        <span>winner {contradiction.winner_item_id ?? 'none'}</span>
                        <span>pinned {contradiction.pinned_item_id ?? 'none'}</span>
                      </div>
                    </article>
                  ))}
                  {memoryBrowser.contradictions.length === 0 && <p>No contradictions matched this filter.</p>}
                </div>
              </section>
            </div>
          )}
        </section>

        <section className="panel event-panel" data-pane="Memory">
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

        <section className="panel event-panel" data-pane="Memory">
          <div className="panel-title">Memory review</div>
          <div className="event-controls">
            <button className="primary-action" onClick={() => void refreshMemoryReview()}>
              Refresh review queue
            </button>
            <button className="tab" onClick={() => void refreshMemoryBrowser(memoryQuery, memoryProjectId)}>
              Refresh browser
            </button>
            <button className="tab" onClick={() => void refreshSnapshot()}>
              Refresh workspace
            </button>
          </div>
          <p className="event-hint">
            Candidate memories can be reviewed before promotion. {memoryReviewState === 'ready' ? `${memoryReview?.candidate_count ?? 0} candidates available, ${memoryReview?.pinned_count ?? 0} pinned, ${memoryReview?.contradiction_count ?? 0} contradictions.` : `State: ${memoryReviewState}.`}
          </p>
          {memoryReviewError && <p className="error-banner">{memoryReviewError}</p>}
          {memoryReviewState === 'ready' && memoryReview?.contradictions && memoryReview.contradictions.length > 0 && (
            <div className="stack compact">
              {memoryReview.contradictions.map((contradiction) => (
                <article key={contradiction.signature} className="memory-card">
                  <div className="memory-card-top">
                    <strong>{contradiction.signature}</strong>
                    <span>{contradiction.recommended_resolution}</span>
                  </div>
                  <p>{contradiction.reason}</p>
                  <div className="memory-meta">
                    <span>{contradiction.item_count} items</span>
                    <span>winner {contradiction.winner_item_id ?? 'none'}</span>
                    <span>pinned {contradiction.pinned_item_id ?? 'none'}</span>
                  </div>
                </article>
              ))}
            </div>
          )}
          <div className="stack compact">
            {memoryReview?.items.map((item) => (
              <article key={item.id} className="memory-card">
                <div className="memory-card-top">
                  <strong>{item.title}</strong>
                  <span>{item.layer} · {item.state}{item.pinned ? ' · pinned' : ''}</span>
                </div>
                <p>{item.summary}</p>
                <div className="memory-meta">
                  <span>{item.project_id ?? 'workspace'}</span>
                  <span>{item.confidence.toFixed(2)}</span>
                  <span>{item.freshness.toFixed(2)}</span>
                  <span>{item.recommended_action ?? 'review'}</span>
                </div>
                <p className="event-hint">{item.review_reason ?? item.reason}</p>
                <div className="crud-actions">
                  <button className="primary-action" onClick={() => void promoteReviewItem(item.id)}>
                    Promote
                  </button>
                  <button className="tab" onClick={() => void pinReviewItem(item.id)}>
                    Pin
                  </button>
                  <button className="tab" onClick={() => void archiveReviewItem(item.id)}>
                    Archive
                  </button>
                  <button className="tab" onClick={() => void forgetReviewItem(item.id)}>
                    Forget
                  </button>
                </div>
              </article>
            ))}
            {memoryReview?.items.length === 0 && memoryReviewState === 'ready' && <p>No candidate memories are waiting for review.</p>}
          </div>
        </section>

        <section className="panel event-panel" data-pane="Memory">
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

        <DiagnosticsPanel
          diagnosticsQuery={diagnosticsQuery}
          diagnosticsStatus={diagnosticsStatus}
          diagnosticsApprovalRequired={diagnosticsApprovalRequired}
          diagnosticsProjectId={diagnosticsProjectId}
          diagnosticsProjectThreadId={diagnosticsProjectThreadId}
          diagnosticsChatSessionId={diagnosticsChatSessionId}
          diagnosticsRuns={diagnosticsRuns}
          diagnosticsState={diagnosticsState}
          diagnosticsError={diagnosticsError}
          replayRunId={replayRunId}
          replayTaskRunId={replayTaskRunId}
          replayHistoryRuns={replayHistoryRuns}
          replay={replay}
          replayState={replayState}
          replayError={replayError}
          replayAgentGroups={replayAgentGroups}
          selectedProjectName={selectedProject?.name ?? null}
          projects={snapshot.projects}
          projectThreads={snapshot.project_threads}
          chatSessions={snapshot.chat_sessions}
          onDiagnosticsQueryChange={setDiagnosticsQuery}
          onDiagnosticsStatusChange={setDiagnosticsStatus}
          onDiagnosticsApprovalRequiredChange={setDiagnosticsApprovalRequired}
          onDiagnosticsProjectIdChange={setDiagnosticsProjectId}
          onDiagnosticsProjectThreadIdChange={setDiagnosticsProjectThreadId}
          onDiagnosticsChatSessionIdChange={setDiagnosticsChatSessionId}
          onReplayRunIdChange={setReplayRunId}
          onRefreshDiagnosticsRuns={() => void refreshDiagnosticsRuns()}
          onLoadReplay={(runId) => void loadRunReplay(runId)}
        />
            </div>
          </div>
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
          </>
        )}

        {activeSection !== 'Chat' && (
          <section className="bottom bottom-dock">
            <div className="bottom-dock-head">
              <div>
                <div className="eyebrow">Operations dock</div>
                <strong>{dockSummary}</strong>
              </div>
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
                <div className="dock-grid">
                  <div className="dock-card">
                    <strong>Current stage</strong>
                    <span>{activeWorkflow.title}</span>
                  </div>
                  <div className="dock-card">
                    <strong>Selected project</strong>
                    <span>{selectedProject?.name ?? snapshot.workspace.active_project}</span>
                  </div>
                  <div className="dock-card">
                    <strong>Pending approvals</strong>
                    <span>{pendingApprovals.length}</span>
                  </div>
                  <div className="dock-card">
                    <strong>Recent runs</strong>
                    <span>{snapshot.task_runs.length}</span>
                  </div>
                </div>
              )}
              {activeTab === 'Trace' && (
                <div className="dock-trace">
                  <span>{workflowSections.map((item) => item.title).join(' -> ')}</span>
                </div>
              )}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
