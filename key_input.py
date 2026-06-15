"""
安全输入模块
Ctrl+C = 返回上一步
GUI 模式下自动返回默认值（空字符串）
"""
import sys

_gui_mode = False

def set_gui_mode(enabled=True):
    global _gui_mode
    _gui_mode = enabled

class BackStep(Exception):
    """返回上一步"""
    pass


def safe_input(prompt=""):
    """Ctrl+C 返回菜单。GUI 模式下自动返回默认值"""
    if _gui_mode:
        print(prompt)  # 日志可见
        return ""
    try:
        return input(prompt)
    except (KeyboardInterrupt, EOFError):
        sys.stdout.write('^C\n')
        sys.stdout.flush()
        raise BackStep()
