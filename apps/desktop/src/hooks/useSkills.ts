import { useCallback, useEffect, useState } from 'react';

import type { Skill, WorkspaceSnapshot } from '@gnosys/shared';

import { createSkillDraft, loadSkillLifecycle, promoteSkill, rollbackSkill, testSkill } from '../lib/api';
import type { SkillLifecycleResponse } from '../lib/api';
import { toErrorMessage } from '../lib/errors';

type AsyncState = 'idle' | 'loading' | 'ready' | 'error';

type UseSkillsArgs = {
  snapshot: WorkspaceSnapshot;
  crudKind: string;
  selectedSkillId: string | null;
  selectedSkillName: string;
  refreshSnapshot: () => Promise<WorkspaceSnapshot>;
  onSelectSkill: (skillId: string) => void;
  onReplaceSkillDraft: (skill: Skill) => void;
};

export function useSkills({
  snapshot,
  crudKind,
  selectedSkillId,
  selectedSkillName,
  refreshSnapshot,
  onSelectSkill,
  onReplaceSkillDraft,
}: UseSkillsArgs) {
  const [skillLifecycle, setSkillLifecycle] = useState<SkillLifecycleResponse | null>(null);
  const [skillLifecycleState, setSkillLifecycleState] = useState<AsyncState>('idle');
  const [skillLifecycleError, setSkillLifecycleError] = useState<string | null>(null);
  const [skillTestScenario, setSkillTestScenario] = useState('Inspect the selected skill against a realistic workflow.');
  const [skillTestExpectedOutcome, setSkillTestExpectedOutcome] = useState('The skill produces a clear, actionable result and passes the lifecycle check.');

  const refreshSkillLifecycle = useCallback(async (skillId: string) => {
    setSkillLifecycleState('loading');
    setSkillLifecycleError(null);
    try {
      const lifecycle = await loadSkillLifecycle(skillId);
      setSkillLifecycle(lifecycle);
      setSkillLifecycleState('ready');
      return lifecycle;
    } catch (error) {
      setSkillLifecycleError(toErrorMessage(error, 'Failed to load skill lifecycle'));
      setSkillLifecycleState('error');
      return null;
    }
  }, []);

  const createLearnedSkillDraft = useCallback(async (skillId: string) => {
    setSkillLifecycleState('loading');
    setSkillLifecycleError(null);
    try {
      await createSkillDraft(skillId);
      const nextSnapshot = await refreshSnapshot();
      const refreshedSkill = nextSnapshot.skills.find((skill) => skill.parent_skill_id === skillId) ?? nextSnapshot.skills[0] ?? null;
      if (refreshedSkill) {
        onSelectSkill(refreshedSkill.id);
        onReplaceSkillDraft(refreshedSkill);
        await refreshSkillLifecycle(refreshedSkill.id);
      }
      return true;
    } catch (error) {
      setSkillLifecycleError(toErrorMessage(error, 'Failed to create learned skill draft'));
      setSkillLifecycleState('error');
      return false;
    }
  }, [onReplaceSkillDraft, onSelectSkill, refreshSkillLifecycle, refreshSnapshot]);

  const runSkillTest = useCallback(async (skillId: string) => {
    setSkillLifecycleState('loading');
    setSkillLifecycleError(null);
    try {
      await testSkill(skillId, {
        scenario: skillTestScenario,
        expected_outcome: skillTestExpectedOutcome,
        requested_by: 'desktop',
      });
      await refreshSnapshot();
      await refreshSkillLifecycle(skillId);
      return true;
    } catch (error) {
      setSkillLifecycleError(toErrorMessage(error, 'Failed to run skill test'));
      setSkillLifecycleState('error');
      return false;
    }
  }, [refreshSkillLifecycle, refreshSnapshot, skillTestExpectedOutcome, skillTestScenario]);

  const promoteSelectedSkill = useCallback(async (skillId: string) => {
    setSkillLifecycleState('loading');
    setSkillLifecycleError(null);
    try {
      await promoteSkill(skillId);
      const nextSnapshot = await refreshSnapshot();
      const current = nextSnapshot.skills.find((skill) => skill.id === skillId) ?? null;
      if (current) {
        onReplaceSkillDraft(current);
        await refreshSkillLifecycle(skillId);
      }
      return true;
    } catch (error) {
      setSkillLifecycleError(toErrorMessage(error, 'Failed to promote skill'));
      setSkillLifecycleState('error');
      return false;
    }
  }, [onReplaceSkillDraft, refreshSkillLifecycle, refreshSnapshot]);

  const rollbackSelectedSkill = useCallback(async (skillId: string) => {
    setSkillLifecycleState('loading');
    setSkillLifecycleError(null);
    try {
      const restored = await rollbackSkill(skillId);
      const nextSnapshot = await refreshSnapshot();
      const current = nextSnapshot.skills.find((skill) => skill.id === restored.id) ?? restored;
      onSelectSkill(current.id);
      onReplaceSkillDraft(current);
      await refreshSkillLifecycle(current.id);
      return true;
    } catch (error) {
      setSkillLifecycleError(toErrorMessage(error, 'Failed to roll back skill'));
      setSkillLifecycleState('error');
      return false;
    }
  }, [onReplaceSkillDraft, onSelectSkill, refreshSkillLifecycle, refreshSnapshot]);

  useEffect(() => {
    const lifecycleSkillId = selectedSkillId;
    if (crudKind !== 'skills' || !lifecycleSkillId) {
      setSkillLifecycle(null);
      setSkillLifecycleState('idle');
      setSkillLifecycleError(null);
      return;
    }

    let cancelled = false;
    async function run() {
      setSkillLifecycleState('loading');
      setSkillLifecycleError(null);
      try {
        const lifecycle = await loadSkillLifecycle(lifecycleSkillId ?? '');
        if (cancelled) {
          return;
        }
        setSkillLifecycle(lifecycle);
        setSkillLifecycleState('ready');
      } catch (error) {
        if (cancelled) {
          return;
        }
        setSkillLifecycleError(toErrorMessage(error, 'Failed to load skill lifecycle'));
        setSkillLifecycleState('error');
      }
    }

    void run();
    setSkillTestScenario(`Inspect ${selectedSkillName} against its described workflow.`);
    setSkillTestExpectedOutcome(`The ${selectedSkillName} skill should resolve the workflow with a passing lifecycle score.`);

    return () => {
      cancelled = true;
    };
  }, [crudKind, selectedSkillId, selectedSkillName, snapshot.skills]);

  return {
    skillLifecycle,
    skillLifecycleState,
    skillLifecycleError,
    skillTestScenario,
    setSkillTestScenario,
    skillTestExpectedOutcome,
    setSkillTestExpectedOutcome,
    refreshSkillLifecycle,
    createLearnedSkillDraft,
    runSkillTest,
    promoteSelectedSkill,
    rollbackSelectedSkill,
  };
}
