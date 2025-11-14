import pandas as pd
import numpy as np
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
import os
import logging


class ExcelColumnComparator:
    def __init__(self):
        # 设置日志
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        # 定义颜色填充
        self.green_fill = PatternFill(start_color="00FF00", end_color="00FF00", fill_type="solid")
        self.red_fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
        self.yellow_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")

    def compare_columns(self, file1_path, file2_path, col_index,
                        sheet1_name=None, sheet2_name=None,
                        start_row=2, output_file=None):
        """
        比较两个Excel文件指定列的数据

        参数:
        - file1_path: 第一个Excel文件路径
        - file2_path: 第二个Excel文件路径
        - col_index: 要比较的列索引（从1开始）
        - sheet1_name: 第一个文件的工作表名称，默认为第一个工作表
        - sheet2_name: 第二个文件的工作表名称，默认为第一个工作表
        - start_row: 开始比较的行号（默认从第2行开始，假设第1行是标题）
        - output_file: 输出结果的文件路径，如果为None则不保存

        返回:
        - 比较结果字典
        """
        try:
            # 读取Excel文件
            self.logger.info(f"读取文件1: {file1_path}")
            if sheet1_name:
                df1 = pd.read_excel(file1_path, sheet_name=sheet1_name, header=None)
            else:
                df1 = pd.read_excel(file1_path, header=None)

            self.logger.info(f"读取文件2: {file2_path}")
            if sheet2_name:
                df2 = pd.read_excel(file2_path, sheet_name=sheet2_name, header=None)
            else:
                df2 = pd.read_excel(file2_path, header=None)

            # 确保列索引有效
            if col_index > df1.shape[1] or col_index > df2.shape[1]:
                raise ValueError(f"列索引 {col_index} 超出文件列数范围")

            # 获取要比较的列数据（从start_row开始）
            col1_data = df1.iloc[start_row - 1:, col_index - 1].reset_index(drop=True)
            col2_data = df2.iloc[start_row - 1:, col_index - 1].reset_index(drop=True)

            # 确定比较的行数（取两个文件中较小的行数）
            min_rows = min(len(col1_data), len(col2_data))
            col1_data = col1_data.head(min_rows)
            col2_data = col2_data.head(min_rows)

            self.logger.info(f"开始比较，共 {min_rows} 行数据")

            # 进行比较
            comparison_results = []
            match_count = 0
            total_comparable = 0

            for i in range(min_rows):
                val1 = col1_data.iloc[i]
                val2 = col2_data.iloc[i]

                # 处理NaN值
                if pd.isna(val1) and pd.isna(val2):
                    is_match = True
                    match_status = "双空值"
                elif pd.isna(val1) or pd.isna(val2):
                    is_match = False
                    match_status = "单空值"
                else:
                    # 转换为字符串进行比较
                    str_val1 = str(val1).strip()
                    str_val2 = str(val2).strip()
                    is_match = (str_val1 == str_val2)
                    match_status = "匹配" if is_match else "不匹配"

                if is_match:
                    match_count += 1

                # 只统计非双空值的行
                if not (pd.isna(val1) and pd.isna(val2)):
                    total_comparable += 1

                comparison_results.append({
                    'row': start_row + i,
                    'value1': val1 if not pd.isna(val1) else "空值",
                    'value2': val2 if not pd.isna(val2) else "空值",
                    'match': is_match,
                    'status': match_status
                })

            # 计算相同率
            if total_comparable > 0:
                similarity_rate = (match_count / total_comparable) * 100
            else:
                similarity_rate = 0

            # 准备结果
            result = {
                'total_rows': min_rows,
                'total_comparable': total_comparable,
                'match_count': match_count,
                'similarity_rate': similarity_rate,
                'comparison_results': comparison_results,
                'file1': file1_path,
                'file2': file2_path,
                'column': col_index
            }

            self.logger.info(
                f"比较完成: 总行数 {min_rows}, 可比较行数 {total_comparable}, 匹配行数 {match_count}, 相同率 {similarity_rate:.2f}%")

            # 如果指定了输出文件，保存详细结果
            if output_file:
                self.save_comparison_result(result, output_file)

            return result

        except Exception as e:
            self.logger.error(f"比较过程中发生错误: {e}")
            raise

    def save_comparison_result(self, result, output_file):
        """保存比较结果到Excel文件"""
        try:
            # 创建DataFrame保存详细结果
            comparison_df = pd.DataFrame(result['comparison_results'])

            # 创建新的Excel文件
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # 保存详细比较结果
                comparison_df.to_excel(writer, sheet_name='详细比较结果', index=False)

                # 创建汇总表
                summary_data = {
                    '指标': ['文件1', '文件2', '比较列', '总行数', '可比较行数', '匹配行数', '相同率'],
                    '值': [
                        result['file1'],
                        result['file2'],
                        f"第{result['column']}列",
                        result['total_rows'],
                        result['total_comparable'],
                        result['match_count'],
                        f"{result['similarity_rate']:.2f}%"
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='汇总', index=False)

            self.logger.info(f"比较结果已保存到: {output_file}")

            # 使用openpyxl添加颜色标记
            workbook = load_workbook(output_file)
            sheet = workbook['详细比较结果']

            # 添加颜色标记
            for row in range(2, len(result['comparison_results']) + 2):  # 从第2行开始（跳过标题）
                match_cell = sheet[f'D{row}']  # D列是match列
                status_cell = sheet[f'E{row}']  # E列是status列

                if match_cell.value == True:
                    match_cell.fill = self.green_fill
                    status_cell.fill = self.green_fill
                elif status_cell.value == "单空值":
                    match_cell.fill = self.yellow_fill
                    status_cell.fill = self.yellow_fill
                else:
                    match_cell.fill = self.red_fill
                    status_cell.fill = self.red_fill

            # 调整列宽
            for column in sheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                sheet.column_dimensions[column_letter].width = adjusted_width

            workbook.save(output_file)
            self.logger.info(f"已添加颜色标记到: {output_file}")

        except Exception as e:
            self.logger.error(f"保存比较结果时发生错误: {e}")
            raise

    def compare_multiple_columns(self, file1_path, file2_path, col_indices,
                                 sheet1_name=None, sheet2_name=None,
                                 start_row=2, output_file=None):
        """
        比较多个列

        参数:
        - col_indices: 列索引列表，如 [1, 2, 3]
        """
        all_results = {}

        for col_index in col_indices:
            self.logger.info(f"开始比较第 {col_index} 列")
            result = self.compare_columns(
                file1_path, file2_path, col_index,
                sheet1_name, sheet2_name, start_row
            )
            all_results[f'第{col_index}列'] = result

        # 计算总体相同率
        total_match = sum(result['match_count'] for result in all_results.values())
        total_comparable = sum(result['total_comparable'] for result in all_results.values())

        if total_comparable > 0:
            overall_similarity = (total_match / total_comparable) * 100
        else:
            overall_similarity = 0

        overall_result = {
            'overall_similarity': overall_similarity,
            'total_columns': len(col_indices),
            'total_match': total_match,
            'total_comparable': total_comparable,
            'column_results': all_results
        }

        # 如果指定了输出文件，保存多列比较结果
        if output_file:
            self.save_multiple_comparison_result(overall_result, output_file)

        return overall_result

    def save_multiple_comparison_result(self, result, output_file):
        """保存多列比较结果"""
        try:
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # 创建列比较汇总表
                summary_data = []
                for col_name, col_result in result['column_results'].items():
                    summary_data.append({
                        '列': col_name,
                        '总行数': col_result['total_rows'],
                        '可比较行数': col_result['total_comparable'],
                        '匹配行数': col_result['match_count'],
                        '相同率': f"{col_result['similarity_rate']:.2f}%"
                    })

                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='列比较汇总', index=False)

                # 添加总体汇总
                overall_df = pd.DataFrame({
                    '指标': ['总体相同率', '比较列数', '总匹配行数', '总可比较行数'],
                    '值': [
                        f"{result['overall_similarity']:.2f}%",
                        result['total_columns'],
                        result['total_match'],
                        result['total_comparable']
                    ]
                })
                overall_df.to_excel(writer, sheet_name='总体汇总', index=False)

            self.logger.info(f"多列比较结果已保存到: {output_file}")

        except Exception as e:
            self.logger.error(f"保存多列比较结果时发生错误: {e}")
            raise


# 使用示例
def main():
    comparator = ExcelColumnComparator()

    # 文件路径
    file1 = "question.xlsx"  # 第一个文件
    file2 = "算法训练集（75道问题及sql语句）.xlsx"  # 第二个文件（标准答案）

    # 比较参数
    col_to_compare = 3  # 要比较的列索引（从1开始）
    start_from_row = 2  # 从第几行开始比较
    output_result = "comparison_result.xlsx"  # 输出结果文件

    # 执行比较
    result = comparator.compare_columns(
        file1_path=file1,
        file2_path=file2,
        col_index=col_to_compare,
        start_row=start_from_row,
        output_file=output_result
    )

    # 打印结果
    print("\n=== 比较结果 ===")
    print(f"文件1: {result['file1']}")
    print(f"文件2: {result['file2']}")
    print(f"比较列: 第{result['column']}列")
    print(f"总行数: {result['total_rows']}")
    print(f"可比较行数: {result['total_comparable']}")
    print(f"匹配行数: {result['match_count']}")
    print(f"相同率: {result['similarity_rate']:.2f}%")

    # 显示前几行不匹配的示例
    print("\n=== 不匹配示例 ===")
    mismatch_count = 0
    for comp in result['comparison_results']:
        if not comp['match'] and mismatch_count < 5:  # 显示前5个不匹配
            print(f"行 {comp['row']}: '{comp['value1']}' vs '{comp['value2']}' - {comp['status']}")
            mismatch_count += 1


def compare_multiple_columns_example():
    """比较多个列的示例"""
    comparator = ExcelColumnComparator()

    file1 = "question_with_sql.xlsx"
    file2 = "ground_truth.xlsx"

    # 要比较的多个列
    columns_to_compare = [2, 3, 4]  # 第2、3、4列

    result = comparator.compare_multiple_columns(
        file1_path=file1,
        file2_path=file2,
        col_indices=columns_to_compare,
        start_row=2,
        output_file="multiple_columns_comparison.xlsx"
    )

    print("\n=== 多列比较结果 ===")
    print(f"总体相同率: {result['overall_similarity']:.2f}%")
    print(f"比较列数: {result['total_columns']}")
    print(f"总匹配行数: {result['total_match']}")
    print(f"总可比较行数: {result['total_comparable']}")

    for col_name, col_result in result['column_results'].items():
        print(f"\n{col_name}:")
        print(f"  相同率: {col_result['similarity_rate']:.2f}%")


if __name__ == "__main__":
    # 单列比较
    main()

    # 多列比较（取消注释以使用）
    # compare_multiple_columns_example()