"""速度基准测试 - 模式1(CPU) 和 模式2(GPU)"""
import subprocess
import sys
import time
import os

BASE = "G:\\TRAE\\去重"
FFMPEG = os.path.join(BASE, "ffmpeg-2026-06-08-git-6028720d70-full_build", "ffmpeg-2026-06-08-git-6028720d70-full_build", "bin", "ffmpeg.exe")

os.chdir(BASE)

# 1. 检查FFmpeg能否运行
print("=" * 50)
print("1. 检查 FFmpeg")
print("=" * 50)
try:
    r = subprocess.run([FFMPEG, "-version"], capture_output=True, creationflags=0x08000000, timeout=10)
    print(f"FFmpeg 版本: {r.stdout[:200].decode('utf-8', errors='ignore')}")
except Exception as e:
    print(f"FFmpeg 失败: {e}")
    sys.exit(1)

# 2. 生成2分钟测试视频
print("\n" + "=" * 50)
print("2. 生成2分钟测试视频 (1080x1920, 30fps)")
print("=" * 50)
test_video = os.path.join(BASE, "benchmark_test_2min.mp4")
t0 = time.time()
cmd = [
    FFMPEG, "-y",
    "-f", "lavfi",
    "-i", "testsrc2=duration=120:size=1080x1920:rate=30",
    "-f", "lavfi",
    "-i", "sine=frequency=440:duration=120",
    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
    "-c:a", "aac", "-b:a", "64k",
    "-shortest", test_video
]
r = subprocess.run(cmd, capture_output=True, creationflags=0x08000000, timeout=60)
print(f"生成耗时: {time.time()-t0:.1f}s, 文件: {os.path.getsize(test_video)//1024}KB")

# 3. 速度测试
print("\n" + "=" * 50)
print("3. 速度基准测试")
print("=" * 50)

test_configs = {
    "模式1 (CPU)": {"use_gpu": False, "use_ai": False},
    "模式2 (GPU)": {"use_gpu": True, "use_ai": False},
}

for name, config in test_configs.items():
    print(f"\n--- {name} ---")
    
    output = os.path.join(BASE, f"benchmark_output_{name.replace(' ','_')}.mp4")
    
    # 动态导入脚本
    from video_processor_simple import VideoProcessor
    
    t0 = time.time()
    proc = VideoProcessor(test_video, output, config)
    ok = proc.run()
    elapsed = time.time() - t0
    
    size = os.path.getsize(output) // 1024 if os.path.exists(output) else 0
    status = "✓ 成功" if ok else "✗ 失败"
    
    print(f"  耗时: {elapsed:.1f}s ({elapsed/60:.1f}分钟)")
    print(f"  输出: {size}KB")
    print(f"  状态: {status}")
    print(f"  速度比: {120/elapsed:.1f}x (2分钟视频 / 处理耗时)")

print("\n" + "=" * 50)
print("测试完成")
print("=" * 50)