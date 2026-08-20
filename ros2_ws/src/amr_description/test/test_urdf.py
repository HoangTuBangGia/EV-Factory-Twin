import subprocess
import tempfile
from pathlib import Path


def test_xacro_expands_to_valid_urdf():
    source = Path(__file__).parents[1] / "urdf" / "amr.urdf.xacro"
    with tempfile.NamedTemporaryFile(suffix=".urdf") as output:
        subprocess.run(
            ["xacro", str(source), "prefix:=amr_01/", "namespace:=amr_01", "-o", output.name],
            check=True,
        )
        subprocess.run(["check_urdf", output.name], check=True)
