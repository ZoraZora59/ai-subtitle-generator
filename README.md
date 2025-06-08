# AI 视频字幕生成器

这是一个基于 Python 的智能视频字幕生成工具，集成了语音识别和大模型翻译功能，可以自动将视频中的语音转换为文字，并支持使用大模型进行智能翻译，生成高质量的字幕文件。

## 功能特点

- 支持多种视频格式
- 使用 OpenAI Whisper 进行高精度语音识别
- 集成大模型智能翻译（支持 Ollama 本地部署）
  - 支持多种翻译模型（llama2、gemma 等）
  - 智能优化翻译结果，保持原文语气和风格
  - 自动清理和优化翻译文本
- 生成 SRT 格式字幕文件
- 简洁直观的图形界面
- 支持原文和译文对照显示

## 系统要求

- Python 3.8 或更高版本
- PyQt5
- OpenAI Whisper
- FFmpeg
- Ollama（用于大模型翻译功能）

## 安装步骤

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/ai-subtitle-generator.git
cd ai-subtitle-generator
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 安装 FFmpeg（如果尚未安装）：
- Windows: 下载 FFmpeg 并添加到系统环境变量
- Linux: `sudo apt-get install ffmpeg`
- macOS: `brew install ffmpeg`

4. 安装 Ollama（用于大模型翻译功能）：
- 访问 [Ollama 官网](https://ollama.ai/) 下载并安装
- 拉取需要的翻译模型：
  ```bash
  ollama pull llama2  # 或其他支持的模型
  ```

## 使用方法

1. 运行程序：
```bash
python main.py
```

2. 在界面中选择视频文件
3. 点击"开始转录"按钮
4. 等待语音识别和翻译完成
5. 在界面上查看原文和译文对照
6. 点击"生成字幕"按钮生成字幕文件

## 大模型翻译特性

- 支持多种翻译模型
  - gemma：更快更好的翻译
  - llama2：稳定可靠的翻译效果
  - 其他 Ollama 支持的模型（deepseek由于思维链展示的问题暂时还没优化好）
- 智能优化
  - 自动清理翻译结果中的多余内容
  - 保持原文的语气和风格
  - 确保翻译的准确性和自然度
- 本地部署
  - 完全本地化运行，保护隐私
  - 无需联网即可使用
  - 支持离线翻译

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 贡献

欢迎提交 Issue 和 Pull Request！

## 致谢

- [OpenAI Whisper](https://github.com/openai/whisper)
- [Ollama](https://ollama.ai/)
- [FFmpeg](https://ffmpeg.org/)