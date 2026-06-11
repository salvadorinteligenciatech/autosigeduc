from app.automation.portal_driver import LoginResult, login_sigeduc


def autenticar_no_sigeduc(email: str, senha: str) -> LoginResult:
    """
    Camada de serviço responsável por autenticar o usuário no SIGEDUC.

    Mantém a GUI desacoplada do Playwright.
    """
    return login_sigeduc(email=email, senha=senha)