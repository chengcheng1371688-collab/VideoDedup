"""
伪时长处理模块
直接在 MP4 二进制层面修改 mvhd/tkhd/mdhd 的 duration 字段，
将视频显示时长压缩到 3~12 秒，但 stts/mdat 完全不动，
确保播放时内容完整、速度正常。
"""
import os
import struct
import random


class Mp4DurationPatcher:
    """MP4 容器时长二进制修改器"""

    def __init__(self, input_path):
        self.input_path = input_path
        self.data = None
        self.real_duration = None       # 真实时长（秒）
        self.fake_duration = None       # 伪时长（秒）
        self.scale_factor = None

    def _read_box_header(self, offset):
        """读取一个 Box 的 header：返回 (box_type, box_start, data_start, box_end)"""
        if offset + 8 > len(self.data):
            return None

        size = struct.unpack_from('>I', self.data, offset)[0]
        box_type = self.data[offset + 4: offset + 8].decode('ascii', errors='ignore')

        if size == 1:
            # 64-bit extended size
            if offset + 16 > len(self.data):
                return None
            size = struct.unpack_from('>Q', self.data, offset + 8)[0]
            data_start = offset + 16
        elif size == 0:
            # size 0 means box extends to end of file
            data_start = offset + 8
            box_end = len(self.data)
            return (box_type, offset, data_start, box_end)
        else:
            data_start = offset + 8

        box_end = offset + size
        return (box_type, offset, data_start, box_end)

    def _parse_duration_fields(self, data_start):
        """
        只读取 mvhd/tkhd/mdhd 盒子中的 duration 和 timescale，不做修改。
        返回 (duration, timescale)
        """
        offset = data_start
        version = self.data[offset]
        offset += 4  # version(1) + flags(3)

        if version == 1:
            offset += 16  # creation_time(8) + modification_time(8)
        else:
            offset += 8   # creation_time(4) + modification_time(4)

        timescale = struct.unpack_from('>I', self.data, offset)[0]
        offset += 4

        if version == 1:
            duration = struct.unpack_from('>Q', self.data, offset)[0]
        else:
            duration = struct.unpack_from('>I', self.data, offset)[0]

        return duration, timescale

    def _write_duration_field(self, data_start):
        """
        将 mvhd/tkhd/mdhd 盒子中的 duration 字段按 self.scale_factor 缩放。
        """
        offset = data_start
        version = self.data[offset]
        offset += 4  # version(1) + flags(3)

        if version == 1:
            offset += 16
        else:
            offset += 8

        # timescale — skip, read only
        offset += 4

        # duration — write
        if version == 1:
            old_dur = struct.unpack_from('>Q', self.data, offset)[0]
            new_dur = max(1, int(old_dur * self.scale_factor))
            struct.pack_into('>Q', self.data, offset, new_dur)
        else:
            old_dur = struct.unpack_from('>I', self.data, offset)[0]
            new_dur = max(1, int(old_dur * self.scale_factor))
            struct.pack_into('>I', self.data, offset, new_dur)

    # ──────── 第一遍：只读真实时长 ────────

    def _read_walk(self, start_offset, end_offset):
        """递归遍历，找到 mvhd 并读取真实时长"""
        offset = start_offset
        while offset < end_offset:
            header = self._read_box_header(offset)
            if header is None:
                break
            box_type, box_start, data_start, box_end = header

            if box_type == 'mvhd':
                dur, ts = self._parse_duration_fields(data_start)
                self.real_duration = dur / ts if ts > 0 else 0
                return  # 找到 mvhd 就退出，第一遍只读

            elif box_type in ('moov', 'trak', 'mdia', 'minf', 'stbl',
                              'dinf', 'edts', 'udta', 'mvex', 'mfra'):
                self._read_walk(data_start, box_end)
                if self.real_duration is not None:
                    return

            offset = box_end

    # ──────── 第二遍：写入伪时长 ────────

    def _write_walk(self, start_offset, end_offset):
        """递归遍历，修改所有 mvhd / tkhd / mdhd 的 duration"""
        offset = start_offset
        while offset < end_offset:
            header = self._read_box_header(offset)
            if header is None:
                break
            box_type, box_start, data_start, box_end = header

            if box_type in ('mvhd', 'tkhd', 'mdhd'):
                self._write_duration_field(data_start)

            elif box_type in ('moov', 'trak', 'mdia', 'minf', 'stbl',
                              'dinf', 'edts', 'udta', 'mvex', 'mfra'):
                self._write_walk(data_start, box_end)

            offset = box_end

    def _find_moov(self):
        """找到 moov box 的位置"""
        offset = 0
        while offset < len(self.data) - 8:
            header = self._read_box_header(offset)
            if header is None:
                break
            box_type, box_start, data_start, box_end = header
            if box_type == 'moov':
                return data_start, box_end
            offset = box_end
        return None, None

    def patch(self, output_path, fake_duration=None, mode='random'):
        """
        对 MP4 文件执行伪时长修改。

        Args:
            output_path:  输出文件路径
            fake_duration: 伪时长（秒），None 则由 mode 决定
            mode:         'random' → 随机 3~12s（模式5）
                          'positive' → 真实时长 × random(0.80, 0.95)（模式6）
                          'boost' → 全部伪装到 1~3 分钟（平台权重最高区间）

        Returns:
            (success, real_duration, fake_duration)
        """
        with open(self.input_path, 'rb') as f:
            self.data = bytearray(f.read())

        moov_start, moov_end = self._find_moov()
        if moov_start is None:
            print(f"    ❌ 未找到 moov box，无法修改时长")
            return (False, 0, 0)

        # ── 第一遍：只读真实时长 ──
        self.real_duration = None
        self._read_walk(moov_start, moov_end)

        if self.real_duration is None or self.real_duration <= 0:
            print(f"    ❌ 无法读取视频真实时长")
            return (False, 0, 0)

        # ── 确定伪时长 ──
        if fake_duration is not None:
            self.fake_duration = float(fake_duration)
        elif mode == 'positive':
            # 正向伪时长：80%~95% 真实时长，保持"正常视频"分类
            self.fake_duration = self.real_duration * random.uniform(0.80, 0.95)
        elif mode == 'boost':
            # 推流加权：将所有视频伪装到 1~3 分钟（平台权重最高区间）
            if self.real_duration < 60:
                # 短于1分钟的视频：伪装到 60~90 秒，消除 -10% 降权
                self.fake_duration = random.uniform(60, 90)
            elif self.real_duration > 180:
                # 长于3分钟的视频：伪装到 120~180 秒，消除 -20% 降权
                self.fake_duration = random.uniform(120, 180)
            else:
                # 已在 1~3 分钟区间：保持 80%~95%
                self.fake_duration = self.real_duration * random.uniform(0.80, 0.95)
        else:
            # 随机 3~12 秒（模式5 激进伪装）
            self.fake_duration = random.uniform(3.0, 12.0)

        self.scale_factor = self.fake_duration / self.real_duration

        # ── 第二遍：用正确的 scale_factor 修改所有 duration ──
        self._write_walk(moov_start, moov_end)

        with open(output_path, 'wb') as f:
            f.write(self.data)

        print(f"    真实时长: {self.real_duration:.1f}s → 伪时长: {self.fake_duration:.1f}s "
              f"(缩放因子: {self.scale_factor:.4f})")

        return (True, self.real_duration, self.fake_duration)


def apply_pseudo_duration(input_path, output_path=None, fake_seconds=None, mode='random'):
    """
    对视频文件应用伪时长处理。

    Args:
        input_path:   输入视频路径
        output_path:  输出路径（None 则覆盖原文件）
        fake_seconds: 伪时长秒数（None 则由 mode 决定）
        mode:         'random' (默认) 或 'positive'

    Returns:
        (success, real_seconds, fake_seconds)
    """
    if output_path is None:
        output_path = input_path

    patcher = Mp4DurationPatcher(input_path)
    return patcher.patch(output_path, fake_seconds, mode=mode)


def batch_pseudo_duration(output_dir, video_files_info):
    """
    批量对已处理的视频应用伪时长。

    Args:
        output_dir:      输出目录
        video_files_info: [(original_path, processed_path), ...]
    """
    from progress_utils import ProgressBar

    print(f"\n  ⏱ 伪时长处理（随机 3~12 秒）...")

    success_count = 0
    pbar = ProgressBar(len(video_files_info), "伪时长注入")

    for i, (_, processed_path) in enumerate(video_files_info, 1):
        fname = os.path.basename(processed_path)
        pbar.set_description(f"[{i}/{len(video_files_info)}] {fname[:30]}")

        ok, real, fake = apply_pseudo_duration(processed_path)
        if ok:
            success_count += 1

        pbar.update(1)

    pbar.close()
    print(f"  伪时长注入: {success_count}/{len(video_files_info)}")
    return success_count


if __name__ == "__main__":
    # 测试
    import sys
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        ok, real, fake = apply_pseudo_duration(test_file)
        print(f"Result: ok={ok}, real={real:.1f}s, fake={fake:.1f}s")
    else:
        print("用法: python pseudo_duration.py <video.mp4>")
