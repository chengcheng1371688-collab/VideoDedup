"""
GPU加速与CPU协同处理器
实现 GPU 解码/滤镜 + CPU 编码的高效处理流程
"""
import os
import sys
import subprocess
import platform
from pathlib import Path

# 设置编码
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# GPU 状态
GPU_AVAILABLE = False
GPU_TYPE = None
CUDA_AVAILABLE = False
NVENC_AVAILABLE = False

def detect_gpu():
    """检测 GPU 信息"""
    global GPU_AVAILABLE, GPU_TYPE, CUDA_AVAILABLE, NVENC_AVAILABLE
    
    os_name = platform.system().lower()
    
    if os_name == 'windows':
        # Windows 检测
        try:
            import ctypes
            nvcuda = ctypes.WinDLL('nvcuda.dll', mode=ctypes.RTLD_GLOBAL)
            CUDA_AVAILABLE = True
            
            # 检查 NVIDIA 编码器
            result = subprocess.run(
                ['nvidia-smi', '-L'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and 'NVIDIA' in result.stdout:
                GPU_AVAILABLE = True
                GPU_TYPE = 'NVIDIA'
                
                # 检查 NVENC 支持
                result_nvenc = subprocess.run(
                    ['nvidia-smi', '--query-gpu=encode.type', '--format=csv'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if 'NVENC' in result_nvenc.stdout:
                    NVENC_AVAILABLE = True
                    
        except Exception as e:
            pass
    
    elif os_name == 'linux':
        # Linux 检测
        try:
            result = subprocess.run(
                ['nvidia-smi', '-L'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and 'NVIDIA' in result.stdout:
                GPU_AVAILABLE = True
                GPU_TYPE = 'NVIDIA'
                CUDA_AVAILABLE = True
                
                result_nvenc = subprocess.run(
                    ['nvidia-smi', '--query-gpu=encode.type', '--format=csv'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if 'NVENC' in result_nvenc.stdout:
                    NVENC_AVAILABLE = True
                    
        except Exception as e:
            pass

def get_gpu_status():
    """获取 GPU 状态信息"""
    return {
        'available': GPU_AVAILABLE,
        'type': GPU_TYPE,
        'cuda_available': CUDA_AVAILABLE,
        'nvenc_available': NVENC_AVAILABLE
    }

def find_ffmpeg_with_gpu():
    """查找支持 GPU 的 FFmpeg"""
    base_dir = os.path.dirname(__file__)
    
    # 优先使用 Waifu2x-Extension-GUI 中的 FFmpeg
    waifu2x_ffmpeg = Path(base_dir) / "完整包138" / "Waifu2x-Extension-GUI-v3.138.01-Win64" / "waifu2x-extension-gui" / "ffmpeg_waifu2xEX.exe"
    
    if waifu2x_ffmpeg.exists():
        return str(waifu2x_ffmpeg)
    
    # 检查其他位置
    known_paths = [
        os.path.join(base_dir, 'ffmpeg-2026-06-08-git-6028720d70-full_build', 'ffmpeg-2026-06-08-git-6028720d70-full_build', 'bin', 'ffmpeg.exe'),
        os.path.join(base_dir, 'ffmpeg-2026-06-08-git-6028720d70-full_build', 'bin', 'ffmpeg.exe'),
        os.path.join(base_dir, 'bin', 'ffmpeg.exe'),
        os.path.join(base_dir, 'ffmpeg.exe'),
    ]
    
    for path in known_paths:
        if os.path.exists(path):
            return path
    
    return 'ffmpeg'

class HybridProcessor:
    """CPU+GPU 混合处理器"""
    
    def __init__(self, use_gpu=True):
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.ffmpeg_path = find_ffmpeg_with_gpu()
        
    def _build_gpu_decode_command(self, input_path):
        """构建 GPU 解码命令"""
        cmd = [self.ffmpeg_path]
        
        if self.use_gpu and CUDA_AVAILABLE:
            cmd.extend(['-hwaccel', 'cuda'])
        
        cmd.extend(['-i', input_path])
        
        return cmd
    
    def _build_gpu_filter_command(self):
        """构建 GPU 滤镜命令"""
        filters = []
        
        if self.use_gpu:
            # GPU 滤镜
            filters.append('hwupload_cuda')
        
        return filters
    
    def _build_cpu_encode_command(self, output_path):
        """构建 CPU 编码命令"""
        cmd = []
        
        # 使用 CPU 进行高质量编码
        cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '22',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-y', output_path
        ])
        
        return cmd
    
    def process_with_hybrid(self, input_path, output_path, filters=None):
        """使用 CPU+GPU 混合处理"""
        print("  处理模式: " + ("GPU+CPU 混合模式" if self.use_gpu else "纯 CPU 模式"))
        
        cmd = []
        
        # 阶段1: GPU 解码
        cmd.extend(self._build_gpu_decode_command(input_path))
        
        # 阶段2: 滤镜处理
        filter_str = ''
        
        if filters:
            gpu_filters = []
            cpu_filters = []
            
            for f in filters:
                # 判断滤镜是在 GPU 还是 CPU 上运行
                # 简单规则：复杂滤镜在 GPU，精细调整在 CPU
                if any(keyword in f.lower() for keyword in ['scale', 'rotate', 'crop']):
                    gpu_filters.append(f)
                else:
                    cpu_filters.append(f)
            
            if self.use_gpu and gpu_filters:
                filter_str = ','.join(gpu_filters)
                
                if cpu_filters:
                    # GPU处理后下载到CPU继续处理
                    filter_str += ',hwdownload'
                    filter_str += ',' + ','.join(cpu_filters)
            else:
                filter_str = ','.join(filters)
        
        if filter_str:
            cmd.extend(['-vf', filter_str])
        
        # 阶段3: CPU 编码
        cmd.extend(self._build_cpu_encode_command(output_path))
        
        print("  执行命令: " + ' '.join(cmd[:10]) + ("..." if len(cmd) > 10 else ""))
        
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=False,
                timeout=600
            )
            
            if result.returncode == 0:
                print("  [OK] 处理完成")
                return True
            else:
                # GPU 失败时回退到纯 CPU 模式
                print("  [WARN] GPU 处理失败，尝试纯 CPU 模式")
                return self.process_with_cpu(input_path, output_path, filters)
                
        except subprocess.TimeoutExpired:
            print("  [WARN] 处理超时，尝试纯 CPU 模式")
            return self.process_with_cpu(input_path, output_path, filters)
        except Exception as e:
            print("  [WARN] GPU 处理异常: " + str(e))
            return self.process_with_cpu(input_path, output_path, filters)
    
    def process_with_cpu(self, input_path, output_path, filters=None):
        """使用纯 CPU 处理（回退模式）"""
        cmd = [self.ffmpeg_path, '-i', input_path]
        
        if filters:
            cmd.extend(['-vf', ','.join(filters)])
        
        cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-y', output_path
        ])
        
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=False,
                timeout=600
            )
            
            if result.returncode == 0:
                print("  [OK] CPU 处理完成")
                return True
            else:
                print("  [FAIL] CPU 处理失败")
                return False
                
        except Exception as e:
            print("  [FAIL] CPU 处理异常: " + str(e))
            return False
    
    def process(self, input_path, output_path, filters=None):
        """处理视频"""
        if self.use_gpu:
            return self.process_with_hybrid(input_path, output_path, filters)
        else:
            return self.process_with_cpu(input_path, output_path, filters)

def print_gpu_info():
    """打印 GPU 信息"""
    status = get_gpu_status()
    
    print("=" * 60)
    print("GPU 加速检测")
    print("=" * 60)
    
    if status['available']:
        print("GPU 状态: [OK] 可用")
        print("GPU 类型: " + status['type'])
        print("CUDA 支持: [OK]" if status['cuda_available'] else "CUDA 支持: [NO]")
        print("NVENC 支持: [OK]" if status['nvenc_available'] else "NVENC 支持: [NO]")
        print("\n处理策略: GPU 解码 + CPU 编码")
    else:
        print("GPU 状态: [NO] 不可用")
        print("处理策略: 纯 CPU 处理")
    
    print("=" * 60)

# 初始化检测
detect_gpu()

# 测试代码
if __name__ == "__main__":
    print_gpu_info()
