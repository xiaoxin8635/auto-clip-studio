# 评测报告

状态：已执行。

说明：本报告基于 10 条带官方字幕的 NASA 公共视频，标注片段为官方字幕自动生成的草稿，仅用于横向对比。本轮已将模型边界强制吸附到转录 cue 边界；误差未达 3 秒，说明剩余瓶颈是模型选择的句子范围与标注草稿不一致，而不是任意毫秒边界。

## 汇总

- 选段命中视频：10/10
- 字幕可用率：100%
- 渲染成功率：100%
- 平均边界误差：7.62 秒
- 平均端到端耗时：10.66 秒

## 明细

| 视频 | 理想片段命中 | 边界误差 | 字幕可用 | 渲染成功 | 端到端耗时 | 失败原因 |
|---|---:|---:|---|---|---:|---|
| GRC-2020-CM-0150.mp4 | 3/5 | 12.38s | 是 | 是 | 15.01s | - |
| GRC-2020-CM-0151.mp4 | 3/5 | 7.00s | 是 | 是 | 8.61s | - |
| Artemis-I-Launches-to-the-Moon-(Official-NASA-Recap).mp4 | 1/4 | 6.99s | 是 | 是 | 7.86s | - |
| The-First-Artemis-Robotic-Launch-to-the-Moon-on-This-Week-@NASA-–-January-5,-2024.mp4 | 4/4 | 6.42s | 是 | 是 | 8.67s | - |
| JPL-20211115-MARSf-0001-Hows-the-Weather-on-Mars.mp4 | 3/5 | 8.22s | 是 | 是 | 9.45s | - |
| JPL-20210416-M2020f-0001-April-16-Mars-Report.mp4 | 3/5 | 8.68s | 是 | 是 | 8.29s | - |
| First-Images-from-the-James-Webb-Space-Telescope-(Official-NASA-Highlights).mp4 | 2/5 | 4.94s | 是 | 是 | 9.91s | - |
| Introducing-NASA’s-NEW-Earth-System-Observatory.mp4 | 4/5 | 9.47s | 是 | 是 | 13.46s | - |
| A-Milestone-for-an-American-Astronaut-on-the-Space-Station-on-This-Week-@NASA-–-February-4,-2022.mp4 | 2/5 | 8.80s | 是 | 是 | 13.87s | - |
| Nasas-SpaceX-Crew-2-Astronauts-Headed-to-International-Space-Station.mp4 | 3/5 | 3.35s | 是 | 是 | 11.47s | - |
