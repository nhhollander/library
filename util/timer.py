import time


class Timer:
    """
    Simple timer utility.
    """

    start: float

    def __init__(self):
        self.start = time.time()

    def time_formatted(self):
        """
        Return a formatted string representing the amount of time since this timer was started.
        """
        duration = time.time() - self.start
        units: list[tuple[int, str]] = [
            (1, 's'),
            (1000, 'ms'),
            (1000000, 'μs')
        ]
        for unit in units:
            if duration > 1 / unit[0]:
                return f"{duration*unit[0]:0.3f}{unit[1]}"
        # Smaller times render with the smallest defined unit
        return f"{duration*units[-1][0]:0.3f}{units[-1][1]}"
