"""
终极版视频去重脚本（GPU+CPU 协同版）
支持: GPU解码 + GPU滤镜 + CPU编码
集成: Waifu2x、DAIN、RIFE、CAIN、IFRNet、Real-CUGAN、Anime4K
"""
import os
import sys
import datetime
import random
from pathlib import Path

# 设置编码
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# 检查 GPU
GPU_AVAILABLE = False

def detect_gpu():
    """检测 GPU"""
    global GPU_AVAILABLE
    
    try:
        import ctypes
        nvcuda = ctypes.WinDLL('nvcuda.dll', mode=ctypes.RTLD_GLOBAL)
        GPU_AVAILABLE = True
        print("  ✅ NVIDIA CUDA GPU 可用")
    except:
        print("  ❌ GPU 不可用，使用纯 CPU 模式")

# 检查 AI 模型
MODEL_DIR = Path(__file__).parent / "models"
RIFE_MODEL_DIR = Path(__file__).parent / "RIFE_trained_model_v3.6"
CLIQ_MODEL_DIR = Path(__file__).parent / "cliqa_pretrained_models_20230419"
WAIFU2X_DIR = Path(__file__).parent / "完整包138" / "Waifu2x-Extension-GUI-v3.138.01-Win64" / "waifu2x-extension-gui"

AI_MODELS = {
    'waifu2x': False,
    'dain': False,
    'rife': False,
    'cain': False,
    'ifrnet': False,
    'real-cugan': False,
    'anime4k': False,
    'cliq': False,
    'esrgan': False
}

def check_all_models():
    """检查所有 AI 模型"""
    print("检测 AI 模型...")
    
    # Waifu2x-Extension-GUI
    if WAIFU2X_DIR.exists():
        AI_MODELS['waifu2x'] = True
        print(f"  ✅ Waifu2x-Extension-GUI")
        
        model_checks = [
            ('dain', WAIFU2X_DIR / "dain-ncnn-vulkan"),
            ('cain', WAIFU2X_DIR / "cain-ncnn-vulkan"),
            ('ifrnet', WAIFU2X_DIR / "ifrnet-ncnn-vulkan"),
            ('real-cugan', WAIFU2X_DIR / "Real-CUGAN-Caffe"),
            ('anime4k', WAIFU2X_DIR / "Anime4K"),
        ]
        
        for model_name, model_path in model_checks:
            if model_path.exists():
                AI_MODELS[model_name] = True
                print(f"    ✅ {model_name.upper()}")
    
    # 独立 RIFE
    if RIFE_MODEL_DIR.exists():
        rife_model = RIFE_MODEL_DIR / "train_log" / "flownet.pkl"
        if rife_model.exists():
            AI_MODELS['rife'] = True
            print(f"  ✅ RIFE (独立模型)")
    
    # CLIQ
    if CLIQ_MODEL_DIR.exists():
        if list(CLIQ_MODEL_DIR.rglob("*.pth")):
            AI_MODELS['cliq'] = True
            print(f"  ✅ CLIQ 质量评估")
    
    # ESRGAN
    if MODEL_DIR.exists():
        if list(MODEL_DIR.glob("*.pth")):
            AI_MODELS['esrgan'] = True
            print(f"  ✅ Real-ESRGAN")

def generate_output_dir():
    """生成输出目录"""
    base_dir = "G:\\TRAE\\去重"
    os.makedirs(base_dir, exist_ok=True)
    
    today = datetime.date.today()
    date_str = f"{today.month}月{today.day}日"
    folder_name = f"去重后视频{date_str}"
    output_dir = os.path.join(base_dir, folder_name)
    
    counter = 1
    while os.path.exists(output_dir):
        folder_name = f"{counter}_去重后视频{date_str}"
        output_dir = os.path.join(base_dir, folder_name)
        counter += 1
    
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n输出目录: {output_dir}")
    return output_dir

def get_video_files(input_dir):
    """获取目录中的视频文件"""
    video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv')
    video_files = []
    
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(video_extensions):
            video_files.append(os.path.join(input_dir, filename))
    
    return sorted(video_files)

def process_video(input_path, output_dir, config):
    """处理单个视频"""
    from video_processor_hybrid import VideoProcessor
    
    filename = os.path.basename(input_path)
    name, ext = os.path.splitext(filename)
    output_path = os.path.join(output_dir, f"{name}_去重{ext}")
    
    # AI预处理
    current_input = input_path
    temp_files = []
    
    if config.get('use_dain', False):
        from waifu2x_processor import Waifu2xProcessor
        
        temp_path = os.path.join(output_dir, f"{name}_dain_temp{ext}")
        temp_files.append(temp_path)
        
        print("  [步骤1] DAIN 帧插值...")
        
        processor = Waifu2xProcessor()
        if processor.process(current_input, temp_path, mode='dain'):
            current_input = temp_path
            print("    ✓ DAIN 处理完成")
        else:
            print("    ✗ DAIN 处理失败，使用原始视频")
    
    elif config.get('use_rife', False):
        from rife_processor import FrameInterpolationProcessor
        
        temp_path = os.path.join(output_dir, f"{name}_rife_temp{ext}")
        temp_files.append(temp_path)
        
        print("  [步骤1] RIFE 帧插值...")
        
        processor = FrameInterpolationProcessor()
        if processor.process(current_input, temp_path):
            current_input = temp_path
            print("    ✓ RIFE 处理完成")
    
    # 核心处理（GPU+CPU协同）
    print("  [步骤2] GPU+CPU 协同处理...")
    processor = VideoProcessor(current_input, output_path, config)
    success = processor.run()
    
    # 清理临时文件
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except:
            pass
    
    return success

def batch_process(input_dir, config):
    """批量处理视频"""
    video_files = get_video_files(input_dir)
    
    if not video_files:
        print("未找到视频文件")
        return
    
    output_dir = generate_output_dir()
    print(f"发现 {len(video_files)} 个视频文件")
    
    success_count = 0
    for i, video_path in enumerate(video_files, 1):
        print(f"\n处理 [{i}/{len(video_files)}]: {os.path.basename(video_path)}")
        
        if process_video(video_path, output_dir, config):
            success_count += 1
    
    print(f"\n=== 处理完成 ===")
    print(f"成功: {success_count}/{len(video_files)}")

def show_system_info():
    """显示系统信息"""
    print("\n📦 系统配置:")
    print("-" * 60)
    print(f"  GPU加速: {'✅ 可用' if GPU_AVAILABLE else '❌ 不可用'}")
    print(f"  CUDA支持: {'✅ 可用' if GPU_AVAILABLE else '❌ 不可用'}")
    print("\n  AI模型:")
    for model, available in AI_MODELS.items():
        print(f"    {'✅' if available else '❌'} {model.upper()}")
    print("-" * 60)

def main():
    """主程序"""
    print("=" * 60)
    print("终极版视频去重脚本 (GPU+CPU 协同版)")
    print("=" * 60)
    
    # 检测 GPU
    detect_gpu()
    
    # 检测 AI 模型
    check_all_models()
    
    # 显示系统信息
    show_system_info()
    
    print("\n自动进入批量处理模式...")
    
    # 获取输入目录
    if len(sys.argv) > 1:
        input_dir = sys.argv[1]
        print(f"使用命令行参数作为目录: {input_dir}")
    else:
        input_dir = input("请输入视频目录路径: ").strip()
    
    if not os.path.isdir(input_dir):
        print("无效的目录路径")
        return
    
    # 选择处理模式
    print("\n🎯 选择处理模式:")
    print("  1. 标准模式 (纯CPU, 快速稳定)")
    print("  2. GPU加速模式 (GPU解码+CPU编码)")
    print("  3. AI增强模式 (最强去重)")
    print("  4. 自定义模式")
    
    choice = input("请选择模式 (1/2/3/4): ").strip()
    
    config = {'use_gpu': False}
    
    if choice == '1':
        print("使用纯 CPU 标准模式")
    
    elif choice == '2':
        if GPU_AVAILABLE:
            config['use_gpu'] = True
            print("启用 GPU 加速模式")
        else:
            print("GPU 不可用，使用纯 CPU 模式")
    
    elif choice == '3':
        config['use_gpu'] = GPU_AVAILABLE
        
        if AI_MODELS['dain']:
            config['use_dain'] = True
            print("  ✓ DAIN 帧插值")
        elif AI_MODELS['rife']:
            config['use_rife'] = True
            print("  ✓ RIFE 帧插值")
        
        if config['use_gpu']:
            print("  ✓ GPU 加速")
        
        print("启用最强去重模式")
    
    elif choice == '4':
        print("\n自定义处理选项:")
        
        if GPU_AVAILABLE:
            choice = input("  [GPU] 是否启用GPU加速? (y/n): ").strip().lower()
            config['use_gpu'] = choice == 'y'
        
        if AI_MODELS['dain']:
            choice = input("  [DAIN] 是否启用帧插值? (y/n): ").strip().lower()
            config['use_dain'] = choice == 'y'
        
        if AI_MODELS['rife'] and not config.get('use_dain'):
            choice = input("  [RIFE] 是否启用帧插值? (y/n): ").strip().lower()
            config['use_rife'] = choice == 'y'
    
    else:
        print("无效选择，使用标准模式")
    
    # 显示配置摘要
    print("\n📋 处理配置:")
    if config.get('use_gpu'):
        print("  ✓ GPU 加速 (解码)")
    if config.get('use_dain'):
        print("  ✓ DAIN 帧插值")
    if config.get('use_rife'):
        print("  ✓ RIFE 帧插值")
    if not any([config.get('use_gpu'), config.get('use_dain'), config.get('use_rife')]):
        print("  纯 CPU 标准模式")
    
    batch_process(input_dir, config)

if __name__ == "__main__":
    main()
