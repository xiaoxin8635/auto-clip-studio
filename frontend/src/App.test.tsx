import { render, screen } from "@testing-library/react";
import { App } from "./App";

describe("App", () => {
  it("renders upload controls", () => {
    render(<App />);
    expect(screen.getByText("新建剪辑任务")).toBeInTheDocument();
    expect(screen.getByText("开始分析")).toBeDisabled();
  });

});
