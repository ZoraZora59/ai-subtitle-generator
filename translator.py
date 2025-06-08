import subprocess
from utils.logger import logger
import re

class Translator:
    """
    文本翻译类，负责将文本翻译成目标语言
    
    目前支持：
    - Ollama本地模型翻译
    - 保持原文不翻译
    """
    
    def __init__(self, use_local_model=True, model_name="gemma"):
        """
        初始化翻译器
        
        Args:
            use_local_model (bool): 是否使用本地Ollama模型
            model_name (str): Ollama模型名称，默认为 gemma
        """
        self.use_local_model = use_local_model
        self.model_name = model_name
    
    def translate_segments(self, segments, progress_callback=None):
        """
        翻译字幕段列表
        
        Args:
            segments (list): 字幕段列表
            progress_callback (callable): 进度回调函数
            
        Returns:
            list: 翻译后的字幕段列表
            
        Raises:
            ValueError: 当输入参数无效时抛出
            RuntimeError: 当翻译过程中发生错误时抛出
        """
        if not segments:
            error_msg = "输入的字幕段列表为空"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        try:
            total = len(segments)
            logger.info(f"开始翻译，共{total}段文本")
            translated_segments = []
            
            # 第一阶段：提交所有文本获取上下文理解
            if self.use_local_model and self.model_name:
                all_texts = "\n---\n".join(segment["text"] for segment in segments)
                context_prompt = f"以下是一段对话的全部内容，请先阅读并理解整体上下文：\n{all_texts}"
                logger.info("正在提交全部文本以获取上下文理解")
            
            # 第二阶段：逐段翻译
            for i, segment in enumerate(segments):
                try:
                    if not isinstance(segment, dict) or 'text' not in segment:
                        error_msg = f"无效的字幕段格式: {segment}"
                        logger.error(error_msg)
                        raise ValueError(error_msg)
                        
                    if self.use_local_model and self.model_name:
                        logger.info(f"正在翻译第{i+1}/{total}段: {segment['text']}")
                        translated_text = self.translate_with_ollama(context_prompt,segment["text"])
                        logger.info(f"第{i+1}段翻译完成: {translated_text}")
                    else:
                        logger.info(f"保持第{i+1}段原文不翻译: {segment['text']}")
                        translated_text = segment["text"]
                    
                    translated_segments.append({
                        "start": segment["start"],
                        "end": segment["end"],
                        "original": segment["text"],
                        "translated": translated_text
                    })
                    
                    if progress_callback:
                        progress = int((i+1) / total * 100)
                        progress_callback(progress)
                        
                except Exception as e:
                    error_msg = f"翻译第{i+1}段文本时发生错误: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    raise RuntimeError(error_msg) from e
            
            logger.info(f"翻译完成，成功翻译{len(translated_segments)}段文本")
            return translated_segments
            
        except Exception as e:
            error_msg = f"翻译过程中发生错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e
    
    def translate_with_ollama(self, context, text):
        """
        使用Ollama模型进行翻译
        
        Args:
            text (str): 要翻译的文本
            is_context (bool): 是否是上下文理解阶段
            
        Returns:
            str: 翻译后的文本
            
        Raises:
            ValueError: 当输入文本为空时抛出
            subprocess.CalledProcessError: 当翻译命令执行失败时抛出
            RuntimeError: 当其他错误发生时抛出
        """
        if not text or not text.strip():
            error_msg = "输入文本为空"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if not self.model_name:
            error_msg = "未指定Ollama模型名称"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        prompt = f"""你是一个专业的字幕翻译助手，负责将给出的视频内容翻译成中文，并保持原文的语气和风格。

翻译规则：
1. 输出格式：仅输出翻译结果，不要有任何前缀、后缀或额外说明
2. 语言要求：只使用中文，禁止使用任何其他语言（包括英文、数字等）
3. 标点符号：使用中文标点，句中标点保留，句末标点可省略
4. 翻译风格：
   - 保持原文的语气和风格
   - 使用自然、流畅的中文表达
   - 保持翻译的一致性
   - 适合字幕阅读的简洁表达

{context}

下面是几个示例，请参考：
原文：I want to test this program.
翻译：我想测试这个程序

原文：The weather is nice today, isn't it?
翻译：今天天气真不错

原文：Please wait a moment.
翻译：请稍等


现在请翻译以下文本：
{text}"""
        
        cmd = ["ollama", "run", self.model_name, prompt]
        
        try:
            logger.debug(f"执行Ollama翻译命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
            
            # 打印Ollama的输出
            logger.debug(f"Ollama输出: {result.stdout}")

            if not result.stdout or not result.stdout.strip():
                error_msg = "Ollama返回的翻译结果为空"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            translated_text = result.stdout.strip()
            
            # 定义允许的标点符号
            allowed_punct = r'，。！？：；、""''……—·《》【】'
            
            # 使用正则表达式匹配中文、数字、英文和允许的标点
            filtered = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9'+allowed_punct+r']+', translated_text)
            translated_text = ''.join(filtered)
            
            # 如果最后一个字符是标点，则去掉
            if translated_text and translated_text[-1] in allowed_punct:
                translated_text = translated_text[:-1]
                
            translated_text = translated_text.strip()
            logger.debug(f"Ollama翻译结果(后处理): {translated_text}")
            return translated_text
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Ollama命令执行失败: {str(e)}\n错误输出: {e.stderr}"
            logger.error(error_msg)
            raise
        except Exception as e:
            error_msg = f"翻译过程中发生未知错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e