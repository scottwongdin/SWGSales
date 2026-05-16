import sys
import os
import time
import subprocess
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Allow passing a config file as argument e.g. python watch_mail.py config_test
config_module = sys.argv[1] if len(sys.argv) > 1 else 'config'

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROCESS_SCRIPT = os.path.join(SCRIPT_DIR, "process_mails.py")
MAIL_DIR = r"C:\SWG Restoration\x64\profiles\philosophy\Restoration\mail_Eponine N'tarra"

# How long to wait after the last file arrives before triggering (seconds)
DEBOUNCE_SECONDS = 30


class MailHandler(FileSystemEventHandler):
    def __init__(self):
        self._timer = None
        self._lock = threading.Lock()
        self._pending_files = 0

    def on_created(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith('.mail'):
            return
        with self._lock:
            self._pending_files += 1
            print(f"  [DETECTED] {os.path.basename(event.src_path)} ({self._pending_files} pending)")
            self._reset_timer()

    def _reset_timer(self):
        """Reset the debounce timer each time a new file arrives."""
        if self._timer is not None:
            self._timer.cancel()
        self._timer = threading.Timer(DEBOUNCE_SECONDS, self._trigger)
        self._timer.start()

    def _trigger(self):
        with self._lock:
            count = self._pending_files
            self._pending_files = 0
        print(f"\n  [{time.strftime('%Y-%m-%d %H:%M:%S')}] {count} mail file(s) detected — running process_mails.py...")
        try:
            result = subprocess.run(
                ["python", PROCESS_SCRIPT, config_module],
                capture_output=False
            )
            if result.returncode == 0:
                print(f"  [DONE] Mail processing complete.\n")
            else:
                print(f"  [ERROR] process_mails.py exited with code {result.returncode}\n")
        except Exception as e:
            print(f"  [ERROR] Failed to run process_mails.py: {e}\n")


def main():
    print("=====================================")
    print("  SWG Mail Watcher")
    print("=====================================")
    print(f"  Config    : {config_module}")
    print(f"  Watching  : {MAIL_DIR}")
    print(f"  Debounce  : {DEBOUNCE_SECONDS} seconds")
    print()
    print("Watching for new .mail files... (Ctrl+C to stop)")
    print()

    if not os.path.isdir(MAIL_DIR):
        print(f"ERROR: Mail directory not found: {MAIL_DIR}")
        sys.exit(1)

    handler = MailHandler()
    observer = Observer()
    observer.schedule(handler, MAIL_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        observer.stop()
    observer.join()
    print("Watcher stopped.")


if __name__ == "__main__":
    main()