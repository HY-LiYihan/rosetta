# 📝 语言学概念标注工具 & 💬 聊天机器人

这个项目包含两个Streamlit应用：

## 1. 📝 语言学概念标注工具 (`streamlit_app.py`)

一个使用大模型（Kimi）辅助标注语言学概念的工具，支持标注如projection、agreement等语言学概念。

### 主要功能
- **概念管理**：管理语言学概念定义、提示词和标注样例
- **智能标注**：使用Kimi大模型对输入文本进行语言学概念标注
- **历史记录**：保存标注历史，支持查看和删除
- **自定义概念**：用户可以添加和编辑自己的语言学概念

### 如何运行
1. 安装依赖
   ```
   $ pip install -r requirements.txt
   ```
2. 运行应用
   ```
   $ streamlit run streamlit_app.py
   ```
3. 在侧边栏输入Kimi API Key（可从 https://platform.moonshot.cn/console/api-keys 获取）

## 2. 💬 聊天机器人 (`chatbot_app.py`)

一个简单的聊天机器人，使用OpenAI的GPT-3.5模型（已修改为支持Kimi模型）。

### 如何运行
```
$ streamlit run chatbot_app.py
```

## 项目结构
```
/workspaces/chatbot/
├── streamlit_app.py          # 语言学概念标注工具（主应用）
├── chatbot_app.py           # 聊天机器人应用
├── concepts.json            # 语言学概念配置文件
├── requirements.txt         # Python依赖包
└── README.md               # 项目说明
```

## 默认语言学概念
项目包含3个默认的语言学概念，每个概念有3个标注样例：
1. **Projection**（句法投射）
2. **Agreement**（一致关系）
3. **Case Marking**（格标记）

## 技术栈
- **前端**: Streamlit
- **大模型**: Kimi API（月之暗面）
- **数据存储**: JSON文件
- **编程语言**: Python 3.11

## 开发说明
- 默认启动的应用是语言学概念标注工具
- 可以通过修改`.devcontainer/devcontainer.json`中的`postAttachCommand`来更改默认启动的应用
- 所有概念数据存储在`concepts.json`文件中，支持实时编辑和保存
