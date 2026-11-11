# 性能采样方法与结果

Flask test_client 连续 100 次：中位 0.230 ms，P95 0.535 ms。范围为进程内处理，不含网络、反向代理、排队和 GPIO/舵机执行时间。

| 视口 | reload 到场景数据就绪 ms |
|---|---|
| 1920x1080 | 1085.85 |
| 1366x768 | 901.54 |
| 1024x768 | 932.56 |
| 390x844 | 900.51 |

Chrome headless requestAnimationFrame 采样 398 个间隔，中位 4.200 ms、P95 8.400 ms。它不代表现场 GPU 帧率或渲染预算；不可据此宣称 60 FPS。

单次页面样本含本地 Vite dev、刷新及状态等待，机器负载和缓存影响明显；没有真实并发压测、硬件延迟或 SLA 验收。原始 api_performance.csv、browser_performance.csv、frame_intervals.csv 保留便于复算。

生产构建通过，仍有 chunk 大小警告；后续按需分包。没有为通过验收而关闭警告。
