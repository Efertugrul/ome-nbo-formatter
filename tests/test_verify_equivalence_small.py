import os
import yaml
from src.generator import generate_linkml_schema
from src.verify_equivalence import generate_report


def test_verify_equivalence_on_sample(sample_xsd_path, tmp_path):
    out_yaml = tmp_path / "sample.yaml"
    generate_linkml_schema(sample_xsd_path, str(out_yaml))
    report = generate_report(sample_xsd_path, str(out_yaml))
    # Sanity: zero per-class mismatches expected on sample
    assert "Classes with mismatches" in report
    # Extract number at end of the line
    for line in report.splitlines():
        if line.startswith("Classes with mismatches"):
            num = int(line.rsplit(" ", 1)[-1])
            assert num == 0
            break

