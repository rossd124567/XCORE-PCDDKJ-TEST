# 玄核 PCDDKJ Railway 数据测试 V2（只读）

覆盖原 GitHub 仓库的 `app.py` 即可。保留原 `Procfile`、`requirements.txt`、`railway.json`。

部署后访问：
- `/health` 服务健康状态
- `/probe` 网站连接、JS 文件和接口名称线索
- `/api/draw` 最新开奖：默认返回 `unconfigured`，必须先核实完整的 `kj.json` Request URL，再在 Railway Variables 设置 `PCDDKJ_DRAW_URL`
- `/api/history` 历史开奖：默认返回 `unconfigured`，必须先核实完整的 `history.json` Request URL，再设置 `PCDDKJ_HISTORY_URL`
- `/api/prediction` 预测页面静态结构诊断；目前返回 `unverified`，**不是已接通预测**

## 为什么不直接使用 /pc28/stats.json？
`/probe` 仅发现该路径的字面线索，没有证据表明它是 `kj.json` 或 `history.json` 的真实接口。

## 数据安全
仅允许访问 pcddkj.com 的 HTTPS URL，且做期号、号码、和值、大小单双校验。没有通过验证的数据不会标记为 `verified:true`。本程序不发送 Telegram 消息，不下注。

## 下一步
在网站 F12 → Network → Fetch/XHR 中，点击 `kj.json` 和 `history.json`，复制 Request URL。不要提供 Cookie、授权头或账号信息。预测接口需要确认实际返回内容后才能继续实现。
