"""Frame-based coroutine scheduler.

Patterns, waves and stages are plain generator functions that `yield n` to
wait n logic frames (or `yield` / `yield None` to wait a single frame)."""


class Task:
    __slots__ = ("gen", "wait", "alive")

    def __init__(self, gen):
        self.gen = gen
        self.wait = 0
        self.alive = True


class Tasks:
    def __init__(self):
        self.tasks = []

    def spawn(self, gen):
        t = Task(gen)
        self.tasks.append(t)
        return t

    def update(self):
        for t in self.tasks[:]:
            if not t.alive:
                continue
            if t.wait > 0:
                t.wait -= 1
                continue
            try:
                w = next(t.gen)
            except StopIteration:
                t.alive = False
                continue
            t.wait = (int(w) if w else 1) - 1
        if any(not t.alive for t in self.tasks):
            self.tasks = [t for t in self.tasks if t.alive]

    def clear(self):
        for t in self.tasks:
            t.alive = False
            try:
                t.gen.close()
            except (RuntimeError, ValueError):
                pass
        self.tasks = []

    def __len__(self):
        return len(self.tasks)


def wait_until(cond, timeout=None):
    """Generator helper: wait until cond() is true."""
    n = 0
    while not cond():
        n += 1
        if timeout is not None and n >= timeout:
            return
        yield 1
