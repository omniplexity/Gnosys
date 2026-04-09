import { useCallback, useEffect, useState } from 'react';

import { appendEvent, archiveMemoryItem, forgetMemoryItem, loadMemoryBrowser, loadMemoryReview, pinMemoryItem, promoteMemoryItem, retrieveMemory } from '../lib/api';
import type { MemoryBrowserResponse, MemoryRetrievalResult, MemoryReviewResponse } from '../lib/api';
import { toErrorMessage } from '../lib/errors';

type AsyncState = 'idle' | 'loading' | 'ready' | 'error';

type UseMemoryArgs = {
  projectIds: string[];
  initialProjectId: string;
  refreshSnapshot: () => Promise<unknown>;
  onShowLogs: () => void;
  onShowTrace: () => void;
};

export function useMemory({
  projectIds,
  initialProjectId,
  refreshSnapshot,
  onShowLogs,
  onShowTrace,
}: UseMemoryArgs) {
  const [eventDraft, setEventDraft] = useState('desktop.checkpoint');
  const [memoryQuery, setMemoryQuery] = useState('persistence event log');
  const [memoryScope, setMemoryScope] = useState('workspace');
  const [memoryRole, setMemoryRole] = useState('orchestrator');
  const [memoryProjectId, setMemoryProjectId] = useState(initialProjectId);
  const [retrieval, setRetrieval] = useState<MemoryRetrievalResult | null>(null);
  const [memoryError, setMemoryError] = useState<string | null>(null);
  const [memoryState, setMemoryState] = useState<AsyncState>('idle');
  const [memoryBrowser, setMemoryBrowser] = useState<MemoryBrowserResponse | null>(null);
  const [memoryBrowserState, setMemoryBrowserState] = useState<AsyncState>('idle');
  const [memoryBrowserError, setMemoryBrowserError] = useState<string | null>(null);
  const [memoryReview, setMemoryReview] = useState<MemoryReviewResponse | null>(null);
  const [memoryReviewState, setMemoryReviewState] = useState<AsyncState>('idle');
  const [memoryReviewError, setMemoryReviewError] = useState<string | null>(null);

  const runMemorySearch = useCallback(async (
    query = memoryQuery,
    role = memoryRole,
    scope = memoryScope,
    projectId = memoryProjectId,
  ) => {
    setMemoryState('loading');
    setMemoryError(null);
    try {
      const result = await retrieveMemory(query, role, scope || null, projectId || null);
      setRetrieval(result);
      setMemoryState('ready');
      onShowTrace();
      return result;
    } catch (error) {
      setMemoryError(toErrorMessage(error, 'Failed to retrieve memory'));
      setMemoryState('error');
      return null;
    }
  }, [memoryProjectId, memoryQuery, memoryRole, memoryScope, onShowTrace]);

  const refreshMemoryBrowser = useCallback(async (query = memoryQuery, projectId = memoryProjectId) => {
    setMemoryBrowserState('loading');
    setMemoryBrowserError(null);
    try {
      const browser = await loadMemoryBrowser(query, projectId || null, 12);
      setMemoryBrowser(browser);
      setMemoryBrowserState('ready');
      return browser;
    } catch (error) {
      setMemoryBrowserError(toErrorMessage(error, 'Failed to load memory browser'));
      setMemoryBrowserState('error');
      return null;
    }
  }, [memoryProjectId, memoryQuery]);

  const refreshMemoryReview = useCallback(async () => {
    setMemoryReviewState('loading');
    setMemoryReviewError(null);
    try {
      const review = await loadMemoryReview();
      setMemoryReview(review);
      setMemoryReviewState('ready');
      return review;
    } catch (error) {
      setMemoryReviewError(toErrorMessage(error, 'Failed to load memory review'));
      setMemoryReviewState('error');
      return null;
    }
  }, []);

  const refreshMemorySurfaces = useCallback(async () => {
    await refreshSnapshot();
    await refreshMemoryBrowser(memoryQuery, memoryProjectId);
    await refreshMemoryReview();
    await runMemorySearch(memoryQuery, memoryRole, memoryScope, memoryProjectId);
    onShowLogs();
  }, [
    memoryProjectId,
    memoryQuery,
    memoryRole,
    memoryScope,
    onShowLogs,
    refreshMemoryBrowser,
    refreshMemoryReview,
    refreshSnapshot,
    runMemorySearch,
  ]);

  const promoteReviewItem = useCallback(async (itemId: string) => {
    try {
      await promoteMemoryItem(itemId);
      await refreshMemorySurfaces();
    } catch (error) {
      setMemoryReviewError(toErrorMessage(error, 'Failed to promote memory item'));
      setMemoryReviewState('error');
    }
  }, [refreshMemorySurfaces]);

  const archiveReviewItem = useCallback(async (itemId: string) => {
    try {
      await archiveMemoryItem(itemId);
      await refreshMemorySurfaces();
    } catch (error) {
      setMemoryReviewError(toErrorMessage(error, 'Failed to archive memory item'));
      setMemoryReviewState('error');
    }
  }, [refreshMemorySurfaces]);

  const pinReviewItem = useCallback(async (itemId: string) => {
    try {
      await pinMemoryItem(itemId);
      await refreshMemorySurfaces();
    } catch (error) {
      setMemoryReviewError(toErrorMessage(error, 'Failed to pin memory item'));
      setMemoryReviewState('error');
    }
  }, [refreshMemorySurfaces]);

  const forgetReviewItem = useCallback(async (itemId: string) => {
    try {
      await forgetMemoryItem(itemId);
      await refreshMemorySurfaces();
    } catch (error) {
      setMemoryReviewError(toErrorMessage(error, 'Failed to forget memory item'));
      setMemoryReviewState('error');
    }
  }, [refreshMemorySurfaces]);

  const appendCheckpointEvent = useCallback(async (payload: { section: string; task_id: string; agent_id: string }) => {
    await appendEvent({
      type: eventDraft,
      source: 'desktop-shell',
      payload,
    });
    await refreshSnapshot();
    onShowLogs();
    await runMemorySearch(memoryQuery, memoryRole, memoryScope, memoryProjectId);
  }, [eventDraft, memoryProjectId, memoryQuery, memoryRole, memoryScope, onShowLogs, refreshSnapshot, runMemorySearch]);

  useEffect(() => {
    if (!memoryProjectId || (projectIds.length > 0 && !projectIds.includes(memoryProjectId))) {
      setMemoryProjectId(projectIds[0] ?? '');
    }
  }, [memoryProjectId, projectIds]);

  return {
    eventDraft,
    setEventDraft,
    memoryQuery,
    setMemoryQuery,
    memoryScope,
    setMemoryScope,
    memoryRole,
    setMemoryRole,
    memoryProjectId,
    setMemoryProjectId,
    retrieval,
    memoryError,
    memoryState,
    memoryBrowser,
    memoryBrowserState,
    memoryBrowserError,
    memoryReview,
    memoryReviewState,
    memoryReviewError,
    runMemorySearch,
    refreshMemoryBrowser,
    refreshMemoryReview,
    promoteReviewItem,
    archiveReviewItem,
    pinReviewItem,
    forgetReviewItem,
    appendCheckpointEvent,
  };
}
