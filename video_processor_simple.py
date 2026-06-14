"""
视频处理器 - GPU+CPU协同（已验证版本）
处理流程:
  [GPU] CUDA硬件解码 -> [CPU] 滤镜处理 -> [GPU] NVENC硬件编码
"""
import subprocess
import os
import random
import time
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

GPU_AVAILABLE = False

def detect_gpu():
    global GPU_AVAILABLE
    try:
        import ctypes
        ctypes.WinDLL('nvcuda.dll', mode=ctypes.RTLD_GLOBAL)
        GPU_AVAILABLE = True
    except:
        pass

def find_best_ffmpeg():
    base_dir = os.path.dirname(__file__)
    waifu2x_paths = [
        os.path.join(base_dir, '完整包138', 'Waifu2x-Extension-GUI-v3.138.01-Win64', 'waifu2x-extension-gui', 'ffmpeg_waifu2xEX.exe'),
        os.path.join(base_dir, 'Waifu2x-Extension-GUI-v3.138.01-Win64', 'waifu2x-extension-gui', 'ffmpeg_waifu2xEX.exe'),
    ]
    for path in waifu2x_paths:
        if os.path.exists(path):
            return path
    return 'ffmpeg'

detect_gpu()

class VideoProcessor:
    def __init__(self, input_path, output_path, config):
        self.input_path = input_path
        self.output_path = output_path
        self.config = config
        self.ffmpeg_cmd = []
        self.ffmpeg_path = find_best_ffmpeg()
        self.use_gpu = GPU_AVAILABLE and config.get('use_gpu', True)
        self.aggressive = config.get('aggressive', False)  # 模式5/6强化模式
        self.mode6 = config.get('mode6', False)            # 模式6额外音频微调
        random.seed(random.randint(0, 999999))
    
    def get_video_info(self):
        # 智能匹配 ffprobe: 先试 waifu2x 自带版本，再试标准命名，最后用系统 PATH
        ffprobe_path = self.ffmpeg_path.replace('ffmpeg_waifu2xEX.exe', 'ffprobe_waifu2xEX.exe')
        if not os.path.exists(ffprobe_path):
            ffprobe_path = self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')
        if not os.path.exists(ffprobe_path):
            ffprobe_path = 'ffprobe'
        cmd = [ffprobe_path, '-v', 'error',
               '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate,duration',
               '-of', 'csv=p=0', self.input_path]
        dur_fallback = False  # 标记是否使用了不可信的回退值
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                data = result.stdout.strip().split(',')
                if len(data) >= 4:
                    w, h = int(data[0]), int(data[1])
                    num, den = map(int, data[2].split('/'))
                    fps = num / den if den != 0 else 30
                    dur = float(data[3])
                    return {'width': w, 'height': h, 'fps': fps, 'duration': dur, '_ok': True}
                # stream duration 缺失，尝试容器级 duration
                if len(data) >= 3:
                    w, h = int(data[0]), int(data[1])
                    num, den = map(int, data[2].split('/'))
                    fps = num / den if den != 0 else 30
                    try:
                        r2 = subprocess.run(
                            [ffprobe_path, '-v', 'error', '-show_entries', 'format=duration',
                             '-of', 'csv=p=0', self.input_path],
                            capture_output=True, text=True, timeout=10)
                        if r2.returncode == 0 and r2.stdout.strip():
                            dur = float(r2.stdout.strip())
                            return {'width': w, 'height': h, 'fps': fps, 'duration': dur, '_ok': True}
                    except:
                        pass
                    dur_fallback = True
        except:
            pass

        # 回退值：force _ok=False 以触发 build_command 的 num_seg=1 保护
        info = {'width': 1080, 'height': 1920, 'fps': 30, 'duration': 60, '_ok': not dur_fallback}
        return info

    def _has_audio(self):
        ffprobe_path = self.ffmpeg_path.replace('ffmpeg_waifu2xEX.exe', 'ffprobe_waifu2xEX.exe')
        if not os.path.exists(ffprobe_path):
            ffprobe_path = self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')
        if not os.path.exists(ffprobe_path):
            ffprobe_path = 'ffprobe'
        cmd = [ffprobe_path, '-v', 'error', '-select_streams', 'a:0',
               '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', self.input_path]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return r.returncode == 0 and r.stdout.strip() != ''
        except:
            return False

    def generate_segment_filter(self, base_w, base_h, orig_fps=30):
        """生成单段滤镜。

        aggressive 模式（模式5专用）额外叠加：
          1. 随机丢帧 0.5%~2%（打破时序指纹）
          2. 动态黑边 2~6px（改变像素分布）
          3. 亮度±8%、对比度±12%（大幅改变色彩统计）
        """
        filters = []

        # 丢帧已移至 build_command 全局层，避免分段内 PTS 冲突

        # ── 2. 变速 ──
        speed_range = (0.97, 1.03) if self.aggressive else (0.98, 1.02)
        speed = random.uniform(*speed_range)
        filters.append(f"setpts={1/speed}*PTS")

        # 动态黑边效果已移至全局变换（concat之后），避免分段尺寸不一致

        # ── 4. 缩放到目标尺寸 ──
        filters.append(f"scale={base_w}:{base_h}")

        # ── 5. 亮度/对比度 ──
        b_range = 0.08 if self.aggressive else 0.02
        c_range = 0.12 if self.aggressive else 0.03
        b = random.uniform(-b_range, b_range)
        c = random.uniform(1 - c_range, 1 + c_range)
        eq_parts = []
        if abs(b) > 0.001:
            eq_parts.append(f"brightness={b:.4f}")
        if abs(c - 1) > 0.001:
            eq_parts.append(f"contrast={c:.4f}")

        # aggressive 模式：放弃色相/饱和度（对CVPR指纹无效）
        if not self.aggressive:
            s = random.uniform(0.95, 1.05)
            if abs(s - 1) > 0.001:
                eq_parts.append(f"saturation={s:.4f}")

        if eq_parts:
            filters.append(f"eq={':'.join(eq_parts)}")

        # aggressive 模式：放弃色相旋转（对CVPR指纹无效）
        if not self.aggressive:
            h = random.uniform(-3, 3)
            if abs(h) > 0.1:
                filters.append(f"hue=h={h:.2f}")

        return ','.join(filters), speed
    
    def build_command(self):
        info = self.get_video_info()
        dur = info['duration']
        ow, oh = info['width'], info['height']
        ofps = info['fps']

        # 分辨率映射
        if self.aggressive:
            # 强制 1200×2134，无论源视频分辨率
            tw, th = 1200, 2134
        elif (ow, oh) == (1080, 1920):
            tw, th = 720, 1280
        elif (ow, oh) == (720, 1280):
            tw, th = 1080, 1920
        else:
            tw, th = 648, 1085
        print(f"  分辨率: {ow}x{oh} -> {tw}x{th}")

        # 帧率
        fps_f = random.uniform(0.90, 1.10)
        tfps = round(ofps * fps_f)
        tfps = max(23, min(62, tfps))
        print(f"  帧率: {ofps:.1f} -> {tfps}fps")

        # 分段（若 duration 来自回退值则强制单段，避免空段 concat 失败）
        if not info.get('_ok', True):
            num_seg = 1
            seg_pts = [0.0, dur]
            print(f"  分段: {num_seg}段 (duration来自回退值)")
        else:
            num_seg = max(1, min(10, random.randint(1, max(1, int(dur / 15)))))
            if num_seg == 1:
                seg_pts = [0.0, dur]
            else:
                seg_pts = [0.0]
                remain = dur
                for i in range(num_seg - 1):
                    sd = random.uniform(15, min(60, remain - (num_seg - i - 1) * 15))
                    seg_pts.append(seg_pts[-1] + sd)
                    remain -= sd
                seg_pts.append(dur)
            print(f"  分段: {num_seg}段")
        
        # ===== 构建命令 =====
        self.ffmpeg_cmd = [self.ffmpeg_path]
        
        # GPU解码
        if self.use_gpu:
            self.ffmpeg_cmd.extend(['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda'])
        
        self.ffmpeg_cmd.extend(['-i', self.input_path])
        
        # 构建滤镜
        vf_parts = []
        af_parts = []
        speeds = []
        has_audio = self._has_audio()
        
        if num_seg == 1:
            vf, spd = self.generate_segment_filter(tw, th)
            speeds.append(spd)
            if self.use_gpu:
                vf_parts.append(f"[0:v]hwdownload,format=nv12,{vf}[outv]")
            else:
                vf_parts.append(f"[0:v]{vf}[outv]")
            # 音频
            if has_audio:
                tempo = min(2.0, max(0.5, spd))
                audio_f = f"[0:a]atempo={tempo:.4f}"
                if not self.aggressive:
                    vol = random.uniform(0.97, 1.03)
                    if abs(vol - 1) > 0.001:
                        audio_f += f",volume={vol:.4f}"
                    if random.random() > 0.5:
                        pitch = random.uniform(-0.5, 0.5)
                        if abs(pitch) > 0.1:
                            pf = 2 ** (pitch / 12)
                            audio_f += f",asetrate=44100*{pf:.6f},atempo={1/pf:.6f},aresample=44100"
                    if random.random() > 0.6:
                        audio_f += ",highpass=f=80,lowpass=f=15000"
                if self.mode6:
                    audio_f += ",afftdn=nr=10:nf=-30,equalizer=f=800:t=q:w=2:g=0.3,aecho=0.8:0.9:10:0.3,aphaser=type=t:delay=0.3:decay=0.2:speed=0.3"
                af_parts.append(f"{audio_f}[outa]")
            else:
                af_parts.append(f"anullsrc=r=44100:cl=stereo[outa]")
        else:
            # split 视频
            vf_parts.append(f"[0:v]split={num_seg}" + ''.join(f"[v{i}]" for i in range(num_seg)))
            if has_audio:
                af_parts.append(f"[0:a]asplit={num_seg}" + ''.join(f"[a{i}]" for i in range(num_seg)))

            for i in range(num_seg):
                st = seg_pts[i]
                et = seg_pts[i + 1]
                vf, spd = self.generate_segment_filter(tw, th, ofps)
                speeds.append(spd)

                if self.use_gpu:
                    vf_parts.append(f"[v{i}]hwdownload,format=nv12,trim=start={st:.2f}:end={et:.2f},setpts=PTS-STARTPTS,{vf}[v{i}out]")
                else:
                    vf_parts.append(f"[v{i}]trim=start={st:.2f}:end={et:.2f},setpts=PTS-STARTPTS,{vf}[v{i}out]")

                # 音频
                if has_audio:
                    tempo = min(2.0, max(0.5, spd))
                    audio_f = f"[a{i}]atrim=start={st:.2f}:end={et:.2f},asetpts=PTS-STARTPTS,atempo={tempo:.4f}"
                    if not self.aggressive:
                        vol = random.uniform(0.97, 1.03)
                        if abs(vol - 1) > 0.001: audio_f += f",volume={vol:.4f}"
                        if random.random() > 0.5:
                            pitch = random.uniform(-0.5, 0.5)
                            if abs(pitch) > 0.1:
                                pf = 2 ** (pitch / 12)
                                audio_f += f",asetrate=44100*{pf:.6f},atempo={1/pf:.6f},aresample=44100"
                        if random.random() > 0.6:
                            audio_f += ",highpass=f=80,lowpass=f=15000"
                    if self.mode6:
                        audio_f += ",afftdn=nr=10:nf=-30,equalizer=f=800:t=q:w=2:g=0.3,aecho=0.8:0.9:10:0.3,aphaser=type=t:delay=0.3:decay=0.2:speed=0.3"
                    af_parts.append(f"{audio_f}[a{i}out]")
                print(f"    段{i+1}: {st:.1f}s-{et:.1f}s")

            # concat 视频
            vf_parts.append(''.join(f"[v{i}out]" for i in range(num_seg)) + f"concat=n={num_seg}:v=1:a=0[outv]")
            # concat 音频（仅当有音频时）
            if has_audio:
                af_parts.append(''.join(f"[a{i}out]" for i in range(num_seg)) + f"concat=n={num_seg}:v=0:a=1[outa]")
            else:
                af_parts.append(f"anullsrc=r=44100:cl=stereo[outa]")
        
        # 全局变换(随机缩放+旋转+黑边) - 最终输出tw x th
        rot_range = 1.0 if self.aggressive else 0.2
        rot = random.uniform(-rot_range, rot_range)

        # 替换最后的 [outv] 为 [preoutv]，添加全局变换
        vf_parts[-1] = vf_parts[-1].replace('[outv]', '[preoutv]')

        if self.aggressive:
            # 强化模式三步：黑边 → 动态缩放呼吸 → 旋转
            # 1. 黑边：缩到略小 + pad 黑边填回
            border = random.randint(6, 12)
            scale_w = tw - border * 2
            scale_h = th - border * 2
            scale_w -= scale_w % 2
            scale_h -= scale_h % 2
            pad_x = (tw - scale_w) // 2
            pad_y = (th - scale_h) // 2

            # 2. 动态缩放呼吸：先放大 1.5%~3%，再用时变 crop 做正弦振荡
            zoom_factor = random.uniform(1.02, 1.05)
            zoom_w = int(tw * zoom_factor)
            zoom_h = int(th * zoom_factor)
            zoom_w -= zoom_w % 2
            zoom_h -= zoom_h % 2

            # crop 基准偏移（居中）和振荡幅度
            base_cx = (zoom_w - tw) // 2
            base_cy = (zoom_h - th) // 2
            amp_x = random.randint(2, max(2, base_cx))
            amp_y = random.randint(3, max(3, base_cy))

            # 振荡周期 10~30 秒，随机相位
            period = random.uniform(10, 30)
            phase = random.uniform(0, 6.283185)  # 0~2π

            vf_parts.append(
                f"[preoutv]"
                f"scale={scale_w}:{scale_h},"
                f"pad={tw}:{th}:{pad_x}:{pad_y}:black,"
                f"scale={zoom_w}:{zoom_h},"
                f"crop={tw}:{th}:"
                f"{base_cx}+round({amp_x}*sin(2*PI*t/{period}+{phase})):"
                f"{base_cy}+round({amp_y}*sin(2*PI*t/{period}+{phase})),"
                f"rotate={rot:.3f}*PI/180,"
                f"noise=c0s=3:c1s=3:allf=t[outv]"
            )
            print(f"  动态黑边: {border}px, "
                  f"缩放呼吸: {zoom_factor:.1%}±{amp_x}px/{amp_y}px "
                  f"(周期{period:.0f}s), 旋转: {rot:.2f}°")
        else:
            # 标准模式：放大再裁回
            sf2 = 1 + random.uniform(0.01, 0.03)
            sw2 = int(tw * sf2)
            sh2 = int(th * sf2)
            sw2 -= sw2 % 2
            sh2 -= sh2 % 2
            cx2 = (sw2 - tw) // 2
            cy2 = (sh2 - th) // 2
            vf_parts.append(
                f"[preoutv]scale={sw2}:{sh2},"
                f"crop={tw}:{th}:{cx2}:{cy2},"
                f"rotate={rot:.3f}*PI/180[outv]"
            )

        # aggressive 模式: 通过输出帧率额外丢帧 0.5%~2%
        if self.aggressive:
            drop_rate = random.uniform(0.005, 0.02)
            tfps = max(23, min(62, round(tfps * (1 - drop_rate))))
            print(f"  强化丢帧: 输出帧率 {tfps}fps (约丢{drop_rate*100:.1f}%)")

        # 合并滤镜
        all_filters = ';'.join(vf_parts + af_parts)
        self.ffmpeg_cmd.extend(['-filter_complex', all_filters])
        self.ffmpeg_cmd.extend(['-map', '[outv]', '-map', '[outa]'])
        self.ffmpeg_cmd.extend(['-r', str(tfps)])
        
        # 编码
        crf = random.randint(22, 26)
        if self.use_gpu:
            self.ffmpeg_cmd.extend([
                '-c:v', 'h264_nvenc',
                '-preset', 'p4',
                '-cq', str(crf),
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                '-b:a', '192k',
            ])
        else:
            self.ffmpeg_cmd.extend([
                '-c:v', 'libx264',
                '-crf', str(crf),
                '-preset', 'medium',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                '-b:a', '192k',
            ])
        
        # 元数据 - 清空原始 + 仅保留AI声明
        self.ffmpeg_cmd.extend([
            '-map_metadata', '-1',
            '-map_chapters', '-1',
            '-metadata', 'comment=含AI生成内容；可能使用AI技术制作；可能含有AI生成内容',
            '-movflags', '+faststart',
            '-y',
            self.output_path
        ])
    
    def run(self):
        self.build_command()
        
        print(f"\n  执行FFmpeg...")
        try:
            result = subprocess.run(
                self.ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=600
            )
            if result.returncode == 0:
                print(f"  ✅ 处理成功: {os.path.basename(self.output_path)}")
                return True
            else:
                stderr = result.stderr.decode('utf-8', errors='ignore')
                print(f"  ❌ 失败 (返回码: {result.returncode})")
                # GPU 模式失败 → 自动回退 CPU
                if self.use_gpu:
                    print("  🔄 GPU 失败，回退 CPU 重试...")
                    self.use_gpu = False
                    return self.run()
                if len(stderr) > 500:
                    stderr = stderr[-500:]
                print(f"  错误: {stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("  ❌ 超时")
            return False
        except Exception as e:
            print(f"  ❌ 异常: {e}")
            return False