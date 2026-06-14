import subprocess
import os
import random
import time

def find_local_ffmpeg():
    """查找本地FFmpeg可执行文件"""
    base_dir = os.path.dirname(__file__)

    known_ffmpeg_paths = [
        os.path.join(base_dir, 'ffmpeg-2026-06-08-git-6028720d70-full_build', 'ffmpeg-2026-06-08-git-6028720d70-full_build', 'bin', 'ffmpeg.exe'),
        os.path.join(base_dir, 'ffmpeg-2026-06-08-git-6028720d70-full_build', 'bin', 'ffmpeg.exe'),
        os.path.join(base_dir, 'bin', 'ffmpeg.exe'),
        os.path.join(base_dir, 'ffmpeg.exe'),
    ]

    for path in known_ffmpeg_paths:
        if os.path.exists(path):
            print(f"  找到FFmpeg: {path}")
            return path

    print("  警告：未找到本地FFmpeg，将使用系统PATH中的ffmpeg")
    return 'ffmpeg'

class VideoProcessor:
    def __init__(self, input_path, output_path, config):
        self.input_path = input_path
        self.output_path = output_path
        self.config = config
        self.ffmpeg_cmd = []
        self.ffmpeg_path = find_local_ffmpeg()
        # 使用实例级随机数生成器，避免污染全局 random 模块
        self.seed = random.randint(0, 999999)
        self._rng = random.Random(self.seed)
        print(f"  随机种子: {self.seed}")

    def get_video_info(self):
        """获取视频基本信息"""
        ffprobe_path = self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')
        cmd = [ffprobe_path, '-v', 'error',
               '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate,duration',
               '-of', 'csv=p=0', self.input_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                data = result.stdout.strip().split(',')
                if len(data) >= 4:
                    # 安全解析帧率（避免 eval()）
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

    def generate_segment_filter(self, segment_index, total_segments, duration, start_time, end_time):
        """为每个片段生成随机滤镜（安全参数，不影响观感）"""
        filters = []

        # 1. 随机变速（±2%，几乎无感）
        speed_factor = self._rng.uniform(0.98, 1.02)
        filters.append(f"setpts={1/speed_factor}*PTS")

        # 2. 随机亮度调整（±2%，肉眼不可见）
        brightness = self._rng.uniform(-0.02, 0.02)
        if abs(brightness) > 0.001:
            filters.append(f"eq=brightness={brightness:.4f}")

        # 3. 随机对比度调整（±3%，轻微感知）
        contrast = self._rng.uniform(0.97, 1.03)
        if abs(contrast - 1) > 0.001:
            filters.append(f"eq=contrast={contrast:.4f}")

        # 4. 随机饱和度调整（±5%，不影响观感）
        saturation = self._rng.uniform(0.95, 1.05)
        if abs(saturation - 1) > 0.001:
            filters.append(f"eq=saturation={saturation:.4f}")

        # 5. 随机色相调整（±3°，几乎无感）
        hue = self._rng.uniform(-3, 3)
        if abs(hue) > 0.1:
            filters.append(f"hue=h={hue:.2f}")

        # 6. 随机轻微模糊（极轻微，人眼几乎察觉不到）
        if self._rng.random() > 0.6:
            blur = self._rng.uniform(0.05, 0.15)
            filters.append(f"gblur=sigma={blur:.3f}")

        # 7. 随机锐化（极轻微）
        if self._rng.random() > 0.6:
            sharpen = self._rng.uniform(0.1, 0.25)
            filters.append(f"unsharp=luma_amount={sharpen:.3f}")

        # 8. 随机边缘增强（极轻微）
        if self._rng.random() > 0.7:
            edge = self._rng.uniform(0.1, 0.25)
            filters.append(f"unsharp=luma_amount={edge:.3f}:chroma_amount={edge/2:.3f}")

        return ','.join(filters), speed_factor

    def build_command(self):
        """构建FFmpeg命令（分段处理）"""
        video_info = self.get_video_info()
        duration = video_info['duration']
        orig_w, orig_h = video_info['width'], video_info['height']

        # 计算目标分辨率（保持9:16比例）
        target_w, target_h = orig_w, orig_h
        if (orig_w, orig_h) == (1080, 1920):
            target_w, target_h = 720, 1280
        elif (orig_w, orig_h) == (720, 1280):
            target_w, target_h = 1080, 1920
        else:
            target_w, target_h = 648, 1085

        # 动态缩放（1%~3%，几乎无感）
        scale_factor = 1 + self._rng.uniform(0.01, 0.03)
        target_w = int(target_w * scale_factor)
        target_h = int(target_h * scale_factor)
        target_w -= target_w % 2
        target_h -= target_h % 2
        print(f"  动态缩放: {scale_factor:.4f} -> {target_w}x{target_h}")

        # 增加分段数量（最多40段，最短8秒）
        min_segment_duration = 8
        max_segment_duration = 60
        min_possible_segments = max(3, int(duration / max_segment_duration))
        max_possible_segments = min(40, int(duration / min_segment_duration))
        num_segments = self._rng.randint(min_possible_segments, max_possible_segments)
        print(f"  分段处理: {num_segments} 段（随机时长）")

        # 生成随机分段点
        segment_points = [0.0]
        remaining_duration = duration
        for i in range(num_segments - 1):
            max_available = remaining_duration - (num_segments - i - 1) * min_segment_duration
            segment_duration = self._rng.uniform(min_segment_duration, min(max_segment_duration, max_available))
            segment_points.append(segment_points[-1] + segment_duration)
            remaining_duration -= segment_duration
        segment_points.append(duration)

        # 基础命令：FFmpeg路径 + 输入文件
        self.ffmpeg_cmd = [self.ffmpeg_path, '-i', self.input_path]

        # 构建复杂滤镜链
        complex_filter = []
        audio_filters = []
        speed_factors = []

        # 分割视频和音频流
        v_split = "[0:v]split={0}".format(num_segments) + "".join([f"[v{i}]" for i in range(num_segments)])
        a_split = "[0:a]asplit={0}".format(num_segments) + "".join([f"[a{i}]" for i in range(num_segments)])
        complex_filter.append(v_split)
        complex_filter.append(a_split)

        # 为每个片段生成不同的处理
        for i in range(num_segments):
            start_time = segment_points[i]
            end_time = segment_points[i + 1]
            segment_dur = end_time - start_time

            # 生成视频滤镜
            vf, speed_factor = self.generate_segment_filter(i, num_segments, duration, start_time, end_time)
            speed_factors.append(speed_factor)

            # 裁剪片段并应用滤镜
            complex_filter.append(f"[v{i}]trim=start={start_time:.2f}:end={end_time:.2f},setpts=PTS-STARTPTS,{vf}[v{i}out]")

            # 音频处理（与视频同步变速，不影响听感）
            audio_filters.append(f"[a{i}]atrim=start={start_time:.2f}:end={end_time:.2f},asetpts=PTS-STARTPTS,atempo={speed_factor:.4f}")

            # 音量调整（±3%，几乎无感）
            volume_factor = self._rng.uniform(0.97, 1.03)
            if abs(volume_factor - 1) > 0.001:
                audio_filters[-1] += f",volume={volume_factor:.4f}"

            # 变调处理（±0.5半音，几乎无感）
            if self._rng.random() > 0.5:
                pitch_shift = self._rng.uniform(-0.5, 0.5)
                if abs(pitch_shift) > 0.1:
                    pitch_factor = 2 ** (pitch_shift / 12)
                    audio_filters[-1] += f",asetrate=44100*{pitch_factor:.6f},atempo={1/pitch_factor:.6f},aresample=44100"

            # 添加轻微白噪音（新增）
            if self._rng.random() > 0.6:
                noise_vol = self._rng.uniform(0.005, 0.015)
                audio_filters[-1] += f",highpass=f=80,lowpass=f=15000,volume={noise_vol:.4f}"

            audio_filters[-1] += f"[a{i}out]"

            print(f"    段{i+1}: {start_time:.1f}s - {end_time:.1f}s ({segment_dur:.1f}s)")

        # 合并视频片段
        v_concat = ''.join([f"[v{i}out]" for i in range(num_segments)])
        complex_filter.append(f"{v_concat}concat=n={num_segments}:v=1:a=0[outv]")

        # 合并音频片段
        a_concat = ''.join([f"[a{i}out]" for i in range(num_segments)])
        audio_filters.append(f"{a_concat}concat=n={num_segments}:v=0:a=1[outa]")

        # 全局变换（微小调整，不影响观感）
        # 微小旋转（±0.2°）
        rotation = self._rng.uniform(-0.2, 0.2)
        # 轻微裁剪（边缘0.1%~0.3%）
        crop_pct = self._rng.uniform(0.997, 0.999)
        crop_w = int(target_w * crop_pct)
        crop_h = int(target_h * crop_pct)
        # 确保裁剪后居中
        crop_x = (target_w - crop_w) // 2
        crop_y = (target_h - crop_h) // 2

        # 先缩放，再裁剪，最后旋转（安全顺序）
        complex_filter.append(f"[outv]scale={target_w}:{target_h}[scaledv]")
        complex_filter.append(f"[scaledv]crop={crop_w}:{crop_h}:{crop_x}:{crop_y}[cropv]")
        # 旋转使用bilinear插值，确保质量
        complex_filter.append(f"[cropv]rotate={rotation:.3f}*PI/180:bilinear=1[finalv]")

        print(f"  全局变换: 缩放至{target_w}x{target_h}, 裁剪{(1-crop_pct)*100:.2f}%, 旋转{rotation:.2f}°")

        # 应用复杂滤镜
        all_filters = ';'.join(complex_filter + audio_filters)
        self.ffmpeg_cmd.extend(['-filter_complex', all_filters])

        # 映射输出
        self.ffmpeg_cmd.extend(['-map', '[finalv]', '-map', '[outa]'])

        # 编码参数（添加更多随机性）
        crf_value = self._rng.randint(22, 26)
        preset_values = ['fast', 'medium', 'slow']
        preset = preset_values[self._rng.randint(0, len(preset_values)-1)]

        self.ffmpeg_cmd.extend([
            '-c:v', 'libx264',
            '-crf', str(crf_value),
            '-preset', preset,
            '-c:a', 'aac',
            '-b:a', '192k',
            '-map_metadata', '-1',
            '-map_chapters', '-1',
            '-metadata', 'comment=含AI生成内容；可能使用AI技术制作；可能含有AI生成内容',
        ])

        # 输出路径
        self.ffmpeg_cmd.append(self.output_path)

    def run(self):
        """执行视频处理"""
        output_dir = os.path.dirname(self.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        self.build_command()
        print(f"\n执行命令: {' '.join(self.ffmpeg_cmd[:3])}...")

        try:
            result = subprocess.run(
                self.ffmpeg_cmd,
                stdout=subprocess.DEVNULL,
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
                if result.stderr:
                    try:
                        stderr_str = result.stderr.decode('utf-8', errors='ignore')
                    except:
                        stderr_str = result.stderr.decode('gbk', errors='ignore')
                    error_lines = stderr_str.strip().split('\n')[-5:]
                    print(f"  错误信息: {'\n'.join(error_lines)}")
            return False
        except subprocess.TimeoutExpired:
            print("✗ 处理超时")
            return False
        except FileNotFoundError:
            print("✗ 未找到FFmpeg")
            return False
        except Exception as e:
            print(f"✗ 处理异常: {str(e)}")
            return False
