import importlib
import sys


def test_dependencies_module_import_does_not_eagerly_construct_template_service(monkeypatch):
    module_name = "app.dependencies"
    original_module = sys.modules.get(module_name)

    if original_module is not None:
        del sys.modules[module_name]

    try:
        import app.services.template_service as template_service_module

        original_class = template_service_module.FileTemplateService

        class ExplodingTemplateService:
            def __init__(self, *args, **kwargs):
                raise AssertionError("should not construct at import time")

        monkeypatch.setattr(
            template_service_module,
            "FileTemplateService",
            ExplodingTemplateService,
        )

        module = importlib.import_module(module_name)

        with monkeypatch.context() as inner:
            inner.setattr(module, "FileTemplateService", ExplodingTemplateService)
            try:
                module.get_template_service()
            except AssertionError as exc:
                assert str(exc) == "should not construct at import time"
            else:
                raise AssertionError("expected lazy construction failure")
    finally:
        template_service_module.FileTemplateService = original_class
        if module_name in sys.modules:
            del sys.modules[module_name]
        if original_module is not None:
            sys.modules[module_name] = original_module
