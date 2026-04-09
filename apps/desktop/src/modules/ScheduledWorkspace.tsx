import type { Schedule, ScheduleRun } from '@gnosys/shared';

import { SchedulesPanel } from './SchedulesPanel';

type ScheduledWorkspaceProps = {
  schedules: Schedule[];
  scheduleRuns: ScheduleRun[];
  taskRuns: import('@gnosys/shared').TaskRun[];
  projects: import('@gnosys/shared').Project[];
  projectThreads: import('@gnosys/shared').ProjectThread[];
  chatSessions: import('@gnosys/shared').ChatSession[];
  selectedSchedule: Schedule | null;
  latestScheduleRun: ScheduleRun | null;
  onRunSchedule: (scheduleId: string) => void;
  onRetryRun: (runId: string) => void;
  onInspectRun: (taskRunId: string) => void;
};

export function ScheduledWorkspace(props: ScheduledWorkspaceProps) {
  const armedRetries = props.schedules.filter((schedule) => Boolean(schedule.next_run_at)).length;
  const enabledSchedules = props.schedules.filter((schedule) => schedule.enabled).length;

  return (
    <section className="section-workspace">
      <header className="workspace-header">
        <div>
          <div className="eyebrow">Scheduled</div>
          <h2>Keep automation calm, visible, and recoverable.</h2>
          <p>The schedule surface focuses on run health, recovery windows, and deferred retry state.</p>
        </div>
        <div className="workspace-actions">
          <details className="workspace-menu">
            <summary className="workspace-menu-trigger">Automation summary</summary>
            <div className="workspace-menu-panel workspace-menu-stats">
              <span>{enabledSchedules} enabled</span>
              <span>{armedRetries} retry armed</span>
              <span>{props.scheduleRuns.length} runs recorded</span>
            </div>
          </details>
        </div>
      </header>
      <SchedulesPanel {...props} />
    </section>
  );
}
