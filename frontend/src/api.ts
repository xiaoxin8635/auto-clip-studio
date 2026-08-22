import type { Project, Segment } from "./types";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail = `Request failed: ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail ?? detail;
    } catch {
      // Keep the status message when the error body is not JSON.
    }
    throw new Error(detail);
  }
  return response.json();
}

export const api = {
  createProject: () => request<Project>("/api/projects", { method: "POST" }),
  upload: (projectId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Project>(`/api/projects/${projectId}/upload`, { method: "POST", body: form });
  },
  analyze: (projectId: string) => request<{ status: string }>(`/api/projects/${projectId}/analyze`, { method: "POST" }),
  project: (projectId: string) => request<Project>(`/api/projects/${projectId}`),
  updateSegment: (projectId: string, segment: Segment, changes: Partial<Pick<Segment, "title" | "start_ms" | "end_ms">>) =>
    request<Segment>(`/api/projects/${projectId}/segments/${segment.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(changes),
    }),
  render: (projectId: string, segment: Segment) =>
    request<{ status: string }>(`/api/projects/${projectId}/segments/${segment.id}/render`, { method: "POST" }),
};
