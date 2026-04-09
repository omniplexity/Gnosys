import { useState } from 'react';

import type { AgentRun, ChatSession, Project, ProjectThread } from '@gnosys/shared';

import type { DiagnosticsRunListResponse, ReplayResponse } from '../api';

type DiagnosticsModule = 'Search' | 'Replay';

type DiagnosticsPanelProps = {
  diagnosticsQuery: string;
  diagnosticsStatus: string;
  diagnosticsApprovalRequired: string;
  diagnosticsProjectId: string;
  diagnosticsProjectThreadId: string;
  diagnosticsChatSessionId: string;
  diagnosticsRuns: DiagnosticsRunListResponse | null;
  diagnosticsState: 'idle' | 'loading' | 'ready' | 'error';
  diagnosticsError: string | null;
  replayRunId: string;
  replayTaskRunId: string;
  replayHistoryRuns: DiagnosticsRunListResponse['task_runs'];
  replay: ReplayResponse | null;
  replayState: 'idle' | 'loading' | 'ready' | 'error';
  replayError: string | null;
  replayAgentGroups: Array<{ agent_id: string; agent_name: string; runs: AgentRun[] }>;
  selectedProjectName: string | null;
  projects: Project[];
  projectThreads: ProjectThread[];
  chatSessions: ChatSession[];
  onDiagnosticsQueryChange: (value: string) => void;
  onDiagnosticsStatusChange: (value: string) => void;
  onDiagnosticsApprovalRequiredChange: (value: string) => void;
  onDiagnosticsProjectIdChange: (value: string) => void;
  onDiagnosticsProjectThreadIdChange: (value: string) => void;
  onDiagnosticsChatSessionIdChange: (value: string) => void;
  onReplayRunIdChange: (value: string) => void;
  onRefreshDiagnosticsRuns: () => void;
  onLoadReplay: (runId: string) => void;
};

export function DiagnosticsPanel({
  diagnosticsQuery,
  diagnosticsStatus,
  diagnosticsApprovalRequired,
  diagnosticsProjectId,
  diagnosticsProjectThreadId,
  diagnosticsChatSessionId,
  diagnosticsRuns,
  diagnosticsState,
  diagnosticsError,
  replayRunId,
  replayTaskRunId,
  replayHistoryRuns,
  replay,
  replayState,
  replayError,
  replayAgentGroups,
  selectedProjectName,
  projects,
  projectThreads,
  chatSessions,
  onDiagnosticsQueryChange,
  onDiagnosticsStatusChange,
  onDiagnosticsApprovalRequiredChange,
  onDiagnosticsProjectIdChange,
  onDiagnosticsProjectThreadIdChange,
  onDiagnosticsChatSessionIdChange,
  onReplayRunIdChange,
  onRefreshDiagnosticsRuns,
  onLoadReplay
}: DiagnosticsPanelProps) {
  const [module, setModule] = useState<DiagnosticsModule>('Search');

  return (
    <section className="panel event-panel" data-pane="Diagnostics">
      <div className="section-header">
        <div>
          <div className="panel-title">Diagnostics replay</div>
          <p className="event-hint">
            Keep observability split between run search and deep replay so the operator can scan first, inspect second.
          </p>
        </div>
        <details className="workspace-menu">
          <summary className="workspace-menu-trigger">View mode</summary>
          <div className="workspace-menu-panel">
            {(['Search', 'Replay'] as DiagnosticsModule[]).map((item) => (
              <button key={item} className={item === module ? 'tab active workspace-menu-button' : 'tab workspace-menu-button'} onClick={() => setModule(item)}>
                {item}
              </button>
            ))}
          </div>
        </details>
      </div>

      {diagnosticsError && <p className="error-banner">{diagnosticsError}</p>}
      {replayError && <p className="error-banner">{replayError}</p>}

      {module === 'Search' && (
        <>
          <details className="workspace-inline-menu" open>
            <summary className="workspace-inline-summary">Search filters</summary>
            <div className="workspace-inline-panel">
              <div className="event-controls">
                <input value={diagnosticsQuery} onChange={(event) => onDiagnosticsQueryChange(event.target.value)} placeholder="Search run history" />
                <select value={diagnosticsStatus} onChange={(event) => onDiagnosticsStatusChange(event.target.value)}>
                  <option>Any</option>
                  <option>Running</option>
                  <option>Needs Approval</option>
                  <option>Completed</option>
                  <option>Failed</option>
                </select>
                <select value={diagnosticsApprovalRequired} onChange={(event) => onDiagnosticsApprovalRequiredChange(event.target.value)}>
                  <option value="any">Any approval state</option>
                  <option value="true">Approval required</option>
                  <option value="false">No approval required</option>
                </select>
                <select value={diagnosticsProjectId} onChange={(event) => onDiagnosticsProjectIdChange(event.target.value)}>
                  <option value="">All projects</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
                <select value={diagnosticsProjectThreadId} onChange={(event) => onDiagnosticsProjectThreadIdChange(event.target.value)}>
                  <option value="">All project threads</option>
                  {projectThreads
                    .filter((thread) => !diagnosticsProjectId || thread.project_id === diagnosticsProjectId)
                    .map((thread) => (
                      <option key={thread.id} value={thread.id}>
                        {thread.title}
                      </option>
                    ))}
                </select>
                <select value={diagnosticsChatSessionId} onChange={(event) => onDiagnosticsChatSessionIdChange(event.target.value)}>
                  <option value="">All chat sessions</option>
                  {chatSessions.map((session) => (
                    <option key={session.id} value={session.id}>
                      {session.title}
                    </option>
                  ))}
                </select>
                <button className="tab" onClick={onRefreshDiagnosticsRuns}>
                  Search runs
                </button>
              </div>
            </div>
          </details>
          <p className="event-hint">
            {diagnosticsState === 'ready' && diagnosticsRuns
              ? `${diagnosticsRuns.filtered_count} of ${diagnosticsRuns.total_count} runs matched.`
              : `History state: ${diagnosticsState}.`}
          </p>
          <div className="detail-strip">
            <span className="status-chip subtle">
              {diagnosticsRuns ? `${diagnosticsRuns.metrics.completed_task_runs} completed` : 'metrics pending'}
            </span>
            <span>{diagnosticsRuns ? `${diagnosticsRuns.metrics.failed_task_runs} failed` : 'failure metrics pending'}</span>
            <span>{diagnosticsRuns ? `${diagnosticsRuns.metrics.approval_required_task_runs} gated` : 'approval metrics pending'}</span>
          </div>
          <div className="stack compact">
            {replayHistoryRuns.map((run) => (
              <article key={run.id} className="run-node">
                <div className="run-node-top">
                  <strong>{run.objective}</strong>
                  <span>{run.status}</span>
                </div>
                <p>{run.summary}</p>
                <div className="run-node-meta">
                  <span>{run.mode}</span>
                  <span>{run.step_count} steps</span>
                  <span>{run.approval_required ? 'approval required' : 'no approval required'}</span>
                  <span>{projects.find((project) => project.id === run.project_id)?.name ?? 'no project'}</span>
                  <span>{projectThreads.find((thread) => thread.id === run.project_thread_id)?.title ?? 'no thread'}</span>
                  <span>{chatSessions.find((session) => session.id === run.chat_session_id)?.title ?? 'no session'}</span>
                </div>
                <div className="crud-actions">
                  <button className="primary-action" onClick={() => onLoadReplay(run.id)}>
                    Open replay
                  </button>
                </div>
              </article>
            ))}
            {replayHistoryRuns.length === 0 && <p>No runs match the current diagnostics filters.</p>}
          </div>
        </>
      )}

      {module === 'Replay' && (
        <>
          <details className="workspace-inline-menu" open>
            <summary className="workspace-inline-summary">Replay controls</summary>
            <div className="workspace-inline-panel">
              <div className="event-controls">
                <select value={replayRunId} onChange={(event) => onReplayRunIdChange(event.target.value)}>
                  <option value="">Select task run</option>
                  {replayHistoryRuns.map((run) => (
                    <option key={run.id} value={run.id}>
                      {run.id} · {run.status}
                    </option>
                  ))}
                </select>
                <button className="primary-action" onClick={() => onLoadReplay(replayRunId || replayTaskRunId)}>
                  Load replay
                </button>
              </div>
            </div>
          </details>
          <p className="event-hint">Replay status: {replayState}. Active project for memory routing: {selectedProjectName ?? 'none'}.</p>
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
                    <span>{projects.find((project) => project.id === replay.task_run.project_id)?.name ?? 'no project'}</span>
                    <span>{projectThreads.find((thread) => thread.id === replay.task_run.project_thread_id)?.title ?? 'no thread'}</span>
                    <span>{chatSessions.find((session) => session.id === replay.task_run.chat_session_id)?.title ?? 'no session'}</span>
                  </div>
                </article>
                <article className="memory-card">
                  <div className="memory-card-top">
                    <strong>Agent-by-agent trace</strong>
                    <span>{replay.agent_runs.length} runs</span>
                  </div>
                  <div className="stack compact">
                    {replayAgentGroups.map((group) => (
                      <div key={group.agent_id} className="trace-step">
                        <strong>{group.agent_name}</strong>
                        <span>{group.runs.length} runs</span>
                        <span>{group.runs.map((run) => `${run.run_kind}:${run.status}`).join(' · ')}</span>
                      </div>
                    ))}
                  </div>
                </article>
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
                      <span>{run.retry_of_run_id ? `retry of ${run.retry_of_run_id}` : 'primary run'}</span>
                    </div>
                  </article>
                ))}
              </div>
              <aside className="trace-panel">
                <div className="panel-title">Replay timeline</div>
                <div className="stack compact">
                  {replay.timeline.map((entry) => (
                    <div key={`${entry.kind}:${entry.source_id ?? entry.created_at}`} className="trace-step">
                      <strong>{entry.kind}</strong>
                      <span>{entry.label}</span>
                      <span>{entry.detail}</span>
                      <span>{entry.created_at}</span>
                    </div>
                  ))}
                  {replay.timeline.length === 0 && <p>No replay timeline entries were found for this run.</p>}
                </div>
                <div className="panel-title" style={{ marginTop: '1rem' }}>Run comparison</div>
                {replay.comparison ? (
                  <div className="stack compact">
                    <div className="trace-step">
                      <strong>Previous</strong>
                      <span>{replay.comparison.previous_task_run_id ?? 'none'}</span>
                    </div>
                    <div className="trace-step">
                      <strong>Status</strong>
                      <span>{replay.comparison.status_changed ? 'changed' : 'unchanged'}</span>
                    </div>
                    <div className="trace-step">
                      <strong>Summary</strong>
                      <span>{replay.comparison.summary_changed ? 'changed' : 'unchanged'}</span>
                    </div>
                    <div className="trace-step">
                      <strong>Steps</strong>
                      <span>{replay.comparison.step_count_delta >= 0 ? '+' : ''}{replay.comparison.step_count_delta}</span>
                    </div>
                    <div className="trace-step">
                      <strong>Approval</strong>
                      <span>{replay.comparison.approval_required_changed ? 'changed' : 'unchanged'}</span>
                    </div>
                    <div className="trace-step">
                      <strong>Task summary</strong>
                      <span>{replay.comparison.task_summary_changed ? 'changed' : 'unchanged'}</span>
                    </div>
                    <div className="trace-step">
                      <strong>Agent runs</strong>
                      <span>{replay.comparison.agent_run_count_delta >= 0 ? '+' : ''}{replay.comparison.agent_run_count_delta}</span>
                    </div>
                    <div className="trace-step">
                      <strong>Schedule runs</strong>
                      <span>{replay.comparison.schedule_run_count_delta >= 0 ? '+' : ''}{replay.comparison.schedule_run_count_delta}</span>
                    </div>
                    <div className="trace-step">
                      <strong>Timeline</strong>
                      <span>{replay.comparison.timeline_entry_count_delta >= 0 ? '+' : ''}{replay.comparison.timeline_entry_count_delta}</span>
                    </div>
                  </div>
                ) : (
                  <p>No comparison data available.</p>
                )}
              </aside>
            </div>
          )}
        </>
      )}
    </section>
  );
}
