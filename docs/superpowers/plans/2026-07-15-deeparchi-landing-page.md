# DeepArchi Landing Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current product-listing homepage with a bilingual-ready Chinese landing page that establishes DeepArchi as an AI-native professional-services brand for clients and partners, and accurately describes its MCP and A2A integration posture.

**Architecture:** Keep GitHub Pages' zero-build static architecture: a single semantic `index.html` containing scoped CSS and small progressive-enhancement JavaScript. Use a Node built-in test that asserts the public page's required content, navigation, accessibility landmarks, and that no local or fabricated protocol endpoint is published.

**Tech Stack:** HTML5, CSS3, vanilla JavaScript, Node.js built-in test runner, GitHub Pages.

## Global Constraints

- Preserve `CNAME` as `www.deeparchi.com.cn`.
- Keep the site dependency-free and deployable from the repository root on GitHub Pages.
- Use the approved three-part ability chain: strategic consulting, validated delivery, and tool-platform operations.
- Present BLM only as a strategic-planning framework, never as a peer service.
- Use `创始人兼首席架构师`, never `主理人`.
- Never publish `localhost`, private IP addresses, tokens, API keys, or invented MCP/A2A service URLs.
- Describe Patent MCP as open-source/self-hosted and A2A as private preview with a contact path.

---

### Task 1: Establish executable landing-page regression checks

**Files:**
- Create: `tests/landing-page.test.mjs`

**Interfaces:**
- Consumes: repository-root `index.html` as UTF-8 text.
- Produces: a Node test suite runnable with `node --test tests/landing-page.test.mjs`.

- [ ] **Step 1: Write the failing test**

```js
import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const html = await readFile(new URL("../index.html", import.meta.url), "utf8");

test("presents the approved DeepArchi positioning and collaboration paths", () => {
  assert.match(html, /从战略判断到持续运营/);
  assert.match(html, /战略咨询/);
  assert.match(html, /验证型交付/);
  assert.match(html, /工具平台/);
  assert.match(html, /探索解决方案/);
  assert.match(html, /探索合作/);
});

test("keeps BLM as a framework and uses the approved accountability title", () => {
  assert.match(html, /战略共创与转型路线图/);
  assert.match(html, /以 BLM 等框架为基础/);
  assert.match(html, /创始人兼首席架构师/);
  assert.doesNotMatch(html, /主理人/);
});

test("describes integrations without publishing unsafe or fabricated endpoints", () => {
  assert.match(html, /Patent MCP/);
  assert.match(html, /自部署/);
  assert.match(html, /A2A.*私测/);
  assert.doesNotMatch(html, /(?:localhost|127\\.0\\.0\\.1|0\\.0\\.0\\.0)/i);
  assert.doesNotMatch(html, /https:\/\/\{[^}]+\}/);
});
```

- [ ] **Step 2: Run the test to verify it fails against the old page**

Run: `node --test tests/landing-page.test.mjs`

Expected: FAIL because the current page has the old hero, treats BLM as a peer item, and has no approved integration wording.

- [ ] **Step 3: Commit the test after the production page is implemented and passing**

```powershell
git add tests/landing-page.test.mjs index.html
git commit -m "feat: launch DeepArchi partner landing page"
```

### Task 2: Replace the homepage with the approved information architecture

**Files:**
- Modify: `index.html`

**Interfaces:**
- Consumes: the content and safety constraints in this plan.
- Produces: an accessible one-page public landing page with anchors `#capabilities`, `#collaborate`, `#integrate`, and `#contact`.

- [ ] **Step 1: Replace the document structure with semantic landmarks**

Use a `header` navigation, `main` sections, and a `footer`. Add a skip link and visible keyboard focus states. The hero must use this approved copy:

```html
<p class="eyebrow">AI-NATIVE PROFESSIONAL SERVICES</p>
<h1>从战略判断到持续运营，<br><span>让 AI 成为可交付的专业能力。</span></h1>
<p class="hero-copy">DeepArchi 以咨询定义方向，以验证型交付验证方法，以工具平台沉淀可持续运行的能力。</p>
<a class="button button-primary" href="#contact">探索解决方案</a>
<a class="button button-secondary" href="#collaborate">探索合作</a>
```

- [ ] **Step 2: Implement the capability-chain and consultation sections**

Render the three capabilities in this order: `战略咨询` → `验证型交付` → `工具平台`.

The strategic-consulting card must contain exactly these service labels and explanations:

```html
<li><strong>AI 战略诊断</strong><span>识别业务机会、现有能力、关键约束与优先议题。</span></li>
<li><strong>战略共创与转型路线图</strong><span>以 BLM 等框架为基础，明确阶段目标、投资重点与行动路径。</span></li>
<li><strong>AI 原生能力、架构与组织设计</strong><span>统筹业务流程、Agent 与数据能力、技术架构、角色分工和治理机制。</span></li>
```

- [ ] **Step 3: Add client, partner, trust, and founder pathways**

Add two visually parallel cards under `#collaborate`:

```html
<article>
  <p class="card-kicker">FOR CLIENTS</p>
  <h3>从问题开始，而不是从工具开始</h3>
  <p>共同界定优先事项，组装可验证能力，再进入可持续运营。</p>
</article>
<article>
  <p class="card-kicker">FOR PARTNERS</p>
  <h3>共同售前、共同交付、共同产品化</h3>
  <p>把行业专长、数据、工具与交付能力组合为可复制的联合方案。</p>
</article>
```

Include a trust section that labels product maturity truthfully: `Patent MCP — 已上线`, `SanctionsSight — 已上线`, `认知外骨骼 — 内测`, and `MACS — 开发中`. Add a person-and-accountability card headed `创始人兼首席架构师`, stating responsibility for strategic judgment, solution architecture, and delivery quality.

- [ ] **Step 4: Add the safe integration section**

Create `#integrate` with two protocol cards. MCP must link to `https://github.com/deeparchi-ai/patent-mcp-server` and state that Patent MCP supports open-source self-hosted integration. A2A must state `私测申请中` and use the existing contact route; it must not contain a pseudo URL, local address, token, or credential sample.

- [ ] **Step 5: Implement responsive design and minimal interaction**

Use CSS custom properties, an accessible mobile navigation toggle, responsive card grids, a `prefers-reduced-motion` rule, and no external JavaScript or CSS dependencies. The browser must remain fully usable with JavaScript disabled except for mobile-menu convenience.

- [ ] **Step 6: Run the regression suite**

Run: `node --test tests/landing-page.test.mjs`

Expected: all three subtests PASS.

### Task 3: Perform static, visual, and deployment verification

**Files:**
- Modify: `index.html` only if verification finds a defect.
- Test: `tests/landing-page.test.mjs`

**Interfaces:**
- Consumes: the completed static page and regression test.
- Produces: a committed GitHub Pages update and post-deployment HTTP verification.

- [ ] **Step 1: Check the document for accidental unsafe values and obsolete copy**

Run:

```powershell
Select-String -Path index.html -Pattern '主理人|localhost|127\.0\.0\.1|0\.0\.0\.0|https://\{' -CaseSensitive:$false
```

Expected: no output.

- [ ] **Step 2: Run the automated test suite**

Run: `node --test tests/landing-page.test.mjs`

Expected: `pass 3`, `fail 0`.

- [ ] **Step 3: Serve and inspect the public page locally**

Run: `python -m http.server 4173 --directory .`

Verify desktop and mobile widths, anchor navigation, focus visibility, and that both integration cards communicate the intended availability states.

- [ ] **Step 4: Commit the finished page and push the Pages branch**

Run:

```powershell
git add index.html tests/landing-page.test.mjs docs/superpowers/plans/2026-07-15-deeparchi-landing-page.md
git commit -m "feat: launch DeepArchi partner landing page"
git push origin master
```

- [ ] **Step 5: Verify the deployed document**

Run:

```powershell
curl.exe -fsS http://www.deeparchi.com.cn/ | Select-String -Pattern '从战略判断到持续运营'
```

Expected: matching HTML after GitHub Pages propagation. If HTTPS certificate validation still fails, report it separately as a GitHub Pages custom-domain configuration issue; do not suppress certificate verification in production validation.

## Self-Review

- Coverage: Task 1 protects approved copy and protocol-safety requirements; Task 2 implements every confirmed website section; Task 3 verifies static content, interaction, deployment, and the custom-domain caveat.
- Placeholder scan: no production endpoints are invented; all content and commands are concrete.
- Consistency: every test expectation maps directly to text created in Task 2, and Task 3 runs the same Node test command.
