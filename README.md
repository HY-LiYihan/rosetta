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

## 🎯 使用入口

1. 访问应用：`http://localhost:8501`
2. 主要页面：
- `首页`
- `概念管理`
- `智能标注`
3. 详细的用户使用说明（概念管理、标注流程、API 密钥配置、常见问题）请查看：
- [用户教程](/Users/liyh/rosetta/docs/user/TUTORIAL.md)

### 项目结构

```
rosetta/
├── streamlit_app.py          # 主应用文件
├── app/infrastructure/llm/api_utils.py  # LLM 统一调用入口
├── assets/concepts.json      # 默认概念数据
├── requirements.txt         # Python 依赖
├── Dockerfile              # Docker 构建文件
├── docker-compose.yml      # Docker Compose 配置
├── README.md              # 项目文档
└── assets/                # 静态资源
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

- 文档总入口：[docs/README.md](/Users/liyh/rosetta/docs/README.md)
- 开发文档入口：[docs/developer/README.md](/Users/liyh/rosetta/docs/developer/README.md)
- 用户教程：[docs/user/TUTORIAL.md](/Users/liyh/rosetta/docs/user/TUTORIAL.md)
- 变更记录：[docs/CHANGELOG.md](/Users/liyh/rosetta/docs/CHANGELOG.md)

## 🙏 致谢

感谢以下开源项目和技术：
- [Streamlit](https://streamlit.io/) - 优秀的交互式应用框架
- [Kimi](https://www.moonshot.cn/) - 月之暗面大语言模型
- [DeepSeek](https://www.deepseek.com/) - DeepSeek 大语言模型

---

**最后更新**: 2026年3月11日
