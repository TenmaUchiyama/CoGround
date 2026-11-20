"""コマンドライン。

  fetch_check list                      確認項目の一覧
  fetch_check run                       level 0 (読むだけ) を全部
  fetch_check run 'sense.*' sys.battery パターンで選ぶ (fnmatch 形式。シェルが展開しないよう '' で囲む)
  fetch_check run -v                    測った値 (details) も表示
  fetch_check run --json out.json       結果を指定ファイルに保存 (既定は $FETCH_CHECK_REPORT_DIR に自動保存)

終了コード: FAIL があれば 1、無ければ 0。
"""
import argparse
import json
import os
import sys
import time

from .core import REGISTRY, Context, Status, run_check, select

ICON = {Status.PASS: "PASS", Status.WARN: "WARN", Status.FAIL: "FAIL", Status.SKIP: "SKIP"}
COLOR = {Status.PASS: "32", Status.WARN: "33", Status.FAIL: "31", Status.SKIP: "90"}


def _c(text, code, enabled):
    return f"\033[{code}m{text}\033[0m" if enabled else text


def _load_checks():
    from . import checks  # noqa: F401  import で REGISTRY に登録される


def cmd_list(args):
    _load_checks()
    level = None if args.all else args.level
    for spec in select(args.patterns or None, level):
        flags = (" [実機のみ]" if spec.real_only else "") + (" [動く]" if spec.motion else "")
        print(f"L{spec.level}  {spec.id:<20} {spec.title}{flags}")
        if args.verbose and spec.description:
            print(f"      {spec.description}")
    return 0


def cmd_run(args):
    _load_checks()
    import rospy
    mode = args.mode or os.environ.get("FETCH_CHECK_MODE", "real")
    specs = select(args.patterns or None, args.level)
    if not specs:
        print("該当する確認項目がない (fetch_check list で一覧)", file=sys.stderr)
        return 2

    color = sys.stdout.isatty() and not args.no_color
    print(f"モード: {mode} / マスター: {os.environ.get('ROS_MASTER_URI', '(未設定)')} / {len(specs)} 項目")
    # マスターが居ないと init_node が永遠に待つので、先に確かめる
    import rosgraph
    if not rosgraph.is_master_online():
        print(_c("FAIL", COLOR[Status.FAIL], color) + " ROS マスターに届かない。ROS_MASTER_URI と roscore を確認")
        return 1
    rospy.init_node("fetch_check", anonymous=True, disable_signals=True)
    ctx = Context(mode=mode, duration=args.duration, allow_motion=False)

    records = []
    for spec in specs:
        if color:  # 端末なら実行中の項目を出しておき、結果で上書きする
            print(f"  … {spec.id}", end="\r", flush=True)
        rec = run_check(spec, ctx)
        records.append(rec)
        print(("\033[K" if color else "") +
              f"{_c(ICON[rec.status], COLOR[rec.status], color)}  {rec.id:<20} {rec.summary}  "
              f"{_c(f'({rec.duration_s:.1f}s)', '90', color)}")
        if rec.hint and rec.status in (Status.FAIL, Status.WARN):
            print(f"      → {rec.hint}")
        if args.verbose:
            for k, v in rec.details.items():
                if k != "traceback":
                    print(f"      {k}: {json.dumps(v, ensure_ascii=False)}")
        if rec.status == Status.FAIL and "traceback" in rec.details and args.verbose:
            print(rec.details["traceback"])

    counts = {s: sum(r.status == s for r in records) for s in Status}
    print("\n" + "  ".join(_c(f"{ICON[s]} {n}", COLOR[s], color) for s, n in counts.items()))

    path = _save(records, mode, args.json)
    if path:
        print(f"結果: {path}")
    return 1 if counts[Status.FAIL] else 0


def _save(records, mode, path):
    report = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "mode": mode,
        "master_uri": os.environ.get("ROS_MASTER_URI"),
        "results": [r.to_dict() for r in records],
    }
    if not path:
        d = os.environ.get("FETCH_CHECK_REPORT_DIR")
        if not d:
            return None
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, time.strftime(f"%Y%m%d-%H%M%S-{mode}.json"))
    try:
        with open(path, "w") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"結果を保存できない: {e}", file=sys.stderr)
        return None
    return path


def main(argv=None):
    p = argparse.ArgumentParser(prog="fetch_check", description="実機 Fetch でできることを 1 つずつ確かめる")
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="確認項目の一覧")
    pl.add_argument("patterns", nargs="*", help="例: 'sense.*'")
    pl.add_argument("--level", type=int, default=None, help="この level 以下だけ")
    pl.add_argument("--all", action="store_true", help="level で絞らない")
    pl.add_argument("-v", "--verbose", action="store_true", help="説明も出す")
    pl.set_defaults(fn=cmd_list)

    pr = sub.add_parser("run", help="確認を実行")
    pr.add_argument("patterns", nargs="*", help="例: 'sense.*' sys.battery (省略で level 0 を全部)")
    pr.add_argument("--level", type=int, default=0, help="この level 以下だけ (既定 0 = 読むだけ)")
    pr.add_argument("--mode", choices=["real", "sim"], help="既定は $FETCH_CHECK_MODE (無ければ real)")
    pr.add_argument("--duration", type=float, default=2.0, help="トピックを測る秒数")
    pr.add_argument("--json", help="結果の保存先 (既定は $FETCH_CHECK_REPORT_DIR/日時.json)")
    pr.add_argument("-v", "--verbose", action="store_true", help="測った値も出す")
    pr.add_argument("--no-color", action="store_true")
    pr.set_defaults(fn=cmd_run)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
