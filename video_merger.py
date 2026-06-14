"""
模式8：批量视频合并
选父目录 → 每个子文件夹的视频按序合并 → 输出到 {子文件夹}/合并/
"""
import os
import sys
import re
import subprocess
from pathlib import Path

def _natural_key(s):
    """自然排序：第2集 < 第10集"""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# ─── FFmpeg ───
def _find_ffmpeg():
    base_dir = Path(__file__).parent
    candidates = [
        base_dir / "完整包138/Waifu2x-Extension-GUI-v3.138.01-Win64/waifu2x-extension-gui/ffmpeg_waifu2xEX.exe",
        base_dir / "ffmpeg-2026-06-08-git-6028720d70-full_build/ffmpeg-2026-06-08-git-6028720d70-full_build/bin/ffmpeg.exe",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return "ffmpeg"

def _find_ffprobe():
    p = _find_ffmpeg().replace("ffmpeg_waifu2xEX.exe", "ffprobe_waifu2xEX.exe")
    if os.path.exists(p): return p
    p = _find_ffmpeg().replace("ffmpeg.exe", "ffprobe.exe")
    if os.path.exists(p): return p
    return "ffprobe"

FFMPEG = _find_ffmpeg()
FFPROBE = _find_ffprobe()
CF = 0x08000000 if sys.platform == 'win32' else 0
VIDEO_EXT = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv')


def get_resolution(video_path):
    cmd = [FFPROBE, '-v', 'error', '-select_streams', 'v:0',
           '-show_entries', 'stream=width,height', '-of', 'csv=p=0', video_path]
    r = subprocess.run(cmd, capture_output=True, text=False, timeout=30, creationflags=CF)
    w, h = map(int, r.stdout.decode().strip().split(','))
    return w, h


def get_codec(video_path):
    cmd = [FFPROBE, '-v', 'error', '-select_streams', 'v:0',
           '-show_entries', 'stream=codec_name', '-of', 'csv=p=0', video_path]
    r = subprocess.run(cmd, capture_output=True, text=False, timeout=30, creationflags=CF)
    return r.stdout.decode().strip()


def merge_videos(video_paths, output_path, use_gpu=False):
    """智能合并：同分辨率同编码→瞬间拼接，不同→先统一再拼接"""
    import tempfile
    if len(video_paths) == 0:
        return False
    if len(video_paths) == 1:
        cmd = [FFMPEG, '-y', '-i', video_paths[0],
               '-c', 'copy', '-movflags', '+faststart', output_path]
        r = subprocess.run(cmd, capture_output=True, text=False, timeout=600, creationflags=CF)
        return r.returncode == 0

    base_w, base_h = get_resolution(video_paths[0])
    base_codec = get_codec(video_paths[0])

    # 检查兼容性：同分辨率+同编码→直接 concat，瞬间完成
    all_compatible = True
    for vp in video_paths[1:]:
        w, h = get_resolution(vp)
        if (w, h) != (base_w, base_h) or get_codec(vp) != base_codec:
            all_compatible = False
            break

    if all_compatible:
        print(f"    同分辨率同编码，瞬间拼接...")
        list_file = os.path.join(tempfile.mkdtemp(prefix="mrg_"), "list.txt")
        with open(list_file, 'w', encoding='utf-8') as f:
            for vp in video_paths:
                f.write(f"file '{vp}'\n")
        cmd = [FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', list_file,
               '-c', 'copy', '-movflags', '+faststart', output_path]
        r = subprocess.run(cmd, capture_output=True, text=False, timeout=600, creationflags=CF)
        import shutil; shutil.rmtree(os.path.dirname(list_file), ignore_errors=True)
        return r.returncode == 0

    # 不兼容→预处理统一格式
    print(f"    统一格式中...")
    base_w -= base_w % 2
    base_h -= base_h % 2
    tmp_dir = tempfile.mkdtemp(prefix="merge_")
    tmp_files = []
    encoder = 'h264_nvenc' if use_gpu else 'libx264'
    enc_opts = ['-preset', 'p4', '-pix_fmt', 'yuv420p'] if use_gpu else ['-crf', '23', '-preset', 'fast', '-pix_fmt', 'yuv420p']

    for i, vp in enumerate(video_paths):
        sys.stdout.write(f"\r    预处理: {i+1}/{len(video_paths)}")
        sys.stdout.flush()
        tmp_out = os.path.join(tmp_dir, f"_{i}.mp4")
        cmd = [FFMPEG, '-y', '-i', vp,
               '-vf', f"scale={base_w}:{base_h}:force_original_aspect_ratio=decrease,pad={base_w}:{base_h}:(ow-iw)/2:(oh-ih)/2,setsar=1",
               '-c:v', encoder] + enc_opts + [
               '-c:a', 'aac', '-b:a', '192k', '-ar', '44100', '-ac', '2', tmp_out]
        r = subprocess.run(cmd, capture_output=True, text=False, timeout=600, creationflags=CF)
        if r.returncode == 0 and os.path.exists(tmp_out):
            tmp_files.append(tmp_out)
        else:
            import shutil; shutil.rmtree(tmp_dir, ignore_errors=True)
            return False

    print(f"\r    拼接中...", end='')
    sys.stdout.flush()
    list_file = os.path.join(tmp_dir, "list.txt")
    with open(list_file, 'w', encoding='utf-8') as f:
        for tf in tmp_files:
            f.write(f"file '{tf}'\n")
    cmd = [FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', list_file,
           '-c', 'copy', '-movflags', '+faststart', output_path]
    r = subprocess.run(cmd, capture_output=True, text=False, timeout=600, creationflags=CF)
    import shutil; shutil.rmtree(tmp_dir, ignore_errors=True)
    if r.returncode != 0:
        print()
        err = r.stderr.decode('utf-8', errors='ignore')[-200:] if r.stderr else ''
        print(f"    ❌ 合并失败: {err}")
        return False
    return True


def batch_merge(parent_dir, output_dir, use_gpu=False):
    """批量处理父目录下所有子文件夹"""
    if not os.path.isdir(parent_dir):
        print("❌ 目录无效")
        return

    # 收集子文件夹（自然排序）
    subdirs = sorted([
        d for d in os.listdir(parent_dir)
        if os.path.isdir(os.path.join(parent_dir, d)) and d != '合并'
    ], key=_natural_key)

    if not subdirs:
        print("❌ 未找到子文件夹")
        return

    os.makedirs(output_dir, exist_ok=True)
    print(f"\n📊 找到 {len(subdirs)} 个子文件夹 → 输出: {output_dir}")

    from progress_utils import ProgressBar
    success = 0

    for sd in subdirs:
        sd_path = os.path.join(parent_dir, sd)
        videos = sorted([
            os.path.join(sd_path, f) for f in os.listdir(sd_path)
            if f.lower().endswith(VIDEO_EXT)
        ], key=_natural_key)

        if not videos:
            print(f"\n  ⏭ {sd}: 无视频，跳过")
            continue

        out_name = f"{sd}-合并.mp4"
        out_path = os.path.join(output_dir, out_name)

        print(f"\n  📁 {sd}: {len(videos)} 个视频")
        print(f"     基准: {get_resolution(videos[0])}")
        print(f"     输出: {out_path}")

        ok = merge_videos(videos, out_path, use_gpu)
        if ok:
            success += 1
            size_mb = os.path.getsize(out_path) / 1024 / 1024
            print(f"     ✅ 合并完成 ({size_mb:.1f}MB)")
        else:
            print(f"     ❌ 合并失败")

    print(f"\n=== 批量合并完成 ===")
    print(f"成功: {success}/{len(subdirs)}")


if __name__ == "__main__":
    print("模式8：批量视频合并")
