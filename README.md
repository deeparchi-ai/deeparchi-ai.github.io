# DeepArchi 需求验证 Demo

无需构建的静态网站，沿用白色、浅灰、蓝色与系统中文字体。首页提供两项专业服务（技术与战略洞察、技术成果转移及概念验证），后置的 A2A 体验区提供四项在线工具（Deep BLM、专利体检、制裁与出口管制速查、Source Slide Editor）。无框架、外部字体或永久服务器；不新增付费第三方依赖或基础设施；工具依赖为本地固定版本，AI 为可选自备 Key 功能，详见下文。

## 文件

- `index.html`：首页 top、capabilities、service-method、online-tools、contact 五个主区块；integrate 作为体验区内的旧锚点保留；包含洞察服务详情弹窗、一个 Deep BLM 本地 A2A 样例、咨询/工具集成入口、需求草稿 dialog；无 JavaScript 时仍可阅读并使用通用邮件联系。
- `assets/insight-services.css`：仅作用于首页洞察卡、详情弹窗及无 JS 原生折叠详情的样式；服务全文只存一份，JS 将其移入原生 dialog，适配 320/390/820/1440 宽度。
- `assets/homepage.css`：首页独立视觉覆盖，两项主业桌面等宽双列、900px 以下单列；工具桌面紧凑四列、900px 以下两列，保留系统字体、原比例 logo、键盘焦点及强制颜色支持。
- `assets/site.css`：共用视觉、移动导航、dialog 和减少动态效果设置。
- `assets/site.mjs`：一个 Deep BLM 虚构样例、五步演示、dialog/焦点、需求草稿与同意界面。
- `assets/signals.mjs`：纯配置/事件校验、RFC6068 草稿编码、默认拒绝的匿名事件适配器。
- `service-catalog.json`：两项人工服务与四项原生工具的机器目录（保留原工具 ID）；不是可运行的 Agent Card。
- `analytics-config.json`：已配置经授权的 CloudBase HTTPS 接收端，`enabled=true`、`consent_required=true`；访客仍默认不发送，须逐页主动同意。
- `developers.html` / `privacy.html`：能力边界、官方文档、公开仓库、浏览器数据行为与统计状态。
- `tests/landing-page.test.mjs` / `tests/insight-services.test.mjs` / `tests/signals.test.mjs`：首页、洞察服务全文/交付/边界与统计的 Node 内置离线测试；无外部包。
- `tests/visual-smoke.py`：两项专业服务、洞察 P1/P2/P3 详情与四项工具的实际交互，320/390/820/1440/1920 布局、无 JS、键盘与强制颜色检查；四个工具真实路由仅加载本地壳，不查询、不上传、不配置模型凭据。保留临时服务器生命周期与错误记录助手。
- `tests/homepage-merge.test.mjs`：PR15 脚本、来源弹窗切换顺序、受保护文件和弹窗的字节保护；两项服务、原工具链接/风险边界及新 CSS 版本校验。
- `scripts/check_site.py` / `tests/test_check_site.py`：静态结构、元数据、链接及资源检查。唯一已知 SPA `apps/source-slide-editor/index.html` 须验证 div#app、无 base、存在的本地 hashed module/CSS 后才豁免静态 h1/main；其他页面继续完整检查。单测覆盖失效 mount/module/resource、元数据、未知 SPA 与路径逃逸。
- `.github/workflows/site-checks.yml`：仅将 Node 命令改为运行所有 `tests/*.test.mjs`，仍只检查、不发布。

## 概念边界

首页以“让技术看得清，让成果走得通。”为居中大标题，主按钮指向两项服务，次按钮沟通项目需求。`#capabilities` 包含两张等权 `article.product`：技术与战略洞察（`tech-insight`）和技术成果转移及概念验证（`tech-transfer-poc`），说明、适合问题与典型交付来自已展示的设计稿；桌面等宽双列、900px 以下单列。`#service-method` 为明确问题、形成判断与方案、分阶段验证与推进三步。后置的 `#online-tools` 标题为“A2A 体验区”，四项真实工具的 URL、ID 和风险说明保留；桌面四列，900px 以下两列。Deep BLM 只有一个原生工具入口，保留 `data-demo="deep-blm"` / `data-tool-entry="deep-blm"`；其他工具不计入 product_view。`#integrate` 和 `#open-a2a` 位于体验区内，明确网页工具和本地虚构样例未连接真实 A2A 服务，不是运行中的端点。`#collaborate` 等联系锚点保留。

白底及品牌蓝 `#0066cc` / hover `#0055ad` 保持；视觉仅通过作用于 `.homepage` 的独立 CSS 覆盖。基于 PR15 `779d1e1` 合并，`site.mjs` 完整 SHA256 为 `603651731d9c7ca2c7c2030fb26d658532e8981664f72a966878bfefca5daf0e`；三页引用仍为 `site.mjs?v=603651731d9c`。来源 dialog 先关闭再打开需求 dialog 的顺序保持。洞察完整 details/dialog 原块字节不变；无 JS 可展开同一份 P1/P2/P3 全文并邮件联系。P1、P2 持续订阅，P3 按项目定制；具体范围、周期与成果形式以双方约定为准。成果转移用原生 `#transfer-details` 说明范围及 PoC 边界，不承诺交易达成、验证通过或转化成功。两项业务的目录均为 manual-contact、production_ready=false，提供原生详情锚点，不提供自动订阅、支付或 A2A。咨询入口沿用 `consulting` 和 `cards` / `support`，`service=null`，不新增事件或服务枚举；详情打开不发产品事件。

概念 Demo 样例均为虚构场景与拟议交付结构。Deep BLM 是独立规划工具，推荐 ≥1024px 电脑端，手机和平板显示说明；不新增 Deep BLM 咨询产品。专利自评不构成法律结论；速查仅为官方清单名称匹配，不构成合规放行；Slide Editor 编辑/导出 HTML，不宣称支持 PPTX，并标注需要 JavaScript、只打开可信文稿。没有真实客户案例、检索或公司/市场研究结论、价格、节省量或交付承诺。咨询和工具集成为独立入口，无需先购买咨询才能表达产品需求。

A2A 仅保留一个 Deep BLM 本地虚构样例，明确“演示样例，非真实客户交付”，不将工具试用推广为 A2A 服务，也不把真实专利体检工具作为虚构样例。展示五个 SAMPLE 阶段：发现服务 / 描述需求 / 确认范围与授权 / 查看进度 / 接收交付样例。重开或重置会清空阶段和样例产物。没有任务执行、Agent 网络调用、服务端任务 ID、真实授权或协议符合性声明；不提供 `.well-known` Agent Card。机器目录保持 `version=1` / `kind=service-catalog`，`services` 包含洞察服务与成果转移及概念验证两项 `manual-contact` 对象；`tools` 数组描述四个工具的真实 ID、名称、URL、可用状态及事实边界。`a2a.available=false`、`a2a.endpoint=null`；可打开工具不代表生产自动化或在线咨询接口可用。公开 Patent MCP、MACS 仓库只证明代码存在，不证明托管服务健康。

需求表单只要求业务问题，期望结果与约束可选，不收集个人邮箱或电话。不要输入敏感数据、密码或密钥。打开/准备草稿都不发信、不上传；用户必须主动点邮件链接，并在本机邮件客户端确认发送。mailto 使用 RFC6068 百分号编码，空格为 `%20`，不是 `+`。复制失败时可手动复制；关闭窗口清空字段与草稿；不依赖 localStorage。文本通过 `textContent` 显示，不插入用户 HTML。短草稿仅在用户主动打开的本机 mailto 中携带正文；编码 URI 超过 1800 字符时保留完整可复制文本，邮件链接不带正文，并提示先复制再粘贴，避免客户端截断。统计和目录不包含正文。

## 事件与统计接入

**经授权的 CloudBase 接收端已部署，原子计数、集合客户端拒绝权限、部署包哈希与真实测试收件已独立读回；这些只是标记测试，不是客户需求证据。本网站没有计数仪表盘，也没有真实 A2A 任务接口。**

已核验精确 Origin 的 CORS/JSON POST、真实201测试事件、去重200与碰撞409、CloudBase集合ADMINONLY及冻结运行文件与云端下载包一致；按累计2000、UTC每日200、会话每日80、测试累计50设限，未压满或重置正式配额。接收量上限不等于共享免费资源隔离，拒收及读库仍会消耗资源。expires_at只是30天标记，无自动删除；平台基础日志字段与保留期待确认（未开通可查CLS不证明平台无其他日志），详见隐私说明。`site_id` 是可选公开配置标签，当前不进入事件正文。配置不能注入脚本；无效配置、HTTP、IP 地址、凭据、URL 查询/片段或缺少强制同意声明均拒绝。传输省略 credentials/referrer，不允许重定向，不重放历史事件，不因失败阻断 Demo 或联系。发送串行且最小间隔 600ms；撤销同意会取消尚未发出的排队事件。限流、共享出口和网络仍可能丢样本，不承诺覆盖全部访问。配置读取失败/无效与未配置分开提示；内部测试/本地预览显式提示不会真实上报。

启用接收端时，首页提供不阻挡使用的可选匿名统计提示；页脚及隐私/开发者页的“匿名统计设置”提供状态和同意/拒绝按钮。默认不发送；每页须主动同意，DNT/GPC 优先于同意。许可与随机 ID 仅存本页内存，不跨页、不写 Cookie/localStorage，可随时关闭。无有效 receiver 时发送零事件。同意后仅测当前或此后进入视口的卡片，不回放同意前的访问。

事件字段严格白名单：

| 字段 | 值 |
| --- | --- |
| `version` | `"1"` |
| `event` | `product_view`, `demo_open`, `demo_complete`, `intent_open`, `mail_draft_ready`, `mailto_click`, `a2a_step`, `a2a_interest` |
| `service` | 当前 UI 仅发送 `deep-blm` 或 `null`（通用入口与两项业务咨询）；接收端冻结枚举仍含历史 ID，前端不发送 |
| `category` | `product`, `a2a`, `consulting`, `integration`, `general`, `partnership` |
| `surface` | `cards`, `demo`, `a2a`, `support`, `contact`, `demand` |
| `audience` | `"browser_interaction"`（浏览器交互，无法据此核验自然人或自动化） |
| `is_test` | 布尔值 |
| `session_id`, `event_id` | 随机临时 ID，仅用于去重 |
| `step` | 仅 `a2a_step` 的 1–5 整数 |

未知事件/服务/字段全部拒绝。`PRODUCTS` 和 A2A 仅含 `deep-blm` 一个虚构样例；卡片可见性统计在观察及同意时都跳过未注册 ID，不发送 `tech-insight` 产品事件。旧 `tech-ma` 已从公开首页、样例定义、A2A 选项和目录移除，接收端与冻结 schema 保持不变。不包含输入、邮箱、完整 URL/query/hash/referrer、个人标识或持久指纹。去重键为事件/服务/分类/界面/步骤的本页组合；会话不等于独立人数，不能报告为 UV。浏览器交互不等于已核实的自然人访问，已知内部验证单独标记 `is_test=true`。GitHub Pages 的静态目录读取目前没有可用访问日志，Agent/爬虫读取量是未知，不是零。`product_view` 只表示卡片至少一半进入视口；`demo_complete` 仅为旧接口兼容枚举，本版不发送，也不据此计算完成率；打开样例只记 `demo_open`，不声称访客看完。通用 A2A 意向只记 `intent_open` 且 service=null，不归属默认产品；产品样例中的 A2A 意向才另记 `a2a_interest`。A2A 步骤是样例操作。有效场景、试点与付费意向须通过真实沟通人工确认，不从页面动作自动推断，也不设置未经用户批准的立项阈值。

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

本地合并验收已由父流程实际执行：57 项 Node 测试、15 项 Python 单测、站点静态检查、首页 visual-smoke、Deep BLM smoke 和 deep-ux-smoke 均通过。首页浏览器用例覆盖两项主业等宽、工具四列/两列降级、320/390/820/1440/1920 无溢出、导航、无 JS 全文、洞察详情、原生工具路由、强制颜色、关闭/Escape/焦点、A2A 五步样例及重置、两项业务通用咨询、需求草稿、剪贴板拒绝、同意/拒绝/DNT/GPC。统计验证使用明确 fixture，无真实远端收件或模型调用；本地通过不代表已经发布。

编码子进程的沙箱可能禁止创建本地 socket，不能据此宣称浏览器通过；应在已授权的父流程环境中真跑交互。实际发布状态以对应 PR 的 CI、Pages 构建及发布后核验报告为准，本机测试不代表线上发布成功或真实手机蜂窝网可达。

## 发布边界

Deep BLM 集成基线为 `b83271a83c5cb0a155b7c57bb32c49526ebd3a16`，实现分支为 `feat/deepblm-trial-integration`。不改 DNS、CNAME、Pages 源、邮箱或凭据。发布前须独立审查、实跑浏览器并核验已授权的外部集成，再通过 PR 合并；CI 不承担部署，也不能假定推送后失败的检查会自动阻止 Pages 发布。共享免费统计环境的接收量限制不等于费用或额度隔离；禁止未经确认开启超额付费或调整既有服务。

### Deep BLM 规划工具试用

入口为 [`apps/deepblm.html`](apps/deepblm.html)。这是完整 15 步浏览器规划工具的公开试用，不是 A2A endpoint，`production_ready` 仍为 false。只使用已获授权的工具字段定义；未包含其他私有仓库材料或业务数据。选定源文件 SHA256 为 `f85c8ccdbbe7bd8d50ecc56ecab285f15791e0e6b41de7a7ca6efab75e7242c7`。

- 初次访问宽度至少 1024px 时加载真实本地 EasyMDE 和 DOMPurify。320/390/820px 为产品、使用场景与咨询说明，不请求编辑器/vendor JS，不创建 Key 表单；从窄屏变为宽屏需刷新才能进入工作台。已启动的桌面会话在缩窄窗口时保留内存，恢复宽屏不会重新初始化或删除草稿。入口不跳转，`internal_test=1` 查询保持不变。
- 桌面工作台采用约 60px 顶栏、分组步骤导航、中央表单和填写帮助三栏；只有工作台在桌面启动后隐藏重复站点页头、标题和页脚。15 步按“现状与差距 / 战略选择 / 战略执行 / 领导力与价值观 / 检查与修订”分组；市场洞察归入战略选择，领导力与价值观单列并标注“贯穿战略与执行”，步骤顺序、字段 ID 和草稿格式不变。当前规划名称实时取企业名称，空白时显示“未命名规划”，没有多项目切换。企业信息使用限 40 字的单行企业名称、三个短文本框和企业现状 Markdown 编辑器；其余长字段保留 EasyMDE，预览按需展开。示例明确标记为虚构且只读，不写入草稿。
- 工作台沿用原 15 步字段、表格和字段 ID，提供编辑、净化预览、添加/删除行、会话内撤销/重做、本机自动保存、手工完整性检查、校验报告及修订记录。导入/导出与撤销/重做/重置采用可键盘操作的 disclosure 菜单；每个字段直接显示“AI 帮写”，文本字段另有独立“导入文本”按钮；完整性报告生成和修订报告复制直接显示在对应步骤。底栏“稍后继续”仅执行真实本机保存，不退出或强制完成。完整性清单按实际字段值生成，支持跳到原字段、编辑后返回原检查位置并显示已补充；它与可编辑的 Markdown 报告并存，**不能证明战略逻辑正确**。自动保存使用 `deepblm-draft-v1`；旧版扁平 `blm-strategy-data` 和 `blm-validation-report` 可恢复，旧原件保留。无账号、云端保存或跨设备自动同步。
- JSON 导入兼容扁平字段与 `{title,created,steps:[{id,title,data}]}`，保留结构化文件的标题与创建时间；新版 `metadata` 保存完成标记与校验报告（含合法旧版字段快照）。字段与表格形状采用白名单；最大 4 MiB、字段 100000 字符、表格 200 行/每单元格 8000 字符、深度 9，节点 60000。未知字段、原型键、错误类型或超限会拒绝，不能用宽松解析静默丢弃内容。导入先校验并保存成功，再替换内存；失败不改草稿或存储。
- 异常旧存储不自动删除或覆盖，暂停自动保存并提供原始恢复副本导出。可显式确认清除本工具数据后重新导入。恢复副本不是规划导入格式；需先在本机检查与修复。浏览器拒绝存储或空间不足时可继续在内存编辑并导出。清理只使用模块列出的工具键，绝不调用 `localStorage.clear()`。
- JSON 用于备份/恢复，Markdown 与 **Word 兼容 .doc** 用于阅读导出；后者是净化的 HTML，不是原生 `.docx`，Office 实际排版尚待核验。不接受 `.docx` 导入；字段可从 UTF-8 `.txt`/`.md` 导入。
- AI 辅助与全局 AI 设置使用独立原生模态对话框；顶栏显示“未配置/已配置”（不代表连接成功），全局配置供 DeepBLM 工作台全部 15 步复用，导入和重置规划不清除配置。写作面板包含当前目标、只读原文快照、补充要求和建议预览；长原文默认折叠，表格按真实列展示，窗口内滚动保持正文和结果可访问。未配置或未获本页同意时仅显示简短全局设置跳转；已配置后不显示设置入口、Key/API/模型配置说明；发送范围、实际接收方和费用同意统一放在全局设置中，一次确认供本页全部 15 步共用，不在步骤内重复展示；从辅助进入设置会暂时关闭辅助，关闭/Esc 返回并保留目标与问题，不叠加模态；支持 Esc、焦点约束和关闭后恢复焦点。关闭正在请求的对话框会取消等待并使旧回复失效；已发送数据无法撤回。AI 为实验性、自备 Key 的可选功能，仅提供 OpenAI 兼容 Chat Completions 接口设置；用户自行核对模型 ID、费用、权限和 CORS。未使用真实凭据验证真实生成。页面打开不请求模型，发送必须主动同意向选定接口传送规划全文、已有校验记录与问题。
- 侧栏“AI 帮写当前步骤”默认选择本步骤首个空字段，全部已填时选择首字段；面板只能切换本步骤字段或“规划讨论”，原 `#ai-discussion` 仍可直接进入讨论。字段模式提供“起草内容 / 完善表达 / 检查缺漏”三个不发送请求的动作，默认按实际字段内容选择起草或完善。补充要求可留空；请求由动作、真实原文、字段指引和规划上下文组合，要求未知信息明确待补充、假设标明，不补造企业事实。表格起草/完善要求原解析器兼容的 JSON 二维字符串数组；只有起草/完善提供人工确认采用，“检查缺漏”和讨论只供阅读，不写入字段。采用后可关闭面板，通过现有撤销恢复。
- 打开已配置的面板时聚焦补充要求，未配置时聚焦全局设置入口；打开字段不会填入预设长问题。每个目标的用户补充要求和动作只存页面内存，同目标关闭/重开及全局设置往返保留，不跨字段串用、不增加存储键；刷新后清空。Ctrl/Cmd+Enter 主动生成，Enter 换行，组合输入期间不发送；生成中阻止重复提交，只在等待时显示取消。打开、切换目标/动作、设置保存和刷新都不自动请求；切换目标/动作、取消、关闭或连接设置变化会取消等待并拒绝迟到回复。结果区明确显示空、生成中、错误与成功状态；原生 dialog 保留 Escape、焦点约束与关闭后焦点恢复。
- 默认 Key 仅在页面内存中，刷新丢失；提供方、接口和模型 ID 通过既有规范化写入 `deepblm-preferences-v1`。个人设备可显式勾选“在此浏览器记住 Key（仅个人设备）”并点击“保存全局设置”，以明文写入独立、版本化的 `deepblm-remembered-key-v1`，绑定精确规范化的提供方与接口。localStorage 可被同源脚本、XSS 或本机用户读取，并非安全密钥库，不宜用于共享设备。仅限同一浏览器与来源，无账号、云端或跨设备同步；刷新/重新打开仍须重新选择外部处理同意，不自动请求。Key 不上传到本站服务器，仅在同意后主动发送时直接交给选定提供方；不进入草稿、恢复副本、报告或导出。取消勾选后保存会删除旧记忆记录；“忘记 Key”和清除本工具数据会清空内存并尝试删除专用记录，失败时明确提示。
- 更改提供方/接口须重新输入 Key 并保存；配置变动使同意、在途请求与旧结果失效。另一标签页更改相关存储也会丢弃本页凭据，避免静默重定向。异常/被拒绝/超额存储不影响手工编辑与导出，不把秘密记录放入恢复副本。不读取其他应用配置，不自动使用 `blm-ai-config` 的旧 Key，检测存在后提供显式删除按钮。
- 自定义接口只接受公共域名的 HTTPS URL，拒绝 URL 凭据、查询、片段、非标准端口、本地名称与 IP 字面量；静态浏览器应用不能审计提供方的 DNS 配置或数据处理，请自行核对所填接口。请求不携带 Cookie，不跟随重定向；错误仅显示通用说明/HTTP 状态，不显示或记录原始提供方响应。
- 公共链接导入、AllOrigins、自动网络搜索、共享 Key/Cursor 配置桥接均未纳入新版。全部运行依赖在 `assets/vendor`，版本、字节数和 SHA256 见 `manifest.json`；保留上游许可。EasyMDE 禁用字体自动下载与拼写检查，不用 CDN 回退。Font Awesome 资产保留但工作台未使用图标字体。
- 工具不导入 `site.mjs`/`signals.mjs`，不初始化首页统计。首页 Deep BLM 卡为普通链接，保留 `data-demo="deep-blm"` 身份及“打开规划工具（试用）”标签；用户同意后的现有 `demo_open` 仅说明入口兴趣，不是规划完成。
- 内容安全入口为 `deepblm-security.mjs`：真实 DOMPurify 严格标签白名单，去除图片等自动外载、事件、样式、SVG、表单、框架等；只允许显式 HTTP(S)/mailto 链接并加 `noopener noreferrer`。文本/表格使用 DOM 文本或转义；预览、AI 回复、报告、修订与 Word HTML 共用净化路径。新版不保留旧内联事件处理器；CSP 的脚本限同源，无 `unsafe-eval` 或内联脚本许可。样式仍允许 `unsafe-inline` 以兼容编辑器布局，AI 的动态 HTTPS 接口使 `connect-src` 为 `https:`，不宣称是完全锁定的 CSP。浏览器端存储与 Key 仍受同源其他页面代码及浏览器扩展的安全边界限制。

### 深度填写与审阅 UX

- 左侧 15 步按实际非空字段显示“未开始 / 填写中 / 已填写”和字段数；仅表示已输入内容，不代表战略通过审核。右侧字段目录可直达真实编辑器，“下一项待补充”循环定位本步实际空字段。正常切换步骤会在本页恢复滚动位置、上次编辑字段与光标/选区；检查清单跳转仍以明确目标为先。成功导入和清除工具数据清理全部位置记忆；单步重置清理本步，取消或失败不抹掉原工作状态。
- AI 建议支持“编辑建议 / 预览 / 原文对照”。对照同时展示生成时原文和当前编辑稿，不冒充语义差异分析；复制、净化预览和人工确认采用都使用最新编辑稿。表格编辑为带列顺序说明的 JSON 二维字符串数组，坏结构、空稿和超限不会写入；检查缺漏和规划讨论始终不可采用。采用后可通过既有历史撤销。
- 大屏采用要求与结果分栏；1024px 宽度按纵向排列。底栏常驻显示明确目标字段的采用、复制、下一空字段与返回字段操作，长结果不会把采用推到视口外。复制被浏览器拒绝时如实展示只读手工复制框；切换目标后的迟到剪贴板回调不会显示旧字段内容或抢走焦点。
- 问题、动作与成功建议编辑稿仅存页面内存：同目标关闭重开或切走再回来可恢复，不额外调用模型。缓存最多 24 个目标、总计 600000 字符，最近最少使用的记录会被淘汰；刷新清空，不写入存储、草稿或导出。任何规划内容/历史变动和连接/Key/同意/其他标签设置变更都会使旧建议不可采用；成功导入清全部会话，单步重置清本步补充要求，取消/失败导入保持会话。生成、重新生成始终需要主动操作。
- 另一标签仅切换步骤、重复保存相同内容（包括序列化时间或键顺序不同）不取消本页请求、不清空建议。真正的外部草稿变更不会自动覆盖本页；在途请求继续接收，但返回内容明确标为过期、只读、可复制且不可采用，外部继续编辑也不会抹掉已收到的参考内容。连接/Key/同意变更仍立即使旧连接和在途请求失效。这不是跨标签协同编辑，建议先核对并导出本页备份。

关键实现：`assets/deepblm-{entry,workspace,ui,sessions,data,schema,security,credentials}.mjs` 与独立 `assets/deepblm.css`；纯 Node 测试含 `tests/deepblm.test.mjs` 和 `tests/deepblm-sessions.test.mjs`；真实浏览器验收含既有与深度 UX 两套 DeepBLM 脚本。

```sh
node --test tests/*.test.mjs
.venv/bin/python scripts/check_site.py
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
.venv/bin/python tests/visual-smoke.py
.venv/bin/python tests/deepblm-smoke.py
.venv/bin/python tests/deepblm-deep-ux-smoke.py
# 可选：BASE_URL=https://预览站点、CHROME_PATH=/浏览器路径
# 可选：DEEPBLM_SCREENSHOT_DIR=${TMPDIR}/deepblm-screenshots
```

浏览器脚本复用既有回环 HTTP helper；AI 请求只使用显式 `fixture-only` 路由与非真实 Key，不调用收费模型。保留 1440/1024 下全部步骤、五组导航及归属、原生控件超限拒绝、只读示例、净化预览、检查清单、导入原子性、存储失败和全局 AI 配置/凭据安全回归。新增写作面板用例覆盖直接字段入口、侧栏首空/全填默认、只读文本/表格快照及目标切换、三个动作不自动请求、空补充要求的实际载荷、同目标重开与设置往返、讨论/检查无采用、Ctrl/Cmd+Enter/换行及模拟 IME 事件、生成中重复提交/取消/迟到结果拒绝、结构化表格拒绝/确认采用/撤销，以及 1024/1440 的长原文和长结果滚动。设置 `DEEPBLM_SCREENSHOT_DIR` 后会额外保存 `writing-composer-{1024,1440}.png` 与 `writing-result-{1024,1440}.png`。

此前 Deep BLM 改版的父流程记录：真实运行 Node 49 项、Python 9 项、站点静态检查及 `deepblm-smoke.py`、`deepblm-deep-ux-smoke.py`、`visual-smoke.py`；并检查 1024/1440 宽度及 1440×560、1024×600 短高场景。前后测量确认：长表单返回由滚动归零变为恢复原位置和焦点；关闭重开由丢掉结果变为保留编辑稿，且请求数不增加；长结果采用按钮由视口外变为常驻可见。新增用例覆盖最新编辑稿预览/对照/采用/撤销、畸形表格拒绝、剪贴板失败及迟到结果隔离、跨目标恢复和规划/连接变更失效、导入/重置/清除位置记忆、真实双标签导航/等价保存/内容冲突与在途响应只读保留。首访断言标题焦点，回访断言明确字段 ID，表格进一步断言行列，不能用“焦点在区域内”放过错误目标。测试仅用非真实 Key 和显式模拟接口；不将网络或沙箱失败视为通过。新增主要选择器：`#field-outline` / `[data-outline-field]` / `#next-missing-field`、`#ai-draft-editor`、`[data-ai-view]`、`#ai-original` / `#ai-compare-draft`、`#ai-footer` / `#ai-copy` / `#ai-copy-fallback` / `#ai-return`；原字段、编辑器、导航、导入/导出与全局设置选择器保留。

验收应同时运行上述纯逻辑、静态与真实浏览器命令；受限编码沙箱的 socket 拒绝不等于浏览器验收成功。模型请求验收仅使用显式非真实夹具，不证明真实提供方的 CORS、账户权限或生成质量；Word 实际排版也需单独核验。同一浏览器请勿在多个标签页同时编辑同一规划，以免后保存的草稿覆盖先前版本；开始研讨前请先导出 JSON 备份。

## 本轮首页工作树预览（2026-10-30）

基于 `origin/master=b453dde`，仅预览，未提交/推送/发布；父流程另提供公开文件暂存区的临时外网预览。共享 `site.css`、vendor、统计接收端/配置、CNAME、DNS 及机器设置不变。专利体检应用仅修改名称与介绍文字，评分与业务逻辑不变；其他工具不变。洞察 P1/P2/P3 全文和无 JS 回退保持原文。下方保留修正前验证记录，最新定点修正的验证状态另列。

在此工作树运行 `python -m http.server 8765 --bind 127.0.0.1`，访问 `http://127.0.0.1:8765/?internal_test=1`。同一解释器可运行 `scripts/check_site.py`、`-m unittest discover -s tests -p 'test_*.py'`、`tests/visual-smoke.py` 与未改动的 `tests/deepblm-smoke.py`；Node 使用 `node --test tests/*.test.mjs`。

修正前预览的父环境验证记录（不代表下述修正已通过浏览器）：Node 51 项、Python 15 项单测、静态检查、`visual-smoke.py`、未修改的 `deepblm-smoke.py` 与 `git diff --check` 均通过。Codex 沙箱最初受本地 socket 权限限制，父环境已实际启动预览并补跑浏览器，不再视为待验。另独立核验 320/390/820/1440/1920 五档宽度、三服务/四工具分类、导航和首屏双路径、详情关闭及焦点恢复、无 JS 完整正文和邮件入口；四个工具页面均实际加载且无页面错误，未发起真实 AI 或清单查询。桌面与手机截图及 JSON 证据保存于当前工程 profile 的 `cache/scratch/homepage-service-tool-ux-evidence/`。洞察 details/dialog、共享 CSS、洞察 CSS、工具内部、统计配置/接收端与 CNAME 均与基线逐字一致。父环境当前预览地址为 `http://127.0.0.1:4181/?internal_test=1`，仍未发布。


### 最新定点修正（2026-10-30）

保留现有未提交工作；首页恢复原品牌蓝与居中布局，主标题改为“AI原生服务，全新体验”。专业服务仅保留技术与战略洞察服务；在线工具为 Deep BLM、专利体检、制裁与出口管制速查、Source Slide Editor。原概念服务已从前端、样例、选择器和机器目录移除，接收端冻结 schema 不变。洞察 details/dialog 原始字节保持一致；专利应用仅文字改名，原十题评分不变。Node 与视觉测试按一服务、四工具和一个 Deep BLM A2A 样例更新。浏览器 socket 在编码沙箱受限，本次不尝试浏览器或启动服务器；视觉、DeepBLM 和公开移动截图由父流程另行验证与刷新现有预览。本次无提交、推送或发布。

本次修正父环境验证：Node 54 项、Python unittest 15 项、`scripts/check_site.py`、`visual-smoke.py`、未修改的 `deepblm-smoke.py` 和 `git diff --check` 均通过。共享 CSS、冻结统计配置、洞察 details/dialog 全文均逐字一致；专利应用脚本仅变更名称和介绍字符串，评分与运行逻辑不变。独立在本地与公网预览真验 320/390/820/1440/1920 五档：原蓝色 `rgb(0, 102, 204)`、精确主标题、居中布局、一服务/四工具、删除旧服务、详情与焦点恢复、无 JS 全文/邮件入口、专利应用改名均通过，零页面错误与 POST。截图与 JSON 位于当前 profile `cache/scratch/homepage-centered-revision-evidence/`。现有临时预览链接已刷新：`https://camping-conviction-maine-indoor.trycloudflare.com/?internal_test=1`，统计关闭、禁止索引，不改正式首页。Cloudflare 会移除 `email_off` 标记；比较时仅忽略该标记，HTML 内容一致，CSS/JS/JSON 精确字节一致。该标记仅加在预览暂存文件，避免邮箱被自动改写而破坏无 JS 邮件入口。
