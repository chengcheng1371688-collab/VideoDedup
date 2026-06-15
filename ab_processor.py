"""
AB 包裹处理器（模式7）
单滤镜链: crop→displace→rotate→sin蠕动→softlight→gloss→字幕噪点
GPU解码+编码(h264_nvenc) | 极限预设(ultrafast/p1)
"""
import os, sys, subprocess, itertools, random
from pathlib import Path

try: sys.stdout.reconfigure(encoding='utf-8')
except: pass

def _find_ffmpeg():
    base_dir = Path(__file__).resolve().parent
    import glob as _glob
    # 搜索本地全量版
    for pat in ["ffmpeg-*-full_build/ffmpeg-*-full_build/bin/ffmpeg.exe",
                "ffmpeg-*-full_build/bin/ffmpeg.exe"]:
        m = sorted(_glob.glob(str(base_dir / pat)), reverse=True)
        if m: return m[0]
    # 回退 Waifu2x 自带版
    for p in [base_dir/"完整包138/Waifu2x-Extension-GUI-v3.138.01-Win64/waifu2x-extension-gui/ffmpeg_waifu2xEX.exe"]:
        if p.exists(): return str(p)
    return "ffmpeg"

FFMPEG = _find_ffmpeg()
CF = 0x08000000 if sys.platform == 'win32' else 0

def _find_ffprobe():
    import glob as _glob
    base_dir = Path(__file__).resolve().parent
    # 搜索全量版 ffprobe
    for pat in ["ffmpeg-*-full_build/ffmpeg-*-full_build/bin/ffprobe.exe",
                "ffmpeg-*-full_build/bin/ffprobe.exe"]:
        m = sorted(_glob.glob(str(base_dir / pat)), reverse=True)
        if m: return m[0]
    # 回退 Waifu2x 版
    for p in [FFMPEG.replace("ffmpeg_waifu2xEX.exe","ffprobe_waifu2xEX.exe"),
              FFMPEG.replace("ffmpeg.exe","ffprobe.exe")]:
        if os.path.exists(p): return p
    return "ffprobe"
FFPROBE = _find_ffprobe()

def get_video_info(video_path):
    cmd = [FFPROBE, '-v', 'error', '-select_streams', 'v:0',
           '-show_entries', 'stream=width,height,r_frame_rate,duration:format=duration',
           '-of', 'csv=p=0', video_path]
    try:
        r = subprocess.run(cmd, capture_output=True, text=False, timeout=60, creationflags=CF)
        parts = r.stdout.decode('utf-8', errors='ignore').strip().split(',')
        w, h = int(parts[0]), int(parts[1])
        fps_str = parts[2]
        if '/' in fps_str: num, den = map(int, fps_str.split('/')); fps = num/den if den else 30
        else: fps = float(fps_str)
        dur = float(parts[3]) if len(parts)>3 and parts[3] else (float(parts[4]) if len(parts)>4 else 0)
        return {'width':w,'height':h,'fps':fps,'duration':dur}
    except: return {'width':1080,'height':1920,'fps':30,'duration':60}

def _meta_opts():
    import random as _r, datetime as _dt
    titles = ["生活记录", "日常分享", "精彩瞬间", "原创作品", "个人创作"]
    days = _r.randint(-30, 30)
    dt = (_dt.datetime.now() + _dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    return ["-metadata", f"title={_r.choice(titles)}_{_r.randint(100,999)}",
            "-metadata", f"creation_time={dt}",
            "-metadata", "comment=原创内容"]

def ab_blend(video_a_path, video_b_path, output_path, use_gpu=False, codec=None, audio_path=None):
    """滤镜链: softlight→字幕噪点
       audio_path: 可选，直接复用音频流，省去外部混流步骤"""
    info_a = get_video_info(video_a_path)
    info_b = get_video_info(video_b_path)
    w_a, h_a = info_a['width'], info_a['height']
    if h_a <= 0 or info_b['height'] <= 0:
        print(f"\n    ❌ 无法获取视频尺寸 (A: {w_a}x{h_a}, B: {info_b['width']}x{info_b['height']})")
        return False
    print(f"    A: {w_a}x{h_a}, {info_a['fps']:.0f}fps, {info_a['duration']:.0f}s")
    print(f"    B: {info_b['width']}x{info_b['height']}")

    # 预循环B素材：重编码而非 -c copy，确保 moov atom 覆盖全部帧
    dur_a = info_a.get('duration', 60)
    dur_b = max(1, info_b.get('duration', 1))
    # 如果 A 视频的 get_video_info 返回了回退值（ffprobe 失败），
    # 假定 A 很长，强制触发预循环以避免 filter_complex 崩溃
    if dur_a == 60 and info_a.get('width') == 1080 and info_a.get('height') == 1920:
        dur_a = max(dur_a, dur_b * 10)  # 假定 A 至少是 B 的 10 倍长
    b_input = video_b_path
    b_looped_temp = None
    if dur_b < dur_a:
        import tempfile
        loop_count = int(dur_a / dur_b) + 2
        b_looped_temp = os.path.join(tempfile.gettempdir(), f"ab_b_{os.getpid()}.mp4")
        print(f"    预循环B: {loop_count}次 (B={dur_b:.0f}s < A={dur_a:.0f}s)")
        r_pre = subprocess.run([FFMPEG, '-y', '-stream_loop', str(loop_count), '-i', video_b_path,
                                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
                                '-pix_fmt', 'yuv420p', '-an',
                                '-t', str(dur_a + 5), b_looped_temp],
                               capture_output=True, creationflags=CF, timeout=300)
        if r_pre.returncode == 0 and os.path.getsize(b_looped_temp) > 1000:
            # 解码验证：确保文件完整可读
            r_val = subprocess.run([FFMPEG, '-v', 'error', '-i', b_looped_temp, '-f', 'null', '-'],
                                   capture_output=True, creationflags=CF, timeout=120)
            if r_val.returncode == 0 and r_val.stderr == b'':
                b_input = b_looped_temp
                print(f"    预循环B完成 ✓")
            else:
                print(f"    ⚠️ 预循环文件解码验证失败，使用原始B")
                try: os.remove(b_looped_temp)
                except: pass
                b_looped_temp = None
        else:
            print(f"    ⚠️ 预循环生成失败 (返回码={r_pre.returncode})，使用原始B")
            if b_looped_temp and os.path.exists(b_looped_temp):
                try: os.remove(b_looped_temp)
                except: pass
            b_looped_temp = None

    # 精简滤镜链：B缩放 → A+B softlight融合 → 字幕噪点
    vf = (
        # 1. B 缩放到 A 尺寸 + A 转 rgba
        f"[1:v]scale={w_a}:{h_a},format=rgba[B_scaled];"
        f"[0:v]format=rgba[A_rgba];"
        # 2. A+B softlight 融合（25% 不透明度）
        f"[A_rgba][B_scaled]blend=all_mode=softlight:all_opacity={random.uniform(0.08, 0.15):.4f}:shortest=1[blended];"
        # 3. 字幕区域噪点（底部 15%，干扰 OCR 提取）
        f"[blended]split[main][sub];"
        f"[sub]crop=iw:ih*0.15:0:ih*0.85,noise=alls=2:allf=t,format=yuv420p[sub_noise];"
        f"[main][sub_noise]overlay=0:main_h-overlay_h,"
        f"format=yuv420p"
    )

    # 方案1+2: GPU加速 + 最快预设
    # 注意：不使用 -hwaccel cuda，因为 filter_complex 全部是 CPU 滤镜（format/blend/overlay）
    # GPU 解码+下载反而不如 CPU 直接解码快，且多输入 + stream_loop 场景下可能隐式 hwdownload 失败
    if use_gpu:
        if codec == 'hevc':
            enc_opts = ['-c:v', 'hevc_nvenc', '-preset', 'p1', '-pix_fmt', 'yuv420p',
                        '-b_ref_mode', '0',          # 禁用B-frame（消费卡必需）
                        '-profile:v', 'main',         # 显式 main profile
                        '-tier', 'main']              # main tier
        else:
            enc_opts = ['-c:v', 'h264_nvenc', '-preset', 'p1', '-pix_fmt', 'yuv420p']
        gpu_flags = []
    else:
        enc_opts = ['-c:v', 'libx264', '-crf', '23', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p']
        gpu_flags = []

    # 音频映射：有外部音频文件则用外部，否则尝试从 A 视频取
    if audio_path and os.path.exists(audio_path):
        audio_input = ['-i', audio_path]
        audio_map = ['-map', '2:a:0']
    else:
        audio_input = []
        audio_map = ['-map', '0:a?']

    cmd = [FFMPEG, '-y'] + gpu_flags + [
           '-i', video_a_path,
           '-i', b_input,
           ] + audio_input + [
           '-filter_complex', vf,
           ] + audio_map + enc_opts + [
           '-c:a', 'aac', '-b:a', '192k',
           '-shortest',
           '-movflags', '+faststart',
           '-map_metadata', '-1',
           ] + _meta_opts() + ['-metadata', 'comment=原创内容',
           output_path]

    _ok = False  # 单出口标志
    print(f"    包裹中...", end='', flush=True)
    try:
        try:
            r = subprocess.run(cmd, capture_output=True, text=False, timeout=7200, creationflags=CF)
        except subprocess.TimeoutExpired:
            print(f"\n    ❌ AB包裹超时（7200s）")
            return False
        if r.returncode != 0:
            # hevc_nvenc 失败自动回退到 h264_nvenc
            if codec == 'hevc' and use_gpu:
                err = r.stderr.decode('utf-8', errors='ignore') if r.stderr else ''
                key_lines = [l for l in err.split('\n') if any(kw in l for kw in
                    ['Error', 'error', 'failed', 'Invalid', 'filter', 'No ', 'Stream', 'stream'])][-8:]
                print(f"\n    ⚠️ hevc_nvenc 失败 → 回退 h264_nvenc...")
                if key_lines:
                    for l in key_lines:
                        print(f"      {l.strip()[:200]}")
                enc_opts_retry = ['-c:v', 'h264_nvenc', '-preset', 'p1', '-pix_fmt', 'yuv420p']
                cmd_retry = [FFMPEG, '-y'] + gpu_flags + [
                    '-i', video_a_path,
                    '-i', b_input,
                    ] + audio_input + [
                    '-filter_complex', vf,
                    ] + audio_map + enc_opts_retry + [
                    '-c:a', 'aac', '-b:a', '192k',
                    '-shortest',
                    '-movflags', '+faststart',
                    '-map_metadata', '-1',
                    ] + _meta_opts() + ['-metadata', 'comment=原创内容',
                    output_path]
                try:
                    r = subprocess.run(cmd_retry, capture_output=True, text=False, timeout=7200, creationflags=CF)
                except subprocess.TimeoutExpired:
                    print(f"\n    ❌ AB包裹回退超时")
                    return False
                if r.returncode != 0:
                    err2 = r.stderr.decode('utf-8', errors='ignore') if r.stderr else ''
                    key_lines2 = [l for l in err2.split('\n') if any(kw in l for kw in
                        ['Error', 'error', 'failed', 'Invalid', 'filter', 'No ', 'Stream', 'stream'])][-8:]
                    print(f"    ❌ 回退也失败")
                    if key_lines2:
                        for l in key_lines2:
                            print(f"      {l.strip()[:200]}")
                    # ── 第三层：诊断 + 超简回退 ──
                    # 先用纯透传测试滤镜图本身是否可用
                    print(f"    🔍 诊断：测试纯透传...", end='', flush=True)
                    import tempfile
                    diag_tmp = os.path.join(tempfile.gettempdir(), f"_ab_diag_{os.getpid()}.mp4")
                    diag_cmd = [FFMPEG, '-y', '-i', video_a_path,
                                '-vf', 'format=yuv420p',
                                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
                                '-an', '-t', '3',
                                '-f', 'mp4', diag_tmp]
                    r_diag = subprocess.run(diag_cmd, capture_output=True, text=False, timeout=60, creationflags=CF)
                    if r_diag.returncode != 0:
                        diag_err = r_diag.stderr.decode('utf-8', errors='ignore')[-300:] if r_diag.stderr else ''
                        print(f"\n    ❌ 输入文件或FFmpeg本身有问题（透传也失败）")
                        print(f"    [诊断日志] {diag_err[-200:]}")
                        print(f"    📁 诊断文件保留: {diag_tmp}")
                        return False
                    print(f" 透传OK → 滤镜链不兼容，尝试超简overlay...")
                    # 超简滤镜：纯 overlay 25% 透明度，无 softlight/blend
                    vf_ultra = (
                        f"[1:v]scale={w_a}:{h_a},format=rgba,colorchannelmixer=aa=0.25[B_s];"
                        f"[0:v][B_s]overlay=format=yuv420p"
                    )
                    ultra_cmd = [FFMPEG, '-y', '-i', video_a_path, '-i', b_input,
                                 ] + audio_input + [
                                 '-filter_complex', vf_ultra,
                                 ] + audio_map + [
                                 '-c:v', 'libx264', '-crf', '23', '-preset', 'ultrafast',
                                 '-pix_fmt', 'yuv420p',
                                 '-c:a', 'aac', '-b:a', '192k', '-shortest',
                                 '-movflags', '+faststart',
                                 '-map_metadata', '-1',
                                 ] + _meta_opts() + ['-metadata', 'comment=原创内容',
                                 output_path]
                    r_ultra = subprocess.run(ultra_cmd, capture_output=True, text=False, timeout=7200, creationflags=CF)
                    if r_ultra.returncode == 0:
                        try: os.remove(diag_tmp)
                        except: pass
                        print(f"\r    包裹完成 (超简overlay回退)   ")
                        return True
                    ultra_err = r_ultra.stderr.decode('utf-8', errors='ignore')[-300:] if r_ultra.stderr else ''
                    print(f"\n    ❌ 超简overlay也失败: {ultra_err[-200:]}")
                    print(f"    📁 诊断文件保留: {diag_tmp}")
                    return False
                print(f"\r    包裹完成 (hevc回退→h264+GPU)   ")
                _ok = True
                return True
            err = r.stderr.decode('utf-8', errors='ignore') if r.stderr else ''
            key_lines = [l for l in err.split('\n') if any(kw in l for kw in
                ['Error', 'error', 'failed', 'Invalid', 'filter', 'No ', 'Stream', 'stream'])][-8:]
            print(f"\n    ❌ 失败")
            if key_lines:
                for l in key_lines:
                    print(f"      {l.strip()[:200]}")
            return False
        label = 'hevc+GPU' if (codec == 'hevc' and use_gpu) else ('h264+GPU' if use_gpu else 'h264+CPU')
        print(f"\r    包裹完成 (softlight+{label})   ")
        _ok = True
        return True
    finally:
        if b_looped_temp:
            try: os.remove(b_looped_temp)
            except: pass

def pair_videos(a_list, b_list):
    pairs = []
    if len(b_list) >= len(a_list):
        for i, a in enumerate(a_list): pairs.append((a, b_list[i]))
    else:
        b_cycle = itertools.cycle(b_list)
        for a in a_list: pairs.append((a, next(b_cycle)))
    return pairs

def batch_ab_process(a_dir, b_dir, output_dir, use_gpu=False):
    import time; t_batch = time.time()
    video_ext = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv')
    a_files = sorted([os.path.join(a_dir,f) for f in os.listdir(a_dir) if f.lower().endswith(video_ext)])
    b_files = sorted([os.path.join(b_dir,f) for f in os.listdir(b_dir) if f.lower().endswith(video_ext)])
    if not a_files: print("❌ A 目录未找到视频"); return (0,0)
    if not b_files: print("❌ B 目录未找到视频"); return (0,0)
    print(f"\n📊 A 视频: {len(a_files)} | B 素材: {len(b_files)}")
    pairs = pair_videos(a_files, b_files)
    os.makedirs(output_dir, exist_ok=True)
    from progress_utils import ProgressBar
    success = 0; pbar = ProgressBar(len(pairs), "AB包裹")
    for i, (a_path, b_path) in enumerate(pairs, 1):
        a_name = os.path.basename(a_path)
        out_path = os.path.join(output_dir, f"{os.path.splitext(a_name)[0]}_AB叠加.mp4")
        pbar.set_description(f"[{i}/{len(pairs)}] {a_name[:25]}")
        print(f"\n  [{i}/{len(pairs)}] {a_name} + {os.path.basename(b_path)}")
        ok = ab_blend(a_path, b_path, out_path, use_gpu)
        if ok: success += 1; print(f"    ✅ {out_path}")
        pbar.update(1)
    pbar.close()
    print(f"\n=== 完成: {success}/{len(pairs)} ===")
    # 复用 run.py 的 _fmt_time
    try:
        from run import _fmt_time
    except:
        def _fmt_time(s): return f"{s:.1f}s"
    print(f"⏱️ [AB批量包裹] 总耗时: {_fmt_time(time.time() - t_batch)}")
    return (success, len(pairs))

if __name__ == "__main__":
    print("AB 包裹处理器（模式7）")
