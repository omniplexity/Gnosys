# Gnosys Technical Architecture

## 1. Architecture Goals

The architecture should support:

- durable local-first operation
- strong memory quality and retrieval flexibility
- bounded hierarchical agent execution
- inspectability and replayability
- project-aware and schedule-aware workflows
- modular growth without monolithic coupling

## 2. Major Subsystems

- Desktop Application Shell
- Workspace and State Management Layer
- Orchestration and Agent Runtime
- Memory Platform
- Skills Platform
- Task and Scheduling Platform
- Tool Execution Layer
- Observability and Event Log Layer
- Policy and Permissions Layer
- Persistence Layer

Current scaffold mapping:

- `apps/desktop/` owns the desktop application shell
- `apps/backend/` owns the backend runtime scaffold
- `packages/shared/` owns shared domain models and seed data

## 3. Desktop Application Shell

Responsibilities:

- render the desktop interface
- manage navigation and layout
- host chat, task, project, agent, and diagnostic views
- connect UI state to backend runtime state

Design note:

- keep the shell thin
- move agent, memory, and execution logic into backend services or modules

## 4. Workspace and State Management

Responsibilities:

- manage current workspace/project/session state
- manage active selections and UI context
- synchronize runtime state to the interface
- support restoration after restart

Core entities:

- Workspace
- Project
- Session
- Task
- Agent
- Skill
- Schedule
- MemoryItem
- Run

Recommended characteristics:

- event-driven updates
- normalized state model
- persisted local app state for recovery

## 5. Orchestration and Agent Runtime

Responsibilities:

- receive user requests from chat
- create or update tasks
- route work to persistent specialists
- spawn bounded ephemeral workers
- manage lifecycle and reporting
- enforce policy and budget limits
- synthesize outputs for the user

Runtime components:

- Orchestrator Runtime
- Specialist Runtime Layer
- Worker Runtime Layer
- Execution Controller
- Delegation Manager

Execution loop:

1. user request enters orchestrator
2. orchestrator creates or updates a task
3. planner or other specialist decomposes work
4. specialists retrieve scoped context
5. specialists execute directly or spawn workers
6. workers return structured outputs
7. critic/evaluator optionally reviews
8. orchestrator synthesizes result
9. memory steward evaluates write-back opportunities
10. task/run state is persisted and exposed to UI

## 6. Memory Platform

Memory subsystems:

- Active Context Store
- Episodic Store
- Semantic Store
- Procedural Store
- Personal/Workspace Store

Memory services:

- Ingestion Service
- Consolidation Service
- Retrieval Service
- Governance Service

Retrieval path:

- recency filter
- semantic retrieval
- keyword retrieval
- relation or graph retrieval if available
- scope filtering
- confidence and freshness filtering
- reranking
- final context assembly

Each durable memory record should support:

- id
- type
- content
- summary
- source_ref
- source_type
- created_at
- updated_at
- scope
- project_id
- session_id
- task_ids
- related_entity_ids
- related_agent_ids
- confidence_score
- freshness_score
- contradiction_state
- validation_state
- tags

## 7. Skills Platform

Responsibilities:

- register skills
- store authored and learned skills
- version skills
- bind skills to tools and scopes
- test and promote skills

Core skill fields:

- id
- name
- description
- scope
- version
- source_type
- required_tools
- input_schema
- output_schema
- execution_policy
- status
- test_results
- performance_metrics

## 8. Task and Scheduling Platform

Task service responsibilities:

- create and update tasks
- track status transitions
- maintain parent-child relationships
- store dependencies
- attach agent ownership
- connect tasks to projects and runs

Schedule service responsibilities:

- manage one-time and recurring schedules
- trigger task creation or execution
- record run history
- manage retries and failure alerts

## 9. Tool Execution Layer

Responsibilities:

- provide safe access to local tools and resources
- execute commands and file operations within policy boundaries
- stream outputs back into task and runtime state

Safety controls:

- permission checks
- workspace scoping
- read/write mode separation
- secrets isolation
- command policy checks
- audit logging

## 10. Policy and Permissions

Responsibilities:

- enforce user-selected autonomy mode
- classify sensitive actions
- gate high-risk operations
- constrain agent permissions
- govern memory writes and schedule execution

Policy domains:

- agent spawning policy
- tool permission policy
- file access policy
- memory write policy
- schedule execution policy
- approval requirements

## 11. Observability and Event Log

Responsibilities:

- record system events
- support logs, timelines, replay, and diagnostics
- expose execution traces to the UI

Event types:

- task lifecycle events
- agent lifecycle events
- delegation events
- tool invocation events
- memory retrieval and write events
- schedule trigger events
- approval events
- failure events

## 12. Persistence Layer

Responsibilities:

- store durable application state locally
- support crash recovery and restart restoration
- persist tasks, sessions, memory, skills, schedules, and events

Storage classes:

- relational or local structured store for entities and metadata
- document or blob storage for larger artifacts and logs
- vector or embedding store for semantic retrieval
- optional graph store later for richer memory relationships

## 13. Core Data Entities

The core domain model should include:

- UserProfile
- Workspace
- Project
- Session
- Run
- Task
- Agent
- AgentRun
- Skill
- SkillVersion
- MemoryItem
- Schedule
- ToolInvocation
- ApprovalRequest
- Event
- Artifact

## 14. Inter-System Flow Summary

Typical interactive flow:

1. User submits request through Chat.
2. Orchestrator creates or updates Task and Run.
3. Relevant specialist retrieves scoped memory.
4. Specialist executes work or spawns workers.
5. Tool layer executes approved actions.
6. Outputs stream to UI and Event Log.
7. Critic or reviewer may validate output.
8. Orchestrator responds to user.
9. Memory services evaluate write-back and consolidation.
10. Task, Session, and Project states are persisted.

Typical scheduled flow:

1. Scheduling service triggers a scheduled job.
2. Target orchestration flow or specialist run is created.
3. Policy layer checks execution and approval requirements.
4. Runtime executes task.
5. Events, results, and memory updates are persisted.
6. UI reflects run history and status.

## 15. Initial Implementation Priorities

Phase 1:

- desktop shell
- task/project/session data model
- orchestrator and a few specialists
- worker spawning with limits
- foundational memory layers
- local persistence
- task board and chat view
- event logging
- basic local tool execution

Phase 2:

- richer memory consolidation
- skill workflows
- scheduling platform
- better diagnostics and replay
- project-aware memory policies

Phase 3:

- advanced memory graph
- automatic skill extraction
- richer parallel agent execution
- formal evaluation frameworks
- deeper personalization

## 16. Risks

- Memory quality risk
- Agent coordination risk
- UI complexity risk
- Local execution safety risk
- Procedural learning risk

## 17. Summary

Gnosys should be a local-first, modular platform composed of a UI shell, orchestration runtime, memory platform, skill system, task and scheduling services, tool execution layer, policy controls, observability infrastructure, and durable persistence.
