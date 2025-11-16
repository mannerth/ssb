"""
配置参数
"""


# DeepSeek API Key
# API_KEY: str = "sk-ccaa87bceda64383a44a36bd0c60c32b"
#DEEPSEEK_MODEL: str = "deepseek-chat"
#DEEPSEEK_BASE_URL : str = "https://api.deepseek.com/v1"

# 平台api key
DEEPSEEK_MODEL: str = "DeepSeek-V3"
API_KEY:str = "82dbf778c5834eecad2bb21c1df632f9"
DEEPSEEK_BASE_URL:str = "https://www.ssfssp.com:8888/ssp/openApi/GkfFhhUy/kvshB4Rh/LNslKxsF/v1"

#最大tokens
MAX_TOKENS: int = 2000
#模型温度，越低回答内容越固定，高则回答内容随机性更强
MODEL_TEMPERATURE: float = 0.1

#最大重试轮数
MAX_RETRY : int = 20
#通过置信度
PASS_LINE: int = 70

#训练集文件
training_file_path:str = "算法训练集（75道问题及sql语句）.xlsx"
#日志文件目录
log_file_path: str = "../log"
#数据目录
data_files_path: str = "../config"