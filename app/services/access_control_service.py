import csv
import io
import requests


SHEET_ID = "1xhFxnPAlCfuZdjz6C_oMDuPiG7ECUGp6NlgffiM1Y-w"

SHEET_CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
)


def _str_to_bool(value: str) -> bool:
    """
    Converte textos como True, TRUE, true, 1, sim para booleano.
    """
    if value is None:
        return False

    return str(value).strip().lower() in {
        "true",
        "1",
        "sim",
        "yes",
        "ativo",
    }


def verificar_acesso(email_digitado: str) -> str:
    """
    Verifica se o e-mail existe na planilha e se está ativo.

    Retornos possíveis:
        - "email_nao_encontrado"
        - "usuario_ativo"
        - "usuario_bloqueado"
        - "erro_consulta"
    """
    email_digitado = email_digitado.strip().lower()

    try:
        response = requests.get(SHEET_CSV_URL, timeout=10)
        response.raise_for_status()

        csv_content = response.content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(csv_content))

        for row in reader:
            email_planilha = row.get("EMAIL", "").strip().lower()
            ativo_planilha = row.get("ATIVO", "")

            if email_planilha == email_digitado:
                if _str_to_bool(ativo_planilha):
                    return "usuario_ativo"

                return "usuario_bloqueado"

        return "email_nao_encontrado"

    except Exception:
        return "erro_consulta"