# Rosetta: 智能语言学概念标注系统

[![GitHub](https://img.shields.io/github/stars/HY-LiYihan/rosetta?style=social)](https://github.com/HY-LiYihan/rosetta)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-支持-blue)](https://www.docker.com/)

**Rosetta** 是一个基于大语言模型的智能语言学概念标注系统，为语言学研究者和教育工作者提供高效的概念标注工具。

## ✨ 核心功能

- **多平台模型支持**：支持 Kimi、DeepSeek 等多个 AI 平台，动态获取可用模型列表
- **智能概念标注**：利用大语言模型自动标注复杂的语言学概念
- **交互式概念管理**：支持自定义概念定义、示例管理和分类
- **数据持久化**：支持概念数据的导入导出和历史记录
- **研究流水线**：支持 `preview`、`build-index`、`batch`、`audit` 四类实验执行模式
- **Codex Skill 集成**：可将研究流水线安装为本地 Codex skill，由代理直接驱动实验与复核
- **现代化界面**：基于 Streamlit 的响应式设计，支持深色主题

## 🚀 部署方式

### 环境要求
- Python 3.11（推荐）
- 2GB+ 可用内存
- 服务器环境需要 Docker + Docker Compose

下方两种方式都统一从 `/opt/streamlit` 开始。

### 方式 A：服务器部署（Docker，推荐生产）

```bash
# 1) 创建目录（如果不存在）
sudo mkdir -p /opt/streamlit
cd /opt/streamlit

# 2) 获取代码（目录不存在时 clone，存在时更新）
if [ ! -d rosetta ]; then
  git clone https://github.com/HY-LiYihan/rosetta.git
else
  git -C rosetta fetch --all --prune
  git -C rosetta pull --ff-only origin main
fi
cd /opt/streamlit/rosetta

# 3) 准备环境变量（首次）
cp -n .env.example .env
# 默认运行目录：/opt/rosetta/runtime（含 data/backups/logs）

# 4) 启动服务
./scripts/deploy/deploy.sh

# 5) 健康检查
./scripts/ops/healthcheck.sh
curl -f http://localhost:8501/_stcore/health
```

访问地址：http://localhost:8501

日常运维命令：

```bash
cd /opt/streamlit/rosetta
./scripts/deploy/update.sh
./scripts/data/backup.sh
./scripts/ops/logs.sh
docker compose ps
ls -la /opt/rosetta/runtime
```

### 方式 B：本地开发（Conda，推荐开发）

```bash
# 1) 创建目录（如果不存在）
mkdir -p /opt/streamlit
cd /opt/streamlit

# 2) 获取代码（目录不存在时 clone，存在时更新）
if [ ! -d rosetta ]; then
  git clone https://github.com/HY-LiYihan/rosetta.git
else
  git -C rosetta fetch --all --prune
  git -C rosetta pull --ff-only origin main
fi
cd /opt/streamlit/rosetta

# 3) 创建并激活开发环境
conda env create -f environment.yml
conda activate rosetta-dev

# 4) 运行测试（建议）
python -m compileall app streamlit_app.py
python -m unittest discover -s tests -p 'test_*.py'

# 5) 启动应用
streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
```

### Debug 模式（可选）

用于在一段时间内留存操作轨迹与中间结果，便于排查问题。开启后：
1. 首次访问会显示中英双语调试提示（5 秒倒计时后可关闭）。
2. 操作与中间结果写入 `.runtime/logs/debug/*.jsonl`。
3. 导入文件副本保存到 `.runtime/data/debug_uploads/`。

启动方式（二选一）：

```bash
# 方式 1：脚本参数（arg parse）
streamlit run streamlit_app.py -- --debug

# 方式 2：环境变量
ROSETTA_DEBUG_MODE=1 streamlit run streamlit_app.py
```

## 🤖 Codex Skill 集成

本分支额外提供仓库内 skill 包 [skills/rosetta-research](./skills/rosetta-research/SKILL.md)，用于让 Codex 直接操作 Rosetta 的研究流水线。

安装到本机 Codex 技能目录：

```bash
./scripts/skill/install_rosetta_research_skill.sh
```

安装后可在 Codex 中直接使用 `$rosetta-research`，典型场景包括：

- 调整 `configs/research/*.json` 中的定义、few-shot、冲突规则
- 预览动态 prompt：`python scripts/research/run_pipeline.py preview ...`
- 构建 `Embedding-3` CPU 索引：`python scripts/research/run_pipeline.py build-index ...`
- 运行 `audit` 并复核 `.runtime/research/*/review_queue.jsonl` 与 `conflicts.jsonl`

研究流水线说明见 [docs/developer/RESEARCH_PIPELINE.md](./docs/developer/RESEARCH_PIPELINE.md)，skill 集成边界见 [docs/developer/SKILL_INTEGRATION.md](./docs/developer/SKILL_INTEGRATION.md)。

## 🎯 使用入口

1. 访问应用：`http://localhost:8501`
2. 主要页面：
- `首页`
- `概念管理`
- `智能标注`
3. 详细的用户使用说明（概念管理、标注流程、标注格式与常见问题）请查看：
- [用户教程](./docs/user/TUTORIAL.md)

### 项目结构

```
rosetta/
├── streamlit_app.py          # 主应用文件
├── app/research/             # 研究流水线核心
├── app/infrastructure/llm/api_utils.py  # LLM 统一调用入口
├── configs/research/         # 研究配置模板与样本
├── scripts/research/         # 研究流水线 CLI
├── scripts/skill/            # Codex skill 安装脚本
├── skills/rosetta-research/  # 仓库内 skill 包
├── assets/concepts.json      # 默认概念数据
├── requirements.txt          # Python 依赖
├── Dockerfile                # Docker 构建文件
├── docker-compose.yml        # Docker Compose 配置
├── README.md                 # 项目文档
└── assets/                  # 静态资源
    ├── rosetta-icon.png
    └── rosetta-icon-whiteback.png
```

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📞 联系方式

- 项目地址：https://github.com/HY-LiYihan/rosetta
- 问题反馈：通过 GitHub Issues 提交

## 📚 架构与运维文档

- 文档总入口：[docs/README.md](./docs/README.md)
- 开发文档入口：[docs/developer/README.md](./docs/developer/README.md)
- 用户教程：[docs/user/TUTORIAL.md](./docs/user/TUTORIAL.md)
- 变更记录：[docs/CHANGELOG.md](./docs/CHANGELOG.md)

## 🙏 致谢

感谢以下开源项目和技术：
- [Streamlit](https://streamlit.io/) - 优秀的交互式应用框架
- [Kimi](https://www.moonshot.cn/) - 月之暗面大语言模型
- [DeepSeek](https://www.deepseek.com/) - DeepSeek 大语言模型

---

**最后更新**: 2026年4月21日
