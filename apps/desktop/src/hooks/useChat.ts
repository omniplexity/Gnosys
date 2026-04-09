import { useCallback, useEffect, useState } from 'react';

import type { ChatAttachment, ChatMessage, ChatSession } from '@gnosys/shared';

import { loadChatAttachments, loadChatMessages, sendChatMessage, uploadChatAttachment } from '../lib/api';
import { toErrorMessage } from '../lib/errors';

type AsyncState = 'idle' | 'loading' | 'ready' | 'error';
type SendState = 'idle' | 'sending' | 'error';

type UseChatArgs = {
  chatSessions: ChatSession[];
  selectedModel: string;
  reasoningStrength: string;
  refreshSnapshot: () => Promise<unknown>;
};

export function useChat({ chatSessions, selectedModel, reasoningStrength, refreshSnapshot }: UseChatArgs) {
  const [activeChatSessionId, setActiveChatSessionId] = useState(chatSessions[0]?.id ?? '');
  const [chatDraft, setChatDraft] = useState('');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatAttachments, setChatAttachments] = useState<ChatAttachment[]>([]);
  const [pendingAttachmentIds, setPendingAttachmentIds] = useState<string[]>([]);
  const [chatThreadState, setChatThreadState] = useState<AsyncState>('idle');
  const [chatThreadError, setChatThreadError] = useState<string | null>(null);
  const [chatSendState, setChatSendState] = useState<SendState>('idle');
  const [chatSendError, setChatSendError] = useState<string | null>(null);

  const refreshChatThread = useCallback(async (sessionId = activeChatSessionId) => {
    if (!sessionId) {
      setChatMessages([]);
      setChatThreadState('idle');
      setChatThreadError(null);
      return [];
    }
    setChatThreadState('loading');
    setChatThreadError(null);
    try {
      const messages = await loadChatMessages(sessionId);
      setChatMessages(messages);
      setChatThreadState('ready');
      return messages;
    } catch (error) {
      setChatMessages([]);
      setChatThreadError(toErrorMessage(error, 'Failed to load chat thread'));
      setChatThreadState('error');
      return [];
    }
  }, [activeChatSessionId]);

  const refreshChatAttachments = useCallback(async (sessionId = activeChatSessionId) => {
    if (!sessionId) {
      setChatAttachments([]);
      setPendingAttachmentIds([]);
      return [];
    }
    try {
      const attachments = await loadChatAttachments(sessionId);
      setChatAttachments(attachments);
      return attachments;
    } catch {
      setChatAttachments([]);
      return [];
    }
  }, [activeChatSessionId]);

  const sendCurrentChatMessage = useCallback(async () => {
    const sessionId = activeChatSessionId || chatSessions[0]?.id || '';
    const content = chatDraft.trim();
    if (!sessionId || !content) {
      return;
    }
    setChatSendState('sending');
    setChatSendError(null);
    try {
      await sendChatMessage(sessionId, {
        content,
        selected_model: selectedModel,
        reasoning_strength: reasoningStrength,
        requested_by: 'desktop',
        mode: 'personal',
        attachment_ids: pendingAttachmentIds,
      });
      setChatDraft('');
      setPendingAttachmentIds([]);
      await Promise.all([refreshSnapshot(), refreshChatThread(sessionId), refreshChatAttachments(sessionId)]);
      setChatSendState('idle');
    } catch (error) {
      setChatSendError(toErrorMessage(error, 'Failed to send chat message'));
      setChatSendState('error');
    }
  }, [
    activeChatSessionId,
    chatDraft,
    chatSessions,
    pendingAttachmentIds,
    reasoningStrength,
    refreshChatAttachments,
    refreshChatThread,
    refreshSnapshot,
    selectedModel,
  ]);

  const uploadChatFiles = useCallback(async (files: FileList | null) => {
    const sessionId = activeChatSessionId || chatSessions[0]?.id || '';
    if (!sessionId || !files || files.length === 0) {
      return;
    }
    setChatSendError(null);
    try {
      const uploaded = await Promise.all(
        Array.from(files).map((file) =>
          uploadChatAttachment(sessionId, {
            file,
            mode: 'personal',
          })
        )
      );
      setChatAttachments((prev) => [...uploaded, ...prev]);
      setPendingAttachmentIds((prev) => [...prev, ...uploaded.map((item) => item.id)]);
    } catch (error) {
      setChatSendError(toErrorMessage(error, 'Failed to upload attachment'));
      setChatSendState('error');
    }
  }, [activeChatSessionId, chatSessions]);

  useEffect(() => {
    if (!activeChatSessionId || !chatSessions.some((session) => session.id === activeChatSessionId)) {
      setActiveChatSessionId(chatSessions[0]?.id ?? '');
    }
  }, [activeChatSessionId, chatSessions]);

  useEffect(() => {
    let cancelled = false;
    if (!activeChatSessionId) {
      setChatMessages([]);
      setChatThreadState('idle');
      setChatThreadError(null);
      return () => {
        cancelled = true;
      };
    }

    async function loadThread() {
      setChatThreadState('loading');
      setChatThreadError(null);
      try {
        const messages = await loadChatMessages(activeChatSessionId);
        if (cancelled) {
          return;
        }
        setChatMessages(messages);
        setChatThreadState('ready');
      } catch (error) {
        if (cancelled) {
          return;
        }
        setChatMessages([]);
        setChatThreadError(toErrorMessage(error, 'Failed to load chat thread'));
        setChatThreadState('error');
      }
    }

    void loadThread();

    return () => {
      cancelled = true;
    };
  }, [activeChatSessionId]);

  useEffect(() => {
    setPendingAttachmentIds([]);
    void refreshChatAttachments();
  }, [activeChatSessionId, refreshChatAttachments]);

  return {
    activeChatSessionId,
    setActiveChatSessionId,
    chatDraft,
    setChatDraft,
    chatMessages,
    chatAttachments,
    pendingAttachmentIds,
    chatThreadState,
    chatThreadError,
    chatSendState,
    chatSendError,
    setChatSendError,
    refreshChatThread,
    refreshChatAttachments,
    sendCurrentChatMessage,
    uploadChatFiles,
  };
}
