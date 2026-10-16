"""Run the SE-KB desktop development launcher."""

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tk", action="store_true", help="使用经典 Tk 窗口")
    args = parser.parse_args()
    try:
        if args.tk:
            from se_kb_app.devtools.window import main as launch
        else:
            from se_kb_app.devtools.desktop import main as launch
        launch()
    except Exception as error:
        message = (
            f"启动器无法打开：{type(error).__name__}: {error}\n\n"
            "请先运行：uv sync --frozen --extra api --extra desktop --group dev\n"
            "Windows 需安装 Microsoft Edge WebView2 Runtime。\n"
            "也可运行：.venv\\Scripts\\python.exe start_launcher.py --tk"
        )
        if sys.stderr is not None:
            print(message, file=sys.stderr)
        else:
            import ctypes

            getattr(ctypes, "windll").user32.MessageBoxW(None, message, "SE-KB Launcher", 16)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
