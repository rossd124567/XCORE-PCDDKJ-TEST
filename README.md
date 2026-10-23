玄核 PCDDKJ Railway V3.1 预测期号修复包

问题：V3 的正则表达式误写成 r"\\d{6,}"，无法匹配 3497742 等数字期号。V3.1 修复为 r"\d{6,}"。

使用：解压后将 app.py 上传 GitHub XCORE-PCDDKJ-TEST 根目录覆盖同名文件并 Commit；其余文件无需改动。Railway 自动部署后打开 /api/prediction。

注意：此修复仅处理期号识别；大小/单双方向读取、动态页面加载及期号同步仍需实际验证。若出现新错误请发送完整响应截图。不要用未经验证的预测进行下注。


## V3.2 stability patch
- Replace unbounded ThreadingHTTPServer with HTTPServer to prevent per-request thread exhaustion.
- One background worker collects draw, history and predictions.
- Endpoints return cached JSON immediately, with loading/stale statuses when appropriate.
- /health reports worker status and cache freshness.
- Existing Railway environment variables remain unchanged.
- Deploy and monitor logs. Upstream availability is not guaranteed.


## V3.3 issue-aware upstream polling
- A completed draw + next-issue size/parity prediction pauses upstream checks for 180 seconds (PCDDKJ_SUCCESS_SLEEP_SECONDS).
- Missing, mismatched or failed data retries every 25 seconds (PCDDKJ_RETRY_SECONDS).
- Windows API reads use the cached snapshot and never trigger scraping.
- Health reports next upstream check time. Snapshots older than 420 seconds are marked stale.
- The 3-minute cadence is approximate; clock alignment and upstream publication delays can occur.


## V3.4 countdown-based schedule
- After successful current draw and matching next-issue size/parity prediction, read `data.countdown_raw` from upstream draw JSON.
- Wait exactly `remaining_seconds + 5` (buffer configurable via `PCDDKJ_COUNTDOWN_BUFFER_SECONDS`). Examples: 30 -> 35; 180 -> 185.
- Supported countdown formats: integer seconds, `MM:SS`, `HH:MM:SS`. Reject invalid or >180 seconds.
- If countdown is missing, use 25-second fallback checks instead of guessing a 3-minute deadline.
- If data is incomplete or failed, retry after `PCDDKJ_RETRY_SECONDS` (default 25).
- `/health` shows `last_countdown_seconds`, `schedule_reason`, and `next_upstream_check_at`.
- WARNING: The upstream countdown must refer to the same draw cycle; confirm semantics in production.
