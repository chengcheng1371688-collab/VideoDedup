"""
测试视频处理器基本功能
"""
import os
import sys

# 设置编码
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def test_processor():
    """测试处理器"""
    print("📊 测试视频处理器...")
    
    # 导入处理器
    from video_processor_hybrid import VideoProcessor, GPU_AVAILABLE
    
    print(f"GPU可用: {GPU_AVAILABLE}")
    
    # 检查是否有测试视频
    test_video = None
    video_extensions = ('.mp4', '.mov', '.avi', '.mkv')
    
    for filename in os.listdir('.'):
        if filename.lower().endswith(video_extensions):
            test_video = filename
            break
    
    if test_video is None:
        print("❌ 未找到测试视频")
        return
    
    print(f"测试视频: {test_video}")
    
    # 创建处理器
    config = {'use_gpu': GPU_AVAILABLE}
    processor = VideoProcessor(test_video, 'test_output.mp4', config)
    
    # 构建命令
    processor.build_command()
    
    # 打印命令（不执行）
    print("\n构建的FFmpeg命令:")
    print("-" * 80)
    print(' '.join(processor.ffmpeg_cmd[:50]))  # 只显示前50个参数
    if len(processor.ffmpeg_cmd) > 50:
        print(f"... (共 {len(processor.ffmpeg_cmd)} 个参数)")
    print("-" * 80)
    
    print("\n✅ 处理器构建成功!")

if __name__ == "__main__":
    test_processor()
