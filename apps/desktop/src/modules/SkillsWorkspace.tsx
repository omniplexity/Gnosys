import type { Project, Skill } from '@gnosys/shared';

import type { SkillLifecycleResponse } from '../api';

type SkillsWorkspaceProps = {
  skills: Skill[];
  projects: Project[];
  selectedSkillId: string;
  skillDraft: Record<string, unknown>;
  crudState: 'idle' | 'saving' | 'error';
  crudError: string | null;
  lifecycle: SkillLifecycleResponse | null;
  lifecycleError: string | null;
  learningSummary: {
    analyzed_runs: number;
    repeated_patterns: number;
    skipped_patterns: number;
    created_skills: Skill[];
  } | null;
  skillTestScenario: string;
  skillTestExpectedOutcome: string;
  onSelectSkill: (skillId: string) => void;
  onCreateSkill: () => void;
  onSkillDraftChange: (field: string, value: unknown) => void;
  onSaveSkill: () => void;
  onDeleteSkill: () => void;
  onRefreshLifecycle: () => void;
  onCreateLearnedDraft: () => void;
  onLearnFromRuns: () => void;
  onRunTest: () => void;
  onPromote: () => void;
  onRollback: () => void;
  onSkillTestScenarioChange: (value: string) => void;
  onSkillTestExpectedOutcomeChange: (value: string) => void;
};

export function SkillsWorkspace({
  skills,
  projects,
  selectedSkillId,
  skillDraft,
  crudState,
  crudError,
  lifecycle,
  lifecycleError,
  learningSummary,
  skillTestScenario,
  skillTestExpectedOutcome,
  onSelectSkill,
  onCreateSkill,
  onSkillDraftChange,
  onSaveSkill,
  onDeleteSkill,
  onRefreshLifecycle,
  onCreateLearnedDraft,
  onLearnFromRuns,
  onRunTest,
  onPromote,
  onRollback,
  onSkillTestScenarioChange,
  onSkillTestExpectedOutcomeChange
}: SkillsWorkspaceProps) {
  const selectedSkill = skills.find((skill) => skill.id === selectedSkillId) ?? skills[0] ?? null;

  return (
    <section className="section-workspace">
      <header className="workspace-header">
        <div>
          <div className="eyebrow">Skills</div>
          <h2>Build learned capability without losing track of lineage.</h2>
          <p>Authored and learned skills live in one surface with lifecycle, tests, and promotion flow attached.</p>
        </div>
        <div className="workspace-actions">
          <details className="workspace-menu">
            <summary className="workspace-menu-trigger">Skill actions</summary>
            <div className="workspace-menu-panel">
              <button className="tab workspace-menu-button" onClick={onCreateSkill}>
                New skill
              </button>
              <button className="tab workspace-menu-button" onClick={onCreateLearnedDraft} disabled={!selectedSkill}>
                Learned draft
              </button>
              <button className="tab workspace-menu-button" onClick={onLearnFromRuns}>
                Learn from runs
              </button>
            </div>
          </details>
        </div>
      </header>

      <div className="workspace-shell">
        <aside className="workspace-list">
          <div className="workspace-list-head">
            <strong>Skill library</strong>
            <span>{skills.length} total</span>
          </div>
          <div className="workspace-list-items">
            {skills.map((skill) => (
              <button
                key={skill.id}
                className={skill.id === selectedSkillId ? 'workspace-list-item active' : 'workspace-list-item'}
                onClick={() => onSelectSkill(skill.id)}
              >
                <strong>{skill.name}</strong>
                <span>{skill.scope} · {skill.status}</span>
                <span>{projects.find((project) => project.id === skill.project_id)?.name ?? 'Workspace'}</span>
              </button>
            ))}
          </div>
        </aside>

        <div className="workspace-detail">
          <section className="panel section-panel">
            <div className="section-header">
              <div>
                <div className="panel-title">Skill editor</div>
                <p className="event-hint">Scope, source, and project binding stay close to the lifecycle controls.</p>
              </div>
              <div className="detail-strip">
                <span className="status-chip">{String(skillDraft.status ?? selectedSkill?.status ?? 'draft')}</span>
                <span>{lifecycle?.ready_for_promotion ? 'ready for promotion' : 'not ready'}</span>
                <span>{crudState === 'saving' ? 'saving' : 'ready'}</span>
              </div>
            </div>
            <div className="workspace-focus-card">
              <strong>{String(skillDraft.name ?? selectedSkill?.name ?? 'Untitled skill')}</strong>
              <p>{String(skillDraft.description ?? selectedSkill?.description ?? 'Define the capability, when it should be invoked, and what it should produce.')}</p>
              <div className="detail-strip">
                <span>{String(skillDraft.scope ?? selectedSkill?.scope ?? 'workspace')}</span>
                <span>{String(skillDraft.source_type ?? selectedSkill?.source_type ?? 'authored')}</span>
                <span>{String(skillDraft.version ?? selectedSkill?.version ?? '0.1.0')}</span>
                <span>{selectedSkill?.evidence_count ?? 0} evidence</span>
              </div>
            </div>
            <details className="workspace-inline-menu" open>
              <summary className="workspace-inline-summary">Edit skill details</summary>
              <div className="workspace-inline-panel">
                <div className="workspace-form">
                  <label>
                    Name
                    <input value={String(skillDraft.name ?? selectedSkill?.name ?? '')} onChange={(event) => onSkillDraftChange('name', event.target.value)} />
                  </label>
                  <label>
                    Version
                    <input value={String(skillDraft.version ?? selectedSkill?.version ?? '0.1.0')} onChange={(event) => onSkillDraftChange('version', event.target.value)} />
                  </label>
                  <label className="workspace-form-span">
                    Description
                    <textarea value={String(skillDraft.description ?? selectedSkill?.description ?? '')} onChange={(event) => onSkillDraftChange('description', event.target.value)} />
                  </label>
                  <label>
                    Scope
                    <select value={String(skillDraft.scope ?? selectedSkill?.scope ?? 'workspace')} onChange={(event) => onSkillDraftChange('scope', event.target.value)}>
                      <option>workspace</option>
                      <option>project</option>
                      <option>session</option>
                      <option>user</option>
                    </select>
                  </label>
                  <label>
                    Source
                    <select value={String(skillDraft.source_type ?? selectedSkill?.source_type ?? 'authored')} onChange={(event) => onSkillDraftChange('source_type', event.target.value)}>
                      <option>authored</option>
                      <option>learned</option>
                    </select>
                  </label>
                  <label>
                    Status
                    <select value={String(skillDraft.status ?? selectedSkill?.status ?? 'draft')} onChange={(event) => onSkillDraftChange('status', event.target.value)}>
                      <option>draft</option>
                      <option>candidate</option>
                      <option>active</option>
                      <option>deprecated</option>
                      <option>archived</option>
                    </select>
                  </label>
                  <label>
                    Project
                    <select value={String(skillDraft.project_id ?? selectedSkill?.project_id ?? '')} onChange={(event) => onSkillDraftChange('project_id', event.target.value)}>
                      <option value="">Workspace</option>
                      {projects.map((project) => (
                        <option key={project.id} value={project.id}>
                          {project.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="workspace-form-span">
                    Provenance
                    <textarea
                      value={String(skillDraft.provenance_summary ?? selectedSkill?.provenance_summary ?? '')}
                      onChange={(event) => onSkillDraftChange('provenance_summary', event.target.value)}
                    />
                  </label>
                  <label className="workspace-form-span">
                    Invocation hints
                    <textarea
                      value={String(
                        skillDraft.invocation_hints ??
                          selectedSkill?.invocation_hints?.join(', ') ??
                          ''
                      )}
                      onChange={(event) => onSkillDraftChange('invocation_hints', event.target.value)}
                    />
                  </label>
                </div>
              </div>
            </details>
            <div className="workspace-footer">
              <button className="primary-action" onClick={onSaveSkill}>
                {selectedSkill ? 'Save skill' : 'Create skill'}
              </button>
              <button className="tab" onClick={onDeleteSkill} disabled={!selectedSkill}>
                Delete
              </button>
            </div>
            {crudError && <p className="error-banner">{crudError}</p>}
            {lifecycleError && <p className="error-banner">{lifecycleError}</p>}
            {learningSummary && (
              <p className="event-hint">
                Learned {learningSummary.created_skills.length} skills from {learningSummary.analyzed_runs} analyzed runs across {learningSummary.repeated_patterns} repeated patterns.
              </p>
            )}
          </section>

          <section className="panel section-panel">
            <div className="section-header">
              <div>
                <div className="panel-title">Lifecycle and tests</div>
                <p className="event-hint">A small, user-first control surface for testing and promotion.</p>
              </div>
              <details className="workspace-menu">
                <summary className="workspace-menu-trigger">Lifecycle actions</summary>
                <div className="workspace-menu-panel">
                  <button className="tab workspace-menu-button" onClick={onRefreshLifecycle} disabled={!selectedSkill}>
                    Refresh
                  </button>
                  <button className="tab workspace-menu-button" onClick={onPromote} disabled={!selectedSkill}>
                    Promote
                  </button>
                  <button className="tab workspace-menu-button" onClick={onRollback} disabled={!selectedSkill}>
                    Roll back
                  </button>
                </div>
              </details>
            </div>
            <details className="workspace-inline-menu" open>
              <summary className="workspace-inline-summary">Test configuration</summary>
              <div className="workspace-inline-panel">
                <div className="workspace-form">
                  <label className="workspace-form-span">
                    Test scenario
                    <textarea value={skillTestScenario} onChange={(event) => onSkillTestScenarioChange(event.target.value)} />
                  </label>
                  <label className="workspace-form-span">
                    Expected outcome
                    <textarea value={skillTestExpectedOutcome} onChange={(event) => onSkillTestExpectedOutcomeChange(event.target.value)} />
                  </label>
                </div>
              </div>
            </details>
            <div className="workspace-footer">
              <button className="primary-action" onClick={onRunTest} disabled={!selectedSkill}>
                Run test
              </button>
            </div>
            {lifecycle && (
              <div className="stack compact" style={{ marginTop: '16px' }}>
                <article className="run-node">
                  <div className="run-node-top">
                    <strong>{lifecycle.skill.name}</strong>
                    <span>{lifecycle.lifecycle_state}</span>
                  </div>
                  <p>{lifecycle.skill.test_summary || 'No test summary recorded yet.'}</p>
                  <div className="run-node-meta">
                    <span>{lifecycle.skill.test_status}</span>
                    <span>{(lifecycle.skill.test_score ?? 0).toFixed(2)}</span>
                    <span>{lifecycle.parent_skill?.name ?? 'no parent skill'}</span>
                    <span>{lifecycle.skill.evidence_count ?? 0} evidence</span>
                  </div>
                </article>
                {lifecycle.skill.provenance_summary && (
                  <article className="run-node">
                    <div className="run-node-top">
                      <strong>Provenance</strong>
                      <span>{lifecycle.skill.source_type}</span>
                    </div>
                    <p>{lifecycle.skill.provenance_summary}</p>
                    <div className="run-node-meta">
                      {(lifecycle.skill.success_signals ?? []).slice(0, 3).map((signal) => (
                        <span key={signal}>{signal}</span>
                      ))}
                    </div>
                  </article>
                )}
                {lifecycle.evidence.slice(0, 4).map((evidence) => (
                  <article key={evidence.id} className="run-node">
                    <div className="run-node-top">
                      <strong>{evidence.source_kind}</strong>
                      <span>{evidence.success_score.toFixed(2)}</span>
                    </div>
                    <p>{evidence.evidence_summary}</p>
                    <div className="run-node-meta">
                      <span>{evidence.pattern_signature}</span>
                      <span>{evidence.task_run_id ?? evidence.agent_run_id ?? 'workspace run'}</span>
                    </div>
                  </article>
                ))}
                {lifecycle.test_runs.slice(0, 4).map((testRun) => (
                  <article key={testRun.id} className="run-node">
                    <div className="run-node-top">
                      <strong>{testRun.passed ? 'passed' : 'failed'}</strong>
                      <span>{testRun.score.toFixed(2)}</span>
                    </div>
                    <p>{testRun.summary}</p>
                    <div className="run-node-meta">
                      <span>{testRun.scenario}</span>
                      <span>{testRun.expected_outcome}</span>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </section>
  );
}
