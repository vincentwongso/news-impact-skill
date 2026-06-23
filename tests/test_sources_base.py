import pytest
from sources.base import SourceAdapter, SOURCE_REGISTRY, register
import sources.stubs  # noqa: F401  (registers stubs on import)

def test_register_adds_to_registry():
    @register
    class Dummy(SourceAdapter):
        name = "dummy"
        def fetch(self, watchlist):
            return []
    assert SOURCE_REGISTRY["dummy"] is Dummy

def test_stub_sources_registered_and_raise():
    assert "x" in SOURCE_REGISTRY
    assert "finnhub" in SOURCE_REGISTRY
    with pytest.raises(NotImplementedError):
        SOURCE_REGISTRY["finnhub"]().fetch(["EURUSD"])
