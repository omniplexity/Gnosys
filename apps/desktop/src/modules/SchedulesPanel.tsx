import { useMemo, useState } from 'react';

import type { WorkspaceSnapshot } from '@gnosys/shared';

type ScheduleModule = 'Overview' | 'History' | 'Recovery';

type SchedulesPanelProps = {
  schedules: WorkspaceSnapshot['schedules'];
  scheduleRuns: WorkspaceSnapshot['schedule_runs'];
  taskRuns: WorkspaceSnapshot['task_runs'];
  projects: WorkspaceSnapshot['projects'];
  projectThreads: WorkspaceSnapshot['project_threads'];
  chatSessions: WorkspaceSnapshot['chat_sessions'];
  selectedSchedule: WorkspaceSnapshot['schedules'][number] | null;
  latestScheduleRun: WorkspaceSnapshot['schedule_runs'][number] | null;
  onRunSchedule: (scheduleId: string) => void;
  onRetryRun: (runId: string) => void;
  onInspectRun: (taskRunId: string) => void;
};

type ScheduleHealth = {
  scheduleId: string;
  latestRun: WorkspaceSnapshot['schedule_runs'][number] | null;
  backoffScheduled: boolean;
  activeRetry: boolean;
  pendingApproval: boolean;
};

function latestRunBySchedule(scheduleRuns: WorkspaceSnapshot['schedule_runs']) {
  return scheduleRuns.reduce<Record<string, WorkspaceSnapshot['schedule_runs'][number]>>((runs, run) => {
    if (!runs[run.schedule_id]) {
      runs[run.schedule_id] = run;
    }
    return runs;
  }, {});
}

export function SchedulesPanel({
  schedules,
  scheduleRuns,
  taskRuns,
  projects,
  projectThreads,
  chatSessions,
  selectedSchedule,
  latestScheduleRun,
  onRunSchedule,
  onRetryRun,
  onInspectRun
}: SchedulesPanelProps) {
  const [module, setModule] = useState<ScheduleModule>('Overview');

  const latestBySchedule = useMemo(() => latestRunBySchedule(scheduleRuns), [scheduleRuns]);
  const taskRunById = useMemo(
    () => taskRuns.reduce<Record<string, WorkspaceSnapshot['task_runs'][number]>>((runs, run) => {
      runs[run.id] = run;
      return runs;
    }, {}),
    [taskRuns]
  );
  const scheduleHealth = useMemo<ScheduleHealth[]>(
    () =>
      schedules.map((schedule) => {
        const latestRun = latestBySchedule[schedule.id] ?? null;
        const pendingApproval = latestRun?.status === 'pending_approval';
        const activeRetry = Boolean(latestRun?.retry_of_run_id) && latestRun?.status === 'running';
        const backoffScheduled = latestRun?.status === 'failed' && Boolean(schedule.next_run_at);
        return {
          scheduleId: schedule.id,
          latestRun,
          backoffScheduled,
          activeRetry,
          pendingApproval
        };
      }),
    [latestBySchedule, schedules]
  );

  const recoveryItems = useMemo(
    () =>
      schedules
        .map((schedule) => {
          const health = scheduleHealth.find((item) => item.scheduleId === schedule.id);
          return { schedule, health: health ?? null };
        })
        .filter(({ health }) => health?.backoffScheduled || health?.activeRetry || health?.pendingApproval),
    [scheduleHealth, schedules]
  );

  return (
    <section className="panel orchestration-panel" data-pane="Schedules">
      <div className="section-header">
        <div>
          <div className="panel-title">Schedule execution</div>
          <p className="event-hint">
            Keep automation visible without turning this surface into a dashboard wall. Run health, recovery, and history stay nested here.
          </p>
        </div>
        <details className="workspace-menu">
          <summary className="workspace-menu-trigger">View mode</summary>
          <div className="workspace-menu-panel">
            {(['Overview', 'History', 'Recovery'] as ScheduleModule[]).map((item) => (
              <button key={item} className={item === module ? 'tab active workspace-menu-button' : 'tab workspace-menu-button'} onClick={() => setModule(item)}>
                {item}
              </button>
            ))}
          </div>
        </details>
      </div>

      {module === 'Overview' && (
        <div className="stack compact">
          {schedules.map((schedule) => {
            const health = scheduleHealth.find((item) => item.scheduleId === schedule.id);
            const latestRun = health?.latestRun ?? null;
            const linkedTaskRun = latestRun?.task_run_id ? taskRunById[latestRun.task_run_id] ?? null : null;
            return (
              <article key={schedule.id} className="run-node">
                <div className="run-node-top">
                  <strong>{schedule.name}</strong>
                  <span>{schedule.target_type} · {schedule.enabled ? 'enabled' : 'disabled'}</span>
                </div>
                <p>{schedule.schedule_expression}</p>
                <div className="run-node-meta">
                  <span>{schedule.timezone}</span>
                  <span>{schedule.approval_policy}</span>
                  <span>{schedule.failure_policy}</span>
                  <span>{schedule.project_id ?? 'workspace'}</span>
                </div>
                <div className="detail-strip">
                  <span className="status-chip">{latestRun ? latestRun.status : 'idle'}</span>
                  <span>{schedule.next_run_at ? `next ${schedule.next_run_at}` : 'no next run scheduled'}</span>
                  <span>{projects.find((project) => project.id === linkedTaskRun?.project_id)?.name ?? 'no project'}</span>
                  <span>{projectThreads.find((thread) => thread.id === linkedTaskRun?.project_thread_id)?.title ?? 'no thread'}</span>
                  <span>{chatSessions.find((session) => session.id === linkedTaskRun?.chat_session_id)?.title ?? 'no session'}</span>
                  {health?.backoffScheduled && <span>retry window armed</span>}
                  {health?.pendingApproval && <span>approval pending</span>}
                  {health?.activeRetry && <span>retry running</span>}
                </div>
                <div className="crud-actions">
                  <button className="primary-action" onClick={() => onRunSchedule(schedule.id)}>
                    Run now
                  </button>
                  {latestRun?.task_run_id && (
                    <button className="tab" onClick={() => onInspectRun(latestRun.task_run_id ?? '')}>
                      Inspect
                    </button>
                  )}
                </div>
              </article>
            );
          })}
          {schedules.length === 0 && <p>No schedules are defined yet.</p>}
        </div>
      )}

      {module === 'History' && (
        <div className="stack compact">
          {scheduleRuns.slice(0, 8).map((run) => (
            <article key={run.id} className="run-node">
              {(() => {
                const linkedTaskRun = run.task_run_id ? taskRunById[run.task_run_id] ?? null : null;
                return (
                  <>
              <div className="run-node-top">
                <strong>{run.schedule_name}</strong>
                <span>{run.status} · attempt {run.attempt_number}</span>
              </div>
              <p>{run.result_summary}</p>
              <div className="run-node-meta">
                <span>{run.target_type}</span>
                <span>{run.requested_by}</span>
                <span>{projects.find((project) => project.id === linkedTaskRun?.project_id)?.name ?? 'no project'}</span>
                <span>{projectThreads.find((thread) => thread.id === linkedTaskRun?.project_thread_id)?.title ?? 'no thread'}</span>
                <span>{chatSessions.find((session) => session.id === linkedTaskRun?.chat_session_id)?.title ?? 'no session'}</span>
                <span>{run.retry_of_run_id ? `retry of ${run.retry_of_run_id}` : 'primary run'}</span>
              </div>
              <div className="crud-actions">
                <button className="tab" onClick={() => onRetryRun(run.id)}>
                  Retry
                </button>
                {run.task_run_id && (
                  <button className="tab" onClick={() => onInspectRun(run.task_run_id ?? '')}>
                    Inspect
                  </button>
                )}
              </div>
                  </>
                );
              })()}
            </article>
          ))}
          {scheduleRuns.length === 0 && <p>No schedule runs have been recorded yet.</p>}
        </div>
      )}

      {module === 'Recovery' && (
        <div className="stack compact">
          {recoveryItems.map(({ schedule, health }) => (
            <article key={schedule.id} className="run-node">
              <div className="run-node-top">
                <strong>{schedule.name}</strong>
                <span>{health?.latestRun?.status ?? 'idle'}</span>
              </div>
              <p>
                {health?.backoffScheduled
                  ? `Retry is deferred until ${schedule.next_run_at}.`
                  : health?.pendingApproval
                    ? 'This schedule is waiting for approval before execution.'
                    : 'A retry is already in flight for this schedule.'}
              </p>
              <div className="detail-strip">
                <span className="status-chip subtle">{schedule.failure_policy}</span>
                <span>{health?.latestRun?.last_error ?? 'no recorded error'}</span>
              </div>
              <div className="crud-actions">
                {health?.latestRun && <button className="tab" onClick={() => onRetryRun(health.latestRun?.id ?? '')}>Retry now</button>}
                {health?.latestRun?.task_run_id && (
                  <button className="tab" onClick={() => onInspectRun(health.latestRun?.task_run_id ?? '')}>
                    Inspect
                  </button>
                )}
              </div>
            </article>
          ))}
          {recoveryItems.length === 0 && <p>No schedules currently need recovery attention.</p>}
        </div>
      )}

      {selectedSchedule && latestScheduleRun && (
        <p className="event-hint">
          Latest run for {selectedSchedule.name}: {latestScheduleRun.status} · {latestScheduleRun.result_summary}
        </p>
      )}
    </section>
  );
}
