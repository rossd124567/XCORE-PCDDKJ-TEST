# 玄核 PCDDKJ Railway 只读测试服务

此版本只测试 Railway 能否访问 `https://pcddkj.com/`，扫描首页脚本和接口名称线索。**尚未连接真实开奖和预测 API**，不涉及 Telegram、自动下注或任何模拟开奖。

## 部署

1. 新建 GitHub 仓库，例如 `XCORE-PCDDKJ-TEST`，上传本目录四个文件至仓库根目录。
2. Railway → New Project → Deploy from GitHub repo → 选择该仓库。
3. 部署成功后进入服务 Settings → Networking → Generate Domain。
4. 打开 `https://你的域名/health`：应返回 `"ok": true`。
5. 打开 `https://你的域名/probe`：查看 `status`、`http_status`、`scripts`、`endpoint_name_hints`。

`homepage_reachable` 只说明首页能访问，**不代表开奖和预测数据已接通**。`live_draw_connected` 和 `prediction_connected` 均为 `false`，直到完成真实接口校验。

测试完成后可停止或删除这个独立测试服务，避免持续计费。
