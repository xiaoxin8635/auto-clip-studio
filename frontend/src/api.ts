import type { Project, ProjectSummary, Segment } from "./types";

const TOKEN_STORAGE_KEY = "autoclip_api_token";
const TOKEN_MAX_LENGTH = 4096;

export class ApiError extends Error {
  readonly status: number;
  readonly unauthorized: boolean;

  constructor(message: string, status: number, unauthorized = false) {
    super(message);
    this.status = status;
    this.unauthorized = unauthorized;
  }
}

export function getStoredApiToken(): string | null {
  try {
    const token = window.localStorage.getItem(TOKEN_STORAGE_KEY);
    return token && token.trim() ? token : null;
  } catch {
    return null;
  }
}

export function setStoredApiToken(token: string): void {
  const normalized = token.trim();
  if (!normalized) {
    removeStoredApiToken();
    return;
  }
  if (normalized.length > TOKEN_MAX_LENGTH) {
    throw new Error("API token 过长");
  }
  try {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, normalized);
  } catch {
    throw new Error("浏览器存储不可用");
  }
}

export function removeStoredApiToken(): void {
  try {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Protected or blocked storage may throw; clearing is then already effective.
  }
}

function authHeaders(): Record<string, string> {
  const token = getStoredApiToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function parseError(response: Response, fallback: string): Promise<ApiError> {
  let detail = response.status === 401 ? "API token 缺失或无效" : fallback;
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string" && payload.detail.trim()) {
      detail = payload.detail;
    }
  } catch {
    // Keep the status message when the body is not JSON.
  }
  return new ApiError(detail, response.status, response.status === 401);
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        ...authHeaders(),
        ...options?.headers,
      },
    });
  } catch {
    throw new ApiError("无法连接服务，请确认后端已启动", 0);
  }
  if (!response.ok) {
    throw await parseError(response, `请求失败：${response.status}`);
  }
  try {
    return await response.json();
  } catch {
    throw new ApiError("服务返回了无法解析的数据", response.status);
  }
}

async function requestDownload(url: string): Promise<void> {
  let response: Response;
  try {
    response = await fetch(url, { headers: authHeaders() });
  } catch {
    throw new ApiError("无法连接服务，请确认后端已启动", 0);
  }
  if (!response.ok) {
    throw await parseError(response, `下载失败：${response.status}`);
  }
  try {
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = `autoclip-${url.split("/").reverse()[1]}.mp4`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
  } catch {
    throw new ApiError("下载文件处理失败", response.status);
  }
}

export const api = {
  createProject: () => request<Project>("/api/projects", { method: "POST" }),
  projects: () => request<{ items: ProjectSummary[] }>("/api/projects"),
  upload: (projectId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Project>(`/api/projects/${projectId}/upload`, { method: "POST", body: form });
  },
  analyze: (projectId: string) => request<{ status: string }>(`/api/projects/${projectId}/analyze`, { method: "POST" }),
  project: (projectId: string) => request<Project>(`/api/projects/${projectId}`),
  updateSegment: (
    projectId: string,
    segment: Segment,
    changes: Partial<Pick<Segment, "title" | "start_ms" | "end_ms">>,
  ) =>
    request<Segment>(`/api/projects/${projectId}/segments/${segment.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(changes),
    }),
  render: (projectId: string, segment: Segment) =>
    request<{ status: string }>(`/api/projects/${projectId}/segments/${segment.id}/render`, { method: "POST" }),
  renderAll: (projectId: string) =>
    request<{ status: string; count: number }>(`/api/projects/${projectId}/render`, { method: "POST" }),
  download: requestDownload,
};
