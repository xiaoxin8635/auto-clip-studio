# 真实素材评测计划

## 目标

验证真实 AI Provider 在长视频上的选段质量、字幕质量、边界准确性和渲染稳定性。

## 素材集

准备 10 条视频，覆盖：

- 中文播客 2 条
- 双人访谈 2 条
- 课程录播 2 条
- 演讲/分享 2 条
- 会议录音录像 2 条

每条建议 20-60 分钟，分辨率不低于 720p。素材只放在本机，不提交仓库。

## 标注格式

在本地 JSON 中为每条视频标注 3-5 个理想片段：

```json
{
  "video": "podcast-01.mp4",
  "duration_ms": 3600000,
  "ideal_segments": [
    {
      "title": "示例片段",
      "start_ms": 120000,
      "end_ms": 165000,
      "reason": "观点完整，有冲突和结论"
    }
  ]
}
```

标注文件必须是一个 JSON 数组，每个视频一条记录；`video` 不能重复。

## 结果格式

每次真实 Provider 评测完成后，在本机记录候选片段和过程指标（文件放在 `.local/`，不要提交）：

```json
{
  "video": "podcast-01.mp4",
  "candidates": [
    {
      "title": "AI 生成的候选标题",
      "start_ms": 120000,
      "end_ms": 165000
    }
  ],
  "transcript_usable": true,
  "rendered": true,
  "analysis_ms": 180000,
  "failure_reason": ""
}
```

结果文件同样必须是 JSON 数组，且与标注文件的 `video` 集合完全一致。

## 指标

- 选段命中率：候选片段与人工理想片段时间重叠超过 50% 记为命中
- 边界误差：候选开始/结束与人工边界的平均绝对差
- 字幕可用率：转录文本可读懂且时间基本同步
- 渲染成功率：成功产出可播放 MP4 的比例
- 端到端耗时：上传完成到候选可 review 的时间

## 通过线

- 至少 6/10 条视频命中一个人工理想片段
- 平均边界误差不超过 3 秒
- 字幕可用率不低于 80%
- 渲染成功率不低于 95%

结果记录到 `docs/evaluation-report.md`，包含每条素材的原始表现和失败原因。

## 生成报告

在项目根目录执行：

```bash
python -m app.evaluation .local/annotations.json .local/results.json --output docs/evaluation-report.md
```

工具会校验输入结构、去重、边界合法性，计算命中率、平均边界误差、字幕可用率、渲染成功率和端到端耗时，并生成 Markdown 汇总与明细表。

## 自动准备素材草稿

可以使用 NASA 图片视频 API 自动下载带官方字幕的公共素材，并生成标注草稿：

```bash
cd backend
python -m app.prepare_evaluation \
  --query "NASA educational video" \
  --count 5 \
  --max-variant mobile \
  --output ..\.local\evaluation-nasa
```

说明：

- 只下载带 `.srt` 字幕的 MP4。
- 下载文件和字幕只保存在 `.local/`，不会提交仓库。
- 生成的 `annotations.json` 只是草稿，必须人工检查标题、理由和起止点后再作为正式标注。
- `--max-variant` 控制清晰度与体积，`mobile` 通常适合本机评测；`medium` 更清晰但下载更慢。
