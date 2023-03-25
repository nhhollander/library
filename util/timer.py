import time


class Timer:
    """Simple timer utility."""

    __start: float
    __lap: float

    def __init__(self):
        self.__start = time.time()
        self.__lap = time.time()

    def time_formatted(self, lap: bool = False):
        """
        Return a formatted string representing the amount of time since this timer was started.

        :param lap: Use the lap timer instead of the main timer.
        """
        duration = self.get_time()
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

    def lap(self):
        """Reset the lap timer."""
        self.__lap = time.time()

    def get_time(self, lap: bool = False):
        """Return the value of the timer."""
        return time.time() - (self.__lap if lap else self.__start)
