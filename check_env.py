import subprocess
import importlib
import shutil
import os

def check_command(cmd, name):
    print(f"\n[检查] {name}...")
    if shutil.which(cmd):
        try:
            output = subprocess.check_output([cmd, "--version"], stderr=subprocess.STDOUT, text=True)
            print(f"[✓] {name} 可用：\n{output.strip()}")
        except subprocess.CalledProcessError as e:
            print(f"[!] {name} 版本获取失败：{e}")
    else:
        print(f"[✗] {name} 未安装或未加入 PATH。")

def check_module(name, test_func=None):
    print(f"\n[检查] Python 模块：{name}...")
    try:
        module = importlib.import_module(name)
        print(f"[✓] {name} 已安装")
        if test_func:
            test_func(module)
    except ImportError:
        print(f"[✗] {name} 未安装")

def test_torch(torch):
    print(f"  - CUDA 可用：{torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  - CUDA 设备：{torch.cuda.get_device_name(0)}")
        print(f"  - CUDA 版本：{torch.version.cuda}")

def test_whisper(whisper):
    try:
        model = whisper.load_model("base", device="cuda" if torch.cuda.is_available() else "cpu")
        print("  - Whisper 模型加载成功")
    except Exception as e:
        print(f"  - Whisper 加载失败：{e}")

def test_ollama():
    print(f"\n[检查] Ollama...")
    if shutil.which("ollama"):
        try:
            output = subprocess.check_output(["ollama", "list"], text=True)
            print(f"[✓] Ollama 已安装，模型列表：\n{output}")
        except subprocess.CalledProcessError as e:
            print(f"[!] 无法获取模型列表：{e}")
    else:
        print("[✗] Ollama 未安装或未加入 PATH")

def test_opencc(opencc):
    try:
        cc = opencc.OpenCC('t2s')
        print(f"  - 繁体转简体示例：臺灣 → {cc.convert('臺灣')}")
    except Exception as e:
        print(f"  - OpenCC 测试失败：{e}")

def main():
    print("========= 本地 AI 字幕环境检查工具 =========")

    check_command("nvidia-smi", "NVIDIA 驱动")
    check_command("ffmpeg", "ffmpeg")

    check_module("torch", test_torch)
    check_module("whisper", test_whisper)
    check_module("transformers")
    check_module("opencc", test_opencc)

    test_ollama()

    print("\n========= 检查完毕 =========")

if __name__ == "__main__":
    import torch  # 提前加载供 whisper 检测用
    main()
