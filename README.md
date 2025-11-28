# 自然语言转 SQL（含验证）

## 项目概览
- 使用 DeepSeek 模型完成供热业务 NL→SQL，并带验证闭环。
- 首次提问会先进入“问题分析”阶段，输出疑点、相关表字段、公式提示，再驱动生成阶段。
- SQL 生成后由验证模型给出置信度与改进建议，若低于阈值自动重试。

## 目录结构
```
├─sql_with_validation.py   # 旧版脚本，保持不变
└─src
   ├─settings.py           # 统一配置
   ├─config_loader.py
   ├─llm_client.py
   ├─prompt_builder.py
   ├─analyzer.py
   ├─workflow.py
   ├─excel_processor.py
   └─main.py               # 入口
```

## 配置
1. 在 `config/` 下放置 `table_descriptions.json`、`formula_descriptions.json`、`common_expressions.json`。
2. 默认训练文件：`算法训练集（75道问题及sql语句）.xlsx`。
3. 所有运行参数集中在 `src/settings.py`：
   - 环境变量覆盖：`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`、`GENERATION_TEMPERATURE`、`CONFIDENCE_THRESHOLD` 等。
   - Excel 处理参数：`EXCEL_INPUT_FILE`、`EXCEL_START_ROW`、`EXCEL_NUM_QUESTIONS` 等。

## 运行
```
cd D:\allwork\AAAproject\AI\validation
python -m src.main
```
执行后：
- 按设置读取 Excel（默认 `复赛-算法打榜评测结果集上传文档.xlsx` 第 2 行起 25 条问题）。
- 生成 SQL 写回 `_with_sql.xlsx`，并输出 `_validation_details.json` 供复盘。

## 主要模块职责
- `settings.AppSettings`：集中管理 LLM、工作流、Excel 参数。
- `llm_client.LLMClient`：封装 Chat API&重试。
- `prompt_builder.PromptBuilder`：统一系统/分析/生成/验证提示词。
- `analyzer.QuestionAnalyzer`：首次问题分析，结果缓存复用。
- `workflow.SQLGenerationWorkflow`：串联分析→生成→验证→重试。
- `excel_processor.ExcelProcessor`：批量读取/写入 Excel，汇总统计。

## 提示
- 若需单题调试，可仿照旧脚本调用 `workflow.generate_sql_with_validation(question)`。
- 配置更��后可直接重新运行入口文件，无需修改其他模块。

处理一个问题：
1. analyzer.analyze 之后的生成都有这个分析
2. _generate_sql <- 系统提示词:prompt_builder.build_system_prompt, 用户提示词:prompt_builder.build_generation_prompt
3. _validate_sql <- 系统提示词:prompt_builder.build_validation_prompt
4. 如果置信度低于阈值：
   1. _generate_sql <- 系统提示词不变，用户提示词：prompt_builder.build_retry_prompt
   2. _validate_sql <- 系统提示词:prompt_builder.build_validation_prompt
5. 返回最终 SQL 及验证结果