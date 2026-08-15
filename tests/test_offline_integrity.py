from pathlib import Path

import pytest

from tools.offline_integrity import build_state_manifest


def test_offline_manifest_requires_exported_state(tmp_path: Path):
    with pytest.raises(AssertionError, match="No exported model state"):
        build_state_manifest(tmp_path)
