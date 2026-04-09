import type { Project, Task, TaskRun } from '@gnosys/shared';

type TasksWorkspaceProps = {
  tasks: Task[];
  projects: Project[];
  selectedTaskId: string;
  taskDraft: Record<string, unknown>;
  crudState: 'idle' | 'saving' | 'error';
  crudError: string | null;
  onSelectTask: (taskId: string) => void;
  onCreateTask: () => void;
  onTaskDraftChange: (field: string, value: unknown) => void;
  onSaveTask: () => void;
  onDeleteTask: () => void;
  onOpenChat: (prompt: string) => void;
  taskRuns: TaskRun[];
};

const boardColumns: Array<Task['status']> = ['Inbox', 'Planned', 'Running', 'Waiting', 'Needs Approval', 'Completed'];

export function TasksWorkspace({
  tasks,
  projects,
  selectedTaskId,
  taskDraft,
  crudState,
  crudError,
  onSelectTask,
  onCreateTask,
  onTaskDraftChange,
  onSaveTask,
  onDeleteTask,
  onOpenChat,
  taskRuns
}: TasksWorkspaceProps) {
  const selectedTask = tasks.find((task) => task.id === selectedTaskId) ?? tasks[0] ?? null;
  const relatedRuns = selectedTask ? taskRuns.filter((run) => run.task_id === selectedTask.id).slice(0, 5) : [];
  const groupedTasks = boardColumns.map((status) => ({
    status,
    items: tasks.filter((task) => task.status === status)
  }));
  const selectedProjectName =
    projects.find((project) => project.id === (taskDraft.project_id || selectedTask?.project_id))?.name ?? 'Workspace';

  return (
    <section className="section-workspace">
      <header className="workspace-header">
        <div>
          <div className="eyebrow">Tasks</div>
          <h2>Keep active work visible, editable, and close to execution.</h2>
          <p>Each task gets a focused editor, recent run context, and a direct path back into chat.</p>
        </div>
        <div className="workspace-actions">
          <details className="workspace-menu">
            <summary className="workspace-menu-trigger">Task actions</summary>
            <div className="workspace-menu-panel">
              <button className="tab workspace-menu-button" onClick={onCreateTask}>
                New task
              </button>
              <button
                className="primary-action workspace-menu-button"
                onClick={() => onOpenChat(`Plan the next execution step for ${selectedTask?.title ?? 'this task'}.`)}
              >
                Open in chat
              </button>
            </div>
          </details>
        </div>
      </header>

      <div className="workspace-shell">
        <div className="workspace-detail">
          <section className="panel section-panel">
            <div className="section-header">
              <div>
                <div className="panel-title">Task board</div>
                <p className="event-hint">A calm Kanban surface keeps status readable at a glance without turning into a dashboard wall.</p>
              </div>
              <div className="detail-strip">
                <span>{tasks.length} tasks</span>
              </div>
            </div>
            <div className="kanban-board">
              {groupedTasks.map((column) => (
                <div key={column.status} className="kanban-column">
                  <div className="kanban-column-head">
                    <strong>{column.status}</strong>
                    <span>{column.items.length}</span>
                  </div>
                  <div className="kanban-column-body">
                    {column.items.map((task) => (
                      <button
                        key={task.id}
                        className={task.id === selectedTaskId ? 'kanban-card active' : 'kanban-card'}
                        onClick={() => onSelectTask(task.id)}
                      >
                        <strong>{task.title}</strong>
                        <span>{task.priority}</span>
                        <span>{projects.find((project) => project.id === task.project_id)?.name ?? 'Workspace'}</span>
                      </button>
                    ))}
                    {column.items.length === 0 && <p>No tasks in this lane.</p>}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="panel section-panel">
            <div className="section-header">
              <div>
                <div className="panel-title">Task editor</div>
                <p className="event-hint">Edit the selected task without dropping into a generic inspector.</p>
              </div>
              <div className="detail-strip">
                <span className="status-chip">{String(taskDraft.status ?? selectedTask?.status ?? 'Inbox')}</span>
                <span>{selectedProjectName}</span>
                <span>{crudState === 'saving' ? 'saving' : 'ready'}</span>
              </div>
            </div>
            <div className="workspace-focus-card">
              <strong>{String(taskDraft.title ?? selectedTask?.title ?? 'Untitled task')}</strong>
              <p>{String(taskDraft.summary ?? selectedTask?.summary ?? 'Add a summary to clarify the operator intent and expected outcome.')}</p>
              <div className="detail-strip">
                <span>{String(taskDraft.priority ?? selectedTask?.priority ?? 'Medium')} priority</span>
                <span>{selectedProjectName}</span>
              </div>
            </div>
            <details className="workspace-inline-menu" open>
              <summary className="workspace-inline-summary">Edit task details</summary>
              <div className="workspace-inline-panel">
                <div className="workspace-form">
                  <label>
                    Title
                    <input value={String(taskDraft.title ?? selectedTask?.title ?? '')} onChange={(event) => onTaskDraftChange('title', event.target.value)} />
                  </label>
                  <label className="workspace-form-span">
                    Summary
                    <textarea value={String(taskDraft.summary ?? selectedTask?.summary ?? '')} onChange={(event) => onTaskDraftChange('summary', event.target.value)} />
                  </label>
                  <label>
                    Status
                    <select value={String(taskDraft.status ?? selectedTask?.status ?? 'Inbox')} onChange={(event) => onTaskDraftChange('status', event.target.value)}>
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
                    <select value={String(taskDraft.priority ?? selectedTask?.priority ?? 'Medium')} onChange={(event) => onTaskDraftChange('priority', event.target.value)}>
                      <option>Low</option>
                      <option>Medium</option>
                      <option>High</option>
                      <option>Critical</option>
                    </select>
                  </label>
                  <label>
                    Project
                    <select value={String(taskDraft.project_id ?? selectedTask?.project_id ?? '')} onChange={(event) => onTaskDraftChange('project_id', event.target.value)}>
                      <option value="">Workspace</option>
                      {projects.map((project) => (
                        <option key={project.id} value={project.id}>
                          {project.name}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              </div>
            </details>
            <div className="workspace-footer">
              <button className="primary-action" onClick={onSaveTask}>
                {selectedTask ? 'Save task' : 'Create task'}
              </button>
              <button className="tab" onClick={onDeleteTask} disabled={!selectedTask}>
                Delete
              </button>
            </div>
            {crudError && <p className="error-banner">{crudError}</p>}
          </section>

          <section className="panel section-panel">
            <div className="section-header">
              <div>
                <div className="panel-title">Execution context</div>
                <p className="event-hint">Recent runs stay attached to the task instead of living in a separate inspector pane.</p>
              </div>
              <div className="detail-strip">
                <span>{relatedRuns.length} recent runs</span>
              </div>
            </div>
            <div className="stack compact">
              {relatedRuns.map((run) => (
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
                  </div>
                </article>
              ))}
              {relatedRuns.length === 0 && <p>No runs have been recorded for this task yet.</p>}
            </div>
          </section>
        </div>
      </div>
    </section>
  );
}
