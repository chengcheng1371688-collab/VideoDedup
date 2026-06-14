"""
增强版视频处理器（集成 GPU+CPU 协同工作）
支持: GPU解码 + GPU滤镜 + CPU编码
"""
import subprocess
import os
import random
import time
import sys

# 设置编码
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# GPU 状态检测
GPU_AVAILABLE = False
GPU_TYPE = None
CUDA_AVAILABLE = False

def detect_gpu():
    """检测 GPU 可用性"""
    global GPU_AVAILABLE, GPU_TYPE, CUDA_AVAILABLE
    
    try:
        # 尝试加载 CUDA
        import ctypes
        try:
            nvcuda = ctypes.WinDLL('nvcuda.dll', mode=ctypes.RTLD_GLOBAL)
            CUDA_AVAILABLE = True
            GPU_TYPE = 'NVIDIA'
            GPU_AVAILABLE = True
            print("  [GPU] NVIDIA CUDA 可用")
        except:
            pass
    except:
        pass

def find_best_ffmpeg():
    """查找最佳 FFmpeg（优先使用 Waifu2x 中的版本）"""
    base_dir = os.path.dirname(__file__)
    
    # 优先使用 Waifu2x-Extension-GUI 中的 FFmpeg（通常支持 CUDA）
    waifu2x_paths = [
        os.path.join(base_dir, '完整包138', 'Waifu2x-Extension-GUI-v3.138.01-Win64', 'waifu2x-extension-gui', 'ffmpeg_waifu2xEX.exe'),
        os.path.join(base_dir, 'Waifu2x-Extension-GUI-v3.138.01-Win64', 'waifu2x-extension-gui', 'ffmpeg_waifu2xEX.exe'),
    ]
    
    for path in waifu2x_paths:
        if os.path.exists(path):
            print(f"  [GPU] 使用 Waifu2x FFmpeg: {os.path.basename(path)}")
            return path
    
    # 回退到标准 FFmpeg
    known_paths = [
        os.path.join(base_dir, 'ffmpeg-2026-06-08-git-6028720d70-full_build', 'ffmpeg-2026-06-08-git-6028720d70-full_build', 'bin', 'ffmpeg.exe'),
        os.path.join(base_dir, 'ffmpeg-2026-06-08-git-6028720d70-full_build', 'bin', 'ffmpeg.exe'),
        os.path.join(base_dir, 'bin', 'ffmpeg.exe'),
        os.path.join(base_dir, 'ffmpeg.exe'),
    ]
    
    for path in known_paths:
        if os.path.exists(path):
            print(f"  找到FFmpeg: {path}")
            return path
    
    print("  警告：未找到本地FFmpeg，将使用系统PATH中的ffmpeg")
    return 'ffmpeg'

# 初始化 GPU 检测
detect_gpu()

class VideoProcessor:
    def __init__(self, input_path, output_path, config):
        self.input_path = input_path
        self.output_path = output_path
        self.config = config
        self.ffmpeg_cmd = []
        self.ffmpeg_path = find_best_ffmpeg()
        self.use_gpu = GPU_AVAILABLE and config.get('use_gpu', True)
        self.seed = random.randint(0, 999999)
        random.seed(self.seed)
        print(f"  随机种子: {self.seed}")
        print(f"  GPU加速: {'启用' if self.use_gpu else '禁用'}")
        
    def get_video_info(self):
        """获取视频基本信息"""
        ffprobe_path = self.ffmpeg_path.replace('ffmpeg_waifu2xEX.exe', 'ffprobe_waifu2xEX.exe')
        if not os.path.exists(ffprobe_path):
            ffprobe_path = self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')
        if not os.path.exists(ffprobe_path):
            ffprobe_path = 'ffprobe'
        
        cmd = [ffprobe_path, '-v', 'error', 
               '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate,duration',
               '-of', 'csv=p=0', self.input_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                data = result.stdout.strip().split(',')
                if len(data) >= 4:
                    fps_str = data[2]
                    if '/' in fps_str:
                        num, den = map(int, fps_str.split('/'))
                        fps = num / den if den != 0 else 30.0
                    else:
                        fps = float(fps_str)
                    return {
                        'width': int(data[0]),
                        'height': int(data[1]),
                        'fps': fps,
                        'duration': float(data[3])
                    }
        except:
            pass
        return {'width': 1080, 'height': 1920, 'fps': 30, 'duration': 60}
    
    def generate_segment_filter(self, segment_index, total_segments, duration, start_time, end_time, base_w, base_h):
        """为每个片段生成随机滤镜（安全参数，不影响观感）"""
        filters = []
        
        # 1. 随机变速（±2%，几乎无感）
        speed_factor = random.uniform(0.98, 1.02)
        filters.append(f"setpts={1/speed_factor}*PTS")
        
        # 2. 统一缩放到目标尺寸(不随机缩放,避免concat因crop参数不同而失败)
        filters.append(f"scale={base_w}:{base_h}")
        segment_scale = 1  # 不再随机缩放
        
        # 3. 合并eq参数
        eq_params = []
        brightness = random.uniform(-0.02, 0.02)
        if abs(brightness) > 0.0005:
            eq_params.append(f"brightness={brightness:.4f}")
        contrast = random.uniform(0.97, 1.03)
        if abs(contrast - 1) > 0.0005:
            eq_params.append(f"contrast={contrast:.4f}")
        saturation = random.uniform(0.95, 1.05)
        if abs(saturation - 1) > 0.0005:
            eq_params.append(f"saturation={saturation:.4f}")
        if eq_params:
            filters.append(f"eq={':'.join(eq_params)}")
        
        # 6. 随机色相调整（±3°，几乎无感）
        hue = random.uniform(-3, 3)
        if abs(hue) > 0.1:
            filters.append(f"hue=h={hue:.2f}")
        
        # 7. 随机轻微模糊（极轻微，人眼几乎察觉不到）
        if random.random() > 0.6:
            blur = random.uniform(0.05, 0.15)
            filters.append(f"gblur=sigma={blur:.3f}")
        
        # 8. 随机锐化（极轻微）
        if random.random() > 0.6:
            sharpen = random.uniform(0.1, 0.25)
            filters.append(f"unsharp=luma_amount={sharpen:.3f}")
        
        # 9. 随机边缘增强（极轻微）
        if random.random() > 0.7:
            edge = random.uniform(0.1, 0.25)
            filters.append(f"unsharp=luma_amount={edge:.3f}:chroma_amount={edge/2:.3f}")
        
        return ','.join(filters), speed_factor, segment_scale
    
    def build_command(self):
        """构建FFmpeg命令（GPU+CPU协同）
        
        处理流程：
        ┌─────────────────────────────────────────────────────────┐
        │  阶段1: 解码 (GPU CUDA 硬件解码)                        │
        │  阶段2: 格式转换 (GPU → CPU: hwdownload)               │
        │  阶段3: 滤镜处理 (CPU: 分段、缩放、亮度、对比度等)       │
        │  阶段4: 编码 (GPU NVENC 硬件编码)                       │
        └─────────────────────────────────────────────────────────┘
        """
        video_info = self.get_video_info()
        duration = video_info['duration']
        orig_w, orig_h = video_info['width'], video_info['height']
        orig_fps = video_info['fps']
        
        # ========== 计算目标分辨率 ==========
        target_w, target_h = orig_w, orig_h
        if (orig_w, orig_h) == (1080, 1920):
            target_w, target_h = 720, 1280
        elif (orig_w, orig_h) == (720, 1280):
            target_w, target_h = 1080, 1920
        else:
            target_w, target_h = 648, 1085
        
        print(f"  分辨率: {orig_w}x{orig_h} -> {target_w}x{target_h}")
        
        # ========== 帧率调整 ==========
        fps_factor = random.uniform(0.90, 1.10)
        target_fps = round(orig_fps * fps_factor)
        if target_fps < 23:
            target_fps = 23
        if target_fps > 62:
            target_fps = 62
        print(f"  帧率调整: {orig_fps:.1f}fps -> {target_fps}fps")
        
        # ========== 分段处理 ==========
        min_segment_duration = 8
        max_segment_duration = 60
        min_possible_segments = max(3, int(duration / max_segment_duration))
        max_possible_segments = min(40, int(duration / min_segment_duration))
        num_segments = random.randint(min_possible_segments, max_possible_segments)
        print(f"  分段处理: {num_segments} 段（随机时长）")
        
        # 生成随机分段点
        segment_points = [0.0]
        remaining_duration = duration
        for i in range(num_segments - 1):
            max_available = remaining_duration - (num_segments - i - 1) * min_segment_duration
            segment_duration = random.uniform(min_segment_duration, min(max_segment_duration, max_available))
            segment_points.append(segment_points[-1] + segment_duration)
            remaining_duration -= segment_duration
        segment_points.append(duration)
        
        # ========== 阶段1: 基础命令 + GPU解码 ==========
        self.ffmpeg_cmd = [self.ffmpeg_path]
        
        if self.use_gpu:
            # [GPU] 阶段1: CUDA 硬件解码
            self.ffmpeg_cmd.extend(['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda'])
            print("\n  ╔════════════════════════════════════════╗")
            print("  ║  [GPU] 阶段1: CUDA 硬件解码           ║")
            print("  ╚════════════════════════════════════════╝")
        else:
            print("\n  ╔════════════════════════════════════════╗")
            print("  ║  [CPU] 阶段1: 软件解码                ║")
            print("  ╚════════════════════════════════════════╝")
        
        self.ffmpeg_cmd.extend(['-i', self.input_path])
        
        # ========== 阶段2+3: 滤镜链构建 ==========
        print("\n  ╔════════════════════════════════════════╗")
        print("  ║  [CPU] 阶段2+3: 滤镜处理              ║")
        print("  ╚════════════════════════════════════════╝")
        
        complex_filter = []
        audio_filters = []
        speed_factors = []
        
        # 分割流
        v_split = "[0:v]split={0}".format(num_segments) + "".join([f"[v{i}]" for i in range(num_segments)])
        a_split = "[0:a]asplit={0}".format(num_segments) + "".join([f"[a{i}]" for i in range(num_segments)])
        complex_filter.append(v_split)
        complex_filter.append(a_split)
        
        # 为每个片段生成处理
        for i in range(num_segments):
            start_time = segment_points[i]
            end_time = segment_points[i + 1]
            segment_dur = end_time - start_time
            
            # 每段独立生成滤镜，包含独立缩放
            vf, speed_factor, segment_scale = self.generate_segment_filter(i, num_segments, duration, start_time, end_time, target_w, target_h)
            speed_factors.append(speed_factor)
            
            # 使用秒数格式，精确到2位小数
            start_str = f"{start_time:.2f}"
            end_str = f"{end_time:.2f}"
            
            if self.use_gpu:
                # [GPU→CPU] 阶段2: 格式转换
                # GPU解码后的数据需要下载到CPU才能使用CPU滤镜
                complex_filter.append(f"[v{i}]hwdownload,format=nv12[cpu{i}]")
                # [CPU] 阶段3: 滤镜处理
                complex_filter.append(f"[cpu{i}]trim=start={start_str}:end={end_str},setpts=PTS-STARTPTS,{vf}[v{i}out]")
            else:
                # [CPU] 纯CPU模式
                complex_filter.append(f"[v{i}]trim=start={start_str}:end={end_str},setpts=PTS-STARTPTS,{vf}[v{i}out]")
            
            # 音频处理（不影响听感）
            audio_filters.append(f"[a{i}]atrim=start={start_str}:end={end_str},asetpts=PTS-STARTPTS,atempo={speed_factor:.6f}")
            
            # 音量调整（±3%，几乎无感）
            volume_factor = random.uniform(0.97, 1.03)
            if abs(volume_factor - 1) > 0.001:
                audio_filters[-1] += f",volume={volume_factor:.4f}"
            
            # 变调处理（±0.5半音，几乎无感）
            if random.random() > 0.5:
                pitch_shift = random.uniform(-0.5, 0.5)
                if abs(pitch_shift) > 0.1:
                    pitch_factor = 2 ** (pitch_shift / 12)
                    audio_filters[-1] += f",asetrate=44100*{pitch_factor:.6f},atempo={1/pitch_factor:.6f},aresample=44100"
            
            if random.random() > 0.6:
                audio_filters[-1] += f",highpass=f=80,lowpass=f=15000"
            
            audio_filters[-1] += f"[a{i}out]"
            
            print(f"    段{i+1}: {start_time:.1f}s - {end_time:.1f}s ({segment_dur:.1f}s), 缩放:{segment_scale:.3f}")
        
        # 合并片段
        v_concat = ''.join([f"[v{i}out]" for i in range(num_segments)])
        complex_filter.append(f"{v_concat}concat=n={num_segments}:v=1:a=0[outv]")
        
        a_concat = ''.join([f"[a{i}out]" for i in range(num_segments)])
        audio_filters.append(f"{a_concat}concat=n={num_segments}:v=0:a=1[outa]")
        
        # 全局变换: 随机缩放+旋转, 最终输出target_w x target_h
        rotation = random.uniform(-0.2, 0.2)
        zoom_factor = 1 + random.uniform(0.01, 0.03)
        zoom_w = int(target_w * zoom_factor)
        zoom_h = int(target_h * zoom_factor)
        zoom_w -= zoom_w % 2
        zoom_h -= zoom_h % 2
        crop_x = (zoom_w - target_w) // 2
        crop_y = (zoom_h - target_h) // 2
        
        # [CPU] 全局变换
        complex_filter.append(f"[outv]scale={zoom_w}:{zoom_h},crop={target_w}:{target_h}:{crop_x}:{crop_y},rotate={rotation:.3f}*PI/180:bilinear=1[finalv]")
        
        print(f"  全局变换: 缩放{zoom_factor:.3f}, 旋转{rotation:.2f}°")
        
        # 应用滤镜
        all_filters = ';'.join(complex_filter + audio_filters)
        self.ffmpeg_cmd.extend(['-filter_complex', all_filters])
        self.ffmpeg_cmd.extend(['-map', '[finalv]', '-map', '[outa]'])
        
        # 设置输出帧率（确保帧率改变生效）
        self.ffmpeg_cmd.extend(['-r', str(target_fps)])
        
        # ========== 阶段4: 编码 ==========
        crf_value = random.randint(22, 26)
        
        if self.use_gpu:
            # [GPU] 阶段4: NVENC 硬件编码
            print("\n  ╔════════════════════════════════════════╗")
            print("  ║  [GPU] 阶段4: NVENC 硬件编码          ║")
            print("  ╚════════════════════════════════════════╝")
            
            encode_params = [
                '-c:v', 'h264_nvenc',
                '-preset', 'p4',
                '-tune', 'hq',
                '-rc', 'vbr',
                '-cq', str(crf_value),
                '-b:v', '0',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-ac', '2',
                '-ar', '44100',
            ]
        else:
            # [CPU] 阶段4: 软件编码
            print("\n  ╔════════════════════════════════════════╗")
            print("  ║  [CPU] 阶段4: libx264 软件编码        ║")
            print("  ╚════════════════════════════════════════╝")
            
            preset_values = ['medium', 'slow']
            preset = preset_values[random.randint(0, len(preset_values)-1)]
            
            encode_params = [
                '-c:v', 'libx264',
                '-crf', str(crf_value),
                '-preset', preset,
                '-tune', 'fastdecode',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-ac', '2',
                '-ar', '44100',
            ]
        
        # 元数据处理
        encode_params.extend([
            '-map_metadata', '-1',
            '-map_chapters', '-1',
            '-metadata', 'comment=含AI生成内容；可能使用AI技术制作；可能含有AI生成内容',
            '-y',
        ])
        
        self.ffmpeg_cmd.extend(encode_params)
        self.ffmpeg_cmd.append(self.output_path)
    
    def run(self):
        """执行视频处理"""
        output_dir = os.path.dirname(self.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        self.build_command()
        
        # 打印完整命令用于调试
        cmd_str = ' '.join(self.ffmpeg_cmd)
        print(f"\n执行命令: {cmd_str[:200]}..." if len(cmd_str) > 200 else f"\n执行命令: {cmd_str}")
        
        try:
            result = subprocess.run(
                self.ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                timeout=600,
                shell=False
            )
            
            if result.returncode == 0:
                print(f"✓ 处理成功: {self.output_path}")
                return True
            else:
                print(f"✗ 处理失败 (返回码: {result.returncode})")
                
                # 打印完整错误信息
                if result.stderr:
                    try:
                        stderr_str = result.stderr.decode('utf-8', errors='ignore')
                    except:
                        stderr_str = result.stderr.decode('gbk', errors='ignore')
                    print(f"\n=== FFmpeg 错误输出 ===")
                    print(stderr_str)
                    print("=====================")
                
                # GPU模式失败，尝试纯CPU模式
                if self.use_gpu:
                    print("  [回退] GPU处理失败，尝试纯CPU模式")
                    self.use_gpu = False
                    return self.run()
                    
            return False
        except subprocess.TimeoutExpired:
            print("✗ 处理超时")
            return False
        except FileNotFoundError:
            print(f"✗ 未找到FFmpeg: {self.ffmpeg_path}")
            return False
        except Exception as e:
            print(f"✗ 处理异常: {str(e)}")
            import traceback
            print(f"  详细错误: {traceback.format_exc()}")
            return False
