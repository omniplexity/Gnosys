import type { ApprovalRequest, EntityPolicy, Project, WorkspaceSnapshot } from '@gnosys/shared';

type SettingsWorkspaceProps = {
  workspace: WorkspaceSnapshot['workspace'];
  selectedProject: Project | null;
  selectedProjectPolicy: EntityPolicy | null;
  effectivePolicy: EntityPolicy | null;
  pendingApprovals: ApprovalRequest[];
  policyState: 'idle' | 'saving' | 'error';
  policyError: string | null;
  workspaceMode: string;
  workspaceKillSwitch: boolean;
  onWorkspaceModeChange: (value: string) => void;
  onWorkspaceKillSwitchToggle: () => void;
  policyEntityType: 'task' | 'project' | 'skill' | 'schedule';
  policyEntityId: string;
  policyEntityItems: Array<{ id: string; name: string }>;
  policyEntityMode: string;
  policyEntityBias: string;
  policyEntityKillSwitch: boolean;
  policyEntityState: 'idle' | 'saving' | 'error';
  policyEntityError: string | null;
  onPolicyEntityTypeChange: (value: 'task' | 'project' | 'skill' | 'schedule') => void;
  onPolicyEntityIdChange: (value: string) => void;
  onPolicyEntityModeChange: (value: string) => void;
  onPolicyEntityBiasChange: (value: string) => void;
  onPolicyEntityKillSwitchChange: (value: boolean) => void;
  onSaveEntityPolicy: () => void;
};

export function SettingsWorkspace({
  workspace,
  selectedProject,
  selectedProjectPolicy,
  effectivePolicy,
  pendingApprovals,
  policyState,
  policyError,
  workspaceMode,
  workspaceKillSwitch,
  onWorkspaceModeChange,
  onWorkspaceKillSwitchToggle,
  policyEntityType,
  policyEntityId,
  policyEntityItems,
  policyEntityMode,
  policyEntityBias,
  policyEntityKillSwitch,
  policyEntityState,
  policyEntityError,
  onPolicyEntityTypeChange,
  onPolicyEntityIdChange,
  onPolicyEntityModeChange,
  onPolicyEntityBiasChange,
  onPolicyEntityKillSwitchChange,
  onSaveEntityPolicy
}: SettingsWorkspaceProps) {
  return (
    <section className="section-workspace">
      <header className="workspace-header">
        <div>
          <div className="eyebrow">Settings</div>
          <h2>Keep policy understandable before it becomes powerful.</h2>
          <p>Workspace controls, scoped overrides, and approval pressure stay in one clearly labeled control center.</p>
        </div>
      </header>

      <div className="workspace-shell">
        <aside className="workspace-list">
          <div className="workspace-list-head">
            <strong>Current state</strong>
          </div>
          <div className="workspace-list-items">
            <div className="workspace-list-item active">
              <strong>{workspace.autonomy_mode}</strong>
              <span>{workspace.kill_switch ? 'kill switch armed' : 'kill switch clear'}</span>
              <span>{pendingApprovals.length} approvals pending</span>
            </div>
            <div className="workspace-list-item">
              <strong>{selectedProject?.name ?? 'No active project'}</strong>
              <span>{selectedProjectPolicy ? 'project override active' : 'inherits workspace policy'}</span>
              <span>{selectedProject?.workspace_path ?? 'no workspace path'}</span>
            </div>
            <div className="workspace-list-item">
              <strong>{effectivePolicy?.autonomy_mode ?? workspace.autonomy_mode}</strong>
              <span>{effectivePolicy ? 'effective override applies' : 'workspace policy applies'}</span>
            </div>
          </div>
        </aside>

        <div className="workspace-detail">
          <section className="panel section-panel">
            <div className="section-header">
              <div>
                <div className="panel-title">Workspace policy</div>
                <p className="event-hint">A small set of controls governs the main orchestrator behavior.</p>
              </div>
              <div className="detail-strip">
                <span className="status-chip">{policyState}</span>
              </div>
            </div>
            <div className="workspace-focus-card">
              <strong>{workspaceMode}</strong>
              <p>{workspaceKillSwitch ? 'The kill switch is armed. Sensitive work remains blocked until it is cleared.' : 'The kill switch is clear. Policy enforcement is driven by the selected autonomy mode.'}</p>
            </div>
            <details className="workspace-inline-menu" open>
              <summary className="workspace-inline-summary">Adjust workspace policy</summary>
              <div className="workspace-inline-panel">
                <div className="workspace-form">
                  <label>
                    Autonomy mode
                    <select value={workspaceMode} onChange={(event) => onWorkspaceModeChange(event.target.value)}>
                      <option>Manual</option>
                      <option>Supervised</option>
                      <option>Autonomous</option>
                      <option>Full Access</option>
                    </select>
                  </label>
                  <label>
                    Kill switch
                    <button className={workspaceKillSwitch ? 'primary-action danger' : 'tab'} onClick={onWorkspaceKillSwitchToggle}>
                      {workspaceKillSwitch ? 'Disable kill switch' : 'Enable kill switch'}
                    </button>
                  </label>
                </div>
              </div>
            </details>
            {policyError && <p className="error-banner">{policyError}</p>}
          </section>

          <section className="panel section-panel">
            <div className="section-header">
              <div>
                <div className="panel-title">Scoped override</div>
                <p className="event-hint">Project, task, skill, and schedule overrides stay explicit instead of getting buried in mixed controls.</p>
              </div>
              <div className="detail-strip">
                <span className="status-chip subtle">{policyEntityState}</span>
              </div>
            </div>
            <details className="workspace-inline-menu" open>
              <summary className="workspace-inline-summary">Configure scoped override</summary>
              <div className="workspace-inline-panel">
                <div className="workspace-form">
                  <label>
                    Entity type
                    <select value={policyEntityType} onChange={(event) => onPolicyEntityTypeChange(event.target.value as 'task' | 'project' | 'skill' | 'schedule')}>
                      <option value="project">Project</option>
                      <option value="task">Task</option>
                      <option value="skill">Skill</option>
                      <option value="schedule">Schedule</option>
                    </select>
                  </label>
                  <label>
                    Entity
                    <select value={policyEntityId} onChange={(event) => onPolicyEntityIdChange(event.target.value)}>
                      {policyEntityItems.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Autonomy mode
                    <select value={policyEntityMode} onChange={(event) => onPolicyEntityModeChange(event.target.value)}>
                      <option>Manual</option>
                      <option>Supervised</option>
                      <option>Autonomous</option>
                      <option>Full Access</option>
                    </select>
                  </label>
                  <label>
                    Approval bias
                    <select value={policyEntityBias} onChange={(event) => onPolicyEntityBiasChange(event.target.value)}>
                      <option value="manual">manual</option>
                      <option value="supervised">supervised</option>
                      <option value="autonomous">autonomous</option>
                      <option value="full-access">full-access</option>
                    </select>
                  </label>
                  <label>
                    Kill switch
                    <select value={policyEntityKillSwitch ? 'true' : 'false'} onChange={(event) => onPolicyEntityKillSwitchChange(event.target.value === 'true')}>
                      <option value="false">clear</option>
                      <option value="true">armed</option>
                    </select>
                  </label>
                </div>
              </div>
            </details>
            <div className="workspace-footer">
              <button className="primary-action" onClick={onSaveEntityPolicy}>
                Save override
              </button>
            </div>
            {policyEntityError && <p className="error-banner">{policyEntityError}</p>}
          </section>
        </div>
      </div>
    </section>
  );
}
