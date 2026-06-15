"""
视频去重工具 GUI - 黑金主题
双击 启动_GUI.bat 运行
"""
import sys, os, threading
sys.path.insert(0, os.path.dirname(__file__))

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
import tkinter as tk

GOLD = "#dea34b"

class RedirectText:
    def __init__(self, widget):
        self.widget = widget
    def write(self, s):
        self.widget.insert(tk.END, s)
        self.widget.see(tk.END)
        self.widget.update_idletasks()
    def flush(self):
        pass


class VideoToolGUI:
    def __init__(self):
        self.root = ttk.Window(themename="darkly")
        self.root.title("视频去重工具")
        self.root.geometry("860x760+150+10")

        WINE = "#722F37"
        style = ttk.Style()
        # 全局字体加粗
        style.configure(".", foreground=GOLD, font=("Microsoft YaHei", 10, "bold"))
        style.configure("TLabelframe", foreground=GOLD)
        style.configure("TLabelframe.Label", foreground=GOLD, font=("Microsoft YaHei", 11, "bold"))
        style.configure("TLabel", foreground=GOLD, font=("Microsoft YaHei", 10, "bold"))
        style.configure("TRadiobutton", foreground=GOLD, font=("Microsoft YaHei", 10, "bold"))
        style.configure("TEntry", foreground=GOLD, fieldbackground="#2e2e3e",
                        font=("Microsoft YaHei", 10, "bold"), bordercolor=GOLD)
        # 按钮：黑底金文字，酒红边框
        style.configure("Gold.TButton", background="#1a1a1a", foreground=GOLD,
                        bordercolor=WINE, font=("Microsoft YaHei", 14, "bold"))
        style.map("Gold.TButton", background=[("active", "#2a2a2a")],
                  foreground=[("active", "#f0d060")], bordercolor=[("active", "#8B3A4A")])
        style.configure("Dark.TButton", background="#1a1a1a", foreground=GOLD,
                        bordercolor=WINE, font=("Microsoft YaHei", 10, "bold"))
        style.map("Dark.TButton", background=[("active", "#2a2a2a")],
                  bordercolor=[("active", "#8B3A4A")])
        style.configure("TProgressbar", troughcolor="#2e2e3e", background=GOLD)

        self.mode_var = tk.StringVar(value="13")
        self.video_dir = tk.StringVar()
        self.b_dir = tk.StringVar()
        self.subdir_sel = tk.StringVar(value="0")
        self.merge_n = tk.StringVar(value="1")

        # ── 主布局：grid 精确控制 ──
        self.root.grid_rowconfigure(3, weight=1)  # 日志区伸缩
        self.root.grid_columnconfigure(0, weight=1)

        self._build_mode_selector()
        self._build_dir_selector()
        self._build_options()
        self._build_progress()
        self._build_buttons()

        redirect = RedirectText(self.output_text)
        sys.stdout = redirect
        sys.stderr = redirect

    def _build_mode_selector(self):
        f = ttk.Labelframe(self.root, text=" 选择模式 ", padding=8)
        f.grid(row=0, column=0, sticky=tk.EW, padx=10, pady=(10, 4))
        modes = [
            ("1", "模式1-标准CPU"), ("2", "模式2-GPU加速"),
            ("3", "模式3-AI增强"), ("4", "模式4-自定义"),
            ("5", "模式5-伪时长"), ("6", "模式6-推流加权"),
            ("7", "模式7-AB包裹增强"), ("8", "模式8-批量合并"),
            ("9", "模式9-RIFE+包裹"), ("10", "模式10-RIFE+SPAN"),
            ("11", "模式11-最强去重"), ("12", "模式12-极限效率"),
            ("13", "模式13-一键合并去重"),
        ]
        for col in range(4):
            f.grid_columnconfigure(col, weight=1)
        for i, (val, label) in enumerate(modes):
            ttk.Radiobutton(f, text=label, variable=self.mode_var, value=val).grid(
                row=i // 4, column=i % 4, sticky=tk.W, padx=5, pady=1)

    def _build_dir_selector(self):
        f = ttk.Labelframe(self.root, text=" 目录选择 ", padding=8)
        f.grid(row=1, column=0, sticky=tk.EW, padx=10, pady=4)
        f.grid_columnconfigure(1, weight=1)
        ttk.Label(f, text="视频目录:").grid(row=0, column=0, sticky=tk.W)
        self.video_entry = ttk.Entry(f, textvariable=self.video_dir)
        self.video_entry.grid(row=0, column=1, padx=5, sticky=tk.EW)
        self.video_entry.bind('<FocusOut>', lambda e: self._scan_subdirs(self.video_dir.get()))
        ttk.Button(f, text="浏览", width=6, style="Dark.TButton",
                   command=lambda: self._browse(self.video_dir)).grid(row=0, column=2)
        ttk.Label(f, text="B素材目录:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Entry(f, textvariable=self.b_dir).grid(row=1, column=1, padx=5, pady=(5, 0), sticky=tk.EW)
        ttk.Button(f, text="浏览", width=6, style="Dark.TButton",
                   command=lambda: self._browse(self.b_dir)).grid(row=1, column=2, pady=(5, 0))

    def _build_options(self):
        f = ttk.Labelframe(self.root, text=" 合并选项 ", padding=8)
        f.grid(row=2, column=0, sticky=tk.EW, padx=10, pady=4)
        ttk.Label(f, text="每N集合一条:").pack(side=tk.LEFT)
        ttk.Entry(f, textvariable=self.merge_n, width=4).pack(side=tk.LEFT, padx=5)
        ttk.Label(f, text="(1=全合一条)").pack(side=tk.LEFT)
        ttk.Label(f, text="  子文件夹:").pack(side=tk.LEFT, padx=(20, 0))
        ttk.Entry(f, textvariable=self.subdir_sel, width=36).pack(side=tk.LEFT, padx=5)
        ttk.Label(f, text="(0=全选)", foreground="#888").pack(side=tk.LEFT)

    def _build_progress(self):
        f = ttk.Labelframe(self.root, text=" 运行日志 ", padding=8)
        f.grid(row=3, column=0, sticky=tk.NSEW, padx=10, pady=4)
        f.grid_rowconfigure(0, weight=1)
        f.grid_columnconfigure(0, weight=1)
        sb = ttk.Scrollbar(f)
        sb.grid(row=0, column=1, sticky=tk.NS)
        self.output_text = tk.Text(f, wrap=tk.WORD, font=("Consolas", 9),
                                   yscrollcommand=sb.set, bg="#1a1a2e", fg=GOLD,
                                   insertbackground=GOLD)
        self.output_text.grid(row=0, column=0, sticky=tk.NSEW)
        sb.config(command=self.output_text.yview)

    def _build_buttons(self):
        f = ttk.Frame(self.root)
        f.grid(row=4, column=0, sticky=tk.EW, padx=10, pady=(4, 10))
        f.grid_columnconfigure(0, weight=1)  # start btn area
        f.grid_columnconfigure(3, weight=1)  # progress area

        self.start_btn = ttk.Button(f, text="▶  开  始  处  理", style="Gold.TButton",
                                    command=self._start, width=16)
        self.start_btn.grid(row=0, column=0, padx=(0, 10))

        ttk.Button(f, text="清空日志", style="Dark.TButton",
                   command=lambda: self.output_text.delete(1.0, tk.END)).grid(row=0, column=1, padx=5)

        self.progress_pct = tk.Label(f, text="0%", fg=GOLD, bg="#1a1a2e", font=("Consolas", 11, "bold"))
        self.progress_pct.grid(row=0, column=2, padx=5)

        self.progress = ttk.Progressbar(f, mode=DETERMINATE, length=280)
        self.progress.grid(row=0, column=3, sticky=tk.EW, padx=(5, 0))

    def _scan_subdirs(self, path):
        if not path or not os.path.isdir(path):
            return
        video_ext = ('.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv')
        subdirs = []
        for d in sorted(os.listdir(path)):
            dp = os.path.join(path, d)
            if os.path.isdir(dp):
                if any(f.lower().endswith(video_ext) for f in os.listdir(dp)):
                    subdirs.append(d)
        if subdirs:
            lines = [f"检测到 {len(subdirs)} 个含视频的子文件夹:"]
            lines.append("  [0] 全选")
            for i, sd in enumerate(subdirs, 1):
                lines.append(f"  [{i}] {sd}")
            lines.append("请在'子文件夹'输入框中输入选择后,再点开始处理")
            self.output_text.insert(tk.END, '\n'.join(lines) + '\n')
            self.output_text.see(tk.END)

    def _browse(self, var):
        path = filedialog.askdirectory()
        if path:
            var.set(path)
            self._scan_subdirs(path)

    def _start(self):
        mode = self.mode_var.get()
        video = self.video_dir.get().strip()
        b = self.b_dir.get().strip()
        if not video or not os.path.isdir(video):
            messagebox.showerror("错误", "请先选择有效的视频目录"); return
        if mode in ('7', '9', '11', '12', '13'):
            if not b or not os.path.isdir(b):
                messagebox.showerror("错误", f"模式{mode}需要选择B素材目录"); return

        self.start_btn.config(state=tk.DISABLED, text="⏳  处  理  中  ...")
        self.progress['value'] = 0
        self.progress_pct.config(text="0%")
        self.output_text.delete(1.0, tk.END)

        # 启用 GUI 模式（safe_input 自动返回默认值）
        from key_input import set_gui_mode
        set_gui_mode(True)

        from progress_utils import set_gui_progress_callback
        def on_progress(current, total, desc):
            pct = current / total * 100
            self.root.after(0, lambda: self.progress.config(value=pct))
            self.root.after(0, lambda: self.progress_pct.config(text=f"{pct:.1f}%"))
        set_gui_progress_callback(on_progress)

        def run():
            try:
                from run import (_fmt_time, check_environment,
                                run_standard_mode, run_gpu_mode, run_ai_mode, run_custom_mode,
                                run_mode5, run_mode6, run_mode7, run_mode8, run_mode9,
                                run_mode10, run_mode11, run_mode12, run_mode13)
                import run as run_mod
                # 传入 GUI 设置的目录
                run_mod._gui_b_dir = b
                check_environment()
                if mode == '1': run_standard_mode(video)
                elif mode == '2': run_gpu_mode(video)
                elif mode == '3': run_ai_mode(video)
                elif mode == '4': run_custom_mode(video)
                elif mode == '5': run_mode5(video)
                elif mode == '6': run_mode6(video)
                elif mode == '7': run_mode7(video)
                elif mode == '8':
                    run_mod._gui_merge_n = int(self.merge_n.get() or 1)
                    run_mod._gui_dir = video; run_mode8()
                elif mode == '9': run_mode9(video)
                elif mode == '10': run_mode10(video)
                elif mode == '11': run_mode11(video)
                elif mode == '12': run_mode12(video)
                elif mode == '13':
                    run_mod._gui_merge_n = int(self.merge_n.get() or 1)
                    run_mod._gui_subdir_sel = self.subdir_sel.get().strip() or "0"
                    run_mode13(video)
                messagebox.showinfo("完成", "处理完成!")
            except Exception as e:
                messagebox.showerror("错误", str(e))
                import traceback; traceback.print_exc()
            finally:
                self.root.after(0, self._done)

        threading.Thread(target=run, daemon=True).start()

    def _done(self):
        self.start_btn.config(state=tk.NORMAL, text="▶  开  始  处  理")
        self.progress['value'] = 100
        self.progress_pct.config(text="100%")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    VideoToolGUI().run()
