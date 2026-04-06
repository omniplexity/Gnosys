import {
  navSections,
  seedAgents,
  seedMemoryLayers,
  seedTasks,
  workspaceSummary
} from '@gnosys/shared';
import { useState } from 'react';

const bottomTabs = ['Logs', 'Timeline', 'Trace'] as const;

export default function App() {
  const [activeSection, setActiveSection] = useState(navSections[0]);
  const [activeTask, setActiveTask] = useState(seedTasks[0].id);
  const [activeTab, setActiveTab] = useState<(typeof bottomTabs)[number]>('Logs');

  const selectedTask = seedTasks.find((task) => task.id === activeTask) ?? seedTasks[0];

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="eyebrow">Gnosys scaffold</div>
          <h1>{workspaceSummary.name}</h1>
          <p>{workspaceSummary.activeProject}</p>
        </div>

        <nav className="nav" aria-label="Primary navigation">
          {navSections.map((section) => (
            <button
              key={section}
              className={section === activeSection ? 'nav-item active' : 'nav-item'}
              onClick={() => setActiveSection(section)}
            >
              {section}
            </button>
          ))}
        </nav>
      </aside>

      <main className="main">
        <header className="hero">
          <div>
            <div className="eyebrow">Desktop console</div>
            <h2>Chat-first operator workspace, scaffolded from the ground up.</h2>
          </div>
          <div className="status-pill">
            {workspaceSummary.mode} · {workspaceSummary.status}
          </div>
        </header>

        <section className="metrics">
          <article>
            <span>Task</span>
            <strong>{selectedTask.title}</strong>
          </article>
          <article>
            <span>Agent</span>
            <strong>{seedAgents[0].name}</strong>
          </article>
          <article>
            <span>Memory</span>
            <strong>{seedMemoryLayers[0].name}</strong>
          </article>
          <article>
            <span>Mode</span>
            <strong>{workspaceSummary.mode}</strong>
          </article>
        </section>

        <section className="content-grid">
          <section className="panel panel-wide">
            <div className="panel-title">Workspace surface</div>
            <div className="stack">
              {seedTasks.map((task) => (
                <button
                  key={task.id}
                  className={task.id === activeTask ? 'row active' : 'row'}
                  onClick={() => setActiveTask(task.id)}
                >
                  <div>
                    <strong>{task.title}</strong>
                    <span>{task.summary}</span>
                  </div>
                  <div className="row-meta">
                    <span>{task.priority}</span>
                    <span>{task.status}</span>
                  </div>
                </button>
              ))}
            </div>
          </section>

          <aside className="panel inspector">
            <div className="panel-title">Inspector</div>
            <div className="detail">
              <strong>Current section</strong>
              <p>{activeSection}</p>
            </div>
            <div className="detail">
              <strong>Plan</strong>
              <p>{selectedTask.summary}</p>
            </div>
            <div className="detail">
              <strong>Memory</strong>
              <p>{seedMemoryLayers[0].description}</p>
            </div>
          </aside>
        </section>

        <section className="bottom">
          <div className="tabs">
            {bottomTabs.map((tab) => (
              <button
                key={tab}
                className={tab === activeTab ? 'tab active' : 'tab'}
                onClick={() => setActiveTab(tab)}
              >
                {tab}
              </button>
            ))}
          </div>
          <div className="bottom-content">
            {activeTab === 'Logs' && (
              <div className="log">
                <span>Bootstrap complete.</span>
                <span>Shared package wired.</span>
                <span>Backend scaffold ready.</span>
              </div>
            )}
            {activeTab === 'Timeline' && (
              <p>Desktop shell, shared domain layer, backend runtime, and docs are ready for iteration.</p>
            )}
            {activeTab === 'Trace' && (
              <p>recency filter → scope filter → task routing → execution → memory write-back</p>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
