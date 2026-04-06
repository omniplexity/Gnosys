import {
  navSections,
  seedAgents,
  seedMemoryLayers,
  seedTasks,
  workspaceSummary,
  type Agent,
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
    events: number;
  };
};

const fallbackSnapshot: WorkspaceSnapshot = {
  workspace: {
    name: workspaceSummary.name,
    mode: workspaceSummary.mode,
    status: workspaceSummary.status,
    active_project: workspaceSummary.activeProject,
    phase: 'Bootstrap scaffold'
  },
  tasks: seedTasks,
  agents: seedAgents,
  memory_layers: seedMemoryLayers,
  recent_events: [],
  counts: {
    tasks: seedTasks.length,
    agents: seedAgents.length,
    memory_layers: seedMemoryLayers.length,
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

export default function App() {
  const [activeSection, setActiveSection] = useState(navSections[0]);
  const [activeTask, setActiveTask] = useState(seedTasks[0].id);
  const [activeTab, setActiveTab] = useState<(typeof bottomTabs)[number]>('Logs');
  const [snapshot, setSnapshot] = useState<WorkspaceSnapshot>(fallbackSnapshot);
  const [loadingState, setLoadingState] = useState<'idle' | 'loading' | 'ready' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [eventDraft, setEventDraft] = useState('desktop.checkpoint');

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setLoadingState('loading');
      try {
        const state = await loadSnapshot();
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

    const nextSnapshot = await loadSnapshot();
    setSnapshot(nextSnapshot);
    setActiveTab('Logs');
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
            <div className="eyebrow">Local persistence</div>
            <h2>Chat-first operator workspace with a live SQLite-backed state layer.</h2>
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
                {snapshot.counts.tasks} tasks, {snapshot.counts.agents} agents, {snapshot.counts.memory_layers} layers
              </p>
            </div>
          </aside>
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
              <p>Workspace state, tasks, agents, memory layers, and events now persist locally in SQLite.</p>
            )}
            {activeTab === 'Trace' && (
              <p>frontend refresh → backend fetch → sqlite read/write → event log append → UI update</p>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
