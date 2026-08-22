import { render, screen } from "@testing-library/react";
import { App } from "./App";

describe("App", () => {
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

});
