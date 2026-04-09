import type { Agent, AgentRun } from '@gnosys/shared';

type AgentsWorkspaceProps = {
  agents: Agent[];
  agentRuns: AgentRun[];
  selectedAgentId: string;
  agentDraft: Record<string, unknown>;
  crudState: 'idle' | 'saving' | 'error';
  crudError: string | null;
  onSelectAgent: (agentId: string) => void;
  onCreateAgent: () => void;
  onAgentDraftChange: (field: string, value: unknown) => void;
  onSaveAgent: () => void;
  onDeleteAgent: () => void;
};

export function AgentsWorkspace({
  agents,
  agentRuns,
  selectedAgentId,
  agentDraft,
  crudState,
  crudError,
  onSelectAgent,
  onCreateAgent,
  onAgentDraftChange,
  onSaveAgent,
  onDeleteAgent
}: AgentsWorkspaceProps) {
  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId) ?? agents[0] ?? null;
  const relatedRuns = selectedAgent ? agentRuns.filter((run) => run.agent_id === selectedAgent.id).slice(0, 6) : [];

  return (
    <section className="section-workspace">
      <header className="workspace-header">
        <div>
          <div className="eyebrow">Agents</div>
          <h2>Keep specialists legible, bounded, and easy to tune.</h2>
          <p>Each agent gets a clean role editor and a visible recent execution trail.</p>
        </div>
        <div className="workspace-actions">
          <details className="workspace-menu">
            <summary className="workspace-menu-trigger">Agent actions</summary>
            <div className="workspace-menu-panel">
              <button className="tab workspace-menu-button" onClick={onCreateAgent}>
                New agent
              </button>
            </div>
          </details>
        </div>
      </header>

      <div className="workspace-shell">
        <aside className="workspace-list">
          <div className="workspace-list-head">
            <strong>Agent roster</strong>
            <span>{agents.length} total</span>
          </div>
          <div className="workspace-list-items">
            {agents.map((agent) => (
              <button
                key={agent.id}
                className={agent.id === selectedAgentId ? 'workspace-list-item active' : 'workspace-list-item'}
                onClick={() => onSelectAgent(agent.id)}
              >
                <strong>{agent.name}</strong>
                <span>{agent.role}</span>
                <span>{agent.status}</span>
              </button>
            ))}
          </div>
        </aside>

        <div className="workspace-detail">
          <section className="panel section-panel">
            <div className="section-header">
              <div>
                <div className="panel-title">Agent configuration</div>
                <p className="event-hint">This stays lightweight: role, current state, and enough context to keep delegation understandable.</p>
              </div>
              <div className="detail-strip">
                <span className="status-chip">{String(agentDraft.status ?? selectedAgent?.status ?? 'Idle')}</span>
                <span>{crudState === 'saving' ? 'saving' : 'ready'}</span>
              </div>
            </div>
            <div className="workspace-focus-card">
              <strong>{String(agentDraft.name ?? selectedAgent?.name ?? 'Untitled agent')}</strong>
              <p>{String(agentDraft.role ?? selectedAgent?.role ?? 'Define the specialist remit, constraints, and operating style.')}</p>
            </div>
            <details className="workspace-inline-menu" open>
              <summary className="workspace-inline-summary">Edit agent configuration</summary>
              <div className="workspace-inline-panel">
                <div className="workspace-form">
                  <label>
                    Name
                    <input value={String(agentDraft.name ?? selectedAgent?.name ?? '')} onChange={(event) => onAgentDraftChange('name', event.target.value)} />
                  </label>
                  <label>
                    Status
                    <select value={String(agentDraft.status ?? selectedAgent?.status ?? 'Idle')} onChange={(event) => onAgentDraftChange('status', event.target.value)}>
                      <option>Idle</option>
                      <option>Working</option>
                      <option>Waiting</option>
                      <option>Reviewing</option>
                    </select>
                  </label>
                  <label className="workspace-form-span">
                    Role
                    <textarea value={String(agentDraft.role ?? selectedAgent?.role ?? '')} onChange={(event) => onAgentDraftChange('role', event.target.value)} />
                  </label>
                </div>
              </div>
            </details>
            <div className="workspace-footer">
              <button className="primary-action" onClick={onSaveAgent}>
                {selectedAgent ? 'Save agent' : 'Create agent'}
              </button>
              <button className="tab" onClick={onDeleteAgent} disabled={!selectedAgent}>
                Delete
              </button>
            </div>
            {crudError && <p className="error-banner">{crudError}</p>}
          </section>

          <section className="panel section-panel">
            <div className="section-header">
              <div>
                <div className="panel-title">Recent execution</div>
                <p className="event-hint">Bounded execution history stays attached to the specialist instead of hiding in a global replay pane.</p>
              </div>
            </div>
            <div className="stack compact">
              {relatedRuns.map((run) => (
                <article key={run.id} className="run-node">
                  <div className="run-node-top">
                    <strong>{run.run_kind}</strong>
                    <span>{run.status}</span>
                  </div>
                  <p>{run.summary}</p>
                  <div className="run-node-meta">
                    <span>{run.objective}</span>
                    <span>depth {run.recursion_depth}</span>
                    <span>{run.child_count} child runs</span>
                  </div>
                </article>
              ))}
              {relatedRuns.length === 0 && <p>No recent agent runs are recorded for this specialist.</p>}
            </div>
          </section>
        </div>
      </div>
    </section>
  );
}
