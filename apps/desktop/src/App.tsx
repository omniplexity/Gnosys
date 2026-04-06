import {
  navSections,
  seedAgents,
  seedMemoryItems,
  seedMemoryLayers,
  seedTasks,
  workspaceSummary,
  type Agent,
  type MemoryItem,
  type MemoryLayer,
  type Task
} from '@gnosys/shared';
import { useEffect, useMemo, useState } from 'react';

const bottomTabs = ['Logs', 'Timeline', 'Trace'] as const;

type WorkspaceSnapshot = {
  workspace: {
    name: string;
    mode: string;
    status: string;
    active_project: string;
    phase: string;
  };
  tasks: Task[];
  agents: Agent[];
  memory_layers: MemoryLayer[];
  memory_items: MemoryItem[];
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
    memory_layers: number;
    memory_items: number;
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

const fallbackSnapshot: WorkspaceSnapshot = {
  workspace: {
    name: workspaceSummary.name,
    mode: workspaceSummary.mode,
    status: workspaceSummary.status,
    active_project: workspaceSummary.activeProject,
    phase: 'Memory engine foundation'
  },
  tasks: seedTasks,
  agents: seedAgents,
  memory_layers: seedMemoryLayers,
  memory_items: seedMemoryItems,
  recent_events: [],
  counts: {
    tasks: seedTasks.length,
    agents: seedAgents.length,
    memory_layers: seedMemoryLayers.length,
    memory_items: seedMemoryItems.length,
    events: 0
  }
};

async function loadSnapshot(): Promise<WorkspaceSnapshot> {
  const response = await fetch('/api/state');
  if (!response.ok) {
    throw new Error(`Failed to load state: ${response.status}`);
  }
  return (await response.json()) as WorkspaceSnapshot;
}

async function retrieveMemory(query: string, role: string, scope: string | null): Promise<MemoryRetrievalResult> {
  const params = new URLSearchParams({
    query,
    role
  });
  if (scope) {
    params.set('scope', scope);
  }

  const response = await fetch(`/api/memory/retrieve?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`Failed to retrieve memory: ${response.status}`);
  }
  return (await response.json()) as MemoryRetrievalResult;
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
  const [retrieval, setRetrieval] = useState<MemoryRetrievalResult | null>(null);
  const [memoryError, setMemoryError] = useState<string | null>(null);
  const [memoryState, setMemoryState] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');

  async function refreshSnapshot() {
    const state = await loadSnapshot();
    setSnapshot(state);
    return state;
  }

  async function runMemorySearch(query = memoryQuery, role = memoryRole, scope = memoryScope) {
    setMemoryState('loading');
    setMemoryError(null);
    try {
      const result = await retrieveMemory(query, role, scope || null);
      setRetrieval(result);
      setMemoryState('ready');
      setActiveTab('Trace');
    } catch (error) {
      setMemoryError(error instanceof Error ? error.message : 'Failed to retrieve memory');
      setMemoryState('error');
    }
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
    void runMemorySearch('persistence event log', 'orchestrator', 'workspace');

    return () => {
      cancelled = true;
    };
  }, []);

  const selectedTask = useMemo(
    () => snapshot.tasks.find((task) => task.id === activeTask) ?? snapshot.tasks[0] ?? fallbackSnapshot.tasks[0],
    [activeTask, snapshot.tasks]
  );

  const selectedAgent = snapshot.agents[0] ?? fallbackSnapshot.agents[0];
  const activeMemoryLayer = snapshot.memory_layers[0] ?? fallbackSnapshot.memory_layers[0];

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
    await runMemorySearch(memoryQuery, memoryRole, memoryScope);
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
            <div className="eyebrow">Memory engine</div>
            <h2>Local persistence with scoped retrieval, ranked candidates, and explainable traces.</h2>
          </div>
          <div className="status-pill">
            {snapshot.workspace.mode} · {snapshot.workspace.status} · {loadingState}
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
            <span>Events</span>
            <strong>{snapshot.counts.events}</strong>
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
              <strong>Persistence phase</strong>
              <p>{snapshot.workspace.phase}</p>
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
              <strong>Retrieval status</strong>
              <p>{memoryState}</p>
            </div>
          </aside>
        </section>

        <section className="panel event-panel">
          <div className="panel-title">Memory retrieval</div>
          <div className="memory-controls">
            <input
              value={memoryQuery}
              onChange={(event) => setMemoryQuery(event.target.value)}
              aria-label="Memory query"
            />
            <select value={memoryScope} onChange={(event) => setMemoryScope(event.target.value)}>
              <option value="">All scopes</option>
              <option value="workspace">Workspace</option>
              <option value="project">Project</option>
              <option value="session">Session</option>
              <option value="user">User</option>
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
              <p className="event-hint">Memory results are ranked against confidence, freshness, scope, and role bias.</p>
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
            <input
              value={eventDraft}
              onChange={(event) => setEventDraft(event.target.value)}
              aria-label="Event type"
            />
            <button className="primary-action" onClick={() => void appendCheckpointEvent()}>
              Record event
            </button>
          </div>
          <p className="event-hint">This writes a durable row into the local SQLite event log and refreshes the UI.</p>
          {errorMessage && <p className="error-banner">{errorMessage}</p>}
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
              <p>Memory engine retrieval now sits on top of the persisted workspace, ready for consolidation and promotion.</p>
            )}
            {activeTab === 'Trace' && (
              <p>frontend query → backend ranking → SQLite read/write → trace explanation → UI refresh</p>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
