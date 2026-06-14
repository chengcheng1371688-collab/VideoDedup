import os
import sys
import datetime
from pathlib import Path
from video_processor import VideoProcessor

# 检查AI模型是否可用
MODEL_DIR = Path(__file__).parent / "models"
AI_MODEL_AVAILABLE = False

def check_ai_model():
    """检查AI模型是否可用"""
    global AI_MODEL_AVAILABLE
    if MODEL_DIR.exists():
        for model_file in MODEL_DIR.glob("*.pth"):
            if model_file.stat().st_size > 1000000:  # 大于1MB
                AI_MODEL_AVAILABLE = True
                print(f"检测到AI模型: {model_file.name}")
                return True
    return False

# 自动检查AI模型
check_ai_model()

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
    print(f"输出目录: {output_dir}")
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
    filename = os.path.basename(input_path)
    name, ext = os.path.splitext(filename)
    output_path = os.path.join(output_dir, f"{name}_processed{ext}")
    
    processor = VideoProcessor(input_path, output_path, config)
    return processor.run()

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

def main():
    """主程序（自动进入批量处理模式）"""
    print("=== 视频去重处理工具 ===")
    
    # 显示AI支持状态
    if AI_MODEL_AVAILABLE:
        print("[AI增强模式] 可用 - 将提供更强的去重效果")
    else:
        print("[AI增强模式] 不可用 - 使用标准模式")
    print("自动进入批量处理模式...")
    
    # 检查是否有命令行参数传入目录路径
    if len(sys.argv) > 1:
        input_dir = sys.argv[1]
        print(f"使用命令行参数作为目录: {input_dir}")
    else:
        input_dir = input("请输入视频目录路径: ").strip()
    
    if not os.path.isdir(input_dir):
        print("无效的目录路径")
        return
    
    # 询问是否使用AI增强
    use_ai = False
    if AI_MODEL_AVAILABLE:
        choice = input("是否使用AI增强模式? (y/n): ").strip().lower()
        use_ai = choice == 'y'
        if use_ai:
            print("已启用AI增强模式")
    
    # 默认配置
    config = {
        'vertical_resolution': {'enabled': True},
        'frame_decimation': {'enabled': True},
        'use_ai': use_ai
    }
    
    batch_process(input_dir, config)

if __name__ == "__main__":
    main()
