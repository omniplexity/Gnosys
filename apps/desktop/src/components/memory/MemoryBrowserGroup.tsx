import type { MemoryItem } from '@gnosys/shared';

type MemoryBrowserGroupProps = {
  title: string;
  hint: string;
  items: Array<
    MemoryItem & {
      score?: number;
      reason?: string | null;
      recommended_action?: string | null;
      review_reason?: string | null;
    }
  >;
  emptyMessage: string;
  onPromote: (itemId: string) => void;
  onPin: (itemId: string) => void;
  onArchive: (itemId: string) => void;
  onForget: (itemId: string) => void;
};

export function MemoryBrowserGroup({
  title,
  hint,
  items,
  emptyMessage,
  onPromote,
  onPin,
  onArchive,
  onForget,
}: MemoryBrowserGroupProps) {
  return (
    <section className="memory-browser-group">
      <div className="memory-browser-head">
        <strong>{title}</strong>
        <span>{items.length} items</span>
      </div>
      <p className="event-hint">{hint}</p>
      <div className="stack compact">
        {items.map((item) => (
          <article key={item.id} className="memory-card">
            <div className="memory-card-top">
              <strong>{item.title}</strong>
              <span>{item.layer} · {item.state}{item.pinned ? ' · pinned' : ''}</span>
            </div>
            <p>{item.summary}</p>
            <div className="memory-meta">
              <span>{item.scope}</span>
              <span>{item.project_id ?? 'workspace'}</span>
              <span>{item.confidence.toFixed(2)}</span>
              <span>{item.freshness.toFixed(2)}</span>
              {typeof item.score === 'number' ? <span>score {item.score.toFixed(2)}</span> : null}
            </div>
            {(item.review_reason || item.reason) && <p className="event-hint">{item.review_reason ?? item.reason}</p>}
            <div className="crud-actions">
              {item.state === 'candidate' ? (
                <button className="primary-action" onClick={() => onPromote(item.id)}>
                  Promote
                </button>
              ) : null}
              <button className="tab" onClick={() => onPin(item.id)}>
                Pin
              </button>
              <button className="tab" onClick={() => onArchive(item.id)}>
                Archive
              </button>
              <button className="tab" onClick={() => onForget(item.id)}>
                Forget
              </button>
            </div>
          </article>
        ))}
        {items.length === 0 && <p>{emptyMessage}</p>}
      </div>
    </section>
  );
}
