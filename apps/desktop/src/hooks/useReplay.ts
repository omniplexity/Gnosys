import { useCallback, useMemo, useState } from 'react';

import type { AgentRun, WorkspaceSnapshot } from '@gnosys/shared';

import { loadDiagnosticsRuns, loadReplay } from '../lib/api';
import type { DiagnosticsRunListResponse, ReplayResponse } from '../lib/api';
import { toErrorMessage } from '../lib/errors';

type AsyncState = 'idle' | 'loading' | 'ready' | 'error';

type UseReplayArgs = {
  snapshot: WorkspaceSnapshot;
  onShowTrace: () => void;
};

export function useReplay({ snapshot, onShowTrace }: UseReplayArgs) {
  const [diagnosticsQuery, setDiagnosticsQuery] = useState('replay');
  const [diagnosticsStatus, setDiagnosticsStatus] = useState('Running');
  const [diagnosticsApprovalRequired, setDiagnosticsApprovalRequired] = useState('any');
  const [diagnosticsProjectId, setDiagnosticsProjectId] = useState('');
  const [diagnosticsProjectThreadId, setDiagnosticsProjectThreadId] = useState('');
  const [diagnosticsChatSessionId, setDiagnosticsChatSessionId] = useState('');
  const [diagnosticsRuns, setDiagnosticsRuns] = useState<DiagnosticsRunListResponse | null>(null);
  const [diagnosticsState, setDiagnosticsState] = useState<AsyncState>('idle');
  const [diagnosticsError, setDiagnosticsError] = useState<string | null>(null);
  const [replayRunId, setReplayRunId] = useState('');
  const [replay, setReplay] = useState<ReplayResponse | null>(null);
  const [replayState, setReplayState] = useState<AsyncState>('idle');
  const [replayError, setReplayError] = useState<string | null>(null);

  const refreshDiagnosticsRuns = useCallback(async (
    query = diagnosticsQuery,
    status = diagnosticsStatus,
    approvalRequired = diagnosticsApprovalRequired,
    projectId = diagnosticsProjectId,
    projectThreadId = diagnosticsProjectThreadId,
    chatSessionId = diagnosticsChatSessionId,
  ) => {
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
        limit: 12,
      });
      setDiagnosticsRuns(result);
      if (!replayRunId && result.task_runs[0]) {
        setReplayRunId(result.task_runs[0].id);
      }
      setDiagnosticsState('ready');
      return result;
    } catch (error) {
      setDiagnosticsError(toErrorMessage(error, 'Failed to load diagnostics runs'));
      setDiagnosticsState('error');
      return null;
    }
  }, [
    diagnosticsApprovalRequired,
    diagnosticsChatSessionId,
    diagnosticsProjectId,
    diagnosticsProjectThreadId,
    diagnosticsQuery,
    diagnosticsStatus,
    replayRunId,
  ]);

  const loadRunReplay = useCallback(async (runId: string) => {
    setReplayState('loading');
    setReplayError(null);
    try {
      const result = await loadReplay(runId);
      setReplay(result);
      setReplayRunId(runId);
      setReplayState('ready');
      onShowTrace();
      return result;
    } catch (error) {
      setReplayError(toErrorMessage(error, 'Failed to load replay'));
      setReplayState('error');
      return null;
    }
  }, [onShowTrace]);

  const replayHistoryRuns = diagnosticsRuns?.task_runs ?? snapshot.task_runs;
  const replayTaskRunId = replayRunId || snapshot.task_runs[0]?.id || '';
  const replayAgentGroups = useMemo(
    () =>
      replay
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
            {},
          ),
        )
        : [],
    [replay],
  );

  return {
    diagnosticsQuery,
    setDiagnosticsQuery,
    diagnosticsStatus,
    setDiagnosticsStatus,
    diagnosticsApprovalRequired,
    setDiagnosticsApprovalRequired,
    diagnosticsProjectId,
    setDiagnosticsProjectId,
    diagnosticsProjectThreadId,
    setDiagnosticsProjectThreadId,
    diagnosticsChatSessionId,
    setDiagnosticsChatSessionId,
    diagnosticsRuns,
    diagnosticsState,
    diagnosticsError,
    replayRunId,
    setReplayRunId,
    replay,
    replayState,
    replayError,
    replayTaskRunId,
    replayHistoryRuns,
    replayAgentGroups,
    refreshDiagnosticsRuns,
    loadRunReplay,
  };
}
