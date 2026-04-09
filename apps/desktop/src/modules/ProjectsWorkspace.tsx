import type { EntityPolicy, Project, ProjectThread, Schedule, Skill, Task } from '@gnosys/shared';

type ProjectsWorkspaceProps = {
  projects: Project[];
  tasks: Task[];
  skills: Skill[];
  schedules: Schedule[];
  projectThreads: ProjectThread[];
  entityPolicies: EntityPolicy[];
  selectedProjectId: string;
  activeThreadId: string;
  projectDraft: Record<string, string | boolean>;
  crudState: 'idle' | 'saving' | 'error';
  crudError: string | null;
  onSelectProject: (projectId: string) => void;
  onCreateProject: () => void;
  onSelectThread: (threadId: string) => void;
  onCreateThread: () => void;
  onProjectDraftChange: (field: string, value: string | boolean) => void;
  onSaveProject: () => void;
  onDeleteProject: () => void;
};

export function ProjectsWorkspace({
  projects,
  tasks,
  skills,
  schedules,
  projectThreads,
  entityPolicies,
  selectedProjectId,
  activeThreadId,
  projectDraft,
  crudState,
  crudError,
  onSelectProject,
  onCreateProject,
  onSelectThread,
  onCreateThread,
  onProjectDraftChange,
  onSaveProject,
  onDeleteProject
}: ProjectsWorkspaceProps) {
  const selectedProject = projects.find((project) => project.id === selectedProjectId) ?? projects[0] ?? null;
  const linkedTasks = selectedProject ? tasks.filter((task) => task.project_id === selectedProject.id) : [];
  const linkedSkills = selectedProject ? skills.filter((skill) => skill.project_id === selectedProject.id) : [];
  const linkedSchedules = selectedProject ? schedules.filter((schedule) => schedule.project_id === selectedProject.id) : [];
  const linkedThreads = selectedProject ? projectThreads.filter((thread) => thread.project_id === selectedProject.id) : [];
  const projectPolicy = selectedProject
    ? entityPolicies.find((policy) => policy.entity_type === 'project' && policy.entity_id === selectedProject.id) ?? null
    : null;

  return (
    <section className="section-workspace">
      <header className="workspace-header">
        <div>
          <div className="eyebrow">Projects</div>
          <h2>Give each initiative its own operating surface.</h2>
          <p>Project health, linked assets, and policy context stay together so section switching stays meaningful.</p>
        </div>
        <div className="workspace-actions">
          <details className="workspace-menu">
            <summary className="workspace-menu-trigger">Project actions</summary>
            <div className="workspace-menu-panel">
              <button className="tab workspace-menu-button" onClick={onCreateProject}>
                New project
              </button>
              <button className="tab workspace-menu-button" onClick={onCreateThread} disabled={!selectedProject}>
                New thread
              </button>
            </div>
          </details>
        </div>
      </header>

      <div className="workspace-shell">
        <aside className="workspace-list">
          <div className="workspace-list-head">
            <strong>Projects</strong>
            <span>{projects.length} total</span>
          </div>
          <div className="workspace-list-items">
            {projects.map((project) => (
              <button
                key={project.id}
                className={project.id === selectedProjectId ? 'workspace-list-item active' : 'workspace-list-item'}
                onClick={() => onSelectProject(project.id)}
              >
                <strong>{project.name}</strong>
                <span>{project.status}</span>
                <span>{project.workspace_path}</span>
              </button>
            ))}
          </div>
        </aside>

        <div className="workspace-detail">
          <section className="panel section-panel">
            <div className="section-header">
              <div>
                <div className="panel-title">Project editor</div>
                <p className="event-hint">The selected project owns its description, owner, and lifecycle state here.</p>
              </div>
              <div className="detail-strip">
                <span className="status-chip">{String(projectDraft.status ?? selectedProject?.status ?? 'Planned')}</span>
                <span>{projectPolicy ? `${projectPolicy.autonomy_mode} override` : 'inherits workspace policy'}</span>
                <span>{selectedProject?.workspace_path ?? 'workspace path pending'}</span>
                <span>{crudState === 'saving' ? 'saving' : 'ready'}</span>
              </div>
            </div>
            <div className="workspace-form">
              <label>
                Name
                <input value={String(projectDraft.name ?? selectedProject?.name ?? '')} onChange={(event) => onProjectDraftChange('name', event.target.value)} />
              </label>
              <label>
                Owner
                <input value={String(projectDraft.owner ?? selectedProject?.owner ?? '')} onChange={(event) => onProjectDraftChange('owner', event.target.value)} />
              </label>
              <label className="workspace-form-span">
                Summary
                <textarea value={String(projectDraft.summary ?? selectedProject?.summary ?? '')} onChange={(event) => onProjectDraftChange('summary', event.target.value)} />
              </label>
              <label>
                Status
                <select value={String(projectDraft.status ?? selectedProject?.status ?? 'Planned')} onChange={(event) => onProjectDraftChange('status', event.target.value)}>
                  <option>Active</option>
                  <option>Planned</option>
                  <option>Archived</option>
                </select>
              </label>
            </div>
            <div className="workspace-footer">
              <button className="primary-action" onClick={onSaveProject}>
                {selectedProject ? 'Save project' : 'Create project'}
              </button>
              <button className="tab" onClick={onDeleteProject} disabled={!selectedProject}>
                Delete
              </button>
            </div>
            {crudError && <p className="error-banner">{crudError}</p>}
          </section>

          <section className="panel section-panel">
            <div className="section-header">
              <div>
                <div className="panel-title">Linked modules</div>
                <p className="event-hint">Tasks, skills, and automation remain attached to the selected project instead of hidden behind a generic CRUD kind switch.</p>
              </div>
            </div>
            <div className="workspace-stat-grid">
              <article>
                <span>Tasks</span>
                <strong>{linkedTasks.length}</strong>
              </article>
              <article>
                <span>Skills</span>
                <strong>{linkedSkills.length}</strong>
              </article>
              <article>
                <span>Schedules</span>
                <strong>{linkedSchedules.length}</strong>
              </article>
            </div>
            <details className="workspace-inline-menu" open>
              <summary className="workspace-inline-summary">Threads and task flow</summary>
              <div className="workspace-inline-panel">
                <div className="linked-columns">
                  <div className="linked-column">
                    <strong>Threads</strong>
                    {linkedThreads.map((thread) => (
                      <button
                        key={thread.id}
                        className={thread.id === activeThreadId ? 'workspace-list-item active' : 'workspace-list-item'}
                        onClick={() => onSelectThread(thread.id)}
                      >
                        <strong>{thread.title}</strong>
                        <span>{thread.status}</span>
                        <span>{thread.context_path}</span>
                      </button>
                    ))}
                    {linkedThreads.length === 0 && <p>No project threads yet.</p>}
                  </div>
                  <div className="linked-column">
                    <strong>Task flow</strong>
                    {linkedTasks.slice(0, 5).map((task) => (
                      <div key={task.id} className="linked-row">
                        <span>{task.title}</span>
                        <span>{task.status}</span>
                      </div>
                    ))}
                    {linkedTasks.length === 0 && <p>No tasks are linked yet.</p>}
                  </div>
                  <div className="linked-column">
                    <strong>Context and files</strong>
                    <div className="linked-row">
                      <span>Workspace root</span>
                      <span>{selectedProject?.workspace_path ?? 'pending'}</span>
                    </div>
                    <div className="linked-row">
                      <span>Skills</span>
                      <span>{linkedSkills.length}</span>
                    </div>
                    <div className="linked-row">
                      <span>Automations</span>
                      <span>{linkedSchedules.length}</span>
                    </div>
                  </div>
                </div>
              </div>
            </details>
            <details className="workspace-inline-menu">
              <summary className="workspace-inline-summary">Skills and automations</summary>
              <div className="workspace-inline-panel">
                <div className="linked-columns">
                  <div className="linked-column">
                    <strong>Skills</strong>
                    {linkedSkills.slice(0, 5).map((skill) => (
                      <div key={skill.id} className="linked-row">
                        <span>{skill.name}</span>
                        <span>{skill.status}</span>
                      </div>
                    ))}
                    {linkedSkills.length === 0 && <p>No skills are linked yet.</p>}
                  </div>
                  <div className="linked-column">
                    <strong>Automations</strong>
                    {linkedSchedules.slice(0, 5).map((schedule) => (
                      <div key={schedule.id} className="linked-row">
                        <span>{schedule.name}</span>
                        <span>{schedule.next_run_at ?? 'unscheduled'}</span>
                      </div>
                    ))}
                    {linkedSchedules.length === 0 && <p>No schedules are linked yet.</p>}
                  </div>
                </div>
              </div>
            </details>
          </section>
        </div>
      </div>
    </section>
  );
}
