import { useCallback } from 'react';

import { retryScheduleRun, runSchedule } from '../lib/api';
import { toErrorMessage } from '../lib/errors';

type UseSchedulesArgs = {
  refreshSnapshot: () => Promise<unknown>;
  runMemorySearch: () => Promise<unknown>;
  setPolicyError: (message: string | null) => void;
  onShowLogs: () => void;
};

export function useSchedules({ refreshSnapshot, runMemorySearch, setPolicyError, onShowLogs }: UseSchedulesArgs) {
  const executeSchedule = useCallback(async (scheduleId: string) => {
    try {
      await runSchedule(scheduleId);
      await refreshSnapshot();
      await runMemorySearch();
      onShowLogs();
    } catch (error) {
      setPolicyError(toErrorMessage(error, 'Failed to run schedule'));
    }
  }, [onShowLogs, refreshSnapshot, runMemorySearch, setPolicyError]);

  const retryRun = useCallback(async (runId: string) => {
    try {
      await retryScheduleRun(runId);
      await refreshSnapshot();
      onShowLogs();
    } catch (error) {
      setPolicyError(toErrorMessage(error, 'Failed to retry schedule'));
    }
  }, [onShowLogs, refreshSnapshot, setPolicyError]);

  return {
    executeSchedule,
    retryRun,
  };
}
