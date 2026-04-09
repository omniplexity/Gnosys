import { Bot, BrainCircuit, ChevronDown, Paperclip, Plus, SendHorizontal } from 'lucide-react';
import { useRef } from 'react';

import type { ChatAttachment, ChatMessage, ChatSession } from '@gnosys/shared';

type ChatWorkspaceProps = {
  chatSessions: ChatSession[];
  activeChatSessionId: string;
  messages: ChatMessage[];
  attachments: ChatAttachment[];
  pendingAttachmentIds: string[];
  threadState: 'idle' | 'loading' | 'ready' | 'error';
  threadError: string | null;
  draft: string;
  selectedModel: string;
  reasoningStrength: string;
  sendState: 'idle' | 'sending' | 'error';
  sendError: string | null;
  onDraftChange: (value: string) => void;
  onUploadFiles: (files: FileList | null) => void;
  onModelChange: (value: string) => void;
  onReasoningStrengthChange: (value: string) => void;
  onSend: () => void;
};

export function ChatWorkspace({
  chatSessions,
  activeChatSessionId,
  messages,
  attachments,
  pendingAttachmentIds,
  threadState,
  threadError,
  draft,
  selectedModel,
  reasoningStrength,
  sendState,
  sendError,
  onDraftChange,
  onUploadFiles,
  onModelChange,
  onReasoningStrengthChange,
  onSend,
}: ChatWorkspaceProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const activeSession = chatSessions.find((session) => session.id === activeChatSessionId) ?? chatSessions[0] ?? null;
  const visibleMessages = messages.filter((message) => message.chat_session_id === activeSession?.id);
  const pendingAttachments = pendingAttachmentIds
    .map((attachmentId) => attachments.find((item) => item.id === attachmentId) ?? null)
    .filter((item): item is ChatAttachment => item !== null);

  return (
    <section className="panel chat-workspace">
      <div className="chat-surface">
        <div className="chat-thread-full">
          <div className="chat-thread-session">
            <span className="chat-thread-session-title">{activeSession?.title ?? 'Persistent session'}</span>
            <span className="chat-thread-session-meta">{activeSession?.status ?? 'Active'} personal thread</span>
          </div>
          {visibleMessages.length > 0 ? (
            visibleMessages.map((message) => {
              const isUser = message.role === 'user';
              const isSystem = message.role === 'system' || message.kind !== 'message';
              const roleLabel =
                message.role === 'user'
                  ? 'You'
                  : message.role === 'assistant'
                    ? 'Gnosys'
                    : message.role === 'tool'
                      ? 'Tool'
                      : 'System';
              const timestamp = new Date(message.created_at);
              const timeLabel = Number.isNaN(timestamp.getTime())
                ? null
                : timestamp.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });

              return (
                <article
                  key={message.id}
                  className={['chat-bubble', isUser ? 'chat-bubble-user' : '', isSystem ? 'chat-bubble-system' : ''].filter(Boolean).join(' ')}
                >
                  <span className="chat-role">{roleLabel}</span>
                  <p>{message.content}</p>
                  <div className="chat-meta">
                    {message.kind !== 'message' && <span>{message.kind}</span>}
                    {message.task_run_id && <span>{message.task_run_id}</span>}
                    {message.agent_run_ids.length > 0 && <span>{message.agent_run_ids.length} agent runs</span>}
                    {timeLabel && <span>{timeLabel}</span>}
                  </div>
                </article>
              );
            })
          ) : threadState === 'loading' ? (
            <div className="chat-empty-full">
              <div className="eyebrow">Loading</div>
              <h2>Loading the persistent thread.</h2>
              <p>Gnosys is restoring this session from local state.</p>
            </div>
          ) : (
            <div className="chat-empty-full">
              <div className="eyebrow">Chat</div>
              <h2>Ask for work. Keep the rest of the system in the background until it matters.</h2>
              <p>This session is ready for direct conversation or bounded execution. Policy, memory, and diagnostics stay outside the thread until they matter.</p>
            </div>
          )}
        </div>

        <div className="chat-footer">
          {threadError && <p className="error-banner">{threadError}</p>}
          {sendError && <p className="error-banner">{sendError}</p>}
          {pendingAttachments.length > 0 && (
            <div className="chat-attachment-strip" aria-label="Pending attachments">
              {pendingAttachments.map((attachment) => (
                <span key={attachment.id} className="chat-attachment-chip">
                  <Paperclip size={14} />
                  {attachment.original_name}
                </span>
              ))}
            </div>
          )}
          <form
            className="chat-composer-wide"
            onSubmit={(event) => {
              event.preventDefault();
              onSend();
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              className="chat-hidden-file-input"
              multiple
              onChange={(event) => {
                onUploadFiles(event.target.files);
                event.currentTarget.value = '';
              }}
            />
            <button
              className="icon-action"
              type="button"
              aria-label="Add files"
              title="Add files"
              onClick={() => fileInputRef.current?.click()}
            >
              <Plus size={16} />
              {pendingAttachments.length > 0 && <span className="icon-badge">{pendingAttachments.length}</span>}
            </button>
            <label className="chat-select-shell">
              <Bot size={15} />
              <select
                className="chat-compact-select"
                value={selectedModel}
                onChange={(event) => onModelChange(event.target.value)}
                aria-label="Model"
              >
                <option value="GPT-5.4">GPT-5.4</option>
                <option value="GPT-5.4-mini">GPT-5.4-mini</option>
                <option value="gpt-5.3-codex">gpt-5.3-codex</option>
              </select>
              <ChevronDown size={14} />
            </label>
            <label className="chat-select-shell">
              <BrainCircuit size={15} />
              <select
                className="chat-compact-select"
                value={reasoningStrength}
                onChange={(event) => onReasoningStrengthChange(event.target.value)}
                aria-label="Reasoning"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
              <ChevronDown size={14} />
            </label>
            <input
              value={draft}
              onChange={(event) => onDraftChange(event.target.value)}
              aria-label="Chat prompt"
              disabled={!activeSession || sendState === 'sending'}
              placeholder="Ask Gnosys to plan, run, inspect, or automate"
            />
            <button className="primary-action chat-send-action" type="submit" disabled={!activeSession || !draft.trim() || sendState === 'sending'}>
              <SendHorizontal size={16} />
              <span>{sendState === 'sending' ? 'Sending' : 'Send'}</span>
            </button>
          </form>
        </div>
      </div>
    </section>
  );
}
