import subprocess
import time
import sys
import datetime
import os

# 設定
INTERVAL_HOURS = 24  # 実行間隔（時間）
TARGET_HOUR = 9  # 毎日この時間の直後に実行 (例: 9 => 9時台に実行)
RETRY_DELAY_MINUTES = 10  # エラー時の再試行待ち時間
MAX_RETRIES = 5  # 最大リトライ回数


def run_bot():
    """Botをサブプロセスとして実行"""
    print(f"[{datetime.datetime.now()}] Botを開始します...")

    # 自身のディレクトリからプロジェクトルート（2つ上の階層）を特定
    # app/utils/scheduler.py -> app/utils -> app -> project_root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))

    # プロジェクトルートで実行するように調整
    cmd = [sys.executable, "-m", "app.main"]

    # 環境変数を継承し、PYTHONPATHにプロジェクトルートを追加
    env = os.environ.copy()
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = project_root + os.pathsep + env["PYTHONPATH"]
    else:
        env["PYTHONPATH"] = project_root

    try:
        # cwdをプロジェクトルートにして実行
        result = subprocess.run(cmd, cwd=project_root, env=env, check=False)

        if result.returncode == 0:
            print(f"[{datetime.datetime.now()}] Botが正常終了しました。")
            return True
        else:
            print(
                f"[{datetime.datetime.now()}] Botがエラー終了しました (Exit Code: {result.returncode})"
            )
            return False

    except Exception as e:
        print(f"[{datetime.datetime.now()}] 実行中に例外が発生しました: {e}")
        return False


def main():
    print("=== RakutenBot 監視型スケジューラ ===")
    print(f"ターゲット時間: 毎日 {TARGET_HOUR}時")
    print(f"エラー時リトライ: 最大 {MAX_RETRIES} 回 (間隔 {RETRY_DELAY_MINUTES} 分)")
    print("Ctrl+C で停止します\n")

    # 初回即実行するか確認（オプション）
    # run_bot()

    while True:
        now = datetime.datetime.now()

        # 指定の時間（例: 9時）になったら実行
        target = now.replace(hour=TARGET_HOUR, minute=0, second=0, microsecond=0)

        # ターゲット時間が「今」より前なら明日の同時刻にする
        if now >= target:
            target = target + datetime.timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        print(f"次の実行({target})まで {wait_seconds/3600:.1f} 時間待機します...")

        try:
            time.sleep(wait_seconds)

            # 待機明け実行（リトライループ）
            for attempt in range(MAX_RETRIES + 1):
                success = run_bot()

                if success:
                    break

                if attempt < MAX_RETRIES:
                    print(
                        f"エラーのため {RETRY_DELAY_MINUTES} 分後にリトライします ({attempt + 1}/{MAX_RETRIES})..."
                    )
                    time.sleep(RETRY_DELAY_MINUTES * 60)
                else:
                    print(
                        f"全リトライ({MAX_RETRIES}回)に失敗しました。次のスケジュールまで待機します。"
                    )

        except KeyboardInterrupt:
            print("\nスケジューラを停止します。")
            break


if __name__ == "__main__":
    main()
