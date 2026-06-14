"""
AB 包裹处理器（模式7）
单滤镜链: crop→displace→rotate→sin蠕动→softlight→gloss→字幕噪点
GPU解码+编码(h264_nvenc) | 极限预设(ultrafast/p1)
"""
import os, sys, subprocess, itertools
from pathlib import Path

try: sys.stdout.reconfigure(encoding='utf-8')
except: pass

def _find_ffmpeg():
    base_dir = Path(__file__).resolve().parent
    for p in [base_dir/"ffmpeg-2026-06-08-git-6028720d70-full_build/ffmpeg-2026-06-08-git-6028720d70-full_build/bin/ffmpeg.exe",
              base_dir/"完整包138/Waifu2x-Extension-GUI-v3.138.01-Win64/waifu2x-extension-gui/ffmpeg_waifu2xEX.exe"]:
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

def ab_blend(video_a_path, video_b_path, output_path, use_gpu=False):
    """滤镜链: displace→rotate→sin蠕动→softlight→gloss"""
    info_a = get_video_info(video_a_path)
    info_b = get_video_info(video_b_path)
    w_a, h_a = info_a['width'], info_a['height']
    print(f"    A: {w_a}x{h_a}, {info_a['fps']:.0f}fps, {info_a['duration']:.0f}s")
    print(f"    B: {info_b['width']}x{info_b['height']}")

    # 单滤镜链：B裁剪→折射→呼吸→蠕动→包裹→光泽（无预处理，零冗余）
    vf = (
        # 0. B居中裁切至A比例 + A灰度位移图
        f"[1:v]crop=ih*{w_a}/{h_a}:ih,scale={w_a}x{h_a},format=rgba[B_scaled];"
        f"[0:v]format=gray,scale={w_a}x{h_a},gblur=sigma=1[A_gray];"
        f"[A_gray]geq=lum='128+(p(X,Y)-128)*0.01'[xmap];"
        f"[A_gray]geq=lum='128+(p(X,Y)-128)*0.01'[ymap];"
        # 1. A灰度位移→B折射扭曲(贴附纹理)
        f"[B_scaled][xmap][ymap]displace=edge=wrap[B_warped];"
        # 2. 微旋转(0.003°呼吸感)
        f"[B_warped]rotate='0.003*sin(2*PI*n/30)':fillcolor=black@0[B_breath];"
        # 3. 透明画布+蠕动偏移(sin平滑波形)
        f"color=black@0:size={w_a}x{h_a}[empty];"
        f"[empty][B_breath]overlay=x='-5+5*sin(t*3)':y='-5+5*sin(t*4)':shortest=1[B_shifted];"
        # 4. A+B softlight融合
        f"[0:v]format=rgba[A_rgba];"
        f"[A_rgba][B_shifted]blend=all_mode=softlight:all_opacity=0.25:shortest=1[blended];"
        # 5. 保鲜膜光泽（真正alpha透明,非addition）→不偏亮不偏暗
        f"[A_rgba]format=gray,geq=lum='p(X,Y)*0.02',format=rgba,colorchannelmixer=aa=0.015[gloss];"
        f"[blended][gloss]overlay=shortest=1[full];"
        f"[full]split[main][sub];"
        f"[sub]crop=iw:ih*0.15:0:ih*0.85,noise=alls=2:allf=t,format=yuv420p[sub_noise];"
        f"[main][sub_noise]overlay=0:main_h-overlay_h,"
        f"format=yuv420p"
    )

    # 方案1+2: GPU加速 + 最快预设
    if use_gpu:
        enc_opts = ['-c:v', 'h264_nvenc', '-preset', 'p1', '-pix_fmt', 'yuv420p']
        gpu_flags = ['-hwaccel', 'cuda']  # CPU滤镜链不加output_format
    else:
        enc_opts = ['-c:v', 'libx264', '-crf', '23', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p']
        gpu_flags = []

    cmd = [FFMPEG, '-y'] + gpu_flags + [
           '-i', video_a_path,
           '-stream_loop', '-1', '-i', video_b_path,
           '-filter_complex', vf,
           '-map', '0:a?',
           ] + enc_opts + [
           '-c:a', 'aac', '-b:a', '192k',
           '-shortest',
           '-movflags', '+faststart',
           '-map_metadata', '-1',
           '-metadata', 'comment=含AI生成内容；可能使用AI技术制作；可能含有AI生成内容',
           output_path]

    print(f"    包裹中...", end='', flush=True)
    r = subprocess.run(cmd, capture_output=True, text=False, timeout=7200, creationflags=CF)
    if r.returncode != 0:
        err = r.stderr.decode('utf-8', errors='ignore')[-400:] if r.stderr else ''
        print(f"\n    ❌ 失败: {err}")
        return False
    print(f"\r    包裹完成 (softlight模式+GPU)   ")
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
    return (success, len(pairs))

if __name__ == "__main__":
    print("AB 包裹处理器（模式7）")
