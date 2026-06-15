"""进度条工具模块 - 简单终端进度条，无需第三方库"""
import sys
import time
import threading
import os

_gui_callback = None  # GUI 可设置回调: fn(current, total, desc)
def set_gui_progress_callback(cb):
    global _gui_callback
    _gui_callback = cb

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# 终端宽度
def _term_width():
    try:
        return os.get_terminal_size().columns
    except:
        return 80


class ProgressBar:
    """简单进度条"""
    def __init__(self, total, desc="处理中", width=40):
        self.total = max(1, total)
        self.current = 0
        self.desc = desc
        self.width = min(width, _term_width() - 25)
        self.start_time = time.time()
        self._running = False
        self._spinner_idx = 0
        self._spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        
    def update(self, n=1):
        self.current = min(self.current + n, self.total)
        self._render()
        
    def set_description(self, desc):
        self.desc = desc
        self._render()
        
    def _render(self):
        pct = self.current / self.total
        filled = int(self.width * pct)
        bar = '█' * filled + '░' * (self.width - filled)
        elapsed = time.time() - self.start_time
        if pct > 0:
            eta = elapsed / pct * (1 - pct)
            eta_str = f"{eta:.0f}s" if eta < 60 else f"{eta/60:.1f}m"
        else:
            eta_str = "?"
        pct_str = f"{pct*100:5.1f}%"
        count_str = f"{self.current}/{self.total}"
        sys.stdout.write(f"\r  {self.desc} |{bar}| {pct_str} {count_str} [{elapsed:.0f}s<{eta_str}]")
        sys.stdout.flush()
        # GUI 回调
        if _gui_callback:
            try: _gui_callback(self.current, self.total, self.desc)
            except: pass
        
    def close(self):
        self.current = self.total
        self._render()
        sys.stdout.write('\n')
        sys.stdout.flush()


class Spinner:
    """旋转指示器 - 用于不确定进度的任务"""
    def __init__(self, desc="处理中"):
        self.desc = desc
        self._running = False
        self._thread = None
        self._idx = 0
        self._chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.start_time = time.time()
        
    def _spin(self):
        while self._running:
            elapsed = time.time() - self.start_time
            ch = self._chars[self._idx % len(self._chars)]
            sys.stdout.write(f"\r  {ch} {self.desc} [{elapsed:.0f}s]")
            sys.stdout.flush()
            self._idx += 1
            time.sleep(0.1)
    
    def start(self):
        self._running = True
        self.start_time = time.time()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        
    def stop(self, msg="完成"):
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.3)
        elapsed = time.time() - self.start_time
        sys.stdout.write(f"\r  ✓ {self.desc} → {msg} [{elapsed:.0f}s]\n")
        sys.stdout.flush()


def print_step(num, total, desc):
    """打印步骤标题"""
    print(f"\n  [{num}/{total}] {desc}")
    print(f"  {'─'*40}")


def print_ok(msg):
    print(f"  ✓ {msg}")


def print_fail(msg):
    print(f"  ✗ {msg}")