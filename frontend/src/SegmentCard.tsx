import { useState } from "react";
import { api } from "./api";
import type { Project, Segment } from "./types";

interface Props {
  project: Project;
  segment: Segment;
  onChanged: () => void;
}

export function SegmentCard({ project, segment, onChanged }: Props) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(segment.title);
  const [start, setStart] = useState((segment.start_ms / 1000).toFixed(1));
  const [end, setEnd] = useState((segment.end_ms / 1000).toFixed(1));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    setError(null);
    try {
      await api.updateSegment(project.id, segment, {
        title,
        start_ms: Math.round(Number(start) * 1000),
        end_ms: Math.round(Number(end) * 1000),
      });
      setEditing(false);
      onChanged();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "保存失败");
    } finally {
      setBusy(false);
    }
  }

  async function render() {
    setBusy(true);
    setError(null);
    try {
      await api.render(project.id, segment);
      onChanged();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "渲染失败");
    } finally {
      setBusy(false);
    }
  }

  async function downloadSegment() {
    if (!segment.download_url) return;
    setBusy(true);
    setError(null);
    try {
      await api.download(segment.download_url);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "下载失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="segment-card">
      <header>
        <h3>{segment.title}</h3>
        <span>{((segment.end_ms - segment.start_ms) / 1000).toFixed(1)} 秒</span>
      </header>
      <p>{segment.rationale}</p>
      <small>
        {segment.start_ms / 1000} 秒 - {segment.end_ms / 1000} 秒
      </small>
      <video
        className="segment-preview"
        src={`/api/projects/${project.id}/source#t=${segment.start_ms / 1000},${segment.end_ms / 1000}`}
        controls
        preload="metadata"
      />
      {editing ? (
        <div className="edit-form">
          <label>
            标题
            <input value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label>
            开始
            <input value={start} onChange={(event) => setStart(event.target.value)} inputMode="decimal" />
          </label>
          <label>
            结束
            <input value={end} onChange={(event) => setEnd(event.target.value)} inputMode="decimal" />
          </label>
          <div className="actions">
            <button onClick={save} disabled={busy}>
              保存
            </button>
            <button className="secondary" onClick={() => setEditing(false)} disabled={busy}>
              取消
            </button>
          </div>
        </div>
      ) : (
        <div className="actions">
          <button onClick={() => setEditing(true)} disabled={busy || project.status === "rendering"}>
            编辑
          </button>
          <button className="primary" onClick={render} disabled={busy || project.status !== "awaiting_review"}>
            渲染
          </button>
          {segment.download_url && (
            <button className="secondary" onClick={() => void downloadSegment()} disabled={busy}>
              下载
            </button>
          )}
        </div>
      )}
      {error && <p className="error">{error}</p>}
    </article>
  );
}
