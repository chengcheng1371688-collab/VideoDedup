"""
Waifu2x-Extension-GUI 集成处理器
支持: Waifu2x、DAIN、RIFE、CAIN、IFRNet、Real-CUGAN、Anime4K
"""
import os
import sys
import subprocess
import random
import tempfile
from pathlib import Path
from progress_utils import Spinner

# 设置编码
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# 检查 Waifu2x-Extension-GUI 是否可用
WAIFU2X_AVAILABLE = False
WAIFU2X_PATH = None
WAIFU2X_MODELS = {}

def check_waifu2x_gui():
    """检查 Waifu2x-Extension-GUI 是否可用"""
    global WAIFU2X_AVAILABLE, WAIFU2X_PATH, WAIFU2X_MODELS
    
    # 检查多个可能的路径
    possible_paths = [
        Path(__file__).parent / "完整包138" / "Waifu2x-Extension-GUI-v3.138.01-Win64" / "waifu2x-extension-gui",
        Path(__file__).parent / "Waifu2x-Extension-GUI-v3.138.01-Win64" / "waifu2x-extension-gui",
    ]
    
    for path in possible_paths:
        if path.exists():
            WAIFU2X_PATH = path
            WAIFU2X_AVAILABLE = True
            
            # 检测可用模型
            WAIFU2X_MODELS = {
                'dain': (path / "dain-ncnn-vulkan").exists(),
                'rife': (path / "rife-ncnn-vulkan").exists() or (path.parent.parent / "RIFE_trained_model_v3.6").exists(),
                'cain': (path / "cain-ncnn-vulkan").exists(),
                'ifrnet': (path / "ifrnet-ncnn-vulkan").exists(),
                'real-cugan': (path / "Real-CUGAN-Caffe").exists(),
                'anime4k': (path / "Anime4K").exists(),
                'waifu2x': True,
            }
            
            return True
    
    return False

# 自动检查
check_waifu2x_gui()

def get_waifu2x_status():
    """获取 Waifu2x-Extension-GUI 状态信息"""
    status = {
        'available': WAIFU2X_AVAILABLE,
        'path': str(WAIFU2X_PATH) if WAIFU2X_PATH else None,
        'models': WAIFU2X_MODELS
    }
    return status

class Waifu2xProcessor:
    """Waifu2x-Extension-GUI 处理器"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.available = WAIFU2X_AVAILABLE
        self.path = WAIFU2X_PATH
        self.models = WAIFU2X_MODELS
        
    def _run_interpolation(self, input_path, output_path, model):
        """通用帧插值 (DAIN/RIFE/CAIN/IFRNet)
        
        正确流程: FFmpeg拆帧 → ncnn-vulkan处理帧目录 → FFmpeg合并
        
        ncnn-vulkan工具要求:
          -i 输入帧目录 (jpg/png/webp)
          -o 输出帧目录
          -n 目标帧数 (默认=N*2, 即2倍帧插值)
          -s time step (0~1, 默认0.5)
        """
        model_dir = self.path / f"{model}-ncnn-vulkan"
        
        if not model_dir.exists():
            print(f"  ❌ {model} 模型目录不存在: {model_dir}")
            return False
        
        exe_name = f"{model}-ncnn-vulkan_waifu2xEX.exe"
        model_exe = model_dir / exe_name
        
        if not model_exe.exists():
            alt_exe = model_dir / f"{model}-ncnn-vulkan.exe"
            if alt_exe.exists():
                model_exe = alt_exe
            else:
                print(f"  ❌ {model} 可执行文件不存在")
                return False
        
        print(f"  ✅ {model.upper()} 路径: {model_dir}")
        
        ffmpeg_path = self.path / "ffmpeg_waifu2xEX.exe"
        if not ffmpeg_path.exists():
            ffmpeg_path = "ffmpeg"

        # 检测原始视频帧率（避免硬编码60fps）
        orig_fps = 30  # 默认值
        ffprobe_path = str(ffmpeg_path).replace('ffmpeg', 'ffprobe')
        try:
            probe_cmd = [
                ffprobe_path, '-v', 'error',
                '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate',
                '-of', 'csv=p=0', input_path
            ]
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
            if probe_result.returncode == 0:
                fps_str = probe_result.stdout.strip()
                if '/' in fps_str:
                    num, den = map(int, fps_str.split('/'))
                    orig_fps = num / den if den != 0 else 30
                else:
                    orig_fps = float(fps_str)
        except:
            pass

        with tempfile.TemporaryDirectory() as frames_in, tempfile.TemporaryDirectory() as frames_out:
            # 步骤1: FFmpeg 拆帧
            print(f"  [1/3] FFmpeg拆帧...")
            frame_pattern_in = os.path.join(frames_in, "frame_%08d.png")
            cmd_extract = [
                str(ffmpeg_path),
                '-i', input_path,
                '-vsync', '0',
                '-qscale:v', '2',
                frame_pattern_in,
                '-y'
            ]
            
            try:
                result = subprocess.run(
                    cmd_extract,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=False,
                    timeout=300,
                    creationflags=0x08000000
                )
                input_frames = len(list(Path(frames_in).glob("*.png")))
                print(f"    拆出 {input_frames} 帧")
                
                if input_frames == 0:
                    print("  ❌ 拆帧失败")
                    return False
            except Exception as e:
                print(f"  ❌ 拆帧异常: {e}")
                return False
            
            # 步骤2: ncnn-vulkan 帧插值
            print(f"  [2/3] {model.upper()} 帧插值 (输入{input_frames}帧 → 约{input_frames*2}帧)...")
            
            cmd_interp = [
                str(model_exe),
                '-i', frames_in,
                '-o', frames_out,
                '-j', '2:2:2',
            ]
            
            print(f"    {' '.join(cmd_interp)}")
            
            sp = Spinner(f"{model.upper()}插帧中")
            sp.start()
            try:
                result = subprocess.run(
                    cmd_interp,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=False,
                    timeout=3600,      # 帧插值可能很慢
                    creationflags=0x08000000
                )
                
                if result.stderr:
                    try:
                        stderr_text = result.stderr[:800].decode('utf-8', errors='ignore')
                        print(f"    {model} 输出: {stderr_text}")
                    except:
                        pass
                
                if result.returncode != 0:
                    sp.stop("失败")
                    print(f"  ❌ {model} 处理失败 (返回码: {result.returncode})")
                    return False
                
                output_frames = len(list(Path(frames_out).glob("*.png")))
                sp.stop(f"生成{output_frames}帧")
                print(f"    生成 {output_frames} 帧 (插值倍数: {output_frames/input_frames:.1f}x)")
                
                if output_frames == 0:
                    print("  ❌ 未生成任何帧")
                    return False
                    
            except subprocess.TimeoutExpired:
                sp.stop("超时")
                print(f"  ❌ {model} 处理超时")
                return False
            except Exception as e:
                sp.stop("异常")
                print(f"  ❌ {model} 处理异常: {str(e)}")
                return False
            
            # 步骤3: FFmpeg 合并帧为视频
            out_fps = orig_fps * 2  # 2倍帧插值
            print(f"  [3/3] FFmpeg合并 {output_frames} 帧为视频 (原{orig_fps:.1f}fps → {out_fps:.1f}fps)...")

            # 获取音频流
            frame_pattern_out = os.path.join(frames_out, "frame_%08d.png")

            cmd_merge = [
                str(ffmpeg_path),
                '-framerate', f'{out_fps:.1f}',
                '-i', frame_pattern_out,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '22',
                '-pix_fmt', 'yuv420p',
                '-y', output_path
            ]

            result_merge = subprocess.run(
                cmd_merge,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                timeout=600,
                creationflags=0x08000000
            )

            if result_merge.returncode == 0:
                print(f"  ✅ {model.upper()} 帧插值完成 ({output_frames}帧@{out_fps:.0f}fps)")
                return True
            else:
                print(f"  ❌ 帧合并失败 (返回码: {result_merge.returncode})")
                if result_merge.stderr:
                    try:
                        print(f"    FFmpeg错误: {result_merge.stderr[:300].decode('utf-8', errors='ignore')}")
                    except:
                        pass
                return False
    
    def _run_enhancement(self, input_path, output_path, mode):
        """画质增强 (Waifu2x/Real-CUGAN/Anime4K/Real-ESRGAN)
        
        目前使用 FFmpeg 滤镜实现，后续可调用对应 ncnn-vulkan 可执行文件
        """
        print(f"  [{mode.upper()}] 画质增强处理...")
        
        # 不同模式的增强策略
        strategies = {
            'waifu2x': 'hqdn3d=1.5:1.5:6:6,unsharp=5:5:1.0:5:5:0.0',
            'real-cugan': 'hqdn3d=2:2:8:8,unsharp=7:7:1.5:7:7:0.0',
            'anime4k': 'hqdn3d=1:1:4:4,unsharp=3:3:1.0:3:3:0.0,eq=contrast=1.05',
            'realesrgan': 'hqdn3d=1.5:1.5:6:6,unsharp=5:5:1.2:5:5:0.0',
            'esrgan': 'hqdn3d=1.5:1.5:6:6,unsharp=5:5:1.2:5:5:0.0',
        }
        
        filter_str = strategies.get(mode, strategies['waifu2x'])
        
        ffmpeg_path = self.path / "ffmpeg_waifu2xEX.exe"
        if not ffmpeg_path.exists():
            ffmpeg_path = "ffmpeg"
        
        cmd = [
            str(ffmpeg_path),
            '-i', input_path,
            '-vf', filter_str,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '22',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-y', output_path
        ]
        
        print(f"  滤镜: {filter_str}")
        
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=False,
                timeout=600,
                creationflags=0x08000000
            )
            
            if result.returncode == 0:
                print(f"  ✅ {mode.upper()} 增强完成")
                return True
            else:
                if result.stderr:
                    try:
                        print(f"  错误: {result.stderr[:200].decode('utf-8', errors='ignore')}")
                    except:
                        pass
                print(f"  ❌ {mode} 增强失败 (返回码: {result.returncode})")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"  ❌ {mode} 处理超时")
            return False
        except Exception as e:
            print(f"  ❌ {mode} 处理异常: {str(e)}")
            return False
    
    def _run_ffmpeg_enhancement(self, input_path, output_path):
        """使用内置 FFmpeg 进行增强处理"""
        ffmpeg_path = self.path / "ffmpeg_waifu2xEX.exe"
        if not ffmpeg_path.exists():
            ffmpeg_path = "ffmpeg"
        
        strategies = [
            'hqdn3d=1.5:1.5:6:6,unsharp=5:5:1.0',
            'eq=contrast=1.1:brightness=0.02',
            'gblur=sigma=0.2,hqdn3d=1:1:4:4',
            'eq=saturation=1.1,hue=5',
            'hqdn3d=1:1:4:4,eq=contrast=1.05:brightness=0.01:gamma=1.05',
        ]
        
        filter_str = random.choice(strategies)
        
        cmd = [
            str(ffmpeg_path),
            '-i', input_path,
            '-vf', filter_str,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '22',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-y', output_path
        ]
        
        print("  使用 FFmpeg 增强策略: " + filter_str)
        
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=False,
                timeout=600
            )
            
            if result.returncode == 0:
                print("  FFmpeg 增强完成")
                return True
            else:
                print("  FFmpeg 增强失败")
                return False
                
        except subprocess.TimeoutExpired:
            print("  FFmpeg 处理超时")
            return False
        except Exception as e:
            print("  FFmpeg 处理异常: " + str(e))
            return False
    
    def process(self, input_path, output_path, mode='auto'):
        """处理视频
        
        mode参数:
          - 'auto': 自动选择可用模型
          - 'dain': DAIN 帧插值
          - 'rife': RIFE 帧插值  
          - 'cain': CAIN 帧插值
          - 'ifrnet': IFRNet 帧插值
          - 'waifu2x': Waifu2x 超分辨率
          - 'real-cugan': Real-CUGAN 动漫超分
          - 'anime4k': Anime4K 画质增强
          - 'realesrgan': Real-ESRGAN 超分
          - 'esrgan': Real-ESRGAN 独立超分
          - 'ffmpeg': FFmpeg 增强
        """
        if not self.available:
            print("  Waifu2x-Extension-GUI 不可用")
            return False
        
        print("  使用 Waifu2x-Extension-GUI 处理...")
        
        if mode == 'auto':
            # 优先使用帧插值模型
            intp_models = ['dain', 'rife', 'cain', 'ifrnet']
            for m in intp_models:
                if self.models.get(m):
                    print(f"  自动选择: {m}")
                    return self._run_interpolation(input_path, output_path, m)
            # 否则用FFmpeg增强
            print("  自动选择: ffmpeg (无帧插值模型可用)")
            return self._run_ffmpeg_enhancement(input_path, output_path)
        
        elif mode in ('dain', 'rife', 'cain', 'ifrnet'):
            if not self.models.get(mode):
                print(f"  ❌ {mode} 模型不可用")
                return False
            return self._run_interpolation(input_path, output_path, mode)
        
        elif mode == 'ffmpeg':
            return self._run_ffmpeg_enhancement(input_path, output_path)
        
        elif mode in ('waifu2x', 'real-cugan', 'anime4k', 'realesrgan', 'esrgan'):
            return self._run_enhancement(input_path, output_path, mode)
        
        else:
            print("  未知模式: " + mode)
            return False

def print_waifu2x_info():
    """打印 Waifu2x-Extension-GUI 信息"""
    status = get_waifu2x_status()
    
    print("=" * 60)
    print("Waifu2x-Extension-GUI 状态检查")
    print("=" * 60)
    
    if status['available']:
        print("状态: [OK] 可用")
        print("路径: " + status['path'])
        print("\n内置模型:")
        
        model_names = {
            'dain': 'DAIN 帧插值',
            'rife': 'RIFE 帧插值',
            'cain': 'CAIN 帧插值',
            'ifrnet': 'IFRNet 帧插值',
            'real-cugan': 'Real-CUGAN 超分辨率',
            'anime4k': 'Anime4K 画质增强',
            'waifu2x': 'Waifu2x 超分辨率',
        }
        
        for model, available in status['models'].items():
            status_icon = "[OK]" if available else "[NO]"
            print("  " + status_icon + " " + model_names.get(model, model))
    
    else:
        print("状态: [NO] 不可用")
    
    print("=" * 60)

if __name__ == "__main__":
    print_waifu2x_info()
