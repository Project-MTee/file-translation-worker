class EventHook():
    def __init__(self):
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self

    def __isub__(self, handler):
        self.handlers.remove(handler)
        return self

    def fire(self, *args, **keywargs):
        for handler in self.handlers:
            handler(*args, **keywargs)