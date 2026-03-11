# 用户教程

更新时间: 2026-03-11

## 1. 你需要准备什么

1. 一个可运行的 Rosetta 环境（服务器 Docker 或本地 Conda）。
2. 至少一个 LLM 平台 API Key（DeepSeek/Kimi/Qwen/Zhipu）。

## 2. 快速开始

1. 打开应用首页。
2. 进入「概念管理」导入或创建概念。
3. 进入「智能标注」输入文本并开始标注。

## 3. 概念管理

1. 导出概念：下载 JSON 文件（包含版本号）。
2. 导入概念：支持替换或追加。
3. 导入前会显示预检摘要：
- 数据版本
- 重复概念数
- 自动修复字段数
- 可导入概念数

## 4. 智能标注

1. 选择平台和模型。
2. 选择概念并输入文本。
3. 查看结构化标注结果与历史记录。

## 5. 常见问题

1. 无可用平台：检查 `.streamlit/secrets.toml` 是否配置 API Key。
2. 导入失败：根据 `字段/原因/建议` 修复 JSON。
3. 启动报 secrets 错误：当前版本已兼容无 secrets 场景，会显示平台未配置而不是崩溃。

## 6. API 密钥配置

### 6.1 获取 API Key

1. DeepSeek：DeepSeek 官网
2. Kimi (Moonshot)：https://platform.moonshot.cn/console/api-keys
3. Qwen (DashScope)：阿里云 DashScope 控制台
4. Zhipu AI (GLM)：智谱 AI 开放平台

### 6.2 配置方式

1. 在线配置：在应用侧边栏输入 API Key。
2. 文件配置（推荐多平台）：

```bash
mkdir -p .streamlit
cat > .streamlit/secrets.toml << EOF
deepseek_api_key = "your_actual_deepseek_api_key_here"
kimi_api_key = "your_actual_kimi_api_key_here"
qwen_api_key = "your_actual_qwen_api_key_here"
zhipuai_api_key = "your_actual_zhipuai_api_key_here"
EOF
```

## 7. 常见运维问题（用户视角）

1. 构建时 pip 安装失败：可尝试 `docker build --network=host ...`。
2. 需要改挂载目录：修改 `docker-compose.yml` 的 `volumes`。
3. 需要备份概念数据：使用 `./scripts/data/backup.sh`。
