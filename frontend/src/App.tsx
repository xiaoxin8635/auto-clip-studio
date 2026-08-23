import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, getStoredApiToken, removeStoredApiToken, setStoredApiToken } from "./api";
import { SegmentCard } from "./SegmentCard";
import type { Project, ProjectSummary } from "./types";
import { isBusy, label } from "./status";

const steps = ["created", "uploaded", "transcribing", "selecting", "awaiting_review", "rendering", "completed"];

export function App() {
  const [project, setProject] = useState<Project | null>(null);
  const [recentProjects, setRecentProjects] = useState<ProjectSummary[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [tokenEditorOpen, setTokenEditorOpen] = useState(false);
  const [tokenValue, setTokenValue] = useState("");
  const [tokenConfigured, setTokenConfigured] = useState(() => getStoredApiToken() !== null);
  const [busy, setBusy] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  const refresh = useCallback(async (projectId: string) => {
    try {
      setProject(await api.project(projectId));
    } catch (exc) {
      setApiFailure(exc, "无法读取项目");
    }
  }, []);

  const loadRecentProjects = useCallback(async () => {
    try {
      const payload = await api.projects();
      setRecentProjects(payload.items);
    } catch (exc) {
      setRecentProjects([]);
      if (exc instanceof ApiError && exc.unauthorized) setApiFailure(exc, "无法读取项目");
    }
  }, []);

  function setApiFailure(value: unknown, fallback: string) {
    const message = value instanceof Error ? value.message : fallback;
    if (value instanceof ApiError && value.unauthorized) {
      setAuthError(message);
      setTokenEditorOpen(true);
    }
    setError(message);
  }

  useEffect(() => {
    void loadRecentProjects();
  }, [loadRecentProjects]);

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
      void loadRecentProjects();
    } catch (exc) {
      setApiFailure(exc, "启动失败");
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
      setApiFailure(exc, "重试失败");
    } finally {
      setBusy(false);
    }
  }

  async function renderAll() {
    if (!project) return;
    setBusy(true);
    try {
      await api.renderAll(project.id);
      await refresh(project.id);
    } catch (exc) {
      setApiFailure(exc, "批量渲染失败");
    } finally {
      setBusy(false);
    }
  }

  function saveToken() {
    try {
      setStoredApiToken(tokenValue);
      setTokenConfigured(getStoredApiToken() !== null);
      setTokenValue("");
      setTokenEditorOpen(false);
      setAuthError(null);
      setError(null);
      void loadRecentProjects();
    } catch (exc) {
      setAuthError(exc instanceof Error ? exc.message : "保存 token 失败");
    }
  }

  function clearToken() {
    removeStoredApiToken();
    setTokenConfigured(false);
    setTokenValue("");
    setAuthError(null);
    setRecentProjects([]);
  }

  return (
    <main className="workspace">
      <header className="topbar">
        <div>
          <strong>AutoClip Studio</strong>
          <span>自动剪辑工作台</span>
        </div>
        <div className="topbar-actions">
          {project && <span className={`status ${project.status}`}>{label(project.status)}</span>}
          <button className="secondary" onClick={() => setTokenEditorOpen((value) => !value)}>
            {tokenConfigured ? "更换 Token" : "设置 Token"}
          </button>
        </div>
      </header>

      {(tokenEditorOpen || authError) && (
        <section className="token-panel">
          <h2>访问 Token</h2>
          {authError && <p className="error">{authError}</p>}
          <div className="token-form">
            <input
              type="password"
              value={tokenValue}
              placeholder="输入后端 AUTOCLIP_API_TOKEN"
              onChange={(event) => setTokenValue(event.target.value)}
              autoComplete="off"
            />
            <button className="primary" onClick={saveToken} disabled={!tokenValue.trim()}>
              保存
            </button>
            {tokenConfigured && (
              <button className="secondary" onClick={clearToken}>
                清除
              </button>
            )}
            <button className="secondary" onClick={() => setTokenEditorOpen(false)} disabled={!tokenConfigured}>
              关闭
            </button>
          </div>
        </section>
      )}

      <section className="recent-projects">
        <h2>最近项目</h2>
        {recentProjects.length === 0 ? (
          <p className="muted">暂无项目</p>
        ) : (
          <ul>
            {recentProjects.map((item) => (
              <li key={item.id}>
                <button className="link-button" onClick={() => void refresh(item.id)}>
                  {item.source_filename ?? item.id}
                </button>
                <span>{label(item.status)}</span>
                <small>{new Date(item.created_at).toLocaleString()}</small>
              </li>
            ))}
          </ul>
        )}
      </section>

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
            <div className="section-heading">
              <h2>候选片段</h2>
              <button className="primary" onClick={renderAll} disabled={busy || project.status !== "awaiting_review"}>
                全部渲染
              </button>
            </div>
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
