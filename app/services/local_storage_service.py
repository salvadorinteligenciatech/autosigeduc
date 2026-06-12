import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.utils.paths import get_users_data_dir


def _normalizar_email(email: str) -> str:
    """
    Normaliza o e-mail usado como chave de armazenamento.
    """
    return (email or "").strip().lower()


def _gerar_user_id(email: str) -> str:
    """
    Gera um identificador local estável sem expor o e-mail no nome da pasta.
    """
    email_normalizado = _normalizar_email(email)
    return hashlib.sha256(email_normalizado.encode("utf-8")).hexdigest()[:16]


def get_user_data_dir(email: str) -> Path:
    """
    Retorna a pasta local de dados de um usuário.
    """
    user_id = _gerar_user_id(email)
    user_dir = get_users_data_dir() / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def get_professor_data_file(email: str) -> Path:
    """
    Retorna o caminho do arquivo JSON com os dados carregados do professor.
    """
    return get_user_data_dir(email) / "professor_data.json"


def salvar_professor_data(email: str, data: dict[str, Any]) -> Path:
    """
    Salva localmente os dados carregados do professor em JSON.
    """
    email_normalizado = _normalizar_email(email)
    output_file = get_professor_data_file(email_normalizado)

    payload = {
        "email": email_normalizado,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "data": data,
    }

    output_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_file


def carregar_professor_data(email: str) -> dict[str, Any] | None:
    """
    Carrega os dados locais do professor, caso já existam.
    """
    input_file = get_professor_data_file(email)

    if not input_file.exists():
        return None

    return json.loads(input_file.read_text(encoding="utf-8"))