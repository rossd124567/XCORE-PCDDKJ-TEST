# XCORE PCDDKJ Railway V3（只读预测验证）
以用户提供的 V2 app.py 为基础；保留 /probe、/api/draw、/api/history。

## 上传
将 app.py、Dockerfile、requirements.txt、railway.json、Procfile 上传到现有 GitHub 仓库根目录，覆盖同名文件，Commit。Railway 自动部署。Dockerfile 使用 Playwright Chromium 基础镜像，镜像较大，构建可能较久且消耗资源。

## 配置
保留已有环境变量 PCDDKJ_DRAW_URL=https://pcddkj.com/yu28/kj.json?nbr=1
无需 Telegram API、卡密或新的 Railway 服务。

## 测试
https://xcore-pcddkj-test-production.up.railway.app/api/draw
https://xcore-pcddkj-test-production.up.railway.app/api/prediction

/api/prediction 用 Chromium 渲染网站，切换“预测”“大小”“单双”标签，从 #pane-yuce-dx / #pane-yuce-ds 表格第一行第 1 列读取期号、第 4 列读取预测方向。预测期号必须等于最新开奖期号+1；否则 verified=false。真实页面可能变动，此逻辑尚未在 Railway 实测。如果页面行没有加载，会返回 error，不会伪造预测。`verified=true` 只代表字段和期号校验通过，不代表预测正确率或优势。

仅供读取/展示，不含下注操作。请勿在实盘中使用未经过实机测试的数据。
