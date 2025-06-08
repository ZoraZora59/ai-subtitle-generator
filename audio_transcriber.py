import torch
import os
import whisper
from faster_whisper import WhisperModel
from utils.logger import logger

class AudioTranscriber:
    """
    音频转录类，负责将音频转换为文本
    
    支持两种转录模型：
    - OpenAI Whisper
    - Faster-Whisper
    
    支持GPU加速：
    - 自动检测CUDA设备
    - 可选的计算精度（FP16/INT8）
    - 可手动控制是否使用GPU
    """
    
    def __init__(self, use_faster_whisper=True, model_path=None, use_gpu=True, compute_type="float16"):
        """
        初始化转录器
        
        Args:
            use_faster_whisper (bool): 是否使用faster-whisper模型
            model_path (str): faster-whisper模型路径
            use_gpu (bool): 是否使用GPU加速（如果可用）
            compute_type (str): 计算精度类型，可选值："float32"、"float16"、"int8"，默认为"float16"
        """
        self.use_faster_whisper = use_faster_whisper
        self.model_path = model_path
        self.use_gpu = use_gpu
        self.compute_type = compute_type
        
        # 检测CUDA是否可用
        cuda_available = torch.cuda.is_available()
        # 根据用户设置和CUDA可用性决定使用的设备
        self.device = "cuda" if (cuda_available and use_gpu) else "cpu"
        
        if self.device == "cuda":
            logger.info(f"GPU加速已启用，使用设备: {torch.cuda.get_device_name(0)}")
            logger.info(f"计算精度: {compute_type}")
        else:
            if cuda_available and not use_gpu:
                logger.info("GPU加速已手动禁用，使用CPU模式")
            else:
                logger.info("未检测到可用的CUDA设备，使用CPU模式")
    
    def transcribe(self, audio_path, progress_callback=None):
        """
        转录音频文件
        
        Args:
            audio_path (str): 音频文件路径
            progress_callback (callable): 进度回调函数
            
        Returns:
            list: 包含时间戳和文本的字幕段列表
        """
        if self.use_faster_whisper and self.model_path:
            logger.info(f"使用faster-whisper模型: {self.model_path}")
            return self.transcribe_with_faster_whisper(audio_path, progress_callback)
        else:
            logger.info("使用OpenAI Whisper模型")
            return self.transcribe_with_whisper(audio_path, progress_callback)
    
    def transcribe_with_whisper(self, audio_path, progress_callback=None):
        """
        使用OpenAI Whisper模型进行转录
        
        Args:
            audio_path (str): 音频文件路径
            progress_callback (callable): 进度回调函数
            
        Returns:
            list: 转录结果列表
            
        Raises:
            FileNotFoundError: 当音频文件不存在时抛出
            RuntimeError: 当模型加载或转录过程中出现错误时抛出
            ModuleNotFoundError: 当Whisper模型未安装时抛出
        """
        if not os.path.exists(audio_path):
            logger.error(f"音频文件不存在: {audio_path}")
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
            
        try:
            # 检查是否安装了whisper模块
            try:
                import whisper
            except ImportError:
                error_msg = "OpenAI Whisper模型未安装，请先运行: pip install openai-whisper"
                logger.error(error_msg)
                raise ModuleNotFoundError(error_msg)
                
            logger.info(f"正在加载Whisper模型(base)到{self.device}设备")
            model = whisper.load_model("base", device=self.device)
            
            # 根据设备和计算精度设置fp16参数
            use_fp16 = self.device == "cuda" and self.compute_type in ["float16", "int8"]
            logger.info(f"开始转录音频文件: {audio_path}，{'启用' if use_fp16 else '禁用'}FP16加速")
            result = model.transcribe(audio_path, fp16=use_fp16)
            
            segments = []
            total_segments = len(result["segments"])
            logger.info(f"音频转录完成，共{total_segments}段")
            
            for i, segment in enumerate(result["segments"]):
                segments.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip()
                })
                if progress_callback:
                    progress = int((i + 1) / total_segments * 100)
                    progress_callback(progress)
                    
            return segments
            
        except Exception as e:
            error_msg = f"Whisper转录过程中发生错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e
    
    def transcribe_with_faster_whisper(self, audio_path, progress_callback=None):
        """
        使用faster-whisper模型进行转录
        
        Args:
            audio_path (str): 音频文件路径
            progress_callback (callable): 进度回调函数
            
        Returns:
            list: 转录结果列表
            
        Raises:
            FileNotFoundError: 当音频文件不存在时抛出
            RuntimeError: 当模型加载或转录过程中出现错误时抛出
        """
        if not os.path.exists(audio_path):
            logger.error(f"音频文件不存在: {audio_path}")
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
            
        try:
            logger.info(f"正在加载faster-whisper模型({self.model_path})到{self.device}设备，计算精度: {self.compute_type}")
            model = WhisperModel(
                self.model_path, 
                device=self.device, 
                compute_type=self.compute_type
            )
            
            logger.info(f"开始转录音频文件: {audio_path}")
            segments, info = model.transcribe(audio_path, beam_size=5)
            
            result = []
            total_duration = info.duration
            logger.info(f"音频时长: {total_duration:.2f}秒")
            
            for segment in segments:
                result.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                })
                if progress_callback:
                    progress = int(segment.end / total_duration * 100)
                    progress_callback(progress)
                    
            logger.info(f"音频转录完成，共{len(result)}段")
            return result
            
        except Exception as e:
            error_msg = f"faster-whisper转录过程中发生错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e