class UpstreamModelError(RuntimeError):
    def __init__(self, message: str = "上游模型调用失败") -> None:
        super().__init__(message)
