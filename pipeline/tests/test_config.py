import pytest
from pydantic import ValidationError

from roundup.config import load_sources
from roundup.models import Group, Source


def test_sources_yaml_loads_and_covers_every_group():
    sources = load_sources()
    assert len({s.id for s in sources}) == len(sources)
    assert {s.group for s in sources} == set(Group)


def test_duplicate_ids_are_rejected(tmp_path):
    entry = "  - {id: x, name: X, group: journal, country_or_region: US, method: crossref, issns: ['1']}\n"
    path = tmp_path / "sources.yaml"
    path.write_text("sources:\n" + entry + entry)
    with pytest.raises(ValueError, match="Duplicate"):
        load_sources(path)


def test_enabled_rss_source_needs_a_feed():
    with pytest.raises(ValidationError, match="feed URL"):
        Source(id="x", name="X", group="g10_cb", country_or_region="US", method="rss")


def test_disabled_source_may_be_unconfigured():
    source = Source(id="x", name="X", group="g10_cb", country_or_region="US", method="html", enabled=False)
    assert not source.enabled


def test_method_none_must_be_disabled():
    with pytest.raises(ValidationError, match="enabled: false"):
        Source(id="x", name="X", group="g10_cb", country_or_region="US", method="none")
