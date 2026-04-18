DETECTION_INTERVAL_SECONDS = 120


def next_detection_window(last_run_at: int) -> int:
    return last_run_at + DETECTION_INTERVAL_SECONDS
