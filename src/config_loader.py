import json
import logging
import os
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)


def _load_json(config_dir: str, filename: str, default: Any):
    filepath = os.path.join(config_dir, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as fp:
            return json.load(fp)
    except FileNotFoundError:
        logger.error("配置文件未找到: %s", filepath)
    except Exception as exc:
        logger.error("读取配置文件失败(%s): %s", filepath, exc)
    return default


def load_introduction_text(config_dir: str) -> str:
    """加载简介"""
    filepath = os.path.join(config_dir, "introduction.txt")
    try:
        with open(filepath, "r", encoding="utf-8") as fp:
            return fp.read()
    except FileNotFoundError:
        logger.warning("简介文件未找到: %s", filepath)
        return "系统简介文件 (introduction.txt) 未找到。"
    except Exception as exc:
        logger.error("读取简介文件失败(%s): %s", filepath, exc)
        return f"读取简介文件失败: {exc}"


def load_formula_descriptions(config_dir: str) -> Dict[str, str]:
    return _load_json(config_dir, "formula_descriptions.json", {})


def load_common_expressions(config_dir: str) -> List[str]:
    return _load_json(config_dir, "common_expressions.json", [])


def load_table_descriptions(config_dir: str) -> List[Dict[str, str]]:
    return _load_json(config_dir, "table_descriptions.json", [])


def load_few_shot_examples(training_file_path: str, num_examples: int = 75) -> List[Dict[str, str]]:
    if not os.path.exists(training_file_path):
        logger.warning("few-shot 训练文件不存在: %s", training_file_path)
        return []
    try:
        df = pd.read_excel(training_file_path)
        df = df.dropna(subset=["题目", "生成的sql"])
        df = df[df["生成的sql"].str.strip().astype(bool)]
        patterns = [
            (r"SELECT.*FROM.*WHERE.*LIKE", 2),
            (r"SELECT.*FROM.*WHERE.*\b(AND|OR)\b.*\b(AND|OR)\b", 2),
            (r"AVG|MAX|MIN|SUM", 2),
            (r"GROUP BY", 2),
            (r"JOIN", 2),
            (r"ORDER BY", 2),
            (r"LIMIT", 1),
            (r"子查询|\(SELECT", 2),
        ]
        used = set()
        examples: List[Dict[str, str]] = []
        for pattern, count in patterns:
            matches = df[~df.index.isin(used) & df["生成的sql"].str.contains(pattern, regex=True, na=False)]
            selected = matches if len(matches) <= count else matches.head(count)
            for idx, row in selected.iterrows():
                examples.append({"question": row["题目"], "sql": row["生成的sql"]})
                used.add(idx)
        if len(examples) < num_examples:
            remaining = df[~df.index.isin(used)]
            additional = remaining if len(remaining) <= num_examples - len(examples) else remaining.sample(
                n=num_examples - len(examples)
            )
            for idx, row in additional.iterrows():
                examples.append({"question": row["题目"], "sql": row["生成的sql"]})
        return examples[:num_examples]
    except Exception as exc:
        logger.error("加载 few-shot 示例失败: %s", exc)
        return []
