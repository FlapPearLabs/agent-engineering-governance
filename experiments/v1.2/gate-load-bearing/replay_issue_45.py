import importlib.util
import json
import tempfile
from pathlib import Path
repo = Path.cwd()
folder = repo / 'experiments/v1.2/gate-load-bearing'
spec = importlib.util.spec_from_file_location('probe', folder / 'probe_gates.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
manifest = json.loads((folder / 'gates.json').read_text())
gate = next(g for g in manifest['gates'] if g['id'] == 'ruff')
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    probe.scratch(repo, 'HEAD', root, worktree=True)
    config = root / 'ruff.toml'
    text = config.read_text()
    assert text.count("\nselect = [\"E9\", \"F\"]") == 1
    config.write_text(text.replace('select = ["E9", "F"]', 'select = []'))
    print(json.dumps(probe.probe_tree(root, {'gates': [gate]}), indent=2))
