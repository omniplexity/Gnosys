import { useCallback, useEffect, useState } from 'react';

import type { TaskRun } from '@gnosys/shared';

import type { LaunchResponse } from '../lib/api';
import { launchOrchestration } from '../lib/api';
import { toErrorMessage } from '../lib/errors';

type AsyncState = 'idle' | 'loading' | 'ready' | 'error';

type RunContext = {
  project_id?: string | null;
  project_thread_id?: string | null;
  chat_session_id?: string | null;
};

type UseOrchestrationArgs = {
  workspaceAutonomyMode: string;
  refreshSnapshot: () => Promise<unknown>;
  onShowTrace: () => void;
};

export function useOrchestration({ workspaceAutonomyMode, refreshSnapshot, onShowTrace }: UseOrchestrationArgs) {
  const [activeTask, setActiveTask] = useState('task-001');
  const [launchObjective, setLaunchObjective] = useState('Implement phase 3 orchestration runtime for Gnosys');
  const [launchMode, setLaunchMode] = useState('Supervised');
  const [selectedModel, setSelectedModel] = useState('GPT-5.4');
  const [reasoningStrength, setReasoningStrength] = useState('medium');
  const [launchState, setLaunchState] = useState<AsyncState>('idle');
  const [launchError, setLaunchError] = useState<string | null>(null);
  const [launchResponse, setLaunchResponse] = useState<LaunchResponse | null>(null);

  useEffect(() => {
    setLaunchMode(workspaceAutonomyMode);
  }, [workspaceAutonomyMode]);

  const runLaunch = useCallback(async (
    objective = launchObjective,
    mode = launchMode,
    taskId?: string,
    context?: RunContext,
  ) => {
    setLaunchState('loading');
    setLaunchError(null);
    try {
      const result = await launchOrchestration(objective, mode, taskId, context);
      setLaunchResponse(result);
      await refreshSnapshot();
      setLaunchState('ready');
      onShowTrace();
      return result;
    } catch (error) {
      setLaunchError(toErrorMessage(error, 'Failed to launch orchestration'));
      setLaunchState('error');
      return null;
    }
  }, [launchMode, launchObjective, onShowTrace, refreshSnapshot]);

  const seedLaunchFromRun = useCallback((taskRun: TaskRun, taskTitle: string, summary: string) => {
    setLaunchResponse({
      task: {
        id: taskRun.task_id,
        title: taskTitle,
        summary,
        status: taskRun.status as never,
        priority: 'High',
        project_id: taskRun.project_id,
      },
      task_run: taskRun,
      agent_runs: [],
      steps: [],
      approvals_required: [],
      summary: taskRun.summary,
      decision: {
        intent_classification: 'general',
        execution_mode: 'task-created',
        delegated_specialists: [],
        invoked_skills: [],
        approvals_triggered: taskRun.approval_required,
        synthesis: taskRun.summary,
      },
    });
  }, []);

  return {
    activeTask,
    setActiveTask,
    launchObjective,
    setLaunchObjective,
    launchMode,
    setLaunchMode,
    selectedModel,
    setSelectedModel,
    reasoningStrength,
    setReasoningStrength,
    launchState,
    launchError,
    launchResponse,
    setLaunchResponse,
    runLaunch,
    seedLaunchFromRun,
  };
}
