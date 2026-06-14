"""
调试视频处理器 - 详细检查每个步骤
"""
import os
import sys

# 设置编码
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def test_ffmpeg():
    """测试FFmpeg基本功能"""
    print("📊 测试FFmpeg...")
    
    # 查找FFmpeg
    from video_processor_hybrid import find_best_ffmpeg
    
    ffmpeg_path = find_best_ffmpeg()
    print(f"FFmpeg路径: {ffmpeg_path}")
    
    # 测试FFmpeg命令
    import subprocess
    cmd = [ffmpeg_path, '-version']
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines[:3]:
                print(f"  {line}")
            print("✅ FFmpeg正常工作")
        else:
            print(f"❌ FFmpeg错误: {result.stderr}")
    except Exception as e:
        print(f"❌ FFmpeg执行失败: {e}")

def test_video_info():
    """测试视频信息获取"""
    print("\n📊 测试视频信息获取...")
    
    # 查找视频文件
    video_extensions = ('.mp4', '.mov', '.avi', '.mkv')
    test_video = None
    
    for filename in os.listdir('.'):
        if filename.lower().endswith(video_extensions):
            test_video = filename
            break
    
    if test_video is None:
        print("❌ 未找到测试视频")
        return None
    
    print(f"测试视频: {test_video}")
    
    # 导入处理器
    from video_processor_hybrid import VideoProcessor
    
    # 创建处理器（不使用GPU进行测试）
    config = {'use_gpu': False}
    processor = VideoProcessor(test_video, 'test_output.mp4', config)
    
    # 获取视频信息
    video_info = processor.get_video_info()
    print(f"视频信息: {video_info}")
    
    return processor

def test_command_build():
    """测试命令构建"""
    print("\n📊 测试命令构建...")
    
    # 查找视频文件
    video_extensions = ('.mp4', '.mov', '.avi', '.mkv')
    test_video = None
    
    for filename in os.listdir('.'):
        if filename.lower().endswith(video_extensions):
            test_video = filename
            break
    
    if test_video is None:
        print("❌ 未找到测试视频")
        return
    
    # 导入处理器
    from video_processor_hybrid import VideoProcessor
    
    # 测试CPU模式
    print("\n--- CPU模式 ---")
    config = {'use_gpu': False}
    processor = VideoProcessor(test_video, 'test_output_cpu.mp4', config)
    processor.build_command()
    
    # 打印关键部分
    print(f"命令长度: {len(processor.ffmpeg_cmd)}")
    print("\n命令参数:")
    for i, arg in enumerate(processor.ffmpeg_cmd):
        if i < 10 or i > len(processor.ffmpeg_cmd) - 10:
            print(f"  [{i}] {arg}")
        elif i == 10:
            print("  ...")
    
    # 检查filter_complex
    try:
        filter_idx = processor.ffmpeg_cmd.index('-filter_complex')
        print(f"\nfilter_complex 位置: {filter_idx}")
        filter_value = processor.ffmpeg_cmd[filter_idx + 1]
        print(f"filter_complex 长度: {len(filter_value)}")
        # 检查是否有问题
        if 't=' in filter_value:
            print("⚠️  检测到时间表达式 t=")
        if 'sin(' in filter_value:
            print("⚠️  检测到 sin() 函数")
        print("✅ 命令构建成功")
    except ValueError:
        print("❌ 未找到 filter_complex")

if __name__ == "__main__":
    test_ffmpeg()
    test_video_info()
    test_command_build()
