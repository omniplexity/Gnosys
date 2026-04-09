import { useCallback, useEffect, useMemo, useState } from 'react';

import type { WorkspaceSnapshot } from '@gnosys/shared';

import { resolveApproval, updateEntityPolicy, updatePolicy } from '../lib/api';
import { toErrorMessage } from '../lib/errors';

type SaveState = 'idle' | 'saving' | 'error';
type PolicyEntityType = 'task' | 'project' | 'skill' | 'schedule';

type UsePolicyArgs = {
  snapshot: WorkspaceSnapshot;
  refreshSnapshot: () => Promise<unknown>;
  initialProjectId: string;
};

function firstEntityId(snapshot: WorkspaceSnapshot, entityType: PolicyEntityType) {
  switch (entityType) {
    case 'task':
      return snapshot.tasks[0]?.id ?? '';
    case 'project':
      return snapshot.projects[0]?.id ?? '';
    case 'skill':
      return snapshot.skills[0]?.id ?? '';
    case 'schedule':
      return snapshot.schedules[0]?.id ?? '';
  }
}

export function usePolicy({ snapshot, refreshSnapshot, initialProjectId }: UsePolicyArgs) {
  const [policyState, setPolicyState] = useState<SaveState>('idle');
  const [policyError, setPolicyError] = useState<string | null>(null);
  const [policyEntityType, setPolicyEntityType] = useState<PolicyEntityType>('project');
  const [policyEntityId, setPolicyEntityId] = useState(initialProjectId);
  const [policyEntityMode, setPolicyEntityMode] = useState('Supervised');
  const [policyEntityKillSwitch, setPolicyEntityKillSwitch] = useState(false);
  const [policyEntityBias, setPolicyEntityBias] = useState('supervised');
  const [policyEntityState, setPolicyEntityState] = useState<SaveState>('idle');
  const [policyEntityError, setPolicyEntityError] = useState<string | null>(null);

  const pendingApprovals = useMemo(
    () => snapshot.approval_requests.filter((request) => request.status === 'pending'),
    [snapshot.approval_requests],
  );

  const policyEntityItems: Array<{ id: string; name: string }> = useMemo(() => {
    switch (policyEntityType) {
      case 'task':
        return snapshot.tasks.map((item) => ({ id: item.id, name: item.title }));
      case 'project':
        return snapshot.projects.map((item) => ({ id: item.id, name: item.name }));
      case 'skill':
        return snapshot.skills.map((item) => ({ id: item.id, name: item.name }));
      case 'schedule':
        return snapshot.schedules.map((item) => ({ id: item.id, name: item.name }));
    }
  }, [policyEntityType, snapshot.projects, snapshot.schedules, snapshot.skills, snapshot.tasks]);

  const savePolicyMode = useCallback(async (nextMode: string, nextKillSwitch: boolean) => {
    setPolicyState('saving');
    setPolicyError(null);
    try {
      await updatePolicy({ autonomy_mode: nextMode, kill_switch: nextKillSwitch });
      await refreshSnapshot();
      setPolicyState('idle');
      return true;
    } catch (error) {
      setPolicyError(toErrorMessage(error, 'Failed to update policy'));
      setPolicyState('error');
      return false;
    }
  }, [refreshSnapshot]);

  const resolveApprovalRequest = useCallback(async (approvalId: string, status: 'approved' | 'rejected') => {
    setPolicyState('saving');
    setPolicyError(null);
    try {
      await resolveApproval(approvalId, status);
      await refreshSnapshot();
      setPolicyState('idle');
      return true;
    } catch (error) {
      setPolicyError(toErrorMessage(error, 'Failed to resolve approval'));
      setPolicyState('error');
      return false;
    }
  }, [refreshSnapshot]);

  const saveEntityPolicy = useCallback(async () => {
    setPolicyEntityState('saving');
    setPolicyEntityError(null);
    try {
      const updated = await updateEntityPolicy(policyEntityType, policyEntityId, {
        autonomy_mode: policyEntityMode,
        kill_switch: policyEntityKillSwitch,
        approval_bias: policyEntityBias,
      });
      setPolicyEntityMode(updated.autonomy_mode);
      setPolicyEntityKillSwitch(updated.kill_switch);
      setPolicyEntityBias(updated.approval_bias);
      await refreshSnapshot();
      setPolicyEntityState('idle');
      return true;
    } catch (error) {
      setPolicyEntityError(toErrorMessage(error, 'Failed to update entity policy'));
      setPolicyEntityState('error');
      return false;
    }
  }, [policyEntityBias, policyEntityId, policyEntityKillSwitch, policyEntityMode, policyEntityType, refreshSnapshot]);

  const updatePolicyEntityType = useCallback((nextType: PolicyEntityType) => {
    setPolicyEntityType(nextType);
    setPolicyEntityId(firstEntityId(snapshot, nextType));
  }, [snapshot]);

  useEffect(() => {
    if (!policyEntityId) {
      return;
    }
    const existing = snapshot.entity_policies.find(
      (policy) => policy.entity_type === policyEntityType && policy.entity_id === policyEntityId,
    );
    if (existing) {
      setPolicyEntityMode(existing.autonomy_mode);
      setPolicyEntityKillSwitch(existing.kill_switch);
      setPolicyEntityBias(existing.approval_bias);
      return;
    }

    const existsByType = {
      task: snapshot.tasks.some((task) => task.id === policyEntityId),
      project: snapshot.projects.some((project) => project.id === policyEntityId),
      skill: snapshot.skills.some((skill) => skill.id === policyEntityId),
      schedule: snapshot.schedules.some((schedule) => schedule.id === policyEntityId),
    };
    if (!existsByType[policyEntityType]) {
      return;
    }
    setPolicyEntityMode(snapshot.workspace.autonomy_mode);
    setPolicyEntityKillSwitch(snapshot.workspace.kill_switch);
    setPolicyEntityBias(snapshot.workspace.approval_bias);
  }, [
    policyEntityId,
    policyEntityType,
    snapshot.entity_policies,
    snapshot.projects,
    snapshot.schedules,
    snapshot.skills,
    snapshot.tasks,
    snapshot.workspace.approval_bias,
    snapshot.workspace.autonomy_mode,
    snapshot.workspace.kill_switch,
  ]);

  return {
    pendingApprovals,
    policyState,
    policyError,
    setPolicyError,
    savePolicyMode,
    resolveApproval: resolveApprovalRequest,
    policyEntityType,
    setPolicyEntityType: updatePolicyEntityType,
    policyEntityId,
    setPolicyEntityId,
    policyEntityItems,
    policyEntityMode,
    setPolicyEntityMode,
    policyEntityBias,
    setPolicyEntityBias,
    policyEntityKillSwitch,
    setPolicyEntityKillSwitch,
    policyEntityState,
    policyEntityError,
    saveEntityPolicy,
  };
}
