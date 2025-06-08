import os
import logging
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal

class LogSignalEmitter(QObject):
    """日志信号发射器，用于将日志消息发送到UI"""
    log_signal = pyqtSignal(str)

def setup_logger():
    """
    配置并初始化日志系统
    
    创建日志目录（如果不存在），设置日志格式和输出文件
    日志文件名格式：logs/translation_YYYYMMDD.log
    
    Returns:
        logging.Logger: 配置好的日志记录器实例
    """
    # 确保日志目录存在
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # 配置日志文件名（使用当前日期）
    log_file = f'logs/translation_{datetime.now().strftime("%Y%m%d")}.log'
    
    # 创建日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 文件处理器，使用UTF-8编码
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)
    
    # UI处理器
    class UIHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.signal_emitter = LogSignalEmitter()
        
        def emit(self, record):
            msg = self.format(record)
            self.signal_emitter.log_signal.emit(msg)
    
    ui_handler = UIHandler()
    ui_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(ui_handler)
    
    return logger

# 创建全局日志记录器实例
logger = setup_logger()