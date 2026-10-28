# DeepArchi 需求验证 Demo

无需构建的静态概念网站，沿用暖纸、深绿、铜色与系统中文字体。目标是围绕 IP 守护、Deep BLM、技术架构规划、Tech M&A 了解需求，再决定开发优先级。无框架、第三方脚本、外部字体、运行时依赖、永久服务器或新增付费服务。

## 文件

- `index.html`：短首页、四个产品卡、本地 A2A 样例、咨询/工具集成入口、需求草稿 dialog；无 JavaScript 时仍可阅读并使用通用邮件联系。
- `assets/site.css`：共用视觉、移动导航、dialog 和减少动态效果设置。
- `assets/site.mjs`：四个虚构样例、五步演示、dialog/焦点、需求草稿与同意界面。
- `assets/signals.mjs`：纯配置/事件校验、RFC6068 草稿编码、默认拒绝的匿名事件适配器。
- `service-catalog.json`：四项服务的同源机器目录；不是可运行的 Agent Card。
- `analytics-config.json`：**接收端当前未连接**，`enabled=false`、`endpoint=null`、`consent_required=true`。
- `developers.html` / `privacy.html`：能力边界、官方文档、公开仓库、浏览器数据行为与统计状态。
- `tests/landing-page.test.mjs` / `tests/signals.test.mjs`：Node 内置离线测试；无外部包。
- `tests/visual-smoke.py`：使用既有 Playwright 的实际交互测试，保留原临时服务器生命周期与错误记录助手。
- `scripts/check_site.py` / `tests/test_check_site.py`：原静态检查器与 9 项单元测试，未修改。
- `.github/workflows/site-checks.yml`：仅将 Node 命令改为运行所有 `tests/*.test.mjs`，仍只检查、不发布。

## 概念边界

所有服务均为“概念 Demo · 招募试点”，所有样例均为虚构场景与拟议交付结构。没有真实客户案例、检索或公司/市场研究结论、价格、节省量或交付承诺。咨询和工具集成为独立的次要入口，无需先购买咨询才能表达产品需求。

A2A 展示五个 SAMPLE 阶段：发现服务 / 描述需求 / 确认范围与授权 / 查看进度 / 接收交付样例。切换产品或重置会清空阶段和样例产物。没有任务执行、Agent 网络调用、服务端任务 ID、真实授权或协议符合性声明；不提供 `.well-known` Agent Card。目录中的 `availability=concept-demo`、`production_ready=false`、`a2a.available=false`、`a2a.endpoint=null` 如实反映状态。公开 Patent MCP、MACS 仓库只证明代码存在，不证明托管服务健康。

需求表单只要求业务问题，期望结果与约束可选，不收集个人邮箱或电话。不要输入敏感数据、密码或密钥。打开/准备草稿都不发信、不上传；用户必须主动点邮件链接，并在本机邮件客户端确认发送。mailto 使用 RFC6068 百分号编码，空格为 `%20`，不是 `+`。复制失败时可手动复制；关闭窗口清空字段与草稿；不依赖 localStorage。文本通过 `textContent` 显示，不插入用户 HTML。仅有用户主动打开的本机 mailto 包含草稿正文，统计和目录不包含正文。

## 事件与统计接入

**远端接收端尚未连接，不可声称已有点击统计或收到需求。父流程在用户授权后配置并核验实际 HTTPS receiver；本分支没有假 URL、接收服务或计数仪表盘。**

父流程需确认接收端所有权、CORS/JSON POST、无重定向、日志与保留策略，配置真实的公网 HTTPS endpoint 后启用；首次真实接收和服务端聚合核验另行完成。`site_id` 是可选公开配置标签，当前不进入事件正文。配置不能注入脚本；无效配置、HTTP、IP 地址、凭据、URL 查询/片段或缺少强制同意声明均拒绝。传输省略 credentials/referrer，不允许重定向，不重放历史事件，不因失败阻断 Demo 或联系。

启用接收端时，首页提供不阻挡使用的可选匿名统计提示；页脚及隐私/开发者页的“匿名统计设置”提供状态和同意/拒绝按钮。默认不发送；每页须主动同意，DNT/GPC 优先于同意。许可与随机 ID 仅存本页内存，不跨页、不写 Cookie/localStorage，可随时关闭。无有效 receiver 时发送零事件。同意后仅测当前或此后进入视口的卡片，不回放同意前的访问。

事件字段严格白名单：

| 字段 | 值 |
| --- | --- |
| `version` | `"1"` |
| `event` | `product_view`, `demo_open`, `demo_complete`, `intent_open`, `mail_draft_ready`, `mailto_click`, `a2a_step`, `a2a_interest` |
| `service` | `ip-guard`, `deep-blm`, `architecture`, `tech-ma` 或非产品入口的 `null` |
| `category` | `product`, `a2a`, `consulting`, `integration`, `general`, `partnership` |
| `surface` | `cards`, `demo`, `a2a`, `support`, `contact`, `demand` |
| `audience` | `"browser_interaction"`（浏览器交互，无法据此核验自然人或自动化） |
| `is_test` | 布尔值 |
| `session_id`, `event_id` | 随机临时 ID，仅用于去重 |
| `step` | 仅 `a2a_step` 的 1–5 整数 |

未知事件/服务/字段全部拒绝。不包含输入、邮箱、完整 URL/query/hash/referrer、个人标识或持久指纹。去重键为事件/服务/分类/界面/步骤的本页组合；会话不等于独立人数，不能报告为 UV。浏览器交互不等于已核实的自然人访问，已知内部验证单独标记 `is_test=true`。GitHub Pages 的静态目录读取目前没有可用访问日志，Agent/爬虫读取量是未知，不是零。`product_view` 只表示卡片至少一半进入视口；`demo_complete` 只表示完整的本地静态样例已展示，不代表阅读完毕或完成服务。A2A 步骤是样例操作。有效场景、试点与付费意向须通过真实沟通人工确认，不从页面动作自动推断，也不设置未经用户批准的立项阈值。

必须区分：**意向入口点击 ≠ 草稿准备 ≠ 邮件实际发出/送达 ≠ 已核实的合格需求**。`mailto_click` 也不能证明邮件发出；页面无法确认邮箱投递或需求质量。

自动化统一使用 `?internal_test=1`。此参数以及本地/非正式域名访问禁止默认真实 transport，即便显式启用测试配置也不发 HTTP 事件；只有测试代码显式注入 fixture transport 才能记录标记为 `is_test=true` 的载荷。正式发送仅允许 HTTPS 的 `www.deeparchi.com.cn` / `deeparchi.com.cn`。fixture 的 `metrics.example.org` 只出现在测试中，由测试 mock，不是配置或接收承诺。模拟成功仅验证适配器，不是远端接收回执。

## 本地验证

使用现有 `.venv`，不需要安装新的运行时/开发包。Node 内置测试无 npm 安装步骤。浏览器测试使用既有 Playwright/Chromium；缺少依赖或沙箱阻止 socket 时如实失败，由父流程在允许环境完成，不作为跳过通过。

```sh
.venv/bin/python scripts/check_site.py
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
node --test tests/*.test.mjs
.venv/bin/python tests/visual-smoke.py
git diff --check
```

浏览器脚本默认仅监听 `127.0.0.1` 的临时随机端口，并在成功/失败时关闭服务器、线程与浏览器；无常驻进程。可传 `BASE_URL` 使用父流程提供的预览，脚本不会管理该外部服务器；`CHROME_PATH` 可指向既有 Chromium。所有测试页面使用测试标识，正式文件不注入测试配置。

浏览器覆盖：320/390/820/1440 无溢出、导航与锚点、键盘/减少动态效果、四项真实按钮的样例内容、关闭/Escape/背景点击及焦点、A2A 全流程/重置/切换、各类需求来源、必填与编码、文本不执行为 HTML、不自动发信、剪贴板拒绝、存储不可用、无 JS、同意/拒绝/DNT/GPC。统计配置与 transport 均为明确 fixture，无真实远端测试。最终实际浏览器视觉检查、receiver 验收和发布由父流程负责。

编码子进程的沙箱可能禁止创建本地 socket，不能据此宣称浏览器通过；应在已授权的父流程环境中真跑交互。实际发布状态以对应 PR 的 CI、Pages 构建及发布后核验报告为准，本机测试不代表线上发布成功或真实手机蜂窝网可达。

## 发布边界

本轮基线为 `c8cd94cb9cdf29db604cde3effc3e58f2f23c42e`，实现分支为 `feat/demand-validation-demo`。不改 DNS、CNAME、Pages 源、邮箱或凭据。发布前须独立审查、实跑浏览器并核验已授权的外部集成，再通过 PR 合并；CI 不承担部署，也不能假定推送后失败的检查会自动阻止 Pages 发布。共享免费统计环境的接收量限制不等于费用或额度隔离；禁止未经确认开启超额付费或调整既有服务。
