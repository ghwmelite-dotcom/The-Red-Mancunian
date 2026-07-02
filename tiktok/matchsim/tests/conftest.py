"""Put the matchsim module dir on sys.path so tests can `import dixon_coles` etc."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
