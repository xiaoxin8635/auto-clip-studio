export const statusLabels: Record<string, string> = {
  created: "待上传",
  uploaded: "已上传",
  transcribing: "转录中",
  selecting: "选段中",
  awaiting_review: "等待确认",
  rendering: "渲染中",
  completed: "已完成",
  failed: "失败",
};

export function label(status: string): string {
  return statusLabels[status] ?? status;
}

export function isBusy(status: string): boolean {
  return ["transcribing", "selecting", "rendering"].includes(status);
}
