import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { App } from "./App";

describe("App", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("renders upload controls", () => {
    render(<App />);
    expect(screen.getByText("新建剪辑任务")).toBeInTheDocument();
    expect(screen.getByText("开始分析")).toBeDisabled();
  });

  it("loads recent projects", async () => {
    window.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          items: [
            {
              id: "project-1",
              status: "awaiting_review",
              source_filename: "sample.mp4",
              duration_ms: 180000,
              segment_count: 3,
              created_at: "2026-08-22T08:00:00Z",
              error_message: null,
            },
          ],
        }),
    });
    render(<App />);
    expect(await screen.findByText("sample.mp4")).toBeInTheDocument();
    expect(screen.getByText("等待确认")).toBeInTheDocument();
  });

  it("shows token setup after a 401 response", async () => {
    window.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: "Invalid API token" }),
    });
    render(<App />);

    expect(await screen.findByText("访问 Token")).toBeInTheDocument();
    expect(screen.getAllByText("Invalid API token").length).toBeGreaterThan(0);
    expect(screen.getByPlaceholderText("输入后端 AUTOCLIP_API_TOKEN")).toBeInTheDocument();
  });

  it("saves a token and retries project loading", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: "Bearer authentication is required" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ items: [] }),
      });
    window.fetch = fetchMock as unknown as typeof fetch;
    render(<App />);

    fireEvent.change(await screen.findByPlaceholderText("输入后端 AUTOCLIP_API_TOKEN"), {
      target: { value: "user-token" },
    });
    fireEvent.click(screen.getByText("保存"));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock.mock.calls[1][1]).toEqual(
      expect.objectContaining({ headers: { Authorization: "Bearer user-token" } }),
    );
  });

});
