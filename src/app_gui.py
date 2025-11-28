import asyncio
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from src.analyzer import QuestionAnalyzer
from src.config_loader import (
    load_common_expressions,
    load_formula_descriptions,
    load_few_shot_examples,
    load_introduction_text,
    load_table_descriptions,
)
from src.excel_processor import ExcelProcessor
from src.llm_client import LLMClient
from src.logger_manager import get_app_logger, setup_logging
from src.prompt_builder import PromptBuilder
from src.settings import (
    AppSettings,
    ExcelConfig,
    LLMConfig,
    LoggingConfig,
    WorkflowConfig,
    load_settings,
)
from src.workflow import SQLGenerationWorkflow

ROOT_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT_DIR / "src" / "web" / "templates"
SESSION_DIR = ROOT_DIR / "data" / "web_sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="自然语言转 SQL 工具")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


class _InMemoryLogHandler(logging.Handler):
    def __init__(self, sink: List[str]):
        super().__init__()
        self.sink = sink

    def emit(self, record: logging.LogRecord):
        self.sink.append(self.format(record))


class WebRunContext:
    def __init__(self):
        self.logs: List[str] = []
        self.status_updates: List[str] = []

    def push_status(self, text: str):
        self.status_updates.append(text)

    def log(self, message: str):
        self.logs.append(message)

    def create_log_handler(self) -> logging.Handler:
        handler = _InMemoryLogHandler(self.logs)
        handler.setFormatter(logging.Formatter("%Y-%m-%d %H:%M:%S - %(message)s"))
        handler.setLevel(logging.INFO)
        return handler


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else ROOT_DIR / path


def _build_workflow(settings: AppSettings, context: WebRunContext) -> SQLGenerationWorkflow:
    config_dir = _resolve_path(settings.config_dir)
    training_file = _resolve_path(settings.training_file_path)

    formula_desc = load_formula_descriptions(str(config_dir))
    common_expr = load_common_expressions(str(config_dir))
    table_desc = load_table_descriptions(str(config_dir))
    few_shot = load_few_shot_examples(str(training_file))

    llm_client = LLMClient(
        api_key=settings.llm.api_key,
        base_url=settings.llm.base_url,
        model=settings.llm.model,
        max_retries=settings.llm.max_retries,
        default_temperature=settings.llm.temperature,
        default_max_tokens=settings.llm.max_tokens,
    )
    prompt_builder = PromptBuilder(table_desc, formula_desc, common_expr, few_shot)
    analyzer = QuestionAnalyzer(llm_client, prompt_builder)

    return SQLGenerationWorkflow(
        llm_client=llm_client,
        prompt_builder=prompt_builder,
        analyzer=analyzer,
        confidence_threshold=settings.workflow.confidence_threshold,
        max_retry_rounds=settings.workflow.max_retry_rounds,
        validation_temperature=settings.workflow.validation_temperature,
        validation_max_tokens=settings.workflow.validation_max_tokens,
        confidence_repeat_count=settings.workflow.confidence_repeat_count,
        confidence_variation_threshold=settings.workflow.confidence_variation_threshold,
        stop_event=threading.Event(),
        status_callback=context.push_status,
    )


def _int_val(value: Optional[str], default: int) -> int:
    try:
        return int(float(value)) if value not in (None, "") else default
    except ValueError:
        return default


def _float_val(value: Optional[str], default: float) -> float:
    try:
        return float(value) if value not in (None, "") else default
    except ValueError:
        return default


def _build_settings_from_form(form: Dict[str, Any], base: AppSettings) -> AppSettings:
    llm = LLMConfig(
        api_key=form.get("llm.api_key", base.llm.api_key),
        base_url=form.get("llm.base_url", base.llm.base_url),
        model=form.get("llm.model", base.llm.model),
        temperature=_float_val(form.get("llm.temperature"), base.llm.temperature),
        max_tokens=_int_val(form.get("llm.max_tokens"), base.llm.max_tokens),
        max_retries=_int_val(form.get("llm.max_retries"), base.llm.max_retries),
    )
    workflow = WorkflowConfig(
        confidence_threshold=_int_val(form.get("workflow.confidence_threshold"), base.workflow.confidence_threshold),
        max_retry_rounds=_int_val(form.get("workflow.max_retry_rounds"), base.workflow.max_retry_rounds),
        validation_temperature=_float_val(form.get("workflow.validation_temperature"), base.workflow.validation_temperature),
        validation_max_tokens=_int_val(form.get("workflow.validation_max_tokens"), base.workflow.validation_max_tokens),
        confidence_repeat_count=_int_val(form.get("workflow.confidence_repeat_count"), base.workflow.confidence_repeat_count),
        confidence_variation_threshold=_int_val(
            form.get("workflow.confidence_variation_threshold"), base.workflow.confidence_variation_threshold
        ),
    )
    excel = ExcelConfig(
        file_path=base.excel.file_path,
        start_row=_int_val(form.get("excel.start_row"), base.excel.start_row),
        start_col=_int_val(form.get("excel.start_col"), base.excel.start_col),
        output_col=_int_val(form.get("excel.output_col"), base.excel.output_col),
        num_questions=_int_val(form.get("excel.num_questions"), base.excel.num_questions),
        sheet_name=form.get("excel.sheet_name", base.excel.sheet_name),
    )
    log_level_raw = form.get("logging.level_str", base.logging.level_str).upper()
    log_level = getattr(logging, log_level_raw, base.logging.level)
    logging_cfg = LoggingConfig(
        log_dir=form.get("logging.log_dir", base.logging.log_dir),
        log_name=form.get("logging.log_name", base.logging.log_name),
        level=log_level,
    )
    return AppSettings(
        llm=llm,
        workflow=workflow,
        excel=excel,
        config_dir=form.get("config_dir", base.config_dir),
        training_file_path=form.get("training_file_path", base.training_file_path),
        logging=logging_cfg,
    )


def _relative_to_session(path: Path) -> str:
    try:
        return str(path.relative_to(SESSION_DIR))
    except ValueError:
        return path.name


def _execute_pipeline(
    mode: str,
    question: str,
    settings: AppSettings,
) -> Dict[str, Any]:
    context = WebRunContext()
    workflow = _build_workflow(settings, context)

    handler = context.create_log_handler()
    root_logger = get_app_logger()
    root_logger.addHandler(handler)

    result_payload: Dict[str, Any] = {}
    try:
        if mode == "single":
            context.log("开始处理单个问题...")
            sql_query = workflow.generate_sql_with_validation(question)
            validation = workflow.validation_results.get(question, {}).get("validation", {})
            result_payload = {
                "mode": "single",
                "question": question,
                "sql": sql_query,
                "confidence": validation.get("confidence"),
                "validation": validation,
            }
        else:
            context.log("开始批量处理 Excel ...")
            processor = ExcelProcessor(workflow)
            summary = processor.process(
                file_path=settings.excel.file_path,
                start_row=settings.excel.start_row,
                start_col=settings.excel.start_col,
                output_col=settings.excel.output_col,
                num_questions=settings.excel.num_questions,
                sheet_name=settings.excel.sheet_name,
            )
            output_path = Path(summary["output_file"])
            validation_path = Path(summary["output_file"].replace(".xlsx", "_validation_details.json"))
            result_payload = {
                "mode": "batch",
                "summary": summary,
                "output_file": _relative_to_session(output_path),
                "validation_file": _relative_to_session(validation_path),
            }
    finally:
        root_logger.removeHandler(handler)

    return {
        "result": result_payload,
        "status": context.status_updates,
        "logs": context.logs,
    }


def _session_subdir() -> Path:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    target = SESSION_DIR / timestamp
    target.mkdir(parents=True, exist_ok=True)
    return target


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    settings = load_settings()
    introduction = load_introduction_text(settings.config_dir)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "settings": settings,
            "mode": "single",
            "question_text": "",
            "result": None,
            "logs": [],
            "status_updates": [],
            "error": None,
            "introduction": introduction,
        },
    )


@app.post("/process", response_class=HTMLResponse)
async def process(request: Request, excel_file: UploadFile | None = File(None)):
    form = await request.form()
    mode = form.get("mode", "single")
    question = (form.get("question") or "").strip()

    base_settings = load_settings()
    settings = _build_settings_from_form(form, base_settings)
    introduction = load_introduction_text(settings.config_dir)

    error: Optional[str] = None
    saved_excel_path: Optional[Path] = None

    if mode == "single" and not question:
        error = "请输入需要转换的问题。"
    if mode == "batch":
        if excel_file is None or not excel_file.filename:
            error = "请上传 Excel 文件。"
        else:
            session_dir = _session_subdir()
            safe_name = Path(excel_file.filename).name or "questions.xlsx"
            saved_excel_path = session_dir / safe_name
            saved_excel_path.write_bytes(await excel_file.read())
            settings.excel.file_path = str(saved_excel_path)

    if error:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "settings": settings,
                "mode": mode,
                "question_text": question,
                "result": None,
                "logs": [],
                "status_updates": [],
                "error": error,
                "introduction": introduction,
            },
            status_code=400,
        )

    setup_logging(settings.logging.log_dir, settings.logging.log_name, settings.logging.level)

    try:
        execution = await asyncio.to_thread(_execute_pipeline, mode, question, settings)
    except Exception as exc:
        get_app_logger().exception("处理失败")
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "settings": settings,
                "mode": mode,
                "question_text": question,
                "result": None,
                "logs": [],
                "status_updates": [],
                "error": f"处理失败: {exc}",
                "introduction": introduction,
            },
            status_code=500,
        )

    context = {
        "request": request,
        "settings": settings,
        "mode": mode,
        "question_text": question,
        "result": execution["result"],
        "logs": execution["logs"],
        "status_updates": execution["status"],
        "error": None,
        "introduction": introduction,
    }
    return templates.TemplateResponse("index.html", context)


@app.get("/download")
async def download(path: str):
    target = (SESSION_DIR / path).resolve()
    if SESSION_DIR not in target.parents and SESSION_DIR != target.parent:
        raise HTTPException(status_code=400, detail="非法路径")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path=target, filename=target.name)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.app_gui:app", host="127.0.0.1", port=int(os.getenv("PORT", 8000)), reload=True)
