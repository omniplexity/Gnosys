import { useCallback, useEffect, useState } from 'react';

import type { WorkspaceSnapshot } from '@gnosys/shared';

import { loadSnapshot } from '../lib/api';
import { toErrorMessage } from '../lib/errors';

type AsyncState = 'idle' | 'loading' | 'ready' | 'error';

export function useWorkspaceSnapshot(fallbackSnapshot: WorkspaceSnapshot) {
  const [snapshot, setSnapshot] = useState<WorkspaceSnapshot>(fallbackSnapshot);
  const [loadingState, setLoadingState] = useState<AsyncState>('loading');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const refreshSnapshot = useCallback(async () => {
    const state = await loadSnapshot();
    setSnapshot(state);
    return state;
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      setLoadingState('loading');
      try {
        const state = await refreshSnapshot();
        if (cancelled) {
          return;
        }
        setSnapshot(state);
        setLoadingState('ready');
        setErrorMessage(null);
      } catch (error) {
        if (cancelled) {
          return;
        }
        setSnapshot(fallbackSnapshot);
        setLoadingState('error');
        setErrorMessage(toErrorMessage(error, 'Failed to load backend state'));
      }
    }

    void run();

    return () => {
      cancelled = true;
    };
  }, [fallbackSnapshot, refreshSnapshot]);

  return {
    snapshot,
    setSnapshot,
    loadingState,
    errorMessage,
    setErrorMessage,
    refreshSnapshot,
  };
}
