"""
统一入口脚本 - 视频去重工具
支持: GPU加速、AI增强、标准处理、伪时长
Ctrl+C=返回菜单
"""
import os
import sys
from key_input import safe_input, BackStep

# 设置编码
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def print_banner():
    """打印横幅"""
    print("\n" + "=" * 60)
    print("          视频去重工具 - 统一入口")
    print("=" * 60)
    print("")

def print_menu():
    """打印菜单"""
    print("🎯 选择处理模式:")
    print("-" * 40)
    print("  1. [快速模式] 标准处理 - CPU处理，快速稳定")
    print("  2. [推荐模式] GPU加速 - GPU解码+CPU编码，平衡之选")
    print("  3. [最强模式] AI增强 - DAIN/RIFE帧插值，最强去重")
    print("  4. [自定义模式] 自定义参数 - 自由配置各项参数")
    print("  5. [伪时长模式] GPU加速 + 分段滤镜 + 伪时长注入（3~12秒）")
    print("  6. [正向伪时长] 模式5全部去重 + 推流加权伪时长 + 音频微调")
    print("  7. [AB抽帧混合] 240fps, B帧随机池600, A帧I帧")
    print("  8. [批量合并] 父目录下所有子文件夹分别合并成一条视频")
    print("  9. [RIFE+去重] RIFE帧插值 + Mode 6全流程")
    print("  10.[完全增强] RIFE + SPAN超分 + Mode 6全流程")
    print("-" * 40)
    print("")

def check_environment():
    """检查环境"""
    from pathlib import Path
    
    print("📊 环境检查...")
    
    # FFmpeg
    waifu2x_ffmpeg = Path(__file__).parent / "完整包138" / "Waifu2x-Extension-GUI-v3.138.01-Win64" / "waifu2x-extension-gui" / "ffmpeg_waifu2xEX.exe"
    if waifu2x_ffmpeg.exists():
        print("  ✅ FFmpeg (Waifu2x版本)")
    
    # GPU
    try:
        import ctypes
        nvcuda = ctypes.WinDLL('nvcuda.dll', mode=ctypes.RTLD_GLOBAL)
        print("  ✅ NVIDIA GPU (CUDA支持)")
        gpu_available = True
    except:
        print("  ⚠️  GPU不可用 (将使用CPU)")
        gpu_available = False
    
    # AI模型
    waifu2x_dir = Path(__file__).parent / "完整包138" / "Waifu2x-Extension-GUI-v3.138.01-Win64" / "waifu2x-extension-gui"
    
    if waifu2x_dir.exists():
        models = [
            ("DAIN", waifu2x_dir / "dain-ncnn-vulkan"),
            ("RIFE", waifu2x_dir / "rife-ncnn-vulkan"),
            ("CAIN", waifu2x_dir / "cain-ncnn-vulkan"),
        ]
        for name, path in models:
            if path.exists():
                print(f"  ✅ {name} 可用")
    
    print("")
    return gpu_available

def run_standard_mode(input_dir):
    """运行标准模式"""
    print("\n[模式 1] 标准处理模式")
    print("-" * 40)
    
    # 使用纯CPU模式
    config = {'use_gpu': False}
    batch_process(input_dir, config)

def run_gpu_mode(input_dir):
    """运行GPU加速模式"""
    print("\n[模式 2] GPU加速模式")
    print("-" * 40)
    
    # 使用GPU模式
    config = {'use_gpu': True}
    batch_process(input_dir, config)

def run_ai_mode(input_dir):
    """运行AI增强模式"""
    print("\n[模式 3] AI增强模式")
    print("-" * 40)
    
    config = {'use_gpu': True, 'use_ai': True}
    batch_process(input_dir, config)

def run_custom_mode(input_dir):
    """运行自定义模式"""
    print("\n[模式 4] 自定义模式")
    print("-" * 40)
    
    # 显示自定义选项
    print("请选择自定义配置:")
    print("  1. GPU加速 + 标准处理")
    print("  2. GPU加速 + AI增强")
    print("  3. 纯CPU + 标准处理")
    print("  4. 纯CPU + AI增强")
    print("")
    
    choice = safe_input("请选择 (1/2/3/4): ").strip()
    
    config = {}
    
    if choice == '1':
        print("运行: GPU加速 + 标准处理")
        config = {'use_gpu': True, 'use_ai': False}
    elif choice == '2':
        print("运行: GPU加速 + AI增强")
        config = {'use_gpu': True, 'use_ai': True}
    elif choice == '3':
        print("运行: 纯CPU + 标准处理")
        config = {'use_gpu': False, 'use_ai': False}
    elif choice == '4':
        print("运行: 纯CPU + AI增强")
        config = {'use_gpu': False, 'use_ai': True}
    else:
        print("无效选择，使用默认配置")
        config = {'use_gpu': True}
    
    batch_process(input_dir, config)


def run_mode5(input_dir):
    """模式5: GPU加速 + 分段滤镜去重 + 伪时长注入"""
    print("\n[模式 5] 伪时长模式")
    print("-" * 40)
    print("  处理流程: GPU加速解码 → 分段滤镜去重 → GPU编码 → MP4伪时长注入")
    print("  伪时长范围: 随机 3~12 秒")
    print("")

    # 阶段1: GPU加速 + 强化滤镜（丢帧/黑边/大幅参数/微旋转）
    print("=" * 50)
    print("  阶段 1/2: GPU加速 + 强化去重处理")
    print("=" * 50)
    config = {'use_gpu': True, 'aggressive': True}
    result = batch_process(input_dir, config)
    success_count, output_dir, processed_paths = result

    if success_count == 0 or not processed_paths:
        print("\n  ⚠️ 阶段1无成功处理的视频，跳过伪时长注入")
        return

    # 阶段2: 伪时长注入
    print("\n" + "=" * 50)
    print("  阶段 2/2: MP4 伪时长注入（随机 3~12 秒）")
    print("=" * 50)
    from pseudo_duration import apply_pseudo_duration
    from progress_utils import ProgressBar

    patch_ok = 0
    pbar = ProgressBar(len(processed_paths), "伪时长注入")
    for i, pp in enumerate(processed_paths, 1):
        fname = os.path.basename(pp)
        pbar.set_description(f"[{i}/{len(processed_paths)}] {fname[:30]}")
        ok, real, fake = apply_pseudo_duration(pp)
        if ok:
            patch_ok += 1
        pbar.update(1)
    pbar.close()

    print(f"\n=== 模式5 处理完成 ===")
    print(f"  去重成功: {success_count}")
    print(f"  伪时长注入成功: {patch_ok}/{len(processed_paths)}")


def run_mode6(input_dir):
    """模式6: 模式5全部去重 + 推流加权伪时长(1~3分钟) + 音频微调"""
    from video_processor_simple import find_best_ffmpeg
    FFMPEG = find_best_ffmpeg()
    print("\n[模式 6] 推流加权模式")
    print("-" * 40)
    print("  区别于模式5:")
    print("   · 伪时长伪装到 1~3 分钟（平台权重最高区间）")
    print("   · 短于1分钟 → 显示60~90秒（消除-10%降权）")
    print("   · 长于3分钟 → 显示120~180秒（消除-20%降权）")
    print("   · 1~3分钟区间 → 保持80~95%真实时长")
    print("   · 🆕 Anime4K GPU 实时增强（线条锐化+降噪）")
    print("")

    # 检查 Anime4K 可用性
    a4k_exe = os.path.join(os.path.dirname(__file__),
                           "完整包138/Waifu2x-Extension-GUI-v3.138.01-Win64/"
                           "waifu2x-extension-gui/Anime4K/Anime4K_waifu2xEX.exe")
    use_anime4k = os.path.exists(a4k_exe)

    # 阶段1: 去重 → 有Anime4K时输出到临时目录，否则直接输出
    import tempfile, shutil, time
    if use_anime4k:
        tmp_dir = tempfile.mkdtemp(prefix="mode6_")
        # 临时修改 batch_process 输出到 tmp_dir（通过 hack get_output_dir）
        # 直接改用内联处理
        from video_processor_simple import VideoProcessor
        video_ext = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv')
        video_files = []
        for fn in os.listdir(input_dir):
            if fn.lower().endswith(video_ext):
                video_files.append(os.path.join(input_dir, fn))
        video_files.sort(key=lambda s: [int(c) if c.isdigit() else c.lower() for c in __import__('re').split(r'(\d+)', s)])
        # 先问输出目录，再处理
        output_dir = get_output_dir(input_dir)

        processed_paths = []
        success_count = 0
        for i, vp in enumerate(video_files, 1):
            name = os.path.splitext(os.path.basename(vp))[0]
            tmp_out = os.path.join(tmp_dir, f"{name}_tmp.mp4")
            print(f"\n  [{i}/{len(video_files)}] 去重: {os.path.basename(vp)[:40]}")
            proc = VideoProcessor(vp, tmp_out, {'use_gpu': True, 'aggressive': True, 'mode6': True})
            if proc.run():
                success_count += 1
                processed_paths.append((vp, tmp_out, name))

        if success_count == 0:
            print("\n  ⚠️ 无成功，跳过后续")
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return

        # 阶段1.5: Anime4K 直接输出到最终目录
        print("\n" + "=" * 50)
        print("  阶段 1.5/3: Anime4K GPU 增强 → 最终输出")
        print("=" * 50)
        import subprocess
        a4k_ok = 0
        env = os.environ.copy()
        ffmpeg_dir = os.path.join(os.path.dirname(__file__),
                      "ffmpeg-2026-06-08-git-6028720d70-full_build",
                      "ffmpeg-2026-06-08-git-6028720d70-full_build", "bin")
        env['PATH'] = ffmpeg_dir + ';' + env.get('PATH', '')

        for i, (orig_vp, tmp_vp, name) in enumerate(processed_paths, 1):
            final_out = os.path.join(output_dir, f"{name}_去重.mp4")
            in_size = os.path.getsize(tmp_vp)
            t_start = time.time()
            cmd = [a4k_exe, '-i', tmp_vp, '-o', final_out,
                   '-v', '-q', '-M', 'opencl', '-Q', '2',
                   '-f', '-b', '-a',
                   '-p', '1', '-n', '2', '-c', '0.2', '-g', '0.5',
                   '-z', '1.0', '-t', '8']
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=False,
                                    env=env, creationflags=0x08000000)
            try:
                import psutil
                p = psutil.Process(proc.pid)
                p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            except: pass
            while proc.poll() is None:
                elapsed = time.time() - t_start
                if os.path.exists(final_out):
                    pct = min(99, int(os.path.getsize(final_out) / max(1, in_size * 1.8) * 100))
                    sys.stdout.write(f"\r  [{i}/{success_count}] {name[:25]} | {pct}% [{elapsed:.0f}s]")
                else:
                    sys.stdout.write(f"\r  [{i}/{success_count}] {name[:25]} | 处理中 [{elapsed:.0f}s]")
                sys.stdout.flush()
                time.sleep(0.5)
            proc.wait()
            print()
            if proc.returncode == 0 and os.path.exists(final_out):
                # 注入元数据
                subprocess.run(
                    [FFMPEG, '-y', '-i', final_out,
                     '-c', 'copy', '-movflags', '+faststart',
                     '-metadata', 'comment=含AI生成内容；可能使用AI技术制作；可能含有AI生成内容',
                     final_out + '.meta.mp4'],
                    capture_output=True, text=False, timeout=120, creationflags=0x08000000)
                if os.path.exists(final_out + '.meta.mp4'):
                    os.replace(final_out + '.meta.mp4', final_out)
                a4k_ok += 1
                print(f"  ✅ [{i}/{success_count}] {name[:40]}")
            else:
                # Anime4K 失败则保留去重版本
                shutil.copy2(tmp_vp, final_out)
                print(f"  ⚠️ [{i}/{success_count}] Anime4K失败，保留去重版")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"  Anime4K: {a4k_ok}/{success_count}")
        processed_paths = [os.path.join(output_dir, f"{name}_去重.mp4") for _, _, name in processed_paths]

    else:
        # 无 Anime4K → 正常流程
        print("=" * 50)
        print("  阶段 1/2: GPU加速 + 强化去重")
        print("=" * 50)
        config = {'use_gpu': True, 'aggressive': True, 'mode6': True}
        result = batch_process(input_dir, config)
        success_count, output_dir, processed_paths = result
        if success_count == 0:
            return

    if success_count == 0:
        return

    # 阶段2: 推流加权伪时长注入
    print("\n" + "=" * 50)
    print("  阶段 2/3: MP4 推流加权伪时长注入（伪装到 1~3 分钟）")
    print("=" * 50)
    from pseudo_duration import apply_pseudo_duration
    from progress_utils import ProgressBar

    patch_ok = 0
    pbar = ProgressBar(len(processed_paths), "推流加权伪时长")
    for i, pp in enumerate(processed_paths, 1):
        fname = os.path.basename(pp)
        pbar.set_description(f"[{i}/{len(processed_paths)}] {fname[:30]}")
        ok, real, fake = apply_pseudo_duration(pp, mode='boost')
        if ok:
            patch_ok += 1
        pbar.update(1)
    pbar.close()

    print(f"\n=== 模式6 处理完成 ===")
    print(f"  去重成功: {success_count}")
    print(f"  正向伪时长注入成功: {patch_ok}/{len(processed_paths)}")


def run_mode9(input_dir):
    """模式9: RIFE帧插值 + Mode 6全流程"""
    from waifu2x_processor import Waifu2xProcessor
    import tempfile, shutil

    print("\n[模式 9] RIFE插帧 + 去重增强")
    print("-" * 40)
    print("  阶段0: RIFE AI帧插值（2倍帧数）")
    print("  阶段1: Mode 6去重增强")
    print("  阶段2: 推流加权伪时长")
    print("")

    # 阶段0: RIFE 插帧 → 临时目录
    tmp_dir = tempfile.mkdtemp(prefix="rife_")
    video_ext = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv')
    video_files = sorted(
        [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith(video_ext)])

    w2x = Waifu2xProcessor()
    if not w2x.models.get('rife'):
        print("  ❌ RIFE 模型不可用")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return

    interp_paths = []
    for i, vp in enumerate(video_files, 1):
        name = os.path.splitext(os.path.basename(vp))[0]
        tmp_out = os.path.join(tmp_dir, f"{name}_rife.mp4")
        print(f"\n  [{i}/{len(video_files)}] RIFE插帧: {os.path.basename(vp)[:40]}")
        ok = w2x.process(vp, tmp_out, mode='rife')
        if ok:
            interp_paths.append((vp, tmp_out, name))
        else:
            print(f"    ⚠️ RIFE失败，跳过")

    if not interp_paths:
        print("\n  ❌ 无成功插帧视频")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return
    print(f"\n  RIFE插帧: {len(interp_paths)}/{len(video_files)}")

    # 阶段1+2: Mode 6流水线（复用 run_mode6 的逻辑）
    a4k_exe = os.path.join(os.path.dirname(__file__),
                           "完整包138/Waifu2x-Extension-GUI-v3.138.01-Win64/"
                           "waifu2x-extension-gui/Anime4K/Anime4K_waifu2xEX.exe")
    use_anime4k = os.path.exists(a4k_exe)
    from video_processor_simple import find_best_ffmpeg, VideoProcessor
    FFMPEG = find_best_ffmpeg()
    output_dir = get_output_dir(input_dir)

    processed_paths = []
    success_count = 0

    for i, (orig_vp, rife_vp, name) in enumerate(interp_paths, 1):
        if use_anime4k:
            # Anime4K 路径：去重→temp, Anime4K→final
            tmp_de = os.path.join(tmp_dir, f"{name}_de.mp4")
            proc = VideoProcessor(rife_vp, tmp_de, {'use_gpu': True, 'aggressive': True, 'mode6': True})
            if proc.run():
                final_out = os.path.join(output_dir, f"{name}_去重.mp4")
                a4k_ok = False
                if os.path.exists(a4k_exe):
                    import subprocess, time
                    env_a4k = os.environ.copy()
                    env_a4k['PATH'] = os.path.join(os.path.dirname(__file__),
                        "ffmpeg-2026-06-08-git-6028720d70-full_build/ffmpeg-2026-06-08-git-6028720d70-full_build/bin") + ';' + env_a4k.get('PATH', '')
                    cmd_a4k = [a4k_exe, '-i', tmp_de, '-o', final_out,
                               '-v', '-q', '-M', 'opencl', '-Q', '2', '-f', '-b', '-a',
                               '-p', '1', '-n', '2', '-c', '0.2', '-g', '0.5', '-z', '1.0', '-t', '8']
                    proc_a4k = subprocess.Popen(cmd_a4k, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                text=False, env=env_a4k, creationflags=0x08000000)
                    while proc_a4k.poll() is None:
                        elapsed = time.time() - (time.time())
                        sys.stdout.write(f"\r  Anime4K: {name[:25]} | 处理中")
                        sys.stdout.flush(); time.sleep(0.5)
                    proc_a4k.wait(); print()
                    if proc_a4k.returncode == 0 and os.path.exists(final_out):
                        a4k_ok = True
                if not a4k_ok:
                    shutil.copy2(tmp_de, final_out)
                # 元数据
                import subprocess
                subprocess.run([FFMPEG, '-y', '-i', final_out, '-c', 'copy', '-movflags', '+faststart',
                    '-metadata', 'comment=含AI生成内容；可能使用AI技术制作；可能含有AI生成内容',
                    final_out + '.m.mp4'], capture_output=True, text=False, timeout=120, creationflags=0x08000000)
                if os.path.exists(final_out + '.m.mp4'):
                    os.replace(final_out + '.m.mp4', final_out)
                success_count += 1
                processed_paths.append(final_out)
                print(f"  ✅ [{i}/{len(interp_paths)}] {name[:40]}")
        else:
            tmp_de = os.path.join(tmp_dir, f"{name}_de.mp4")
            proc = VideoProcessor(rife_vp, tmp_de, {'use_gpu': True, 'aggressive': True, 'mode6': True})
            if proc.run():
                final_out = os.path.join(output_dir, f"{name}_去重.mp4")
                shutil.copy2(tmp_de, final_out)
                success_count += 1
                processed_paths.append(final_out)

    shutil.rmtree(tmp_dir, ignore_errors=True)

    if success_count == 0:
        return

    # 阶段2: 伪时长
    print("\n" + "=" * 50)
    print("  阶段2: 推流加权伪时长注入")
    print("=" * 50)
    from pseudo_duration import apply_pseudo_duration
    from progress_utils import ProgressBar
    patch_ok = 0
    pbar = ProgressBar(len(processed_paths), "伪时长")
    for i, pp in enumerate(processed_paths, 1):
        pbar.set_description(f"[{i}/{len(processed_paths)}] {os.path.basename(pp)[:30]}")
        ok, _, _ = apply_pseudo_duration(pp, mode='boost')
        if ok: patch_ok += 1
        pbar.update(1)
    pbar.close()
    print(f"\n=== 模式9 完成 ===")
    print(f"  成功: {success_count}/{len(video_files)}, 伪时长: {patch_ok}/{len(processed_paths)}")


def run_mode10(input_dir):
    """模式10: RIFE插帧 + SPAN超分 + Mode 6全流程"""
    from waifu2x_processor import Waifu2xProcessor
    import tempfile, shutil, subprocess, time

    print("\n[模式 10] RIFE + SPAN + 去重增强")
    print("-" * 40)
    print("  阶段0: RIFE AI帧插值（2倍帧数）")
    print("  阶段0.5: SPAN 超分增强（2倍分辨率）")
    print("  阶段1: Mode 6去重增强")
    print("  阶段2: 推流加权伪时长")
    print("  ⚠️ 耗时较长，建议1分钟以内视频")
    print("")

    # 检查 SPAN
    span_dir = os.path.join(os.path.dirname(__file__), "SPAN-ncnn-vulkan",
                            "span-ncnn-vulkan-20240831-055257-windows")
    span_exe = os.path.join(span_dir, "span-ncnn-vulkan.exe")
    span_models = os.path.join(span_dir, "models")
    if not os.path.exists(span_exe):
        print("  ❌ SPAN 未安装，请先下载")
        return

    # 阶段0: RIFE
    tmp_dir = tempfile.mkdtemp(prefix="mode10_")
    video_ext = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv')
    video_files = sorted(
        [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith(video_ext)])

    w2x = Waifu2xProcessor()
    if not w2x.models.get('rife'):
        print("  ❌ RIFE 模型不可用"); shutil.rmtree(tmp_dir, ignore_errors=True); return

    rife_ok = []
    for i, vp in enumerate(video_files, 1):
        name = os.path.splitext(os.path.basename(vp))[0]
        tmp_rife = os.path.join(tmp_dir, f"{name}_rife.mp4")
        print(f"\n  [{i}/{len(video_files)}] RIFE: {os.path.basename(vp)[:40]}")
        if w2x.process(vp, tmp_rife, mode='rife'):
            rife_ok.append((vp, tmp_rife, name))
        else:
            print(f"    ⚠️ 失败，跳过")
    if not rife_ok:
        print("  ❌ 无成功"); shutil.rmtree(tmp_dir, ignore_errors=True); return

    # 阶段0.5: SPAN 2x
    FFMPEG = os.path.join(os.path.dirname(__file__),
              "ffmpeg-2026-06-08-git-6028720d70-full_build/ffmpeg-2026-06-08-git-6028720d70-full_build/bin/ffmpeg.exe")
    span_ok = []
    for i, (orig_vp, rife_vp, name) in enumerate(rife_ok, 1):
        fi = os.path.join(tmp_dir, f"span_in_{i}")
        fo = os.path.join(tmp_dir, f"span_out_{i}")
        os.makedirs(fi, exist_ok=True); os.makedirs(fo, exist_ok=True)
        print(f"  [{i}/{len(rife_ok)}] SPAN拆帧: {name[:30]}")
        subprocess.run([FFMPEG, '-y', '-i', rife_vp, '-vsync', '0', '-qscale:v', '2',
                        os.path.join(fi, 'f%08d.png')],
                       capture_output=True, creationflags=0x08000000, timeout=300)
        in_cnt = len(os.listdir(fi))
        print(f"    SPAN 2x: {in_cnt}帧...")
        t0 = time.time()
        subprocess.run([span_exe, '-m', span_models, '-n', 'spanx2_ch48', '-s', '2',
                        '-i', fi, '-o', fo, '-j', '2:2:2'],
                       capture_output=True, creationflags=0x08000000, timeout=7200)
        t1 = time.time()
        out_cnt = len(os.listdir(fo))
        if out_cnt > 0:
            tmp_span = os.path.join(tmp_dir, f"{name}_span.mp4")
            subprocess.run([FFMPEG, '-y', '-framerate', '60', '-i',
                            os.path.join(fo, 'f%08d.png'), '-i', rife_vp,
                            '-c:v', 'libx264', '-crf', '22', '-preset', 'fast',
                            '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                            '-map', '0:v', '-map', '1:a', '-shortest', tmp_span],
                           capture_output=True, creationflags=0x08000000, timeout=600)
            span_ok.append((orig_vp, tmp_span, name))
            print(f"    ✅ SPAN: {in_cnt}→{out_cnt}帧, {t1-t0:.0f}s")
        else:
            print(f"    ❌ SPAN失败")
        shutil.rmtree(fi, ignore_errors=True); shutil.rmtree(fo, ignore_errors=True)

    if not span_ok:
        print("  ❌ SPAN全失败"); shutil.rmtree(tmp_dir, ignore_errors=True); return

    # 阶段1+2: Mode 6
    a4k_exe = os.path.join(os.path.dirname(__file__),
                           "完整包138/Waifu2x-Extension-GUI-v3.138.01-Win64/"
                           "waifu2x-extension-gui/Anime4K/Anime4K_waifu2xEX.exe")
    use_anime4k = os.path.exists(a4k_exe)
    from video_processor_simple import find_best_ffmpeg, VideoProcessor
    FFMPEG2 = find_best_ffmpeg()
    output_dir = get_output_dir(input_dir)
    processed_paths = []; success_count = 0

    for i, (orig_vp, span_vp, name) in enumerate(span_ok, 1):
        tmp_de = os.path.join(tmp_dir, f"{name}_de.mp4")
        proc = VideoProcessor(span_vp, tmp_de, {'use_gpu': True, 'aggressive': True, 'mode6': True})
        if proc.run():
            final_out = os.path.join(output_dir, f"{name}_去重.mp4")
            if use_anime4k:
                env_a4k = os.environ.copy()
                env_a4k['PATH'] = os.path.dirname(FFMPEG) + ';' + env_a4k.get('PATH', '')
                cmd = [a4k_exe, '-i', tmp_de, '-o', final_out, '-v', '-q', '-M', 'opencl', '-Q', '2',
                       '-f', '-b', '-a', '-p', '1', '-n', '2', '-c', '0.2', '-g', '0.5', '-z', '1.0', '-t', '8']
                sp = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      text=False, env=env_a4k, creationflags=0x08000000)
                while sp.poll() is None:
                    sys.stdout.write(f"\r  Anime4K: {name[:25]} | 处理中"); sys.stdout.flush(); time.sleep(0.5)
                sp.wait(); print()
                if sp.returncode != 0 or not os.path.exists(final_out):
                    shutil.copy2(tmp_de, final_out)
            else:
                shutil.copy2(tmp_de, final_out)
            subprocess.run([FFMPEG2, '-y', '-i', final_out, '-c', 'copy', '-movflags', '+faststart',
                '-metadata', 'comment=含AI生成内容；可能使用AI技术制作；可能含有AI生成内容',
                final_out + '.m.mp4'], capture_output=True, text=False, timeout=120, creationflags=0x08000000)
            if os.path.exists(final_out + '.m.mp4'): os.replace(final_out + '.m.mp4', final_out)
            success_count += 1; processed_paths.append(final_out)
            print(f"  ✅ [{i}/{len(span_ok)}] {name[:40]}")

    shutil.rmtree(tmp_dir, ignore_errors=True)
    if success_count == 0: return

    print("\n" + "=" * 50)
    print("  阶段2: 推流加权伪时长注入")
    print("=" * 50)
    from pseudo_duration import apply_pseudo_duration
    from progress_utils import ProgressBar
    patch_ok = 0; pbar = ProgressBar(len(processed_paths), "伪时长")
    for i, pp in enumerate(processed_paths, 1):
        pbar.set_description(f"[{i}/{len(processed_paths)}] {os.path.basename(pp)[:30]}")
        ok, _, _ = apply_pseudo_duration(pp, mode='boost')
        if ok: patch_ok += 1
        pbar.update(1)
    pbar.close()
    print(f"\n=== 模式10 完成 ===")
    print(f"  成功: {success_count}/{len(video_files)}, 伪时长: {patch_ok}/{len(processed_paths)}")


def run_mode7(input_dir_a):
    """模式7: AB抽帧混合 — 240fps底层帧混合"""
    print("\n[模式 7] AB 抽帧混合模式")
    print("-" * 40)
    print("  算法: 240fps, A帧12.5%, B帧随机池87.5%→平台编码器丢弃B噪点保留A")
    print("")

    # B 素材目录
    b_dir = safe_input("  请输入 B 素材目录路径: ").strip()
    if not os.path.isdir(b_dir):
        print("❌ B 素材目录无效")
        return

    # GPU 选择
    use_gpu = False
    try:
        import ctypes
        ctypes.WinDLL('nvcuda.dll', mode=ctypes.RTLD_GLOBAL)
        use_gpu = True
        print("  ✅ GPU 加速可用")
    except:
        print("  ⚠️ GPU 不可用，使用 CPU 编码")

    # 输出目录
    output_dir = get_output_dir(input_dir_a)

    # 执行
    from ab_processor import batch_ab_process
    batch_ab_process(input_dir_a, b_dir, output_dir, use_gpu)


def run_mode8():
    """模式8: 批量视频合并"""
    print("\n[模式 8] 批量视频合并")
    print("-" * 40)
    print("  选择父目录，每个子文件夹的视频按序合并成一条")
    parent_dir = safe_input("\n  请输入父目录路径: ").strip()
    if not os.path.isdir(parent_dir):
        print("❌ 无效目录")
        return

    use_gpu = False
    try:
        import ctypes
        ctypes.WinDLL('nvcuda.dll', mode=ctypes.RTLD_GLOBAL)
        use_gpu = True
    except:
        pass

    output_dir = get_output_dir(parent_dir)
    from video_merger import batch_merge
    batch_merge(parent_dir, output_dir, use_gpu)


def get_output_dir(input_dir):
    """获取输出目录 - 自由选择
    1. 直接回车 → 在输入视频目录内创建"去重后视频N月N日"
    2. 输入路径 → 使用自定义路径
    """
    import datetime
    import os

    today = datetime.date.today()
    date_str = f"{today.month}月{today.day}日"

    user_input = safe_input(f"\n  输入输出目录 (回车在视频目录内创建, 或输入自定义路径): ").strip()

    if user_input == '':
        base_dir = os.path.abspath(input_dir)
        folder_name = f"去重后视频{date_str}"
        output_dir = os.path.join(base_dir, folder_name)

        counter = 1
        while os.path.exists(output_dir):
            folder_name = f"{counter}_去重后视频{date_str}"
            output_dir = os.path.join(base_dir, folder_name)
            counter += 1
    else:
        output_dir = user_input

    os.makedirs(output_dir, exist_ok=True)
    print(f"  输出目录: {output_dir}")
    return output_dir

def batch_process(input_dir, config):
    """批量处理视频
    Returns: (success_count, output_dir, processed_paths) 或 None（失败时）
    """
    import os

    # 如果启用AI模式，委托给 main_ultimate.py
    if config.get('use_ai', False):
        return batch_process_ai(input_dir, config)

    from video_processor_simple import VideoProcessor

    # 获取视频文件
    video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv')
    video_files = []

    for filename in os.listdir(input_dir):
        if filename.lower().endswith(video_extensions):
            video_files.append(os.path.join(input_dir, filename))

    if not video_files:
        print("未找到视频文件")
        return (0, None, [])

    # 选择输出目录
    output_dir = get_output_dir(input_dir)

    # 处理视频
    success_count = 0
    processed_paths = []
    from progress_utils import ProgressBar, Spinner
    pbar = ProgressBar(len(video_files), "批量去重")

    for i, video_path in enumerate(video_files, 1):
        fname = os.path.basename(video_path)
        pbar.set_description(f"[{i}/{len(video_files)}] {fname[:30]}")

        filename = os.path.basename(video_path)
        name, ext = os.path.splitext(filename)
        output_path = os.path.join(output_dir, f"{name}_去重{ext}")

        # 用Spinner包裹处理过程
        spinner = Spinner(f"FFmpeg处理 {fname[:25]}")
        spinner.start()
        processor = VideoProcessor(video_path, output_path, config)
        ok = processor.run()
        spinner.stop("完成" if ok else "失败")

        if ok:
            success_count += 1
            processed_paths.append(output_path)
        pbar.update(1)

    pbar.close()

    print(f"\n=== 处理完成 ===")
    print(f"成功: {success_count}/{len(video_files)}")
    return (success_count, output_dir, processed_paths)


def batch_process_ai(input_dir, config):
    """AI增强批量处理 - 使用 main_ultimate.py"""
    import os
    from main_ultimate import process_video_with_ai, get_video_files, check_all_models, AI_MODELS, show_model_info
    
    # 检查并显示AI模型
    check_all_models()
    show_model_info()
    
    # 获取视频文件
    video_files = get_video_files(input_dir)
    
    if not video_files:
        print("未找到视频文件")
        return (0, None, [])

    # 用户手动选择AI模型
    print("\n🎯 AI增强选项:")

    # 收集可用模型
    interp_options = []
    if AI_MODELS['rife']:
        interp_options.append(('rife', 'RIFE 帧插值 (强, 较快)'))
    if AI_MODELS['dain']:
        interp_options.append(('dain', 'DAIN 帧插值 (最强, 慢)'))
    if AI_MODELS['cain']:
        interp_options.append(('cain', 'CAIN 帧插值 (快)'))
    if AI_MODELS['ifrnet']:
        interp_options.append(('ifrnet', 'IFRNet 帧插值'))

    enhance_options = []
    if AI_MODELS['waifu2x']:
        enhance_options.append(('waifu2x', 'Waifu2x 超分辨率'))
    if AI_MODELS['real-cugan']:
        enhance_options.append(('real-cugan', 'Real-CUGAN 动漫超分'))
    if AI_MODELS['anime4k']:
        enhance_options.append(('anime4k', 'Anime4K 画质增强'))
    if AI_MODELS['real-esrgan']:
        enhance_options.append(('real-esrgan', 'Real-ESRGAN 超分'))
    if AI_MODELS['esrgan']:
        enhance_options.append(('esrgan', 'Real-ESRGAN 独立超分'))
    if AI_MODELS['cliq']:
        enhance_options.append(('cliq', 'CLIQ 质量评估'))

    if not interp_options and not enhance_options:
        print("  ⚠️ 没有检测到可用AI模型，回退到标准模式")
        return batch_process(input_dir, {'use_gpu': True, 'use_ai': False})

    # ---- 帧插值模型选择（互斥，选一个或不选） ----
    if interp_options:
        print("\n  【帧插值模型】(互斥，只能选一个或不选)")
        for idx, (key, desc) in enumerate(interp_options, 1):
            print(f"    {idx}. {desc}")
        print(f"    0. 跳过帧插值")
        choice = safe_input("  请选择 (0~{0}): ".format(len(interp_options))).strip()
        try:
            idx = int(choice)
            if 1 <= idx <= len(interp_options):
                key, desc = interp_options[idx - 1]
                config[f'use_{key}'] = True
                print(f"  ✓ 已启用: {desc}")
            else:
                print("  已跳过帧插值")
        except:
            print("  已跳过帧插值")

    # ---- 画质增强模型选择（可多选） ----
    if enhance_options:
        print("\n  【画质增强模型】(可多选，逐个确认)")
        for key, desc in enhance_options:
            choice = safe_input(f"  启用 {desc}? (y/n): ").strip().lower()
            if choice == 'y':
                config[f'use_{key}'] = True
                print(f"    ✓ 已启用")
            else:
                config[f'use_{key}'] = False
                print(f"    - 已跳过")

    enabled = [k for k, v in config.items() if v and k.startswith('use_') and k != 'use_gpu' and k != 'use_ai']
    if not enabled:
        print("  未选择任何AI模型，回退到标准模式")
        return batch_process(input_dir, {'use_gpu': True, 'use_ai': False})

    print(f"\n  已启用: {', '.join(enabled)}")
    
    # 选择输出目录
    output_dir = get_output_dir(input_dir)
    
    # 处理视频
    from progress_utils import ProgressBar
    success_count = 0
    processed_paths = []
    pbar = ProgressBar(len(video_files), "AI批量去重")

    for i, video_path in enumerate(video_files, 1):
        fname = os.path.basename(video_path)
        pbar.set_description(f"[{i}/{len(video_files)}] {fname[:30]}")

        name, ext = os.path.splitext(fname)
        output_path = os.path.join(output_dir, f"{name}_AI去重{ext}")

        try:
            ok = process_video_with_ai(video_path, output_dir, config.copy())
            if ok:
                success_count += 1
                processed_paths.append(output_path)
        except Exception as e:
            print(f"\n  ❌ 处理失败: {e}")
        pbar.update(1)

    pbar.close()

    print(f"\n=== 处理完成 ===")
    print(f"成功: {success_count}/{len(video_files)}")
    return (success_count, output_dir, processed_paths)

def get_input_dir():
    """获取输入目录"""
    if len(sys.argv) > 1:
        input_dir = sys.argv[1]
        if os.path.isdir(input_dir):
            return input_dir
    
    return safe_input("请输入视频目录路径: ").strip()

def main():
    """主函数"""
    print_banner()

    # 检查环境（仅运行一次）
    gpu_available = check_environment()

    # 获取初始输入目录
    input_dir = get_input_dir()

    while True:
        try:
            if not os.path.isdir(input_dir):
                print("❌ 无效的目录路径")
                input_dir = safe_input("请重新输入视频目录路径: ").strip()
                continue

            # 显示菜单
            print_menu()

            # 获取用户选择
            choice = safe_input("请选择模式 (1/2/3/4/5/6/7/8/9/10): ").strip()

            # 根据选择运行对应模式
            if choice == '1':
                run_standard_mode(input_dir)
            elif choice == '2':
                if not gpu_available:
                    print("⚠️  GPU不可用，将使用CPU模式")
                run_gpu_mode(input_dir)
            elif choice == '3':
                run_ai_mode(input_dir)
            elif choice == '4':
                run_custom_mode(input_dir)
            elif choice == '5':
                if not gpu_available:
                    print("⚠️  GPU不可用，将使用CPU编码")
                run_mode5(input_dir)
            elif choice == '6':
                if not gpu_available:
                    print("⚠️  GPU不可用，将使用CPU编码")
                run_mode6(input_dir)
            elif choice == '7':
                run_mode7(input_dir)
            elif choice == '8':
                run_mode8()
            elif choice == '9':
                run_mode9(input_dir)
            elif choice == '10':
                run_mode10(input_dir)
            else:
                print("无效选择，默认使用GPU加速模式")
                run_gpu_mode(input_dir)

            # 处理完成后询问是否继续
            print("\n" + "-" * 40)
            next_action = safe_input("是否继续使用脚本？(y/n): ").strip().lower()

            if next_action == 'y':
                input_dir = get_input_dir()
            else:
                print("已退出")
                break

        except (BackStep, KeyboardInterrupt):
            print("\n↩ 返回模式选择")
            continue

if __name__ == "__main__":
    main()
