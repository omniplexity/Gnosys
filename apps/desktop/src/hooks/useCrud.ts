import { useCallback, useEffect, useState } from 'react';

import type { WorkspaceSnapshot } from '@gnosys/shared';

import { deleteCrudResource, saveCrudResource } from '../lib/api';
import { toErrorMessage } from '../lib/errors';

export type CrudKind = 'tasks' | 'projects' | 'agents' | 'skills' | 'schedules';
export type CrudDraft = Record<string, string | boolean>;

export const NEW_ITEM_SENTINEL = '__new__';
export const crudKinds: CrudKind[] = ['tasks', 'projects', 'agents', 'skills', 'schedules'];

export function getCrudItems(snapshot: WorkspaceSnapshot, kind: CrudKind): Array<Record<string, unknown> & { id: string }> {
  switch (kind) {
    case 'tasks':
      return snapshot.tasks as unknown as Array<Record<string, unknown> & { id: string }>;
    case 'projects':
      return snapshot.projects as unknown as Array<Record<string, unknown> & { id: string }>;
    case 'agents':
      return snapshot.agents as unknown as Array<Record<string, unknown> & { id: string }>;
    case 'skills':
      return snapshot.skills as unknown as Array<Record<string, unknown> & { id: string }>;
    case 'schedules':
      return snapshot.schedules as unknown as Array<Record<string, unknown> & { id: string }>;
  }
}

export function buildCrudDraft(item: unknown): CrudDraft {
  if (!item || typeof item !== 'object') {
    return {};
  }
  return { ...item } as CrudDraft;
}

export function normalizeCrudDraft(kind: CrudKind, draft: CrudDraft): Record<string, unknown> {
  switch (kind) {
    case 'tasks':
      return {
        title: String(draft.title ?? ''),
        summary: String(draft.summary ?? ''),
        status: String(draft.status ?? 'Inbox'),
        priority: String(draft.priority ?? 'Medium'),
        project_id: draft.project_id ? String(draft.project_id) : null,
      };
    case 'projects':
      return {
        name: String(draft.name ?? ''),
        summary: String(draft.summary ?? ''),
        status: String(draft.status ?? 'Planned'),
        owner: String(draft.owner ?? 'Gnosys'),
      };
    case 'agents':
      return {
        name: String(draft.name ?? ''),
        role: String(draft.role ?? ''),
        status: String(draft.status ?? 'Idle'),
      };
    case 'skills':
      return {
        name: String(draft.name ?? ''),
        description: String(draft.description ?? ''),
        scope: String(draft.scope ?? 'workspace'),
        version: String(draft.version ?? '0.1.0'),
        source_type: String(draft.source_type ?? 'authored'),
        status: String(draft.status ?? 'draft'),
        project_id: draft.project_id ? String(draft.project_id) : null,
      };
    case 'schedules':
      return {
        name: String(draft.name ?? ''),
        target_type: String(draft.target_type ?? 'skill'),
        target_ref: String(draft.target_ref ?? ''),
        schedule_expression: String(draft.schedule_expression ?? ''),
        timezone: String(draft.timezone ?? 'America/New_York'),
        enabled: Boolean(draft.enabled),
        approval_policy: String(draft.approval_policy ?? 'inherit'),
        failure_policy: String(draft.failure_policy ?? 'retry_once'),
        last_run_at: draft.last_run_at ? String(draft.last_run_at) : null,
        next_run_at: draft.next_run_at ? String(draft.next_run_at) : null,
        project_id: draft.project_id ? String(draft.project_id) : null,
      };
  }
}

export function crudConfig(kind: CrudKind) {
  switch (kind) {
    case 'tasks':
      return { title: 'Tasks', createLabel: 'Create task', endpoint: '/api/tasks' };
    case 'projects':
      return { title: 'Projects', createLabel: 'Create project', endpoint: '/api/projects' };
    case 'agents':
      return { title: 'Agents', createLabel: 'Create agent', endpoint: '/api/agents' };
    case 'skills':
      return { title: 'Skills', createLabel: 'Create skill', endpoint: '/api/skills' };
    case 'schedules':
      return { title: 'Schedules', createLabel: 'Create schedule', endpoint: '/api/schedules' };
  }
}

type SaveState = 'idle' | 'saving' | 'error';

type UseCrudArgs = {
  snapshot: WorkspaceSnapshot;
  refreshSnapshot: () => Promise<WorkspaceSnapshot>;
};

export function useCrud({ snapshot, refreshSnapshot }: UseCrudArgs) {
  const [crudKind, setCrudKind] = useState<CrudKind>('tasks');
  const [crudSelectionId, setCrudSelectionId] = useState('');
  const [crudDraft, setCrudDraft] = useState<CrudDraft>({});
  const [crudState, setCrudState] = useState<SaveState>('idle');
  const [crudError, setCrudError] = useState<string | null>(null);

  const saveCrudItem = useCallback(async () => {
    const endpoint = crudConfig(crudKind).endpoint;
    const normalized = normalizeCrudDraft(crudKind, crudDraft);
    const creating = crudSelectionId === '' || crudSelectionId === NEW_ITEM_SENTINEL;
    setCrudState('saving');
    setCrudError(null);

    try {
      const saved = await saveCrudResource(endpoint, crudSelectionId, normalized, creating);
      const nextSnapshot = await refreshSnapshot();
      const items = getCrudItems(nextSnapshot, crudKind) as Array<{ id: string }>;
      const nextSelection = saved.id || items[0]?.id || '';
      setCrudSelectionId(nextSelection);
      setCrudDraft(buildCrudDraft(items.find((item) => item.id === nextSelection) ?? items[0] ?? {}));
      setCrudState('idle');
      return true;
    } catch (error) {
      setCrudError(toErrorMessage(error, 'Failed to save item'));
      setCrudState('error');
      return false;
    }
  }, [crudDraft, crudKind, crudSelectionId, refreshSnapshot]);

  const deleteCrudItem = useCallback(async () => {
    if (!crudSelectionId || crudSelectionId === NEW_ITEM_SENTINEL) {
      return false;
    }
    const endpoint = crudConfig(crudKind).endpoint;
    setCrudState('saving');
    setCrudError(null);

    try {
      await deleteCrudResource(endpoint, crudSelectionId);
      const nextSnapshot = await refreshSnapshot();
      const items = getCrudItems(nextSnapshot, crudKind) as Array<{ id: string }>;
      const nextSelection = items[0]?.id || '';
      setCrudSelectionId(nextSelection);
      setCrudDraft(buildCrudDraft(items[0] ?? {}));
      setCrudState('idle');
      return true;
    } catch (error) {
      setCrudError(toErrorMessage(error, 'Failed to delete item'));
      setCrudState('error');
      return false;
    }
  }, [crudKind, crudSelectionId, refreshSnapshot]);

  const startNewCrudItem = useCallback(() => {
    setCrudSelectionId(NEW_ITEM_SENTINEL);
    setCrudDraft({});
    setCrudError(null);
    setCrudState('idle');
  }, []);

  useEffect(() => {
    if (crudSelectionId === NEW_ITEM_SENTINEL) {
      return;
    }
    const items = getCrudItems(snapshot, crudKind) as Array<{ id: string }>;
    const nextSelection = items.find((item) => item.id === crudSelectionId)?.id ?? items[0]?.id ?? '';
    if (nextSelection !== crudSelectionId) {
      setCrudSelectionId(nextSelection);
    }
    const selectedItem = items.find((item) => item.id === nextSelection) ?? items[0];
    setCrudDraft(selectedItem ? buildCrudDraft(selectedItem) : {});
  }, [crudKind, crudSelectionId, snapshot]);

  return {
    crudKind,
    setCrudKind,
    crudSelectionId,
    setCrudSelectionId,
    crudDraft,
    setCrudDraft,
    crudState,
    crudError,
    saveCrudItem,
    deleteCrudItem,
    startNewCrudItem,
  };
}
