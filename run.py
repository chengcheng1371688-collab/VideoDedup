"""
统一入口脚本 - 视频去重工具
支持: GPU加速,AI增强,标准处理,伪时长
Ctrl+C=返回菜单
规则: 所有新模式必须用 get_output_dir() 统一输出路径
      所有耗时步骤必须有进度条
      处理后视频必须写入 comment 元数据
"""
import os
import sys
from key_input import safe_input, BackStep

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

def _fmt_time(seconds):
    """格式化耗时: 小于60s显示秒, 大于等于60s显示分加秒"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}分{s}秒"

def print_menu():
    """打印菜单"""
    print("🎯 选择处理模式:")
    print("-" * 40)
    print("  1. [快速模式] 标准处理 - CPU处理,快速稳定")
    print("  2. [推荐模式] GPU加速 - GPU解码+CPU编码,平衡之选")
    print("  3. [最强模式] AI增强 - DAIN/RIFE帧插值,最强去重")
    print("  4. [自定义模式] 自定义参数 - 自由配置各项参数")
    print("  5. [伪时长模式] GPU加速 + 分段滤镜 + 伪时长注入(3~12秒)")
    print("  6. [正向伪时长] 模式5全部去重 + 推流加权伪时长 + 音频微调")
    print("  7. [AB包裹+增强] softlight包裹 + Mode6全流程")
    print("  8. [批量合并] 父目录下所有子文件夹分别合并成一条视频")
    print("  9. [RIFE+包裹] RIFE帧插值 + Mode 7 AB包裹")
    print("  10.[完全增强] RIFE + SPAN超分 + Mode 6全流程")
    print("  11.[最强去重] RIFE + 音频改造 + 分段乱序 + AB包裹")
    print("  12.[极限效率] TRT RIFE + AB包裹 (VapourSynth+NVENC)")
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
        print("无效选择,使用默认配置")
        config = {'use_gpu': True}
    
    batch_process(input_dir, config)


def run_mode5(input_dir):
    """模式5: GPU加速 + 分段滤镜去重 + 伪时长注入"""
    import time; t_batch = time.time()
    print("\n[模式 5] 伪时长模式")
    print("-" * 40)
    print("  处理流程: GPU加速解码 -> 分段滤镜去重 -> GPU编码 -> MP4伪时长注入")
    print("  伪时长范围: 随机 3~12 秒")
    print("")

    # 阶段1: GPU加速 + 强化滤镜(丢帧/黑边/大幅参数/微旋转)
    print("=" * 50)
    print("  阶段 1/2: GPU加速 + 强化去重处理")
    print("=" * 50)
    config = {'use_gpu': True, 'aggressive': True}
    result = batch_process(input_dir, config)
    success_count, output_dir, processed_paths = result

    if success_count == 0 or not processed_paths:
        print("\n  ⚠️ 阶段1无成功处理的视频,跳过伪时长注入")
        return

    # 阶段2: 伪时长注入
    print("\n" + "=" * 50)
    print("  阶段 2/2: MP4 伪时长注入(随机 3~12 秒)")
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
    print(f"⏱️ [模式5] 总耗时: {_fmt_time(time.time() - t_batch)}")





def run_mode6(input_dir):
    """模式6: 模式5全部去重 + 推流加权伪时长(1~3分钟) + 音频微调"""
    import time; t_batch = time.time()
    print("\n[模式 6] 推流加权模式")
    print("-" * 40)
    print("  区别于模式5:")
    print("   - 伪时长伪装到 1~3 分钟(平台权重最高区间)")
    print("   - 短于1分钟 -> 显示60~90秒(消除-10%降权)")
    print("   - 长于3分钟 -> 显示120~180秒(消除-20%降权)")
    print("   - 1~3分钟区间 -> 保持80~95%真实时长")
    print("")

    # 阶段1: GPU加速 + 强化去重
    print("=" * 50)
    print("  阶段 1/2: GPU加速 + 强化去重")
    print("=" * 50)
    config = {'use_gpu': True, 'aggressive': True, 'mode6': True}
    result = batch_process(input_dir, config)
    success_count, output_dir, processed_paths = result
    if success_count == 0:
        return

    # 阶段2: 推流加权伪时长注入
    print("\n" + "=" * 50)
    print("  阶段 2/3: MP4 推流加权伪时长注入(伪装到 1~3 分钟)")
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
    print(f"⏱️ [模式6] 总耗时: {_fmt_time(time.time() - t_batch)}")





def run_mode7(input_dir_a):
    """模式7: AB包裹叠加 + Mode6全流程增强"""
    import time; t_batch = time.time()
    print("\n[模式 7] AB包裹增强模式")
    print("-" * 40)
    print("  算法: softlight包裹 + Mode6全流程增强")
    print("  阶段1: AB softlight包裹 (B每帧微偏移,保鲜膜效果)")
    print("  阶段2: Mode6强化 (黑边/呼吸/旋转/噪点/混响)")
    print("  阶段3: boost伪时长")
    print("")

    b_dir = safe_input("  请输入 B 素材目录路径: ").strip()
    if not os.path.isdir(b_dir):
        print("❌ B 素材目录无效")
        return

    use_gpu = False
    try:
        import ctypes
        ctypes.WinDLL('nvcuda.dll', mode=ctypes.RTLD_GLOBAL)
        use_gpu = True
        print("  ✅ GPU 加速可用")
    except:
        print("  ⚠️ GPU 不可用,使用 CPU 编码")

    output_dir = get_output_dir(input_dir_a)

    print("=" * 50)
    print("  阶段 1/2: AB softlight 包裹")
    print("=" * 50)
    import tempfile, shutil
    tmp_dir = tempfile.mkdtemp(prefix="ab7_")
    from ab_processor import batch_ab_process
    ok_count, total = batch_ab_process(input_dir_a, b_dir, tmp_dir, use_gpu)

    if ok_count == 0:
        print("\n  ⚠️ AB 包裹无成功,跳过增强")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return

    print("\n" + "=" * 50)
    print("  阶段 2/2: Mode 6 强化增强")
    print("=" * 50)
    from video_processor_simple import VideoProcessor
    from progress_utils import ProgressBar

    ab_files = sorted([f for f in os.listdir(tmp_dir) if f.endswith('.mp4')])
    success = 0
    pbar = ProgressBar(len(ab_files), "Mode6增强")
    for i, fn in enumerate(ab_files, 1):
        name = os.path.splitext(fn)[0].replace('_AB叠加', '')
        tmp_ab = os.path.join(tmp_dir, fn)
        final_out = os.path.join(output_dir, f"{name}_AB去重.mp4")
        pbar.set_description(f"[{i}/{len(ab_files)}] {name[:25]}")

        proc = VideoProcessor(tmp_ab, final_out, {'use_gpu': use_gpu, 'aggressive': True, 'mode6': True})
        if not proc.run():
            pbar.update(1); continue

        from video_processor_simple import find_best_ffmpeg
        FFMPEG_META = find_best_ffmpeg()
        subprocess.run([FFMPEG_META, '-y', '-i', final_out, '-c', 'copy', '-movflags', '+faststart',
            '-metadata', 'comment=含AI生成内容;可能使用AI技术制作;可能含有AI生成内容',
            final_out + '.m.mp4'], capture_output=True, text=False, timeout=120, creationflags=0x08000000)
        if os.path.exists(final_out + '.m.mp4'): os.replace(final_out + '.m.mp4', final_out)
        success += 1; pbar.update(1)
    pbar.close()
    shutil.rmtree(tmp_dir, ignore_errors=True)

    if success > 0:
        from pseudo_duration import apply_pseudo_duration
        pbar2 = ProgressBar(success, "伪时长"); patch_ok = 0
        for fn in os.listdir(output_dir):
            if fn.endswith('_AB去重.mp4'):
                pp = os.path.join(output_dir, fn)
                if apply_pseudo_duration(pp, mode='boost')[0]: patch_ok += 1
                pbar2.update(1)
        pbar2.close()
        print(f"  伪时长: {patch_ok}/{success}")
    print(f"\n=== 模式7(叠加增强) 完成 === 成功: {success}/{total}")
    print(f"⏱️ [模式7] 总耗时: {_fmt_time(time.time() - t_batch)}")





def run_mode8():
    """模式8: 批量视频合并 - 自适应目录, 支持每文件夹一条/每N集一条, 纯合并不去重"""
    import time; t_batch = time.time()
    import re, subprocess, tempfile, shutil
    from progress_utils import ProgressBar

    print("\n[模式 8] 批量视频合并")
    print("-" * 40)
    dir_input = safe_input("\n  请输入目录路径: ").strip()
    if not os.path.isdir(dir_input):
        print("❌ 无效目录"); return

    video_ext = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv')
    CF = 0x08000000

    # ── 智能识别：子文件夹 还是 单目录 ──
    subdirs_raw = sorted([d for d in os.listdir(dir_input)
                          if os.path.isdir(os.path.join(dir_input, d))])
    # 过滤出包含视频的子文件夹
    subdirs_with_video = []
    for sd in subdirs_raw:
        sd_path = os.path.join(dir_input, sd)
        has_v = any(f.lower().endswith(video_ext) for f in os.listdir(sd_path))
        if has_v:
            subdirs_with_video.append(sd)

    direct_videos = sorted([f for f in os.listdir(dir_input)
                            if f.lower().endswith(video_ext)])

    if subdirs_with_video:
        # 有含视频的子文件夹 → 列出让用户选择
        print(f"\n  检测到 {len(subdirs_with_video)} 个含视频的子文件夹:")
        print(f"    [0] 全选")
        for i, sd in enumerate(subdirs_with_video, 1):
            print(f"    [{i}] {sd}")
        sel_input = safe_input("\n  输入要处理的序号 (如: 0=全选, 1,3,5 或 1-3): ").strip()
        selected = set()
        for part in sel_input.split(','):
            part = part.strip()
            if '-' in part:
                try:
                    a, b = part.split('-', 1)
                    for j in range(int(a.strip()), int(b.strip()) + 1):
                        selected.add(j)
                except: pass
            elif part == '0':
                selected = set(range(1, len(subdirs_with_video) + 1))
                break
            else:
                try: selected.add(int(part))
                except: pass
        selected = sorted(s for s in selected if 1 <= s <= len(subdirs_with_video))
        if not selected:
            print("❌ 未选中任何文件夹"); return
        targets = [(subdirs_with_video[i-1], os.path.join(dir_input, subdirs_with_video[i-1]))
                   for i in selected]
    elif direct_videos:
        # 无子文件夹, 目录本身就有视频
        targets = [(os.path.basename(dir_input), dir_input)]
    else:
        print("❌ 未找到视频文件"); return

    # ── 合并模式 ──
    print("\n  合并模式:")
    print("    1. 所有集合并为一条视频")
    print("    2. 每N集合为一条视频(如2集/3集)")
    mode_choice = safe_input("  请选择 (1/2): ").strip()
    merge_n = 1
    if mode_choice == '2':
        n_input = safe_input("  每几集合为一条? (输入数字): ").strip()
        try: merge_n = max(1, int(n_input))
        except: merge_n = 1
    elif mode_choice != '1':
        print("  无效选择, 默认合并为一条")
        merge_n = 1

    # ── GPU / FFmpeg ──
    use_gpu = False
    try:
        import ctypes
        ctypes.WinDLL('nvcuda.dll', mode=ctypes.RTLD_GLOBAL)
        use_gpu = True; print("  ✅ GPU 加速可用")
    except: print("  ⚠️ GPU 不可用, 使用 CPU 编码")

    base = os.path.dirname(__file__)
    import glob as _glob
    ffmpeg_exe = "ffmpeg"
    for pattern in ["ffmpeg-*-full_build/ffmpeg-*-full_build/bin/ffmpeg.exe",
                    "ffmpeg-*-full_build/bin/ffmpeg.exe"]:
        matches = sorted(_glob.glob(os.path.join(base, pattern)), reverse=True)
        if matches: ffmpeg_exe = matches[0]; break

    encoder = 'h264_nvenc' if use_gpu else 'libx264'
    enc_opts = ['-c:v', encoder, '-preset', 'p1', '-pix_fmt', 'yuv420p'] if use_gpu else \
               ['-c:v', 'libx264', '-crf', '23', '-preset', 'medium', '-pix_fmt', 'yuv420p']

    output_dir = get_output_dir(dir_input)
    total_merged = 0
    pbar = ProgressBar(len(targets), "合并")

    for si, (folder_name, folder_path) in enumerate(targets, 1):
        videos = sorted([os.path.join(folder_path, f) for f in os.listdir(folder_path)
                        if f.lower().endswith(video_ext)])
        if not videos:
            pbar.update(1); continue

        # 提取剧名
        first_name = os.path.splitext(os.path.basename(videos[0]))[0]
        show_name = first_name.rsplit(' - ', 1)[0].rsplit('-', 1)[0].strip()

        # 分组
        total = len(videos)
        if merge_n > 1 and total > merge_n:
            groups = []
            i = 0
            while i < total:
                remaining = total - i
                if remaining < 2 * merge_n:
                    groups.append(list(range(i + 1, total + 1)))
                    break
                else:
                    groups.append(list(range(i + 1, i + merge_n + 1)))
                    i += merge_n
        else:
            groups = [list(range(1, total + 1))]

        pbar.set_description(f"[{si}/{len(targets)}] {folder_name[:20]}")

        for grp in groups:
            st, ed = grp[0], grp[-1]
            out_name = f"{show_name}_{st}-{ed}_合并.mp4" if st != ed else f"{show_name}_{st}_合并.mp4"
            out_path = os.path.join(output_dir, out_name)

            if st == ed:
                shutil.copy2(videos[st - 1], out_path)
                total_merged += 1
                continue

            # FFmpeg concat
            concat_list = os.path.join(tempfile.gettempdir(), f"m8_concat_{os.getpid()}.txt")
            with open(concat_list, 'w', encoding='utf-8') as cf:
                for idx in range(st - 1, ed):
                    cf.write(f"file '{videos[idx].replace(chr(92), '/')}'\n")

            r = subprocess.run([ffmpeg_exe, '-y', '-f', 'concat', '-safe', '0',
                                '-i', concat_list] + enc_opts + [
                                '-c:a', 'aac', '-b:a', '192k',
                                '-movflags', '+faststart',
                                out_path],
                               capture_output=True, creationflags=CF, timeout=7200)
            try: os.remove(concat_list)
            except: pass

            if r.returncode == 0:
                total_merged += 1
                print(f"\n    ✅ {out_name}")
            else:
                err = r.stderr.decode('utf-8', errors='ignore')[-200:] if r.stderr else ''
                print(f"\n    ❌ {out_name}: {err}")

        pbar.update(1)
    pbar.close()

    # ── 伪时长 ──
    if total_merged > 0:
        from pseudo_duration import apply_pseudo_duration
        out_files = sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir)
                           if f.endswith('_合并.mp4')])
        if out_files:
            pbar2 = ProgressBar(len(out_files), "伪时长"); patch_ok = 0
            for fp in out_files:
                if apply_pseudo_duration(fp, mode='boost')[0]: patch_ok += 1
                pbar2.update(1)
            pbar2.close()
            print(f"  伪时长: {patch_ok}/{len(out_files)}")

    print(f"\n=== 模式8 完成 === 合并: {total_merged} 条")
    print(f"⏱️ [模式8] 总耗时: {_fmt_time(time.time() - t_batch)}")

def run_mode9(input_dir):
    """模式9: RIFE帧插值 + Mode 7全流程"""
    from waifu2x_processor import Waifu2xProcessor
    import tempfile, shutil, subprocess, time
    t_batch = time.time()

    print("\n[模式 9] RIFE插帧 + AB包裹增强")
    print("-" * 40)
    print("  阶段0: RIFE AI帧插值(2倍帧数)")
    print("  阶段1: Mode 7 AB包裹")
    print("  阶段2: 推流加权伪时长")
    print("")

    # B 素材目录
    b_dir = safe_input("  请输入 B 素材目录路径: ").strip()
    if not os.path.isdir(b_dir):
        print("❌ B 素材目录无效")
        return

    # GPU
    use_gpu = False
    try:
        import ctypes
        ctypes.WinDLL('nvcuda.dll', mode=ctypes.RTLD_GLOBAL)
        use_gpu = True
    except: pass

    # 阶段0: RIFE
    tmp_dir = tempfile.mkdtemp(prefix="rife_")
    video_ext = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv')
    video_files = sorted(
        [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith(video_ext)])

    w2x = Waifu2xProcessor()
    if not w2x.models.get('rife'):
        print("  ❌ RIFE 模型不可用"); shutil.rmtree(tmp_dir, ignore_errors=True); return

    interp_paths = []
    for i, vp in enumerate(video_files, 1):
        name = os.path.splitext(os.path.basename(vp))[0]
        tmp_out = os.path.join(tmp_dir, f"{name}_rife.mp4")
        print(f"\n  [{i}/{len(video_files)}] RIFE: {os.path.basename(vp)[:40]}")
        if w2x.process(vp, tmp_out, mode='rife'):
            interp_paths.append((vp, tmp_out, name))

    if not interp_paths:
        print("\n  ❌ 无成功"); shutil.rmtree(tmp_dir, ignore_errors=True); return
    print(f"\n  RIFE: {len(interp_paths)}/{len(video_files)}")

    # 阶段1: AB包裹
    print("\n" + "=" * 50)
    print("  阶段1/2: AB 包裹")
    print("=" * 50)
    b_files = sorted([os.path.join(b_dir,f) for f in os.listdir(b_dir) if f.lower().endswith(video_ext)])
    if not b_files: print("❌ B目录无视频"); shutil.rmtree(tmp_dir, ignore_errors=True); return

    output_dir = get_output_dir(input_dir)
    from ab_processor import ab_blend
    from progress_utils import ProgressBar
    wrapped = 0; pbar = ProgressBar(len(interp_paths), "AB包裹")
    for i, (_, rife_vp, name) in enumerate(interp_paths, 1):
        b_vp = b_files[i % len(b_files)]
        final_out = os.path.join(output_dir, f"{name}_去重.mp4")
        pbar.set_description(f"[{i}/{len(interp_paths)}] {name[:25]}")
        if ab_blend(rife_vp, b_vp, final_out, use_gpu): wrapped += 1
        pbar.update(1)
    pbar.close()
    shutil.rmtree(tmp_dir, ignore_errors=True)

    if wrapped == 0: return

    # 阶段2: 伪时长
    print("\n" + "=" * 50)
    print("  阶段2/2: 推流加权伪时长注入")
    print("=" * 50)
    from pseudo_duration import apply_pseudo_duration
    patch_ok = 0; pbar2 = ProgressBar(wrapped, "伪时长")
    for f in os.listdir(output_dir):
        if f.endswith('_去重.mp4'):
            if apply_pseudo_duration(os.path.join(output_dir, f), mode='boost')[0]: patch_ok += 1
            pbar2.update(1)
    pbar2.close()
    print(f"\n=== 模式9 完成 === 成功: {wrapped}/{len(video_files)}, 伪时长: {patch_ok}/{wrapped}")
    print(f"⏱️ [模式9] 总耗时: {_fmt_time(time.time() - t_batch)}")





def run_mode10(input_dir):
    """模式10: RIFE插帧 + SPAN超分 + Mode 6全流程"""
    from waifu2x_processor import Waifu2xProcessor
    import tempfile, shutil, subprocess, time
    t_batch = time.time()

    print("\n[模式 10] RIFE + SPAN + 去重增强")
    print("-" * 40)
    print("  阶段0: RIFE AI帧插值(2倍帧数)")
    print("  阶段0.5: SPAN 超分增强(2倍分辨率)")
    print("  阶段1: Mode 6去重增强")
    print("  阶段2: 推流加权伪时长")
    print("  ⚠️ 耗时较长,建议1分钟以内视频")
    print("")

    span_dir = os.path.join(os.path.dirname(__file__), "SPAN-ncnn-vulkan",
                            "span-ncnn-vulkan-20240831-055257-windows")
    span_exe = os.path.join(span_dir, "span-ncnn-vulkan.exe")
    span_models = os.path.join(span_dir, "models")
    if not os.path.exists(span_exe):
        print("  ❌ SPAN 未安装,请先下载")
        return

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
            print(f"    ⚠️ 失败,跳过")
    if not rife_ok:
        print("  ❌ 无成功"); shutil.rmtree(tmp_dir, ignore_errors=True); return

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
            print(f"    ✅ SPAN: {in_cnt}->{out_cnt}帧, {t1-t0:.0f}s")
        else:
            print(f"    ❌ SPAN失败")
        shutil.rmtree(fi, ignore_errors=True); shutil.rmtree(fo, ignore_errors=True)

    if not span_ok:
        print("  ❌ SPAN全失败"); shutil.rmtree(tmp_dir, ignore_errors=True); return

    a4k_exe = os.path.join(os.path.dirname(__file__),
                           "完整包138/Waifu2x-Extension-GUI-v3.138.01-Win64/"
                           "waifu2x-extension-gui/Mode6强化/Mode6强化_waifu2xEX.exe")
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
                    sys.stdout.write(f"\r  Mode6强化: {name[:25]} | 处理中"); sys.stdout.flush(); time.sleep(0.5)
                sp.wait(); print()
                if sp.returncode != 0 or not os.path.exists(final_out):
                    shutil.copy2(tmp_de, final_out)
            else:
                shutil.copy2(tmp_de, final_out)
            subprocess.run([FFMPEG2, '-y', '-i', final_out, '-c', 'copy', '-movflags', '+faststart',
                '-metadata', 'comment=含AI生成内容;可能使用AI技术制作;可能含有AI生成内容',
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
    print(f"⏱️ [模式10] 总耗时: {_fmt_time(time.time() - t_batch)}")





def run_mode11(input_dir):
    """模式11: RIFE插帧 + 音频深度改造 + AB包裹 + 分段乱序"""
    from waifu2x_processor import Waifu2xProcessor
    import tempfile, shutil, random, subprocess, time
    t_batch = time.time()

    print("\n[模式 11] RIFE + 音频改造 + AB包裹 + 乱序")
    print("-" * 40)
    print("  阶段0: RIFE AI帧插值(2倍帧数)")
    print("  阶段1: 音频深度改造(音量/压缩/动态)")
    print("  阶段2: 分段随机乱序重组")
    print("  阶段3: AB softlight包裹")
    print("  阶段4: 推流加权伪时长")
    print("")

    tmp_dir = tempfile.mkdtemp(prefix="m11_")
    video_ext = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv')
    video_files = sorted([os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith(video_ext)])
    if not video_files: print("❌ 无视频"); return

    print("=" * 50)
    print("  阶段0/4: RIFE 帧插值")
    print("=" * 50)
    w2x = Waifu2xProcessor()
    if not w2x.models.get('rife'): print("❌ RIFE不可用"); shutil.rmtree(tmp_dir, ignore_errors=True); return
    from progress_utils import ProgressBar
    rife_ok = []
    pbar0 = ProgressBar(len(video_files), "RIFE插帧")
    for i, vp in enumerate(video_files, 1):
        name = os.path.splitext(os.path.basename(vp))[0]
        tmp_rife = os.path.join(tmp_dir, f"{name}_rife.mp4")
        pbar0.set_description(f"[{i}/{len(video_files)}] {os.path.basename(vp)[:30]}")
        print(f"\n  [{i}/{len(video_files)}] RIFE: {os.path.basename(vp)[:40]}")
        if w2x.process(vp, tmp_rife, mode='rife'): rife_ok.append((vp, tmp_rife, name))
        pbar0.update(1)
    pbar0.close()
    if not rife_ok: print("❌ RIFE全失败"); shutil.rmtree(tmp_dir, ignore_errors=True); return

    print("\n" + "=" * 50)
    print("  阶段1-2/4: 音频改造 + 分段乱序")
    print("=" * 50)
    pbar = ProgressBar(len(rife_ok), "音频+乱序")
    shuffled_ok = []
    for i, (orig_vp, rife_vp, name) in enumerate(rife_ok, 1):
        tmp_final = os.path.join(tmp_dir, f"{name}_shuffled.mp4")
        af = ("acompressor=threshold=0.1:ratio=4:attack=5:release=50,"
              "volume='1+random(0)*0.3-0.15',"
              "alimiter=limit=0.95,"
              "aresample=44050,aresample=44100")
        dur = ab_processor_get_duration(rife_vp)
        seg_count = max(3, int(dur / 8))
        seg_pts = [0]
        for _ in range(seg_count - 1):
            seg_pts.append(seg_pts[-1] + random.uniform(5, 15))
        seg_pts.append(dur)
        order = list(range(seg_count))
        random.shuffle(order)
        vf_parts = []; af_parts = []
        for j, idx in enumerate(order):
            st, et = seg_pts[idx], seg_pts[idx+1]
            vf_parts.append(f"[0:v]trim=start={st:.1f}:end={et:.1f},setpts=PTS-STARTPTS[v{j}]")
            af_parts.append(f"[0:a]atrim=start={st:.1f}:end={et:.1f},asetpts=PTS-STARTPTS,{af}[a{j}]")
        vf_parts.append(''.join(f"[v{j}]" for j in range(seg_count)) + f"concat=n={seg_count}:v=1:a=0[outv]")
        af_parts.append(''.join(f"[a{j}]" for j in range(seg_count)) + f"concat=n={seg_count}:v=0:a=1[outa]")
        vf_parts.append("[outv]split[main][sub];"
                        "[sub]crop=iw:ih*0.15:0:ih*0.85,noise=alls=2:allf=t,format=yuv420p[sub_noise];"
                        "[main][sub_noise]overlay=0:ih*0.85[outv2]")
        fc = ';'.join(vf_parts + af_parts)
        FFM = ab_processor_get_ffmpeg()
        r = subprocess.run([FFM, '-y', '-i', rife_vp, '-filter_complex', fc, '-map', '[outv2]', '-map', '[outa]',
                           '-c:v', 'libx264', '-crf', '23', '-preset', 'fast', '-c:a', 'aac', '-b:a', '192k',
                           '-movflags', '+faststart', tmp_final],
                          capture_output=True, creationflags=0x08000000, timeout=7200)
        if r.returncode == 0: shuffled_ok.append((orig_vp, tmp_final, name))
        else:
            err = r.stderr.decode('utf-8', errors='ignore')[-200:] if r.stderr else '未知'
            print(f"\n    ❌ 音频/乱序失败: {err}")
        pbar.update(1)
    pbar.close()
    if not shuffled_ok: print("❌ 乱序全失败"); shutil.rmtree(tmp_dir, ignore_errors=True); return

    print("\n" + "=" * 50)
    print("  阶段3/4: AB 包裹")
    print("=" * 50)
    b_dir = safe_input("  请输入 B 素材目录路径: ").strip()
    if not os.path.isdir(b_dir): print("❌ B目录无效"); shutil.rmtree(tmp_dir, ignore_errors=True); return
    use_gpu = False
    try:
        import ctypes
        ctypes.WinDLL('nvcuda.dll', mode=ctypes.RTLD_GLOBAL)
        use_gpu = True
    except: pass
    output_dir = get_output_dir(input_dir)
    from ab_processor import ab_blend
    wrapped = 0; pbar2 = ProgressBar(len(shuffled_ok), "AB包裹")
    for i, (orig_vp, shuf_vp, name) in enumerate(shuffled_ok, 1):
        b_files = sorted([os.path.join(b_dir,f) for f in os.listdir(b_dir) if f.lower().endswith(video_ext)])
        b_vp = b_files[i % len(b_files)] if b_files else None
        if not b_vp: continue
        final_out = os.path.join(output_dir, f"{name}_M11.mp4")
        pbar2.set_description(f"[{i}/{len(shuffled_ok)}] {name[:25]}")
        if ab_blend(shuf_vp, b_vp, final_out, use_gpu): wrapped += 1
        pbar2.update(1)
    pbar2.close()

    if wrapped > 0:
        from pseudo_duration import apply_pseudo_duration
        pbar3 = ProgressBar(wrapped, "伪时长"); patch_ok = 0
        for f in os.listdir(output_dir):
            if f.endswith('_M11.mp4'):
                if apply_pseudo_duration(os.path.join(output_dir, f), mode='boost')[0]: patch_ok += 1
                pbar3.update(1)
        pbar3.close()
        print(f"  伪时长: {patch_ok}/{wrapped}")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    print(f"\n=== 模式11 完成 === 成功: {wrapped}/{len(video_files)}")
    print(f"⏱️ [模式11] 总耗时: {_fmt_time(time.time() - t_batch)}")





def run_mode12(input_dir):
    """模式12: VapourSynth TRT RIFE + AB包裹 - 极限效率版"""
    import tempfile, shutil, subprocess, time
    from progress_utils import ProgressBar
    from ab_processor import ab_blend
    from video_processor_simple import VideoProcessor
    t_batch = time.time()

    print("\n[模式 12] TRT RIFE + AB包裹 - 极限效率版")
    print("-" * 40)
    print("  阶段0: TRT RIFE 插帧(VapourSynth ffms2 + TRT fp16)")
    print("  阶段1: AB softlight 包裹 + Mode6 增强")
    print("  阶段2: 推流加权伪时长")
    print("")

    # B素材目录
    b_dir = safe_input("  请输入 B 素材目录路径: ").strip()
    if not os.path.isdir(b_dir):
        print("❌ B 素材目录无效"); return

    use_gpu = False
    try:
        import ctypes
        ctypes.WinDLL('nvcuda.dll', mode=ctypes.RTLD_GLOBAL)
        use_gpu = True; print("  ✅ GPU 加速可用")
    except: print("  ⚠️ GPU 不可用,使用 CPU 编码")

    output_dir = get_output_dir(input_dir)
    video_ext = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv')
    video_files = sorted([os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith(video_ext)])
    if not video_files: print("❌ 无视频"); return

    # B素材列表(循环外构建一次)
    b_files = sorted([os.path.join(b_dir, f) for f in os.listdir(b_dir) if f.lower().endswith(video_ext)])
    if not b_files: print("❌ B素材目录无视频"); return

    # 环境变量
    PLUGINS = os.path.join(os.path.dirname(__file__), "vs-plugins")
    os.environ['PATH'] = PLUGINS + ';' + os.path.join(PLUGINS, 'vsmlrt-cuda') + ';' + os.environ.get('PATH', '')

    # FFmpeg 路径(搜索而非硬编码,避免换版本即失效)
    def _find_ffmpeg_mode12():
        base = os.path.dirname(__file__)
        import glob as _glob
        for pattern in ["ffmpeg-*-full_build/ffmpeg-*-full_build/bin/ffmpeg.exe",
                        "ffmpeg-*-full_build/bin/ffmpeg.exe"]:
            matches = sorted(_glob.glob(os.path.join(base, pattern)), reverse=True)
            if matches: return matches[0]
        for sub in ["完整包138/Waifu2x-Extension-GUI-v3.138.01-Win64/waifu2x-extension-gui/ffmpeg_waifu2xEX.exe",
                    "Waifu2x-Extension-GUI-v3.138.01-Win64/waifu2x-extension-gui/ffmpeg_waifu2xEX.exe"]:
            p = os.path.join(base, sub)
            if os.path.exists(p): return p
        print("  ⚠️ 未找到本地 FFmpeg,将使用 PATH 中的 ffmpeg")
        return "ffmpeg"
    FFMPEG_EXE = _find_ffmpeg_mode12()
    print(f"  FFmpeg: {FFMPEG_EXE}")

    # vspipe 路径(多候选回退,避免 FileNotFoundError 崩溃)
    _vspipe_candidates = [
        os.path.join(os.path.dirname(sys.executable), "Scripts", "vspipe.exe"),
        os.path.join(PLUGINS, "vspipe.exe"),
        "vspipe.exe",
    ]
    vspipe_exe = None
    for c in _vspipe_candidates:
        if c == "vspipe.exe" or os.path.exists(c):
            vspipe_exe = c; break
    if not vspipe_exe or (vspipe_exe != "vspipe.exe" and not os.path.exists(vspipe_exe)):
        print("❌ 未找到 vspipe.exe,请安装 VapourSynth 或将其加入 PATH")
        return
    print(f"  vspipe: {vspipe_exe}")

    tmp_dir = tempfile.mkdtemp(prefix="m12_")
    tmp_audio = os.path.join(tmp_dir, "audio.m4a")  # 每轮循环覆盖复用
    success = 0
    pbar = ProgressBar(len(video_files), "TRT RIFE")

    for i, vp in enumerate(video_files, 1):
        name = os.path.splitext(os.path.basename(vp))[0]
        tmp_silent = os.path.join(tmp_dir, f"{name}_silent.mp4")
        final_out = os.path.join(output_dir, f"{name}_去重.mp4")
        pbar.set_description(f"[{i}/{len(video_files)}] {os.path.basename(vp)[:25]}")
        t_video = time.time()

        try:
            # ── 提取音频 ──
            has_audio = subprocess.run([FFMPEG_EXE, '-y', '-i', vp, '-vn', '-c:a', 'copy', tmp_audio],
                                       capture_output=True, creationflags=0x08000000, timeout=60).returncode == 0
            if not has_audio: tmp_audio = None

            # ── vspipe 输出 -> FFmpeg NVENC 编码 ──
            vpy_script = os.path.join(tmp_dir, "rife.vpy")
            # 路径全部用正斜杠,避免中文编码问题
            base_dir_fwd = os.path.dirname(__file__).replace('\\', '/')
            plugins_fwd = PLUGINS.replace('\\', '/')
            vp_fwd = vp.replace('\\', '/')
            # ffindex 缓存到持久目录,避免源目录污染 + 下次重跑复用索引
            ffindex_dir = os.path.join(os.path.dirname(__file__), "ffindex_cache")
            os.makedirs(ffindex_dir, exist_ok=True)
            ffindex_cache = os.path.join(ffindex_dir, os.path.basename(vp))
            # CPU 线程自动检测,预留 2 核防死机
            cpu_threads = max(2, (os.cpu_count() or 4) - 2)
            with open(vpy_script, 'w', encoding='utf-8') as f:
                f.write(f'''
import vapoursynth as vs, sys, os, math
sys.path.insert(0, r"{base_dir_fwd}")
core = vs.core
core.max_cache_size = 4000
core.num_threads = {cpu_threads}
core.std.LoadPlugin(os.path.join(r"{plugins_fwd}", "ffms2.dll"))
core.std.LoadPlugin(os.path.join(r"{plugins_fwd}", "vstrt.dll"))
from vsmlrt import RIFE, RIFEModel, BackendV2
src = core.ffms2.Source(r"{vp_fwd}", cachefile=r"{ffindex_cache}")
# ── 自适应补边到 32 倍数(TensorRT 卷积硬性要求)──
orig_w, orig_h = src.width, src.height
pad_w = math.ceil(orig_w / 32) * 32
pad_h = math.ceil(orig_h / 32) * 32
if orig_w != pad_w or orig_h != pad_h:
    src = core.std.AddBorders(src, right=pad_w - orig_w, bottom=pad_h - orig_h)
src = core.resize.Bicubic(src, format=vs.RGBS, matrix_in_s="709")
clip = RIFE(src, multi=2, model=RIFEModel.v4_6, backend=BackendV2.TRT(fp16=True, num_streams=1, workspace=4096))
# 用源帧率×2 而非 clip.fps×2(RIFE 内部可能已翻倍,用 clip.fps 会翻两次 -> 音画不同步)
clip = core.std.AssumeFPS(clip, fpsnum=src.fps.numerator * 2, fpsden=src.fps.denominator)
# ── 切回原始尺寸 ──
if orig_w != pad_w or orig_h != pad_h:
    clip = core.std.Crop(clip, right=pad_w - orig_w, bottom=pad_h - orig_h)
clip = core.resize.Bicubic(clip, format=vs.YUV420P8, matrix_s="709")
clip.set_output()
''')
            # 剧名水印：3%透明度移动式, XY周期互质避免时域预测优化
            show_name = name.split(' - ')[0].split('-')[0].strip()
            import re as _re
            show_name = _re.sub(r'[:\'\"\\\\]', '', show_name)
            wm_text = '© ' + show_name
            # 检测可用中文字体（Windows 自带黑体）
            font_candidates = [
                'C\\:/Windows/Fonts/simhei.ttf',
                'C\\:/Windows/Fonts/msyh.ttc',
                'C\\:/Windows/Fonts/simsun.ttc',
            ]
            fontfile = ''
            for fc in font_candidates:
                if os.path.exists(fc.replace('\\:', ':')):
                    fontfile = ":fontfile='" + fc + "'"
                    break
            if not fontfile:
                print(f"    ⚠️ 未找到中文字体, 跳过水印")
            wm_available = bool(fontfile)
            wm_filter = ("drawtext=text='" + wm_text + "'" + fontfile +
                         ":fontsize=18:fontcolor=white@0.10:bordercolor=black@0.10:borderw=1:"
                         "x=W*0.3+W*0.4*sin(t*0.15):y=H*0.35+H*0.3*cos(t*0.2)")

            # 编码命令：有字体加水印, 无字体直接用基础命令
            if wm_available:
                nvenc_cmd = [FFMPEG_EXE, '-y', '-i', 'pipe:', '-vf', wm_filter,
                             '-c:v', 'h264_nvenc', '-preset', 'p1', '-pix_fmt', 'yuv420p',
                             '-an', '-movflags', '+faststart', tmp_silent]
            else:
                nvenc_cmd = [FFMPEG_EXE, '-y', '-i', 'pipe:',
                             '-c:v', 'h264_nvenc', '-preset', 'p1', '-pix_fmt', 'yuv420p',
                             '-an', '-movflags', '+faststart', tmp_silent]

            vsp = subprocess.Popen([vspipe_exe, '-c', 'y4m', vpy_script, '-'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=0x08000000)
            nvenc = subprocess.Popen(nvenc_cmd,
                             stdin=vsp.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                             creationflags=0x08000000)
            vsp.stdout.close()
            try:
                _, nvenc_stderr_data = nvenc.communicate(timeout=7200)
            except subprocess.TimeoutExpired:
                nvenc.kill(); vsp.kill()
                nvenc.wait(); vsp.wait()
                print(f"\n  ❌ TRT RIFE 编码超时")
                pbar.update(1); continue
            vsp.wait()
            # 安全读取 stderr（communicate 后管道可能已关闭）
            try: vsp_err = vsp.stderr.read().decode('utf-8', errors='ignore')
            except: vsp_err = ''
            nvenc_err = ''
            try:
                if nvenc_stderr_data:
                    nvenc_err = nvenc_stderr_data.decode('utf-8', errors='ignore')
            except: pass

            if vsp.returncode != 0:
                print(f"\n  ❌ VapourSynth 脚本崩溃 (返回码={vsp.returncode})")
                if vsp_err:
                    for l in vsp_err.strip().split('\n')[-15:]:
                        print(f"    [vpy] {l.strip()[:200]}")
                if nvenc_err:
                    for l in nvenc_err.strip().split('\n')[-8:]:
                        print(f"    [ffmpeg] {l.strip()[:200]}")
                pbar.update(1); continue
            if nvenc.returncode != 0:
                print(f"\n  ⚠️ 编码失败 (返回码={nvenc.returncode})")
                if nvenc_err:
                    for l in nvenc_err.strip().split('\n')[-6:]:
                        print(f"    [ffmpeg] {l.strip()[:200]}")
                print(f"    回退无滤镜编码...")
                # 回退命令：无水印基础编码
                nvenc_cmd_fb = [FFMPEG_EXE, '-y', '-i', 'pipe:',
                                '-c:v', 'h264_nvenc', '-preset', 'p1', '-pix_fmt', 'yuv420p',
                                '-an', '-movflags', '+faststart', tmp_silent]
                vsp2 = subprocess.Popen([vspipe_exe, '-c', 'y4m', vpy_script, '-'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=0x08000000)
                nvenc2 = subprocess.Popen(nvenc_cmd_fb,
                                 stdin=vsp2.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                 creationflags=0x08000000)
                vsp2.stdout.close()
                try:
                    nvenc2.communicate(timeout=7200)
                except subprocess.TimeoutExpired:
                    nvenc2.kill(); vsp2.kill()
                    nvenc2.wait(); vsp2.wait()
                    print(f"\n  ❌ TRT RIFE 回退编码超时")
                    pbar.update(1); continue
                vsp2.wait()
                if vsp2.returncode != 0 or nvenc2.returncode != 0:
                    print(f"\n  ❌ TRT RIFE 编码失败 (有水印和无水印均失败)")
                    pbar.update(1); continue
                print(f"    无水印回退成功 (水印滤镜不可用)")
                if not os.path.exists(tmp_silent) or os.path.getsize(tmp_silent) < 10000:
                    print(f"\n  ❌ 回退输出无效")
                    pbar.update(1); continue

            # 验证 TRT RIFE 输出有效
            if not os.path.exists(tmp_silent) or os.path.getsize(tmp_silent) < 10000:
                print(f"\n  ❌ TRT RIFE 输出无效 (size={os.path.getsize(tmp_silent) if os.path.exists(tmp_silent) else 0})")
                pbar.update(1); continue

            # ── AB包裹(音频直传,省混流)──
            b_vp = b_files[(i - 1) % len(b_files)]
            tmp_wrap = os.path.join(tmp_dir, f"{name}_wrap.mp4")
            audio_arg = tmp_audio if (has_audio and tmp_audio) else None
            if not ab_blend(tmp_silent, b_vp, tmp_wrap, use_gpu, audio_path=audio_arg):
                pbar.update(1); continue

            # ── Mode6 增强 ──
            proc = VideoProcessor(tmp_wrap, final_out, {'use_gpu': use_gpu, 'aggressive': True, 'mode6': True})
            if proc.run():
                from video_processor_simple import find_best_ffmpeg
                meta_r = subprocess.run([find_best_ffmpeg(), '-y', '-i', final_out, '-c', 'copy', '-movflags', '+faststart',
                    '-metadata', 'comment=含AI生成内容；可能使用AI技术制作；可能含有AI生成内容',
                    final_out + '.m.mp4'], capture_output=True, text=False, timeout=120, creationflags=0x08000000)
                if meta_r.returncode == 0 and os.path.exists(final_out + '.m.mp4'):
                    # 加重试避免文件占用导致 Access Denied
                    for _ in range(3):
                        try:
                            os.replace(final_out + '.m.mp4', final_out)
                            break
                        except PermissionError:
                            time.sleep(0.5)
                    else:
                        # 3次都失败, 保留带元数据的副本, 删除原文件
                        try: os.remove(final_out)
                        except: pass
                        os.rename(final_out + '.m.mp4', final_out)
                elif os.path.exists(final_out + '.m.mp4'):
                    os.remove(final_out + '.m.mp4')
                success += 1; print(f"\n  ✅ [{i}/{len(video_files)}] {name[:40]} | ⏱️ {_fmt_time(time.time() - t_video)}")
            pbar.update(1)

        except FileNotFoundError as e:
            print(f"\n  ❌ 缺少依赖: {e}")
            pbar.update(1); continue
        except subprocess.TimeoutExpired:
            print(f"\n  ❌ 处理超时（非编码阶段）")
            pbar.update(1); continue
        except Exception as e:
            print(f"\n  ❌ 未知错误: {e}")
            pbar.update(1); continue
    pbar.close()

    # ── 伪时长 ──
    if success > 0:
        from pseudo_duration import apply_pseudo_duration
        out_files = sorted([f for f in os.listdir(output_dir) if f.endswith('_去重.mp4')])
        todo = len(out_files)
        if todo > 0:
            pbar2 = ProgressBar(todo, "伪时长"); patch_ok = 0
            for f in out_files:
                if apply_pseudo_duration(os.path.join(output_dir, f), mode='boost')[0]: patch_ok += 1
                pbar2.update(1)
            pbar2.close()
            print(f"  伪时长: {patch_ok}/{todo}")
        else:
            print(f"  ⚠️ 未找到待注入文件")

    shutil.rmtree(tmp_dir, ignore_errors=True)
    print(f"\n=== 模式12 完成 === 成功: {success}/{len(video_files)}")
    print(f"⏱️ [模式12] 总耗时: {_fmt_time(time.time() - t_batch)}")





def ab_processor_get_duration(video_path):
    """Helper: get video duration for mode11"""
    from ab_processor import get_video_info
    return get_video_info(video_path)['duration']



def ab_processor_get_ffmpeg():
    """Helper: get FFmpeg path from ab_processor"""
    from ab_processor import FFMPEG
    return FFMPEG

def get_output_dir(input_dir):
    """获取输出目录 - 自由选择
    1. 直接回车 -> 在输入视频目录内创建去重后视频
    2. 输入路径 -> 使用自定义路径
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
    Returns: (success_count, output_dir, processed_paths) 或 None(失败时)
    """
    import os

    # 如果启用AI模式,委托给 main_ultimate.py
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
        enhance_options.append(('anime4k', 'Mode6强化 画质增强'))
    if AI_MODELS['real-esrgan']:
        enhance_options.append(('real-esrgan', 'Real-ESRGAN 超分'))
    if AI_MODELS['esrgan']:
        enhance_options.append(('esrgan', 'Real-ESRGAN 独立超分'))
    if AI_MODELS['cliq']:
        enhance_options.append(('cliq', 'CLIQ 质量评估'))

    if not interp_options and not enhance_options:
        print("  ⚠️ 没有检测到可用AI模型,回退到标准模式")
        return batch_process(input_dir, {'use_gpu': True, 'use_ai': False})

    # ---- 帧插值模型选择(互斥,选一个或不选) ----
    if interp_options:
        print("\n  【帧插值模型】(互斥,只能选一个或不选)")
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

    # ---- 画质增强模型选择(可多选) ----
    if enhance_options:
        print("\n  【画质增强模型】(可多选,逐个确认)")
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
        print("  未选择任何AI模型,回退到标准模式")
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

    # 检查环境(仅运行一次)
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
            choice = safe_input("请选择模式 (1/2/3/4/5/6/7/8/9/10/11/12): ").strip()

            # 根据选择运行对应模式
            if choice == '1':
                run_standard_mode(input_dir)
            elif choice == '2':
                if not gpu_available:
                    print("⚠️  GPU不可用,将使用CPU模式")
                run_gpu_mode(input_dir)
            elif choice == '3':
                run_ai_mode(input_dir)
            elif choice == '4':
                run_custom_mode(input_dir)
            elif choice == '5':
                if not gpu_available:
                    print("⚠️  GPU不可用,将使用CPU编码")
                run_mode5(input_dir)
            elif choice == '6':
                if not gpu_available:
                    print("⚠️  GPU不可用,将使用CPU编码")
                run_mode6(input_dir)
            elif choice == '7':
                run_mode7(input_dir)
            elif choice == '8':
                run_mode8()
            elif choice == '9':
                run_mode9(input_dir)
            elif choice == '10':
                run_mode10(input_dir)
            elif choice == '11':
                run_mode11(input_dir)
            elif choice == '12':
                run_mode12(input_dir)
            else:
                print("无效选择,默认使用GPU加速模式")
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
