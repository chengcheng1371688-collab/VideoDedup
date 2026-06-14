"""
安全输入模块
Ctrl+C = 返回上一步
"""
import sys


class BackStep(Exception):
    """返回上一步"""
    pass


def safe_input(prompt=""):
    """Ctrl+C 返回菜单"""
    try:
        return input(prompt)
    except (KeyboardInterrupt, EOFError):
        sys.stdout.write('^C\n')
        sys.stdout.flush()
        raise BackStep()
