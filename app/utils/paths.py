from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"
DATA_INPUT_DIR = DATA_DIR / "input"
DATA_OUTPUT_DIR = DATA_DIR / "output"

USERS_DATA_DIR = DATA_OUTPUT_DIR / "users"


def ensure_directory(path: Path) -> Path:
    """
    Garante que uma pasta exista e retorna o próprio Path.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_users_data_dir() -> Path:
    """
    Retorna a pasta onde os dados locais dos usuários serão armazenados.
    """
    return ensure_directory(USERS_DATA_DIR)