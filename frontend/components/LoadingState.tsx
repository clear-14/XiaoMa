/** 统一加载状态视图。 */
export default function LoadingState({ label = "加载中…" }: { label?: string }) {
  return (
    <div className="loading-state" role="status" aria-label={label}>
      <span className="loading-spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
