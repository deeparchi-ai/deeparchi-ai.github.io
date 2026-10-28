# DeepArchi 官网

这是无需构建的静态官网。现有发布源为 **GitHub Pages 的 `master` 分支根目录 `/`**（`master:/`），当前主域为 **https://www.deeparchi.com.cn/**，另需核验裸域 `deeparchi.com.cn`。发布方式参见 [GitHub Pages 官方说明](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)。

## 文件职责与基线

- `index.html`：实际发布的页面，包含文案、CSS、JavaScript 和内嵌 favicon。
- `CNAME`：保存现有自定义主域 `www.deeparchi.com.cn`；它不是 DNS 配置，也不能代替 GitHub Pages 的域名与 HTTPS 设置。
- `scripts/check_site.py`：仅用 Python 标准库离线检查入口及链接到的 HTML、资源、锚点和 CNAME；不联网探测外链，也不验证 DNS、证书或线上重定向。解析 HTML 属性、内联及引用 CSS 中的资源 URL；浏览器测试补充检查实际加载与交互。
- `tests/landing-page.test.mjs`：已有的 5 项页面文案与约束检查，使用 Node 内置测试。
- `tests/test_check_site.py`：用临时站点文件验证静态检查器的成功与错误行为。
- `tests/visual-smoke.py`：已有桌面和手机菜单场景；入口负责浏览器配置、临时静态服务器及清理。
- `.github/workflows/site-checks.yml`：只检查的 CI，不承担部署。

HTTPS 修复后的基线提交为 `ec9f38079775541ec194fe4555921217de436060`，对应标签 `baseline-https-fixed-20261028`。发布或准备回退前，应核对远端标签确实指向该提交；标签本身不会执行回退。

每次发布的实际检查结果以对应 PR 的 CI 回执及发布后核验记录为准。

## 本地开发与检查

使用 Python 3.12、Node.js 22。网站运行不需要 Node 依赖、Python 服务后台或第三方运行时；Playwright 仅用于开发检查。固定版本 `1.61.0` 已在 [PyPI 发布页](https://pypi.org/project/playwright/1.61.0/) 确认存在。只在仓库虚拟环境安装依赖，不全局安装：

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m playwright install chromium
```

Windows 可用 `py -3.12 -m venv .venv`，并将后续 `.venv/bin/python` 替换为 `.venv\Scripts\python.exe`。Linux 若缺少浏览器系统库，按 Playwright 的安装提示处理；CI 在 GitHub runner 上执行 `playwright install --with-deps chromium`。

在仓库根目录依次执行，任一命令非零退出都需处理后再合并：

```sh
.venv/bin/python scripts/check_site.py
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/landing-page.test.mjs
.venv/bin/python tests/visual-smoke.py
```

浏览器检查默认启动以仓库为根目录、**仅监听 `127.0.0.1` 的临时端口** HTTPServer，结束或检查失败时关闭服务器及浏览器。默认使用 Playwright 安装的 Chromium；设置 `CHROME_PATH` 时仅用于覆盖可执行文件路径，显式无效路径会失败。缺少 Playwright 或浏览器会失败，不会作为跳过通过。通过输出分别列出桌面 1440×960 和手机 390×844 的实际场景。

开发时可在另一个终端启动预览：

```sh
.venv/bin/python -m http.server 4173 --bind 127.0.0.1
```

需要检查已运行的预览时，POSIX shell 可使用：

```sh
BASE_URL=http://127.0.0.1:4173 .venv/bin/python tests/visual-smoke.py
```

也可用当前 shell 的环境变量语法传入 `BASE_URL` 和可选的 `CHROME_PATH`。传入 `BASE_URL` 时脚本不启动或关闭外部服务器。临时预览、测试不会向页面注入配置或更改发布文件。

## PR、合并与发布

1. 在工作分支做最小改动，检查 diff 和本地检查结果，通过 PR 请求独立审查。
2. **先检查、后合并**：确认本地检查及 PR 的 `Site checks` 全部通过，审查完成后再合并 `master`。不要把网络、依赖或浏览器受限导致的未运行记为通过。
3. 合并进入 `master` 后，现有 GitHub Pages 自动发布。`Site checks` 在指向 `master` 的 PR、推送 `master` 及手动触发时运行，只有 `contents: read` 权限，不部署、不读取或上传秘密。
4. **推送后的 CI 和 Pages 发布并行运行，CI 不是 Pages 发布的技术强制门禁。** 本工作流没有配置 branch protection；“先检查、后合并”是当前人工流程约束，不能假定失败检查会自动阻止合并或发布。

## 发布后核验

发布负责人确认 Pages 部署成功后，分别检查以下四个入口的状态码、完整重定向链和最终 URL：

| 入口 | 预期 |
| --- | --- |
| `http://deeparchi.com.cn/` | 最终到达 HTTPS 主域，无循环或错误页 |
| `https://deeparchi.com.cn/` | 证书有效，最终到达 HTTPS 主域 |
| `http://www.deeparchi.com.cn/` | 最终到达 HTTPS 主域 |
| `https://www.deeparchi.com.cn/` | 证书有效，正常显示官网 |

可对每个入口执行 `curl -IL --max-redirs 10 URL` 查看响应链，再用浏览器实际打开；不能仅凭 HEAD 请求成功就认定内容正确。核验页面标题、首屏“AI 原生服务公司”、能力/合作/集成/联系区块及主要链接，检查桌面和手机菜单、console/pageerror、失败资源和横向溢出，排除旧缓存、404 或证书告警。记录发布时间、发布提交和核验结果；本地静态检查不能替代线上核验。

## 回退

回退必须由负责人**人工确认**目标版本、受影响提交和预期结果，再在回退分支通过 `git revert <需撤销的提交>` 生成新提交，运行上述检查并经 PR 审查后合并 `master`，由既有 Pages 流程重新发布。若撤销的是 merge commit，应先确认正确的主线父提交，不能盲目执行。

基线标签只用于定位和比对；不要通过 reset 或 **force-push** 重写发布分支。回退发布后仍需完成双域 HTTP/HTTPS 和页面内容核验。不要将本地备份、凭据或个人环境文件加入仓库。
