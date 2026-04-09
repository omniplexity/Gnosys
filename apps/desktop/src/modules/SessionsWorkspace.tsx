import type { AgentRun, ChatSession, Project, ProjectThread } from '@gnosys/shared';

import type { DiagnosticsRunListResponse, ReplayResponse } from '../api';
import { DiagnosticsPanel } from './DiagnosticsPanel';

type SessionsWorkspaceProps = {
  recentRuns: DiagnosticsRunListResponse['task_runs'];
  currentReplayId: string;
  replayState: 'idle' | 'loading' | 'ready' | 'error';
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

export function SessionsWorkspace({
  recentRuns,
  currentReplayId,
  replayState,
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
}: SessionsWorkspaceProps) {
  return (
    <section className="section-workspace">
      <header className="workspace-header">
        <div>
          <div className="eyebrow">Sessions</div>
          <h2>Search first, replay second, keep the whole run graph inspectable.</h2>
          <p>Run history and deep diagnostics share one session surface instead of competing with unrelated controls.</p>
        </div>
        <div className="workspace-actions">
          <details className="workspace-menu">
            <summary className="workspace-menu-trigger">Session status</summary>
            <div className="workspace-menu-panel workspace-menu-stats">
              <span>Replay {replayState}</span>
              <span>{recentRuns.length} recent runs</span>
            </div>
          </details>
        </div>
      </header>

      <div className="workspace-shell workspace-shell-wide">
        <aside className="workspace-list">
          <div className="workspace-list-head">
            <strong>Recent runs</strong>
            <span>{recentRuns.length} visible</span>
          </div>
          <div className="workspace-list-items">
            {recentRuns.slice(0, 8).map((run) => (
              <button
                key={run.id}
                className={run.id === currentReplayId ? 'workspace-list-item active' : 'workspace-list-item'}
                onClick={() => onLoadReplay(run.id)}
              >
                <strong>{run.objective}</strong>
                <span>{run.status}</span>
                <span>{run.step_count} steps</span>
              </button>
            ))}
          </div>
        </aside>

        <div className="workspace-detail">
          <section className="panel section-panel">
            <div className="section-header">
              <div>
                <div className="panel-title">Session diagnostics</div>
                <p className="event-hint">This section is dedicated to run search, replay, and execution history.</p>
              </div>
            </div>
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
              selectedProjectName={selectedProjectName}
              projects={projects}
              projectThreads={projectThreads}
              chatSessions={chatSessions}
              onDiagnosticsQueryChange={onDiagnosticsQueryChange}
              onDiagnosticsStatusChange={onDiagnosticsStatusChange}
              onDiagnosticsApprovalRequiredChange={onDiagnosticsApprovalRequiredChange}
              onDiagnosticsProjectIdChange={onDiagnosticsProjectIdChange}
              onDiagnosticsProjectThreadIdChange={onDiagnosticsProjectThreadIdChange}
              onDiagnosticsChatSessionIdChange={onDiagnosticsChatSessionIdChange}
              onReplayRunIdChange={onReplayRunIdChange}
              onRefreshDiagnosticsRuns={onRefreshDiagnosticsRuns}
              onLoadReplay={onLoadReplay}
            />
          </section>
        </div>
      </div>
    </section>
  );
}
