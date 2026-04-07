# Gnosys Product Requirements Document

## 1. Product Overview

Gnosys is a desktop-native, chat-centered agent workspace designed to solve a core weakness of current LLM systems: poor continuity over time. It combines memory, hierarchical multi-agent execution, task and project management, procedural learning, scheduled workflows, and inspectable execution inside a desktop application.

## 1.1 Current implementation status

As of 2026-04-06, the repository contains a working implementation of the product core.

- implemented: desktop shell, backend runtime, persistence, memory retrieval, orchestration, CRUD, approvals, replay, and memory review
- in progress: schedule automation maturity, memory governance depth, skill lifecycle workflows, and richer diagnostics
- planned: advanced memory intelligence, learned skills, evaluation harnesses, and deeper automation

## 2. Product Thesis

An LLM cannot consistently thrive if it cannot remember properly, retrieve context precisely, adapt to the user and workspace, and accumulate procedural competence over time. Gnosys addresses that gap by making memory, delegation, and observable execution first-class systems.

## 3. Product Principles

- Memory is a core engine, not an add-on.
- Chat is the command surface, not the entire product.
- Agents must have bounded responsibility.
- Retrieval must be contextual.
- Durable memory must be curated.
- Users must be able to inspect what matters.

## 4. Target Users

- developers
- researchers
- technical operators
- power users managing complex, long-running work
- agent builders supervising and improving workflows

## 5. Core Product Goals

- Build a state-of-the-art memory system optimized for recall, precision, personalization, and procedural learning.
- Support hierarchical multi-agent workflows with persistent specialists and ephemeral workers.
- Provide a desktop-native, chat-first workspace with first-class sections for tasks, projects, agents, skills, scheduling, sessions, and settings.
- Support long-running, resumable, and scheduled work.
- Preserve user trust through observability, governable autonomy, and inspectable execution.

## 6. Must-Have Product Scope

### Core desktop workspace

- desktop-native shell
- chat as the default landing view
- left sidebar navigation
- center chat/work area
- right contextual inspector
- bottom drawer for logs and diagnostics
- global navigation for Chat, Tasks, Projects, Agents, Skills, Scheduled, Sessions, Settings

### Memory engine foundation

- multi-tier memory architecture
- active context layer
- episodic memory layer
- semantic memory layer
- procedural memory layer
- personal/workspace memory layer
- layered retrieval pipeline
- provenance and metadata support
- confidence and freshness scoring
- memory inspection UI
- role-conditioned retrieval

### Hierarchical multi-agent foundation

- persistent orchestrator agent
- persistent specialist agents
- ephemeral worker agent spawning
- bounded delegation rules
- parent-child task relationships
- agent role definitions
- explicit task decomposition support
- agent-private scratch memory plus shared scoped memory

### Task and project system

- first-class task objects
- task board with status states
- task assignment to agents
- project grouping and organization
- project-aware context and memory boundaries
- session continuity across project work

### Local execution and tooling

- controlled local execution environment
- file system access with policy constraints
- terminal access with policy constraints
- local artifact creation
- permission prompts for sensitive actions
- read-only and write-enabled execution modes

### Skills and procedural foundations

- skill registry
- authored skill support
- learned skill placeholder/model
- skill metadata and versioning
- project/global skill scope distinction

### Scheduling and sessions

- scheduled task support
- recurring and one-time runs
- session history
- prior run/session inspection

### Human control and safety

- pause/resume/cancel
- approval gates
- autonomy modes
- explain-before-execute behavior for sensitive actions
- kill switch / emergency stop

### Observability

- execution timeline
- logs and diagnostics
- plan inspection
- active agent visibility
- memory retrieval trace at a usable level
- task history

## 7. Functional Requirements Summary

### Memory

- Store active task context separately from durable long-term memory.
- Preserve task episodes, decisions, and prior runs as episodic memory.
- Support distilled semantic memory for high-precision retrieval.
- Support procedural memory for reusable workflows and skills.
- Support user-level, workspace-level, and project-level scopes.
- Assemble context differently depending on the requesting agent role.
- Attach provenance, confidence, freshness, and scope metadata to durable memory.
- Allow users to inspect retrieved memory and understand why it was surfaced.
- Support editing, pinning, and forgetting.
- Distinguish transient, candidate, validated, and archived memory.

### Agents

- Include a persistent orchestrator as the primary user-facing agent.
- Support persistent specialists with identity and continuity.
- Support ephemeral worker agents spawned by specialists for bounded subtasks.
- Enforce recursion depth, child-count, and budget constraints.
- Support parent-child task and reporting relationships.
- Support shared scoped context and agent-private scratch memory.
- Expose agent state and activity through the UI.

### UI

- Default to Chat as the main landing surface.
- Provide first-class sections for Tasks, Projects, Agents, Skills, Scheduled, Sessions, and Settings.
- Provide a contextual inspector showing relevant plan, memory, agent, or task details.
- Provide a task board with distinct states.
- Make active agent work visible while preserving a chat-first experience.
- Support session continuity and return-to-work flows.
- Keep diagnostics accessible without overwhelming the default flow.

### Projects

- Projects must be first-class organizational units.
- Each project must support project-specific memory.
- Each project must support task grouping, history, artifacts, and conventions.
- Projects should support project-specific skill routing and policies.

### Skills

- Skills must be first-class objects.
- Skills must support name, description, scope, version, associated tools, and status.
- The system must distinguish between authored skills and learned skills.
- The system should support testing, promotion, and rollback of skills.

### Scheduling

- The system must support one-time and recurring scheduled tasks.
- Scheduled runs must link to a project, agent, skill, or orchestration flow.
- Scheduled tasks must preserve run history and status.
- The system should support retries, failure notifications, and policy controls.

### Safety and control

- The system must support Manual, Supervised, and Autonomous modes.
- Sensitive actions must support approval gates.
- The system must support pause, resume, and cancel.
- The system must provide a kill switch.
- The system should classify actions by sensitivity and risk.

### Observability

- The system must expose plans, task states, agent activity, and execution logs.
- The system must expose a usable memory retrieval trace.
- The system should support replay, comparison, and richer diagnostics.

## 8. MVP Definition

### V1 must deliver

- desktop shell and navigation
- chat-first workflow
- tasks section
- projects section
- agents section
- skills section
- scheduled section
- sessions section
- settings section
- persistent orchestrator
- 2-4 persistent specialists beyond orchestrator
- ephemeral worker spawning
- foundational multi-tier memory
- memory inspection
- local execution with permissions
- plan and task visibility
- logs and core observability

### V1 success criteria

- Users can resume prior work with meaningful continuity.
- The memory system improves context quality in real usage.
- Persistent specialists feel distinct and useful.
- Worker subagents reduce complexity rather than increasing confusion.
- The task/project structure makes long-running work manageable.
- Users can inspect enough of the system to trust it.

## 9. Open Questions

- What exact promotion rules govern movement from candidate to validated memory?
- How should stale and contradictory memories be resolved in the user experience?
- Which persistent specialists are truly necessary for v1?
- Which specialist should own worker spawning policy?
- How much task and agent information should be shown inline in chat by default?
- Should the agent tree be a dedicated view, a panel, or both?
- Should learned skills first appear only as drafts?
- What level of human approval should be required before activation?
- Should scheduled runs always go through the orchestrator, or may they directly invoke specialists or skills?

## 10. Summary

Gnosys is a desktop-native, chat-first agent IDE and operating console designed around state-of-the-art memory, hierarchical multi-agent execution, and structured, inspectable work management.
