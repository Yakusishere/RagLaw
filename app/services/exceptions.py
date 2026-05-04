class UpstreamDependencyError(RuntimeError):
    def __init__(self, message: str = "上游依赖调用失败") -> None:
        super().__init__(message)


UpstreamModelError = UpstreamDependencyError
