from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.automation.portal_driver import coletar_dados_docente_sigeduc
from app.services.local_storage_service import salvar_professor_data


@dataclass
class ProfessorDataServiceResult:
    success: bool
    status: str
    message: str
    data: dict[str, Any] | None = None
    saved_file: Path | None = None


def carregar_dados_professor(email: str, senha: str) -> ProfessorDataServiceResult:
    """
    Coleta os dados do professor no SIGEDUC e salva localmente associado ao e-mail.
    """
    resultado = coletar_dados_docente_sigeduc(email=email, senha=senha)

    if not resultado.success:
        return ProfessorDataServiceResult(
            success=False,
            status=resultado.status,
            message=resultado.message,
            data=resultado.data,
        )

    data = resultado.data or {}
    saved_file = salvar_professor_data(email=email, data=data)

    return ProfessorDataServiceResult(
        success=True,
        status=resultado.status,
        message=resultado.message,
        data=data,
        saved_file=saved_file,
    )