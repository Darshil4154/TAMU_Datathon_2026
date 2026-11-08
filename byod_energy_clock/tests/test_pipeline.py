"""Serialization must separate metadata from view keys and mark fake records."""
import numpy as np
from src.pipeline import clean_json


def test_fake_json_records_not_container_keys():
    result = clean_json({"is_fake": True, "views": {"All": {"rows": [{"value": np.nan}]}}}, fake=True)
    assert list(result["views"]) == ["All"]
    assert result["views"]["All"]["rows"] == [{"value": None, "is_fake": True}]
