import os
from datetime import timedelta
from utils.logger import logger

class SubtitleGenerator:
    """
    字幕生成类，负责生成SRT格式字幕文件
    
    功能：
    - 生成SRT格式字幕文件
    - 支持选择使用原文或翻译文本
    - 时间码格式化
    """
    
    def __init__(self, segments, output_path, use_translation=True):
        """
        初始化字幕生成器
        
        Args:
            segments (list): 字幕段列表
            output_path (str): 输出文件路径
            use_translation (bool): 是否使用翻译文本
        """
        self.segments = segments
        self.output_path = output_path
        self.use_translation = use_translation
    
    def generate_srt(self, progress_callback=None):
        """
        生成SRT格式字幕文件
        
        Args:
            progress_callback (callable): 进度回调函数
            
        Returns:
            str: 生成的字幕文件路径
        """
        srt_path = os.path.splitext(self.output_path)[0] + ".srt"
        logger.info(f"开始生成字幕文件，输出路径: {srt_path}")
        
        with open(srt_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(self.segments):
                # SRT格式：序号、时间码、文本、空行
                f.write(f"{i+1}\n")
                
                # 格式化时间码
                start = self._format_time(segment["start"])
                end = self._format_time(segment["end"])
                f.write(f"{start} --> {end}\n")
                
                # 根据设置选择原文或翻译
                if self.use_translation and "translated" in segment:
                    f.write(f"{segment['translated']}\n")
                elif "original" in segment:
                    f.write(f"{segment['original']}\n")
                else:
                    f.write(f"{segment['text']}\n")
                
                f.write("\n")
                
                if progress_callback:
                    progress = int((i+1) / len(self.segments) * 100)
                    progress_callback(progress)
        
        logger.info(f"字幕文件生成完成: {srt_path}")
        return srt_path
    
    @staticmethod
    def _format_time(seconds):
        """
        将秒数转换为SRT格式的时间码 (HH:MM:SS,mmm)
        
        Args:
            seconds (float): 秒数
            
        Returns:
            str: 格式化的时间码
        """
        td = timedelta(seconds=seconds)
        hours = td.seconds // 3600
        minutes = (td.seconds % 3600) // 60
        seconds = td.seconds % 60
        milliseconds = int(td.microseconds / 1000)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"