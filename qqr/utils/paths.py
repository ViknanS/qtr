from pathlib import Path

_current_file = Path(__file__).resolve()

base_dir = _current_file.parents[2]
package_dir = _current_file.parents[1]

data_dir = base_dir / "data"
