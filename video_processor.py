import os
import subprocess
from utils.logger import logger

class VideoProcessor:
    """
    视频处理类，负责视频文件的相关操作
    
    主要功能：
    - 音频提取
    - 临时文件管理
    """
    
    @staticmethod
    def extract_audio(video_path):
        """
        从视频文件中提取音频
        
        Args:
            video_path (str): 视频文件路径
            
        Returns:
            str: 提取的音频文件路径
            
        Raises:
            FileNotFoundError: 当视频文件不存在时抛出
            subprocess.CalledProcessError: 当音频提取失败时抛出
            RuntimeError: 当其他错误发生时抛出
        """
        if not os.path.exists(video_path):
            error_msg = f"视频文件不存在: {video_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
            
        if not os.path.isfile(video_path):
            error_msg = f"指定路径不是文件: {video_path}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
            
        # 生成临时音频文件路径
        audio_path = os.path.splitext(video_path)[0] + "_temp.wav"
        
        try:
            logger.info(f"开始从视频提取音频: {video_path}")
            # 使用ffmpeg提取音频
            cmd = ["ffmpeg", "-i", video_path, "-q:a", "0", "-map", "a", audio_path, "-y"]
            process = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # 检查输出文件是否成功创建
            if not os.path.exists(audio_path):
                error_msg = "音频提取完成但输出文件未生成"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
            logger.info(f"音频提取完成，临时文件: {audio_path}")
            return audio_path
            
        except subprocess.CalledProcessError as e:
            error_msg = f"音频提取失败: {str(e)}\nffmpeg输出: {e.stderr}"
            logger.error(error_msg)
            raise
        except Exception as e:
            error_msg = f"音频提取过程中发生未知错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e
    
    @staticmethod
    def cleanup_temp_file(file_path):
        """
        清理临时文件
        
        Args:
            file_path (str): 要清理的文件路径
            
        Raises:
            PermissionError: 当没有权限删除文件时抛出
            OSError: 当文件删除过程中发生其他错误时抛出
        """
        if not file_path:
            logger.warning("清理临时文件时收到空路径")
            return
            
        try:
            if os.path.exists(file_path):
                logger.info(f"正在清理临时文件: {file_path}")
                os.remove(file_path)
                logger.info(f"临时文件清理完成: {file_path}")
            else:
                logger.warning(f"要清理的临时文件不存在: {file_path}")
                
        except PermissionError as e:
            error_msg = f"没有权限删除文件: {file_path}"
            logger.error(error_msg)
            raise
        except OSError as e:
            error_msg = f"删除临时文件时发生错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise