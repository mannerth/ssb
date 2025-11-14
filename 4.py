import os
import json


def setup_config():
    """初始化配置文件"""
    config_dir = "config"

    # 创建配置目录
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
        print(f"✅ 创建配置目录: {config_dir}")
if __name__ == "__main__":
            setup_config()