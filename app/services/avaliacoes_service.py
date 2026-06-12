from dataclasses import dataclass
from typing import Any

from app.automation.portal_driver import abrir_cadastro_avaliacoes_turma_sigeduc


@dataclass
class AvaliacoesServiceResult:
    success: bool
    status: str
    message: str
    data: dict[str, Any] | None = None
    current_url: str = ""


def abrir_cadastro_avaliacoes_turma(
    email: str,
    senha: str,
    id_turma_componente: str,
) -> AvaliacoesServiceResult:
    """
    Aciona a automação para abrir a tela de cadastro de avaliações
    da turma selecionada.
    """
    resultado = abrir_cadastro_avaliacoes_turma_sigeduc(
        email=email,
        senha=senha,
        id_turma_componente=id_turma_componente,
    )

    return AvaliacoesServiceResult(
        success=resultado.success,
        status=resultado.status,
        message=resultado.message,
        data=resultado.data,
        current_url=resultado.current_url,
    )
