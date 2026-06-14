"""
测试简化版视频处理器
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def test_simple_processor():
    """测试简化版处理器"""
    print("📊 测试简化版视频处理器...")
    
    from video_processor_simple import VideoProcessor, GPU_AVAILABLE
    
    print(f"GPU可用: {GPU_AVAILABLE}")
    
    # 创建一个模拟的测试视频信息
    # 由于没有实际视频文件，我们直接检查命令构建
    print("\n测试命令构建...")
    
    # 创建一个虚拟处理器（使用不存在的文件，但只测试命令构建）
    config = {'use_gpu': GPU_AVAILABLE}
    processor = VideoProcessor('test.mp4', 'output.mp4', config)
    
    # 修改get_video_info方法返回预设值以便测试
    processor.get_video_info = lambda: {'width': 1080, 'height': 1920, 'fps': 30, 'duration': 60}
    
    # 构建命令
    processor.build_command()
    
    # 检查命令
    print(f"\n命令长度: {len(processor.ffmpeg_cmd)}")
    print("\n关键参数:")
    
    # 查找关键参数
    for i, arg in enumerate(processor.ffmpeg_cmd):
        if arg in ['-filter_complex', '-c:v', '-r', '-hwaccel']:
            print(f"  [{i}] {arg}")
            if i + 1 < len(processor.ffmpeg_cmd):
                if arg == '-filter_complex':
                    # 只显示滤镜的前200字符
                    filter_str = processor.ffmpeg_cmd[i + 1]
                    print(f"       滤镜长度: {len(filter_str)}")
                    # 检查是否有时间表达式
                    if 't=' in filter_str:
                        print("       ⚠️  检测到时间表达式")
                    else:
                        print("       ✅ 无时间表达式")
                else:
                    print(f"       {processor.ffmpeg_cmd[i + 1]}")
    
    print("\n✅ 简化版处理器测试通过!")

if __name__ == "__main__":
    test_simple_processor()
