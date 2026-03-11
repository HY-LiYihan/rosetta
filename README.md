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

## 🚀 快速开始

### 环境要求
- Python 3.8+
- 2GB+ 可用内存（1G 比较极限）

### 一键部署（推荐）

无需 Docker，直接运行以下命令即可快速启动：

```bash
# 克隆项目
git clone https://github.com/HY-LiYihan/rosetta.git
cd rosetta

# 安装依赖
pip install -r requirements.txt

# 启动应用
streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
```

访问应用：http://localhost:8501

## 🧭 双环境说明（服务器 + 开发）

本项目长期维护两套环境：

1. 服务器部署环境（Docker + Compose）
- 目标：稳定运行、可回滚、可脚本化运维
- 推荐入口：`./scripts/deploy/deploy.sh`、`./scripts/deploy/update.sh`

2. 本地开发环境（Conda）
- 目标：快速迭代与调试
- 推荐入口：`conda env create -f environment.yml` + `conda activate rosetta-dev`

说明：依赖基线以 `requirements.txt` 为准，Conda 环境通过 `environment.yml` 引用同一依赖清单。

## 📋 详细部署指南

### 完整部署步骤

以下是在新设备上从零开始配置 Rosetta 的完整步骤：

```bash
# 1. 创建工作目录并进入
sudo mkdir -p /opt/streamlit
cd /opt/streamlit

# 2. 克隆仓库
git clone https://github.com/HY-LiYihan/rosetta.git
cd rosetta

# 3. 构建 Docker 镜像（使用 --network=host 解决网络问题）
docker build --network=host -t rosetta-app .

# 4. 使用 Docker Compose 启动服务（使用已构建的镜像）
docker-compose up -d

# 5. 验证服务运行
docker ps
curl http://localhost:8501/_stcore/health

# 6. 访问应用
# 打开浏览器访问 http://localhost:8501
```

**注意事项**：
- 步骤3使用 `--network=host` 参数可以解决某些网络环境下 pip 安装失败的问题
- docker-compose.yml 已配置为使用已构建的镜像 (`image: rosetta-app`) 和只读挂载 (`/opt/streamlit/rosetta:/app:ro`)
- 如果端口 8501 已被占用，请先停止占用该端口的服务或修改 docker-compose.yml 中的端口映射
- 如果之前构建过，Docker 会使用缓存加速构建过程

### Docker Compose 配置

项目已包含优化后的 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  rosetta:
    image: rosetta-app
    container_name: rosetta-app
    ports:
      - "8501:8501"
    restart: unless-stopped
    volumes:
      - /opt/streamlit/rosetta:/app:ro
```

### 管理命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose up -d

# 更新服务（重新构建）
docker-compose up --build -d
```

推荐使用项目内运维脚本（已分层）：

```bash
./scripts/deploy/deploy.sh
./scripts/deploy/update.sh
./scripts/ops/healthcheck.sh
./scripts/data/backup.sh
```

## 🎯 使用指南

### 首次使用配置

1. **访问应用**：打开 http://localhost:8501
2. **配置 API 密钥**：
   - 在侧边栏选择 AI 平台（Kimi 或 DeepSeek）
   - 输入对应的 API 密钥
   - 系统会自动获取可用模型列表

### 核心功能使用

#### 1. 概念管理
- **查看现有概念**：在侧边栏选择概念查看详情
- **添加新概念**：点击"添加新概念"，填写名称、提示词和示例
- **编辑概念**：选择概念后点击"编辑概念"进行修改
- **导入导出**：支持 JSON 格式的概念数据导入导出

#### 2. 文本标注
1. 选择要标注的概念
2. 输入需要标注的文本
3. 点击"开始标注"按钮
4. 查看 AI 生成的标注结果

#### 3. 历史记录
- 查看最近的标注历史
- 支持删除历史记录

### API 密钥配置

#### 获取 API 密钥
- **DeepSeek 平台**：访问 DeepSeek 官网获取 API 密钥
- **Kimi (Moonshot) 平台**：访问 https://platform.moonshot.cn/console/api-keys
- **Qwen (DashScope) 平台**：访问阿里云 DashScope 控制台获取
- **Zhipu AI (GLM) 平台**：访问智谱 AI 开放平台获取

#### 配置方式
1. **在线配置**：在应用侧边栏直接输入 API 密钥
2. **文件配置**（高级，支持多平台）：
   ```bash
   # 创建配置文件
   mkdir -p .streamlit
   cat > .streamlit/secrets.toml << EOF
   # DeepSeek API 配置
   deepseek_api_key = "your_actual_deepseek_api_key_here"
   
   # Kimi API 配置
   kimi_api_key = "your_actual_kimi_api_key_here"
   
   # Qwen API 配置
   qwen_api_key = "your_actual_qwen_api_key_here"
   
   # Zhipu AI API 配置
   zhipuai_api_key = "your_actual_zhipuai_api_key_here"
   EOF
   ```
   
   系统会自动探测配置文件中可用的平台。

## 🔧 本地开发

### 不使用 Docker 的本地部署（推荐 Conda）

```bash
# 1. 克隆仓库
git clone https://github.com/HY-LiYihan/rosetta.git
cd rosetta

# 2. 创建 Conda 环境（推荐）
conda env create -f environment.yml
conda activate rosetta-dev

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行应用
streamlit run streamlit_app.py
```

如不使用 Conda，也可使用 `venv`：

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\\Scripts\\activate  # Windows
pip install -r requirements.txt
```

## ✅ 环境测试（简要）

### A. 服务器 Docker 环境测试

```bash
# 1) 部署/更新
./scripts/deploy/deploy.sh

# 2) 健康检查
./scripts/ops/healthcheck.sh
curl -f http://localhost:8501/_stcore/health

# 3) 查看状态与日志
docker compose ps
./scripts/ops/logs.sh
```

### B. 本地 Conda 开发环境测试

```bash
# 1) 创建并激活环境
conda env create -f environment.yml
conda activate rosetta-dev

# 2) 运行静态检查与测试
python -m compileall app pages streamlit_app.py api_utils.py
python -m unittest discover -s tests -p 'test_*.py'

# 3) 启动应用
streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
```

### 项目结构

```
rosetta/
├── streamlit_app.py          # 主应用文件
├── api_utils.py             # API 工具函数
├── assets/concepts.json            # 默认概念数据
├── requirements.txt         # Python 依赖
├── Dockerfile              # Docker 构建文件
├── docker-compose.yml      # Docker Compose 配置
├── README.md              # 项目文档
└── assets/                # 静态资源
    ├── rosetta-icon.png
    └── rosetta-icon-whiteback.png
```

## ❓ 常见问题

### Q1: 构建时 pip 安装失败怎么办？
A: 使用 `--network=host` 参数构建：
```bash
docker build --network=host -t rosetta-app .
```

### Q2: 如何修改挂载目录？
A: 编辑 `docker-compose.yml` 中的 volumes 配置：
```yaml
volumes:
  - /your/custom/path:/app:ro
```

### Q3: 如何备份概念数据？
A: 使用侧边栏的导出功能，或直接备份挂载目录中的数据。

### Q4: 支持哪些 AI 平台和模型？
A: 目前支持以下 AI 平台：
- **DeepSeek**：支持 deepseek-chat、deepseek-reasoner、deepseek-coder 等模型
- **Kimi (Moonshot)**：支持 moonshot 和 kimi 系列模型，包括 kimi-k2-thinking 等
- **Qwen (DashScope)**：支持 qwen-plus、qwen-max 等模型
- **Zhipu AI (GLM)**：支持 glm-4.7 等模型

系统会自动探测在 secrets.toml 中配置的可用平台，并动态获取该平台的模型列表。

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

- 文档总入口：`docs/README.md`
- 开发文档入口：`docs/developer/README.md`
- 用户教程：`docs/user/TUTORIAL.md`
- 变更记录：`docs/CHANGELOG.md`

## 🙏 致谢

感谢以下开源项目和技术：
- [Streamlit](https://streamlit.io/) - 优秀的交互式应用框架
- [Kimi](https://www.moonshot.cn/) - 月之暗面大语言模型
- [DeepSeek](https://www.deepseek.com/) - DeepSeek 大语言模型

---

**最后更新**: 2026年3月11日
