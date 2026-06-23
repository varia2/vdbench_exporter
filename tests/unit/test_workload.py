import sys
from pathlib import Path

from src.utils import get_default_lun, render_workload


def test_get_default_lun():
    lun = get_default_lun()

    assert isinstance(lun, str)
    assert len(lun) > 0

    if sys.platform.startswith("win"):
        assert ":" in lun
    else:
        assert lun.startswith("/") or lun.startswith(".")


def test_render_workload(tmp_path):
    template = tmp_path / "template.tpl"

    template.write_text(
        "sd=sd1,lun={LUN},size=1G\n"
    )

    output = render_workload(str(template))

    output_path = Path(output)

    assert output_path.exists()

    content = output_path.read_text()

    assert "{LUN}" not in content
    assert "sd=sd1" in content

def test_render_workload_replaces_lun(tmp_path):
    template = tmp_path / "template.tpl"

    template.write_text("lun={LUN}")

    output = render_workload(str(template))

    content = Path(output).read_text()

    assert "{LUN}" not in content
    assert "lun=" in content