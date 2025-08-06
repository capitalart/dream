import importlib.util
import pathlib
import sys

# Load the actual application module from project root
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
spec = importlib.util.spec_from_file_location("real_app", ROOT / "app.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Re-export selected attributes for tests
create_app = module.create_app
login_manager = module.login_manager
User = module.User
USERS = module.USERS
