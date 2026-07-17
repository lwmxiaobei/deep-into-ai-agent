# 部署到 GitHub Pages

本站是纯静态的 [Docsify](https://docsify.js.org/) 站点，**无需构建**，把仓库文件托管到 GitHub Pages 即可访问。

## 方式一：分支直接托管（最简单，推荐）

1. 在 GitHub 新建一个仓库，例如 `deep-into-ai-agent`（Public）。
2. 在本目录推送代码：
   ```bash
   git remote add origin https://github.com/<你的用户名>/deep-into-ai-agent.git
   git branch -M main
   git push -u origin main
   ```
3. 打开仓库 **Settings → Pages**：
   - **Source** 选择 `Deploy from a branch`
   - **Branch** 选择 `main`，目录选择 `/ (root)`，保存。
4. 等待 1～2 分钟，访问：
   ```
   https://<你的用户名>.github.io/deep-into-ai-agent/
   ```

> 仓库根目录已包含 `.nojekyll` 空文件，确保 GitHub Pages 不用 Jekyll 处理（否则 `_sidebar.md`、`_coverpage.md` 等下划线开头的文件会被忽略）。

## 方式二：GitHub Actions 自动部署（可选）

本仓库默认采用方式一（分支托管），未启用 Actions。若偏好用 Actions 部署，在 **Settings → Pages → Source** 选 **GitHub Actions**，并添加一个使用 `actions/upload-pages-artifact` 的工作流，把仓库根目录作为 artifact 上传即可。

## 本地预览

```bash
# 任选其一
python3 -m http.server 8848      # 然后访问 http://localhost:8848
# 或
npx docsify-cli serve .
```

## 目录结构

```
.
├── index.html          # Docsify 入口与主题配置
├── README.md           # 首页
├── _coverpage.md       # 封面
├── _sidebar.md         # 侧边栏导航
├── .nojekyll           # 关闭 Jekyll
├── docs/
│   ├── 00-引言.md ~ 11-后记.md   # 各章正文
│   ├── images/                    # 图表/表格截图 + 封面图
│   └── 深入理解-AI-Agent.pdf      # PDF 原版（供下载）
├── tools/
│   └── extract.py      # PDF → Markdown 提取脚本（可复现，依赖 PyMuPDF）
└── .github/workflows/deploy.yml
```

## 重新生成正文（可选）

如需从 PDF 重新生成 Markdown 与图片：

```bash
pip3 install PyMuPDF
# 按需修改 tools/extract.py 顶部的 PDF / SITE 路径
python3 tools/extract.py
```

---

**内容版权归原作者李博杰所有**，本在线版仅用于便捷阅读。
