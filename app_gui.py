import logging
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import (
    ttk,
    filedialog,
    messagebox,
    scrolledtext,
)
from typing import Callable

# 确保能从 src 目录导入模块
import sys

from openpyxl.reader.excel import load_workbook

project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.analyzer import QuestionAnalyzer
from src.config_loader import (
    load_common_expressions,
    load_formula_descriptions,
    load_few_shot_examples,
    load_table_descriptions,
    load_introduction_text,
)
from src.excel_processor import ExcelProcessor
from src.llm_client import LLMClient
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
from src.logger_manager import setup_logging, get_app_logger


class AppGui:
    def __init__(self, root):
        self.root = root
        self.root.title("自然语言转SQL工具")
        self.root.geometry("1200x800")

        self.settings = load_settings()
        self.introduction_text = load_introduction_text(self.settings.config_dir)
        self.vars = {}
        self.worker_thread = None
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()

        # --- Main Layout ---
        main_paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        settings_frame = ttk.LabelFrame(main_paned_window, text="配置")
        main_paned_window.add(settings_frame, weight=1)

        right_pane = ttk.PanedWindow(main_paned_window, orient=tk.VERTICAL)
        main_paned_window.add(right_pane, weight=3)

        # --- Right Pane: Input and Output ---
        input_output_frame = ttk.Frame(right_pane)
        right_pane.add(input_output_frame, weight=2)

        log_frame = ttk.LabelFrame(right_pane, text="日志和输出")
        right_pane.add(log_frame, weight=1)

        # --- Settings Frame Content ---
        self.create_settings_widgets(settings_frame)

        # --- Input/Output Frame Content ---
        self.create_input_output_widgets(input_output_frame)

        # --- Log Frame Content ---
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Status and Progress Bar ---
        status_frame = ttk.Frame(root)
        status_frame.pack(fill=tk.X, padx=10, pady=(5, 0))
        self.status_label = ttk.Label(status_frame, text="状态: 空闲")
        self.status_label.pack(side=tk.LEFT)

        # --- Progress Bar ---
        self.progress_bar = ttk.Progressbar(root, orient='horizontal', mode='determinate')
        self.progress_bar.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Start queue listener
        self.root.after(100, self.process_log_queue)

    def create_settings_widgets(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # LLM, Workflow, Excel, Paths tabs
        self.create_llm_settings_tab(notebook)
        self.create_workflow_settings_tab(notebook)
        self.create_excel_settings_tab(notebook)
        self.create_path_settings_tab(notebook)

    def _create_setting_entry(self, parent, text, var_name, value):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(frame, text=text, width=25).pack(side=tk.LEFT)
        var = tk.StringVar(value=str(value))
        self.vars[var_name] = var
        ttk.Entry(frame, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def create_llm_settings_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="LLM")
        self._create_setting_entry(tab, "API Key", "llm.api_key", self.settings.llm.api_key)
        self._create_setting_entry(tab, "Base URL", "llm.base_url", self.settings.llm.base_url)
        self._create_setting_entry(tab, "Model", "llm.model", self.settings.llm.model)
        self._create_setting_entry(tab, "Temperature", "llm.temperature", self.settings.llm.temperature)
        self._create_setting_entry(tab, "Max Tokens", "llm.max_tokens", self.settings.llm.max_tokens)
        self._create_setting_entry(tab, "Max Retries", "llm.max_retries", self.settings.llm.max_retries)

    def create_workflow_settings_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="工作流")
        self._create_setting_entry(tab, "通过置信度", "workflow.confidence_threshold", self.settings.workflow.confidence_threshold)
        self._create_setting_entry(tab, "最大重试轮数", "workflow.max_retry_rounds", self.settings.workflow.max_retry_rounds)
        self._create_setting_entry(tab, "验证Temperature", "workflow.validation_temperature", self.settings.workflow.validation_temperature)
        self._create_setting_entry(tab, "验证Max Tokens", "workflow.validation_max_tokens", self.settings.workflow.validation_max_tokens)
        self._create_setting_entry(tab, "置信度重复次数", "workflow.confidence_repeat_count", self.settings.workflow.confidence_repeat_count)
        self._create_setting_entry(tab, "置信度容差", "workflow.confidence_variation_threshold", self.settings.workflow.confidence_variation_threshold)

    def create_excel_settings_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Excel")
        self._create_setting_entry(tab, "开始行", "excel.start_row", self.settings.excel.start_row)
        self._create_setting_entry(tab, "问题列", "excel.start_col", self.settings.excel.start_col)
        self._create_setting_entry(tab, "输出列", "excel.output_col", self.settings.excel.output_col)
        self._create_setting_entry(tab, "问题数量", "excel.num_questions", self.settings.excel.num_questions)
        self._create_setting_entry(tab, "Sheet名称", "excel.sheet_name", self.settings.excel.sheet_name)

    def create_path_settings_tab(self, notebook):
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="路径")
        self._create_setting_entry(tab, "配置文件目录", "config_dir", self.settings.config_dir)
        self._create_setting_entry(tab, "训练文件", "training_file_path", self.settings.training_file_path)
        self._create_setting_entry(tab, "日志目录", "logging.log_dir", self.settings.logging.log_dir)
        self._create_setting_entry(tab, "日志名称", "logging.log_name", self.settings.logging.log_name)
        self._create_setting_entry(tab, "日志级别", "logging.level_str", logging.getLevelName(self.settings.logging.level))

    def create_input_output_widgets(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        # Single Question Tab
        single_tab = ttk.Frame(notebook)
        notebook.add(single_tab, text="单个问题")
        ttk.Label(single_tab, text="在此输入您的问题:").pack(anchor='w', padx=5, pady=5)
        self.single_question_text = scrolledtext.ScrolledText(single_tab, height=5, wrap=tk.WORD)
        self.single_question_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Batch Processing Tab
        batch_tab = ttk.Frame(notebook)
        notebook.add(batch_tab, text="批量处理")
        file_frame = ttk.Frame(batch_tab)
        file_frame.pack(fill=tk.X, padx=5, pady=10)
        self.file_path_var = tk.StringVar(value=self.settings.excel.file_path)
        ttk.Label(file_frame, text="Excel文件:").pack(side=tk.LEFT)
        ttk.Entry(file_frame, textvariable=self.file_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(file_frame, text="选择文件", command=self.select_file).pack(side=tk.LEFT, padx=(5, 0))

        # Action Buttons
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=10)
        self.start_button = ttk.Button(action_frame, text="开始处理", command=self.start_processing)
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(action_frame, text="停止", command=self.stop_processing, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)

        info_button = ttk.Button(action_frame, text="系统简介", command=self.show_introduction)
        info_button.pack(side=tk.LEFT, padx=5)

        self.mode_var = tk.StringVar(value="single")
        ttk.Radiobutton(action_frame, text="处理单个问题", variable=self.mode_var, value="single").pack(side=tk.RIGHT, padx=5)
        ttk.Radiobutton(action_frame, text="处理文件", variable=self.mode_var, value="batch").pack(side=tk.RIGHT, padx=5)

        # Result Display Area
        result_frame = ttk.LabelFrame(parent, text="最终结果")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(10, 5))
        self.result_text = scrolledtext.ScrolledText(result_frame, height=8, wrap=tk.WORD, state='disabled')
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=(("Excel files", "*.xlsx"), ("All files", "*.*")),
            initialdir=os.getcwd()
        )
        if file_path:
            self.file_path_var.set(file_path)

    def show_introduction(self):
        """显示系统简介信息框"""
        messagebox.showinfo("系统简介", self.introduction_text)

    def log(self, message, level=logging.INFO):
        self.log_queue.put((message, level))

    def process_log_queue(self):
        while not self.log_queue.empty():
            message, level = self.log_queue.get()
            self.log_text.configure(state='normal')
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.configure(state='disabled')
            self.log_text.see(tk.END)
            # Also log to file
            get_app_logger().log(level, message)
        self.root.after(100, self.process_log_queue)

    def update_status(self, text: str):
        """Thread-safe method to update the status label."""
        self.root.after(0, lambda: self.status_label.config(text=f"状态: {text}"))

    def update_result_text(self, text: str):
        """Thread-safe method to update the result text widget."""
        self.result_text.configure(state='normal')
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, text)
        self.result_text.configure(state='disabled')

    def get_current_settings(self) -> AppSettings:
        # Helper to safely convert var to int/float
        def _to_int(val, default):
            try: return int(val)
            except (ValueError, TypeError): return default
        def _to_float(val, default):
            try: return float(val)
            except (ValueError, TypeError): return default

        llm_cfg = LLMConfig(
            api_key=self.vars["llm.api_key"].get(),
            base_url=self.vars["llm.base_url"].get(),
            model=self.vars["llm.model"].get(),
            temperature=_to_float(self.vars["llm.temperature"].get(), 0.1),
            max_tokens=_to_int(self.vars["llm.max_tokens"].get(), 3000),
            max_retries=_to_int(self.vars["llm.max_retries"].get(), 5),
        )
        workflow_cfg = WorkflowConfig(
            confidence_threshold=_to_int(self.vars["workflow.confidence_threshold"].get(), 90),
            max_retry_rounds=_to_int(self.vars["workflow.max_retry_rounds"].get(), 20),
            validation_temperature=_to_float(self.vars["workflow.validation_temperature"].get(), 0.1),
            validation_max_tokens=_to_int(self.vars["workflow.validation_max_tokens"].get(), 4000),
            confidence_repeat_count=_to_int(self.vars["workflow.confidence_repeat_count"].get(), 5),
            confidence_variation_threshold=_to_int(self.vars["workflow.confidence_variation_threshold"].get(), 30),
        )
        excel_cfg = ExcelConfig(
            file_path=self.file_path_var.get(),
            start_row=_to_int(self.vars["excel.start_row"].get(), 2),
            start_col=_to_int(self.vars["excel.start_col"].get(), 2),
            output_col=_to_int(self.vars["excel.output_col"].get(), 3),
            num_questions=_to_int(self.vars["excel.num_questions"].get(), 75),
            sheet_name=self.vars["excel.sheet_name"].get(),
        )
        log_level_str = self.vars["logging.level_str"].get().upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        logging_cfg = LoggingConfig(
            log_dir=self.vars["logging.log_dir"].get(),
            log_name=self.vars["logging.log_name"].get(),
            level=log_level,
        )
        return AppSettings(
            llm=llm_cfg,
            workflow=workflow_cfg,
            excel=excel_cfg,
            config_dir=self.vars["config_dir"].get(),
            training_file_path=self.vars["training_file_path"].get(),
            logging=logging_cfg,
        )

    def start_processing(self):
        self.settings = self.get_current_settings()

        # Setup logging based on GUI settings
        setup_logging(
            log_dir=self.settings.logging.log_dir,
            log_name=self.settings.logging.log_name,
            level=self.settings.logging.level,
        )

        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')

        self.update_result_text("")  # Clear previous result

        self.log("开始处理...")
        self.update_status("准备中...")
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.progress_bar['value'] = 0
        self.stop_event.clear()

        mode = self.mode_var.get()
        if mode == "single":
            question = self.single_question_text.get(1.0, tk.END).strip()
            if not question:
                messagebox.showerror("错误", "请输入问题！")
                self.processing_finished()
                return
            self.worker_thread = threading.Thread(target=self.run_single_question, args=(question, self.settings))
        else: # batch
            file_path = self.file_path_var.get()
            if not file_path or not os.path.exists(file_path):
                messagebox.showerror("错误", "请选择一个有效的Excel文件！")
                self.processing_finished()
                return
            self.worker_thread = threading.Thread(target=self.run_batch_processing, args=(self.settings,))

        self.worker_thread.start()

    def stop_processing(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.log("正在发送停止信号...")
            self.stop_event.set()
            self.stop_button.config(state='disabled')

    def processing_finished(self):
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.progress_bar['value'] = 100
        self.update_status("处理完成" if not self.stop_event.is_set() else "处理中断")
        self.worker_thread = None
        self.stop_event.clear()

    def update_progress(self, current, total):
        if total > 0:
            percentage = (current / total) * 100
            self.progress_bar['value'] = percentage
        self.root.update_idletasks()

    def build_workflow(self, settings: AppSettings) -> SQLGenerationWorkflow:
        # This function is similar to the one in main.py
        # Ensure paths are absolute
        project_root = Path(__file__).parent
        config_dir = settings.config_dir if os.path.isabs(settings.config_dir) else str(project_root / settings.config_dir)
        training_file = settings.training_file_path if os.path.isabs(settings.training_file_path) else str(project_root / settings.training_file_path)

        formula_desc = load_formula_descriptions(config_dir)
        common_expr = load_common_expressions(config_dir)
        table_desc = load_table_descriptions(config_dir)
        few_shot = load_few_shot_examples(training_file)

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
            llm_client,
            prompt_builder,
            analyzer,
            confidence_threshold=settings.workflow.confidence_threshold,
            max_retry_rounds=settings.workflow.max_retry_rounds,
            validation_temperature=settings.workflow.validation_temperature,
            validation_max_tokens=settings.workflow.validation_max_tokens,
            confidence_repeat_count=settings.workflow.confidence_repeat_count,
            confidence_variation_threshold=settings.workflow.confidence_variation_threshold,
            stop_event=self.stop_event,
            status_callback=self.update_status,
        )

    def run_single_question(self, question: str, settings: AppSettings):
        try:
            workflow = self.build_workflow(settings)

            # Hook logger to send messages to GUI
            class GuiLogHandler(logging.Handler):
                def __init__(self, app_instance):
                    super().__init__()
                    self.app_instance = app_instance
                def emit(self, record):
                    self.app_instance.log(self.format(record))

            # Add handler to the logger used by workflow
            workflow_logger = logging.getLogger('src.workflow')
            gui_handler = GuiLogHandler(self)
            # You might want to set a specific format for the GUI log
            formatter = logging.Formatter('%(message)s')
            gui_handler.setFormatter(formatter)
            workflow_logger.addHandler(gui_handler)

            self.progress_bar['maximum'] = settings.workflow.max_retry_rounds
            self.update_progress(0, settings.workflow.max_retry_rounds)
            self.log(f"正在处理问题: {question}")

            # Override status callback to include progress for single question
            original_callback = workflow.status_callback
            def single_question_status_updater(text: str):
                if original_callback:
                    original_callback(text)
                # Update progress bar based on retry round
                import re
                match = re.search(r"\[第(\d+)/(\d+)轮\]", text)
                if match:
                    current_round = int(match.group(1))
                    self.update_progress(current_round, settings.workflow.max_retry_rounds)

            workflow.status_callback = single_question_status_updater

            sql_query = workflow.generate_sql_with_validation(question)
            self.log(f"\n--- 生成的SQL ---\n{sql_query}\n--------------------")
            self.root.after(0, self.update_result_text, sql_query)

            validation_info = workflow.validation_results.get(question, {})
            if validation_info:
                confidence = validation_info.get("validation", {}).get("confidence", 0)
                self.log(f"最终置信度: {confidence}")

            self.log("\n处理完成。")
            self.update_progress(settings.workflow.max_retry_rounds, settings.workflow.max_retry_rounds)

        except Exception as e:
            self.log(f"处理失败: {e}", level=logging.ERROR)
            messagebox.showerror("错误", f"处理过程中发生错误: {e}")
        finally:
            self.root.after(0, self.processing_finished)

    def run_batch_processing(self, settings: AppSettings):
        try:
            workflow = self.build_workflow(settings)

            # Custom ExcelProcessor that reports progress
            class GuiExcelProcessor(ExcelProcessor):
                def __init__(self, wf, app_gui):
                    super().__init__(wf)
                    self.app_gui = app_gui

                def process(self, *args, **kwargs):
                    # Override to add progress reporting
                    self.app_gui.log("开始批量处理Excel文件...")

                    # This is a simplified version of the original process method
                    # to integrate progress updates and stop signals.
                    file_path = kwargs.get('file_path')
                    num_questions = kwargs.get('num_questions')

                    workbook = load_workbook(file_path)
                    sheet_name = kwargs.get('sheet_name')
                    worksheet = workbook[sheet_name] if sheet_name else workbook.active

                    processed_count = 0
                    for idx in range(num_questions):
                        if self.app_gui.stop_event.is_set():
                            self.app_gui.log("处理被用户中断。")
                            break

                        row_num = kwargs.get('start_row', 2) + idx
                        question_cell = worksheet.cell(row=row_num, column=kwargs.get('start_col', 2))
                        question = (question_cell.value or "").strip()

                        if not question:
                            continue

                        self.app_gui.log(f"处理第 {idx + 1}/{num_questions} 个问题: {question}")
                        try:
                            sql = self.workflow.generate_sql_with_validation(question)
                            self.app_gui.root.after(0, self.app_gui.update_result_text, sql)
                            worksheet.cell(row=row_num, column=kwargs.get('output_col', 3)).value = sql
                            processed_count += 1
                        except Exception as e:
                            error_msg = f"问题 '{question}' 处理失败: {e}"
                            self.app_gui.log(error_msg, level=logging.ERROR)
                            worksheet.cell(row=row_num, column=kwargs.get('output_col', 3)).value = f"ERROR: {e}"

                        self.app_gui.update_progress(idx + 1, num_questions)

                    output_file = file_path.replace(".xlsx", "_with_sql.xlsx")
                    workbook.save(output_file)
                    self.workflow.save_validation_details(output_file.replace(".xlsx", "_validation_details.json"))

                    self.app_gui.log(f"\n批量处理完成。共处理 {processed_count} 个问题。")
                    self.app_gui.log(f"结果已保存到: {output_file}")
                    return {"output_file": output_file, "processed_count": processed_count}

            processor = GuiExcelProcessor(workflow, self)
            processor.process(
                file_path=settings.excel.file_path,
                start_row=settings.excel.start_row,
                start_col=settings.excel.start_col,
                output_col=settings.excel.output_col,
                num_questions=settings.excel.num_questions,
                sheet_name=settings.excel.sheet_name,
            )

        except Exception as e:
            self.log(f"批量处理失败: {e}", level=logging.ERROR)
            messagebox.showerror("错误", f"批量处理过程中发生错误: {e}")
        finally:
            self.root.after(0, self.processing_finished)


if __name__ == "__main__":
    app_root = tk.Tk()
    gui = AppGui(app_root)
    app_root.mainloop()
