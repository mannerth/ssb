# 自然语言转 SQL 工具 (NL2SQL Tool)

这是一个基于大语言模型 (DeepSeek-V3) 的自然语言转 SQL (NL2SQL) 工具。它能够将自然语言问题转换为 SQL 查询语句，并具备自我验证和修正功能，以提高生成的准确性。

## ✨ 主要功能

*   **智能转换**: 利用 DeepSeek-V3 模型将自然语言问题解析并转换为 SQL 语句。
*   **自我验证与修正**: 内置验证工作流，模型会对生成的 SQL 进行置信度评估。如果置信度低于阈值，会自动进行多轮自我修正。
*   **双模式支持**:
    *   **单条模式**: 在 Web 界面直接输入单个问题进行转换。
    *   **批量模式**: 上传包含多个问题的 Excel 文件，批量生成 SQL。
*   **Web 可视化界面**: 提供现代化的 Web 界面，支持实时日志显示、结果预览和文件下载。
*   **高度可配置**: 支持自定义表结构描述、公式描述和常用表达，以适应不同的业务场景。

## 🚀 快速开始

### 1. 环境要求

*   Python 3.8+
*   DeepSeek API Key

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置

在运行之前，请确保配置了必要的环境变量或修改 `src/settings.py` 中的默认设置。主要需要配置 DeepSeek 的 API Key 和 Base URL。

项目依赖 `config/` 目录下的配置文件来构建 Prompt：
*   `table_descriptions.json`: 数据库表结构描述。
*   `formula_descriptions.json`: 业务公式描述。
*   `common_expressions.json`: 常用术语和表达映射。

### 4. 运行应用

#### 方式一：启动 Web 界面 (推荐)

```bash
python src/app_gui.py
```
启动后，访问浏览器 `http://127.0.0.1:8000` 即可使用。

#### 方式二：命令行运行 (批量处理)

修改 `src/settings.py` 或通过环境变量指定 Excel 文件路径，然后运行：

```bash
python src/main.py
```

#### 方式三：Docker 部署

```bash
docker-compose up -d
```

## 📂 项目结构

```
.
├── config/                 # 配置文件目录 (Prompt 上下文)
│   ├── common_expressions.json
│   ├── formula_descriptions.json
│   ├── table_descriptions.json
│   └── introduction.txt
├── data/                   # 数据目录 (输入/输出 Excel)
├── logs/                   # 日志目录
├── src/                    # 源代码
│   ├── web/                # Web 前端资源
│   │   └── templates/
│   │       └── index.html
│   ├── analyzer.py         # 问题分析模块
│   ├── app_gui.py          # Web 应用入口 (FastAPI)
│   ├── config_loader.py    # 配置加载器
│   ├── excel_processor.py  # Excel 处理模块
│   ├── llm_client.py       # LLM 客户端
│   ├── main.py             # 命令行入口
│   ├── prompt_builder.py   # Prompt 构建器
│   ├── settings.py         # 全局设置
│   └── workflow.py         # 核心工作流 (生成+验证)
├── docker-compose.yml      # Docker 编排文件
├── Dockerfile              # Docker 构建文件
├── requirements.txt        # Python 依赖
└── README.md               # 项目说明文档
```

## 🛠️ 使用说明

### Web 界面使用

1.  **单条模式**:
    *   选择 "单条模式"。
    *   在输入框中输入您的自然语言问题。
    *   点击 "开始处理"。
    *   右侧将显示生成的 SQL、置信度以及验证分析。

2.  **批量模式**:
    *   选择 "批量模式"。
    *   点击上传 Excel 文件 (需包含问题列)。
    *   配置 Excel 读取设置 (如起始行、问题列号等)。
    *   点击 "开始处理"。
    *   系统将逐行处理，并在完成后提供结果文件下载。

### 核心参数说明

*   **置信度阈值 (Confidence Threshold)**: 只有当模型自评置信度高于此值时，才认为 SQL 可用 (默认 75)。
*   **最大重试轮数 (Max Retry Rounds)**: 如果置信度不足，最大尝试修正的次数 (默认 10)。
*   **Temperature**: 控制生成的随机性，验证阶段通常设置较低以获得稳定评估。

## 📝 注意事项

*   生成的 SQL 仅包含 `SELECT` 查询，系统会拦截 `INSERT`, `UPDATE`, `DELETE` 等危险操作。
*   批量处理时，结果文件会保存在 `data/web_sessions/` 目录下，并包含详细的验证日志 JSON 文件。
