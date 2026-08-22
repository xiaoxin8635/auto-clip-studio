import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { SegmentCard } from "./SegmentCard";
import type { Project } from "./types";
import { isBusy, label } from "./status";

const steps = ["created", "uploaded", "transcribing", "selecting", "awaiting_review", "rendering", "completed"];

export function App() {
  const [project, setProject] = useState<Project | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  const refresh = useCallback(async (projectId: string) => {
    try {
      setProject(await api.project(projectId));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "无法读取项目");
    }
  }, []);

  useEffect(() => {
    if (!project || !isBusy(project.status)) return;
    timer.current = window.setInterval(() => void refresh(project.id), 2000);
    return () => window.clearInterval(timer.current);
  }, [project, refresh]);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      const created = await api.createProject();
      if (!file) throw new Error("请选择 MP4 或 MOV 文件");
      const uploaded = await api.upload(created.id, file);
      setProject(uploaded);
      await api.analyze(uploaded.id);
      await refresh(uploaded.id);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "启动失败");
    } finally {
      setBusy(false);
    }
  }

  async function retryAnalysis() {
    if (!project) return;
    setBusy(true);
    try {
      await api.analyze(project.id);
      await refresh(project.id);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "重试失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="workspace">
      <header className="topbar">
        <div>
          <strong>AutoClip Studio</strong>
          <span>自动剪辑工作台</span>
        </div>
        {project && <span className={`status ${project.status}`}>{label(project.status)}</span>}
      </header>

      <section className="upload-panel">
        <h2>新建剪辑任务</h2>
        <input
          type="file"
          accept="video/mp4,video/quicktime,.mp4,.mov"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <button className="primary" onClick={start} disabled={busy || !file}>
          开始分析
        </button>
        {error && (
          <p className="error">
            {error}
            {project?.status === "failed" && (
              <button onClick={retryAnalysis} disabled={busy}>
                重试
              </button>
            )}
          </p>
        )}
      </section>

      {project && (
        <>
          <section className="timeline-panel">
            <h2>处理进度</h2>
            <ol className="timeline">
              {steps.map((step) => (
                <li key={step} className={project.status === step ? "active" : undefined}>
                  {label(step)}
                </li>
              ))}
            </ol>
            {project.error_message && <p className="error">{project.error_message}</p>}
          </section>

          {project.transcript_text && (
            <section className="transcript-panel">
              <h2>转录文本</h2>
              <p>{project.transcript_text}</p>
            </section>
          )}

          <section className="segments-panel">
            <h2>候选片段</h2>
            <div className="segments-grid">
              {project.segments.map((segment) => (
                <SegmentCard
                  key={segment.id}
                  project={project}
                  segment={segment}
                  onChanged={() => void refresh(project.id)}
                />
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
