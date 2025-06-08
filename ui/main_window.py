from PyQt5.QtWidgets import (QMainWindow, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
                             QWidget, QFileDialog, QTextEdit, QComboBox, QProgressBar, QCheckBox, QMessageBox, QSizePolicy, QApplication)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt5.QtGui import QFont, QTextCursor
import os
import subprocess
import torch

from video_processor import VideoProcessor
from audio_transcriber import AudioTranscriber
from translator import Translator
from subtitle_generator import SubtitleGenerator
from utils.logger import logger

class TranscriptionThread(QThread):
    """
    音频转录线程类
    
    负责在后台线程中处理音频转录任务，避免阻塞UI
    """
    progress_signal = pyqtSignal(int)
    result_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, video_path, use_faster_whisper=True, model_path=None, use_gpu=True, compute_type="float16"):
        super().__init__()
        self.video_path = video_path
        self.transcriber = AudioTranscriber(use_faster_whisper, model_path, use_gpu, compute_type)
        self.video_processor = VideoProcessor()
    
    def run(self):
        try:
            if not self.video_path:
                error_msg = "未指定视频文件路径"
                logger.error(error_msg)
                self.error_signal.emit(error_msg)
                return
                
            logger.info(f"开始处理视频: {self.video_path}")
            
            try:
                # 提取音频
                logger.info("正在提取音频...")
                audio_path = self.video_processor.extract_audio(self.video_path)
                
                # 转录音频
                logger.info("正在转录音频...")
                segments = self.transcriber.transcribe(audio_path, self.progress_signal.emit)
                
                # 清理临时文件
                logger.info("正在清理临时文件...")
                self.video_processor.cleanup_temp_file(audio_path)
                
                logger.info(f"转录完成，共{len(segments)}段文本")
                self.result_signal.emit(segments)
                
            except FileNotFoundError as e:
                error_msg = f"文件不存在: {str(e)}"
                logger.error(error_msg)
                self.error_signal.emit(error_msg)
            except PermissionError as e:
                error_msg = f"权限不足: {str(e)}"
                logger.error(error_msg)
                self.error_signal.emit(error_msg)
            except subprocess.CalledProcessError as e:
                error_msg = f"外部命令执行失败: {str(e)}"
                logger.error(error_msg)
                self.error_signal.emit(error_msg)
            except Exception as e:
                error_msg = f"处理过程中发生错误: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self.error_signal.emit(error_msg)
                
        except Exception as e:
            error_msg = f"线程执行过程中发生未知错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_signal.emit(error_msg)

class TranslationThread(QThread):
    """
    文本翻译线程类
    
    负责在后台线程中处理翻译任务，避免阻塞UI
    """
    progress_signal = pyqtSignal(int)
    result_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, segments, use_local_model=True, model_name=None):
        super().__init__()
        self.translator = Translator(use_local_model, model_name)
        self.segments = segments
    
    def run(self):
        try:
            translated_segments = self.translator.translate_segments(
                self.segments,
                self.progress_signal.emit
            )
            self.result_signal.emit(translated_segments)
            
        except Exception as e:
            logger.error(f"翻译过程中发生错误: {str(e)}", exc_info=True)
            self.error_signal.emit(str(e))

class SubtitleGenerationThread(QThread):
    """
    字幕生成线程类
    
    负责在后台线程中处理字幕生成任务，避免阻塞UI
    """
    progress_signal = pyqtSignal(int)
    result_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, segments, output_path, use_translation=True):
        super().__init__()
        self.subtitle_generator = SubtitleGenerator(segments, output_path, use_translation)
    
    def run(self):
        try:
            srt_path = self.subtitle_generator.generate_srt(self.progress_signal.emit)
            self.result_signal.emit(srt_path)
            
        except Exception as e:
            logger.error(f"字幕生成过程中发生错误: {str(e)}", exc_info=True)
            self.error_signal.emit(str(e))

class MainWindow(QMainWindow):
    """
    主窗口类
    
    应用程序的主界面，包含所有UI组件和业务逻辑
    """
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.segments = None
        self.video_path = None
        
        # 连接日志信号
        from utils.logger import logger
        logger.handlers[-1].signal_emitter.log_signal.connect(self.update_log)
    
    def detect_ollama_models(self):
        """
        检测本地可用的Ollama模型
        """
        try:
            # 执行ollama list命令获取本地模型列表
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            if result.returncode == 0:
                # 解析模型列表
                lines = result.stdout.splitlines()
                if len(lines) > 1:  # 第一行是表头
                    models = [line.split()[0] for line in lines[1:] if line.strip()]
                    self.ollama_model_combo.clear()
                    self.ollama_model_combo.addItems(models)
                    
                    # 如果存在gemma模型，将其设为默认值
                    gemma_models = [model for model in models if 'gemma' in model.lower()]
                    if gemma_models:
                        self.ollama_model_combo.setCurrentText(gemma_models[0])
                    
                    self.translation_combo.setEnabled(True)
                    self.translation_combo.setToolTip("选择是否启用翻译：\n不翻译 - 只生成原语言字幕\n使用Ollama翻译 - 使用本地Ollama模型翻译")
                    self.ollama_model_combo.setEnabled(True)
                    return True
            
            # 如果没有检测到模型，使用默认列表
            self.ollama_model_combo.clear()
            self.translation_combo.setEnabled(False)
            self.translation_combo.setToolTip("本地没有检测到可用的Ollama模型，无法使用翻译功能")
            self.ollama_model_combo.setEnabled(False)
            return False
        except Exception as e:
            logger.error(f"检测Ollama模型时出错: {str(e)}")
            self.ollama_model_combo.clear()
            self.ollama_model_combo.addItems(['qwen:7b', 'qwen:14b', 'llama2:7b', 'llama2:13b', 'yi:6b', 'yi:34b'])
            self.translation_combo.setEnabled(False)
            self.translation_combo.setToolTip("检测Ollama模型时出错: {str(e)}")
            self.ollama_model_combo.setEnabled(False)
            return False
            
    def init_ui(self):
        """
        初始化用户界面
        """
        self.setWindowTitle('视频字幕翻译工具')
        
        # 获取屏幕分辨率
        screen = QApplication.primaryScreen().geometry()
        # 设置窗口大小为屏幕的二分之一
        window_width = screen.width() // 2
        window_height = screen.height() // 2
        # 设置窗口位置在屏幕中央
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)
        
        # 创建主窗口部件和布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # 文件选择区域
        file_layout = QHBoxLayout()
        self.file_label = QLabel('选择视频文件：')
        self.file_button = QPushButton('浏览...')
        self.file_button.setToolTip('点击选择要处理的视频文件')
        self.file_button.clicked.connect(self.select_video)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.file_button)
        layout.addLayout(file_layout)
        
        # 模型选择区域
        model_layout = QVBoxLayout()
        
        # 语音识别模型选择
        whisper_layout = QHBoxLayout()
        whisper_layout.addWidget(QLabel('语音识别模型：'))
        self.whisper_combo = QComboBox()
        self.whisper_combo.addItems(['OpenAI Whisper', 'Faster Whisper'])
        self.whisper_combo.setToolTip('选择用于语音识别的模型：\nOpenAI Whisper - 原始Whisper模型\nFaster Whisper - 优化后的更快版本')
        whisper_layout.addWidget(self.whisper_combo)
        whisper_layout.addStretch()
        model_layout.addLayout(whisper_layout)
        
        # 翻译设置区域
        translation_layout = QHBoxLayout()
        translation_layout.addWidget(QLabel('翻译设置：'))
        self.translation_combo = QComboBox()
        self.translation_combo.addItems(['不翻译', '使用Ollama翻译'])
        self.translation_combo.setToolTip('选择是否启用翻译：\n不翻译 - 只生成原语言字幕\n使用Ollama翻译 - 使用本地Ollama模型翻译')
        self.translation_combo.setCurrentText('不翻译')
        self.translation_combo.currentTextChanged.connect(self.on_translation_model_changed)
        translation_layout.addWidget(self.translation_combo)
        
        # Ollama模型选择
        self.ollama_model_combo = QComboBox()
        self.ollama_model_combo.setToolTip('选择要使用的Ollama模型')
        self.ollama_model_combo.setEnabled(False)
        translation_layout.addWidget(QLabel('Ollama模型：'))
        translation_layout.addWidget(self.ollama_model_combo)
        translation_layout.addStretch()
        model_layout.addLayout(translation_layout)
        
        # 初始化时检测本地可用的Ollama模型
        self.detect_ollama_models()
        
        layout.addLayout(model_layout)
        
        # GPU加速选项区域
        gpu_layout = QHBoxLayout()
        self.use_gpu_checkbox = QCheckBox('启用GPU加速')
        self.use_gpu_checkbox.setToolTip('启用GPU加速可以显著提高转录速度（需要NVIDIA GPU）')
        self.use_gpu_checkbox.setChecked(torch.cuda.is_available())
        self.use_gpu_checkbox.setEnabled(torch.cuda.is_available())
        if not torch.cuda.is_available():
            self.use_gpu_checkbox.setToolTip('未检测到可用的CUDA设备，无法启用GPU加速')
        
        self.compute_type_combo = QComboBox()
        self.compute_type_combo.addItems(['float16 (推荐)', 'float32 (精度高)', 'int8 (速度快)'])
        self.compute_type_combo.setToolTip('计算精度类型：\nfloat16 - 平衡速度和精度\nfloat32 - 更高精度但更慢\nint8 - 更快速度但精度较低')
        self.compute_type_combo.setEnabled(torch.cuda.is_available())
        
        gpu_layout.addWidget(self.use_gpu_checkbox)
        gpu_layout.addWidget(QLabel('计算精度：'))
        gpu_layout.addWidget(self.compute_type_combo)
        layout.addLayout(gpu_layout)
        
        # 进度条和状态标签
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setToolTip('显示当前任务的处理进度')
        self.statusBar = self.statusBar()
        self.log_label = QLabel('就绪')
                #     QLabel {
        #         background-color: #f5f5f5;
        #         padding: 5px;
        #         border-radius: 3px;
        #     }
        self.log_label.setStyleSheet('QLabel { color: #666666; background-color: #f5f5f5;border-radius: 3px;padding: 5px;}')  # 使用灰色字体
        self.statusBar.addPermanentWidget(self.log_label)
        self.status_label = QLabel('就绪')
        self.status_label.setToolTip('显示当前正在执行的任务')
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        layout.addLayout(progress_layout)
        
        # 文本显示区域
        text_layout = QHBoxLayout()
        
        # 左侧原文显示
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel('原文：'))
        self.original_text = QTextEdit()
        self.original_text.setReadOnly(True)
        self.original_text.setToolTip('显示识别出的原文')
        self.original_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.original_text.setMinimumHeight(200)  # 设置最小高度
        # 设置滚动条以行为单位
        self.original_text.setLineWrapMode(QTextEdit.NoWrap)  # 禁用自动换行
        self.original_text.verticalScrollBar().setSingleStep(1)  # 设置单步滚动为1行
        left_layout.addWidget(self.original_text)
        
        # 右侧译文显示
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel('译文：'))
        self.translated_text = QTextEdit()
        self.translated_text.setReadOnly(True)
        self.translated_text.setToolTip('显示翻译后的文本')
        self.translated_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.translated_text.setMinimumHeight(200)  # 设置最小高度
        # 设置滚动条以行为单位
        self.translated_text.setLineWrapMode(QTextEdit.NoWrap)  # 禁用自动换行
        self.translated_text.verticalScrollBar().setSingleStep(1)  # 设置单步滚动为1行
        right_layout.addWidget(self.translated_text)
        
        # 连接滚动条信号
        self.original_text.verticalScrollBar().valueChanged.connect(
            lambda value: self.translated_text.verticalScrollBar().setValue(value)
        )
        self.translated_text.verticalScrollBar().valueChanged.connect(
            lambda value: self.original_text.verticalScrollBar().setValue(value)
        )
        
        # 添加到水平布局
        text_layout.addLayout(left_layout)
        text_layout.addLayout(right_layout)
        layout.addLayout(text_layout)
        
        # 控制按钮区域
        button_layout = QHBoxLayout()
        self.start_button = QPushButton('开始转录')
        self.start_button.setToolTip('开始处理视频并转录语音为文字')
        self.start_button.clicked.connect(self.start_transcription)
        self.generate_button = QPushButton('生成字幕')
        self.generate_button.setToolTip('将转录的文本生成SRT格式的字幕文件')
        self.generate_button.clicked.connect(self.generate_subtitle)
        self.generate_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.generate_button)
        layout.addLayout(button_layout)
        
        # 翻译选项
        self.use_translation_checkbox = QCheckBox('使用翻译结果')
        self.use_translation_checkbox.setToolTip('选中此项将在字幕中使用翻译后的文本，否则使用原文')
        self.use_translation_checkbox.setChecked(False)  # 默认不选中
        self.use_translation_checkbox.setEnabled(False)  # 默认禁用
        # layout.addWidget(self.use_translation_checkbox)
        
        # 用于存储详细日志的变量
        self.log_history = []
    
    def select_video(self):
        """
        选择视频文件
        """
        try:
            logger.info("打开文件选择对话框")
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                "选择视频文件",
                "",
                "视频文件 (*.mp4 *.mkv *.avi *.mov);;所有文件 (*.*)"
            )
            
            if file_name:
                logger.info(f"用户选择了视频文件: {file_name}")
                # 验证文件是否存在且可访问
                if not os.path.exists(file_name):
                    error_msg = f"选择的文件不存在: {file_name}"
                    logger.error(error_msg)
                    QMessageBox.critical(self, "错误", error_msg)
                    return
                    
                if not os.path.isfile(file_name):
                    error_msg = f"选择的路径不是文件: {file_name}"
                    logger.error(error_msg)
                    QMessageBox.critical(self, "错误", error_msg)
                    return
                    
                try:
                    # 尝试打开文件以验证访问权限
                    with open(file_name, 'rb') as _:
                        pass
                except PermissionError:
                    error_msg = f"没有权限访问文件: {file_name}"
                    logger.error(error_msg)
                    QMessageBox.critical(self, "错误", error_msg)
                    return
                except Exception as e:
                    error_msg = f"验证文件访问时发生错误: {str(e)}"
                    logger.error(error_msg)
                    QMessageBox.critical(self, "错误", error_msg)
                    return
                
                self.video_path = file_name
                self.file_label.setText(f'已选择：{file_name}')
                self.start_button.setEnabled(True)
                logger.info("文件选择完成，已启用开始按钮")
            else:
                logger.info("用户取消了文件选择")
                
        except Exception as e:
            error_msg = f"文件选择过程中发生错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, "错误", error_msg)

    
    def start_transcription(self):
        """
        开始音频转录过程
        """
        if not self.video_path:
            QMessageBox.warning(self, '警告', '请先选择视频文件！')
            return
            
        # 检查模型选择
        use_faster_whisper = self.whisper_combo.currentText() == 'Faster Whisper'
        if not use_faster_whisper:
            try:
                import whisper
            except ImportError:
                QMessageBox.critical(self, '错误', 'OpenAI Whisper模型未安装，请先运行: pip install openai-whisper')
                return
        
        # 禁用按钮，避免重复操作
        self.start_button.setEnabled(False)
        self.generate_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.original_text.clear()
        self.translated_text.clear()
        self.update_status('正在提取音频...')
        
        # 获取GPU加速相关设置
        use_gpu = self.use_gpu_checkbox.isChecked()
        compute_type_text = self.compute_type_combo.currentText()
        # 从UI选项中提取实际的compute_type值
        if "float16" in compute_type_text:
            compute_type = "float16"
        elif "float32" in compute_type_text:
            compute_type = "float32"
        elif "int8" in compute_type_text:
            compute_type = "int8"
        else:
            compute_type = "float16"  # 默认值
            
        # 创建转录线程
        self.transcription_thread = TranscriptionThread(
            self.video_path,
            use_faster_whisper,
            'faster-whisper-large' if use_faster_whisper else None,
            use_gpu,
            compute_type
        )
        
        # 连接信号
        self.transcription_thread.progress_signal.connect(self.update_progress)
        self.transcription_thread.result_signal.connect(self.handle_transcription_result)
        self.transcription_thread.error_signal.connect(self.handle_error)
        
        # 开始转录
        self.transcription_thread.start()
    
    def handle_transcription_result(self, segments):
        """
        处理转录结果
        
        Args:
            segments (list): 转录的字幕段列表
        """
        self.segments = segments
        self.original_text.clear()
        self.translated_text.clear()
        
        # 显示转录结果
        for segment in segments:
            # 格式化时间戳
            start_time = self.format_timestamp(segment['start'])
            end_time = self.format_timestamp(segment['end'])
            time_str = f"[{start_time} --> {end_time}]"
            self.original_text.append(f"{time_str} {segment['text']}\n")
        
        # 如果翻译功能和Ollama模型都可用，且选择了翻译，则开始翻译过程
        if (self.translation_combo.isEnabled() and 
            self.ollama_model_combo.isEnabled() and 
            self.translation_combo.currentText() == '使用Ollama翻译'):
            self.start_translation()
        else:
            self.start_button.setEnabled(True)
            self.generate_button.setEnabled(True)
    
    def start_translation(self):
        """
        开始翻译过程
        """
        self.progress_bar.setValue(0)
        self.update_status('正在翻译文本...')
        self.translation_thread = TranslationThread(
            self.segments,
            True,
            self.ollama_model_combo.currentText()
        )
        
        # 连接信号
        self.translation_thread.progress_signal.connect(self.update_progress)
        self.translation_thread.result_signal.connect(self.handle_translation_result)
        self.translation_thread.error_signal.connect(self.handle_error)
        
        # 开始翻译
        self.translation_thread.start()
    
    def handle_translation_result(self, translated_segments):
        """
        处理翻译结果
        
        Args:
            translated_segments (list): 翻译后的字幕段列表
        """
        self.segments = translated_segments
        self.original_text.clear()
        self.translated_text.clear()
        
        # 显示原文和翻译结果
        for segment in translated_segments:
            # 格式化时间戳
            start_time = self.format_timestamp(segment['start'])
            end_time = self.format_timestamp(segment['end'])
            time_str = f"[{start_time} --> {end_time}]"
            self.original_text.append(f"{time_str} {segment['original']}\n")
            self.translated_text.append(f"{time_str} {segment['translated']}\n")
        
        # 启用翻译选项复选框并默认选中
        self.use_translation_checkbox.setEnabled(True)
        self.use_translation_checkbox.setChecked(True)
        
        self.start_button.setEnabled(True)
        self.generate_button.setEnabled(True)
    
    def generate_subtitle(self):
        """
        生成字幕文件
        """
        if not self.segments:
            QMessageBox.warning(self, '警告', '没有可用的字幕内容！')
            return
        
        # 选择输出文件
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存字幕文件",
            "",
            "字幕文件 (*.srt);;所有文件 (*.*)"
        )
        
        if output_path:
            self.progress_bar.setValue(0)
            self.generate_button.setEnabled(False)
            self.update_status('正在生成字幕文件...')
            
            # 创建字幕生成线程
            self.subtitle_thread = SubtitleGenerationThread(
                self.segments,
                output_path,
                self.use_translation_checkbox.isChecked()
            )
            
            # 连接信号
            self.subtitle_thread.progress_signal.connect(self.update_progress)
            self.subtitle_thread.result_signal.connect(self.handle_subtitle_result)
            self.subtitle_thread.error_signal.connect(self.handle_error)
            
            # 开始生成字幕
            self.subtitle_thread.start()
    
    def handle_subtitle_result(self, srt_path):
        """
        处理字幕生成结果
        
        Args:
            srt_path (str): 生成的字幕文件路径
        """
        QMessageBox.information(self, '成功', f'字幕文件已生成：\n{srt_path}')
        self.generate_button.setEnabled(True)
    
    def update_progress(self, value):
        """
        更新进度条
        
        Args:
            value (int): 进度值（0-100）
        """
        self.progress_bar.setValue(value)

    def update_status(self, status):
        """
        更新状态标签
        
        Args:
            status (str): 状态信息
        """
        self.status_label.setText(status)
    
    def update_log(self, message):
        """
        更新日志显示
        
        Args:
            message (str): 日志消息
        """
        self.log_label.setText(message)
        self.log_history.append(message)
        # 保持最多显示最近的50条日志
        if len(self.log_history) > 50:
            self.log_history = self.log_history[-50:]
        # 更新工具提示
        self.log_label.setToolTip('\n'.join(self.log_history))

    def handle_error(self, error_msg):
        """
        统一的异常处理方法
        
        处理所有线程中的异常，记录日志并显示错误信息
        
        Args:
            error_msg (str): 错误信息
        """
        # 记录错误到日志
        logger.error(f"线程执行错误: {error_msg}")
        
        # 显示错误对话框
        error_box = QMessageBox(self)
        error_box.setIcon(QMessageBox.Critical)
        error_box.setWindowTitle("错误")
        error_box.setText("操作执行失败")
        error_box.setInformativeText(error_msg)
        error_box.setDetailedText("详细错误信息已记录到日志文件中。")
        error_box.exec_()
        
        # 重置界面状态
        self.start_button.setEnabled(True)
        self.generate_button.setEnabled(bool(self.segments))
        self.progress_bar.setValue(0)
        self.update_status("就绪")

    def on_translation_model_changed(self, text):
        """处理翻译模型选择变化"""
        if text == '不翻译':
            self.use_translation_checkbox.setChecked(False)
            self.use_translation_checkbox.setEnabled(False)
            self.ollama_model_combo.setEnabled(False)
        else:
            self.use_translation_checkbox.setEnabled(True)
            self.ollama_model_combo.setEnabled(True)

    def format_timestamp(self, seconds):
        """
        将秒数格式化为时间戳字符串
        
        Args:
            seconds (float): 秒数
            
        Returns:
            str: 格式化的时间戳字符串 (HH:MM:SS,mmm)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"