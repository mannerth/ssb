import logging
from typing import Dict, Optional

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from .workflow import SQLGenerationWorkflow


class ExcelProcessor:
    def __init__(self, workflow: SQLGenerationWorkflow):
        self.workflow = workflow
        self.logger = logging.getLogger(__name__)

    def process(
        self,
        file_path: str,
        start_row: int,
        start_col: int,
        output_col: int,
        num_questions: int,
        sheet_name: Optional[str] = None,
    ) -> Dict:
        workbook = load_workbook(file_path)
        worksheet = workbook[sheet_name] if sheet_name else workbook.active
        stats = {
            "total_questions": 0,
            "passed_validation": 0,
            "average_confidence": 0,
            "max_rounds_used": 0,
        }
        processed = 0
        errors = []
        for idx in range(num_questions):
            row = start_row + idx
            question_cell = worksheet.cell(row=row, column=start_col)
            question = (question_cell.value or "").strip()
            if not question:
                self.logger.warning("第%s行问题为空，跳过", row)
                continue
            self.logger.info("处理第%s行问题: %s", row, question)
            try:
                sql_query = self.workflow.generate_sql_with_validation(question)
                validation_info = self.workflow.validation_results.get(question, {})
                worksheet.cell(row=row, column=output_col).value = sql_query
                stats["total_questions"] += 1
                confidence = validation_info.get("validation", {}).get("confidence", 0)
                stats["average_confidence"] += confidence
                if validation_info.get("validation", {}).get("passed"):
                    stats["passed_validation"] += 1
                stats["max_rounds_used"] = max(stats["max_rounds_used"], validation_info.get("round", 1))
                processed += 1
            except Exception as exc:
                error_msg = f"第{row}行处理失败: {exc}"
                errors.append(error_msg)
                worksheet.cell(row=row, column=output_col).value = f"ERROR: {exc}"
                self.logger.error(error_msg)
        if stats["total_questions"]:
            stats["average_confidence"] /= stats["total_questions"]
        output_file = file_path.replace(".xlsx", "_with_sql.xlsx")
        workbook.save(output_file)
        self.workflow.save_validation_details(output_file.replace(".xlsx", "_validation_details.json"))
        return {
            "processed_count": processed,
            "total_questions": num_questions,
            "output_file": output_file,
            "validation_stats": stats,
            "errors": errors,
        }

