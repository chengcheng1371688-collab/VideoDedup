"""
AB 像素融合处理器（模式7）
每帧像素 = A + B×1~2% (blend addition)。B融入A体内，不分层。
肉眼看不到B，但每一帧每个像素的MD5和指纹全变。
"""
import os, sys, subprocess, random, itertools
from pathlib import Path

try: sys.stdout.reconfigure(encoding='utf-8')
except: pass

def _find_ffmpeg():
    base_dir = Path(__file__).parent
    for p in [base_dir/"完整包138/Waifu2x-Extension-GUI-v3.138.01-Win64/waifu2x-extension-gui/ffmpeg_waifu2xEX.exe",
              base_dir/"ffmpeg-2026-06-08-git-6028720d70-full_build/ffmpeg-2026-06-08-git-6028720d70-full_build/bin/ffmpeg.exe"]:
        if p.exists(): return str(p)
    return "ffmpeg"

FFMPEG = _find_ffmpeg()
CF = 0x08000000 if sys.platform == 'win32' else 0

def _find_ffprobe():
    for p in [FFMPEG.replace("ffmpeg_waifu2xEX.exe","ffprobe_waifu2xEX.exe"),
              FFMPEG.replace("ffmpeg.exe","ffprobe.exe")]:
        if os.path.exists(p): return p
    return "ffprobe"
FFPROBE = _find_ffprobe()

def get_video_info(video_path):
    cmd = [FFPROBE, '-v', 'error', '-select_streams', 'v:0',
           '-show_entries', 'stream=width,height,r_frame_rate,duration',
           '-show_entries', 'format=duration', '-of', 'csv=p=0', video_path]
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

def ab_overlay(video_a_path, video_b_path, output_path, use_gpu=False):
    """A底层 + B顶层(1~2%透明度) = 画中画叠加"""
    info_a = get_video_info(video_a_path)
    info_b = get_video_info(video_b_path)
    w_a, h_a = info_a['width'], info_a['height']
    opacity = random.uniform(0.01, 0.02)
    print(f"    A: {w_a}x{h_a}, {info_a['fps']:.0f}fps, {info_a['duration']:.0f}s")
    print(f"    B: {info_b['width']}x{info_b['height']}, 不透明度: {opacity*100:.1f}%")

    # blend: B像素融入A像素，不分轨道，单帧融合
    blend_opacity = f"{opacity:.4f}"
    vf = (f"[1:v]scale={w_a}:{h_a}:force_original_aspect_ratio=decrease,"
          f"pad={w_a}:{h_a}:(ow-iw)/2:(oh-ih)/2[b];"
          f"[0:v][b]blend=all_mode=addition:all_opacity={blend_opacity}")

    encoder = 'h264_nvenc' if use_gpu else 'libx264'
    enc_opts = ['-preset', 'p6', '-pix_fmt', 'yuv420p'] if use_gpu else ['-crf', '23', '-preset', 'fast', '-pix_fmt', 'yuv420p']

    cmd = [FFMPEG, '-y',
           '-i', video_a_path,
           '-stream_loop', '-1', '-i', video_b_path,  # B循环
           '-filter_complex', vf,
           '-map', '0:a',                             # A的音频
           '-c:v', encoder] + enc_opts + [
           '-c:a', 'aac', '-b:a', '192k',
           '-shortest',                               # A播完就停
           '-movflags', '+faststart',
           '-map_metadata', '-1',
           '-metadata', 'comment=含AI生成内容；可能使用AI技术制作；可能含有AI生成内容',
           output_path]

    pct = opacity * 100
    print(f"    叠加中...", end='', flush=True)
    r = subprocess.run(cmd, capture_output=True, text=False, timeout=7200, creationflags=CF)
    if r.returncode != 0:
        err = r.stderr.decode('utf-8', errors='ignore')[-400:] if r.stderr else ''
        print(f"\n    ❌ 失败: {err}")
        return False
    print(f"\r    叠加完成 (不透明度{pct:.1f}%)   ")
    return True

def pair_videos(a_list, b_list):
    pairs = []
    if len(b_list) >= len(a_list):
        for i, a in enumerate(a_list): pairs.append((a, b_list[i]))
    else:
        b_cycle = itertools.cycle(b_list)
        for a in a_list: pairs.append((a, next(b_cycle)))
    return pairs

def batch_ab_process(a_dir, b_dir, output_dir, use_gpu=False):
    video_ext = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv')
    a_files = sorted([os.path.join(a_dir,f) for f in os.listdir(a_dir) if f.lower().endswith(video_ext)])
    b_files = sorted([os.path.join(b_dir,f) for f in os.listdir(b_dir) if f.lower().endswith(video_ext)])
    if not a_files: print("❌ A 目录未找到视频"); return (0,0)
    if not b_files: print("❌ B 目录未找到视频"); return (0,0)
    print(f"\n📊 A 视频: {len(a_files)} | B 素材: {len(b_files)}")
    pairs = pair_videos(a_files, b_files)
    os.makedirs(output_dir, exist_ok=True)
    from progress_utils import ProgressBar
    success = 0; pbar = ProgressBar(len(pairs), "AB画中画叠加")
    for i, (a_path, b_path) in enumerate(pairs, 1):
        a_name = os.path.basename(a_path)
        out_path = os.path.join(output_dir, f"{os.path.splitext(a_name)[0]}_AB叠加.mp4")
        pbar.set_description(f"[{i}/{len(pairs)}] {a_name[:25]}")
        print(f"\n  [{i}/{len(pairs)}] {a_name} + {os.path.basename(b_path)}")
        ok = ab_overlay(a_path, b_path, out_path, use_gpu)
        if ok: success += 1; print(f"    ✅ {out_path}")
        pbar.update(1)
    pbar.close()
    print(f"\n=== 完成: {success}/{len(pairs)} ===")
    return (success, len(pairs))

if __name__ == "__main__":
    print("AB 画中画叠加处理器（模式7）")
