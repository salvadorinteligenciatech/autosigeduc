from dataclasses import dataclass

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.config.settings import (
    PLAYWRIGHT_HEADLESS,
    PLAYWRIGHT_TIMEOUT_MS,
    SIGEDUC_LOGIN_URL,
    SIGEDUC_PORTAL_DOCENTE_URL,
)


@dataclass
class LoginResult:
    success: bool
    status: str
    message: str
    current_url: str = ""


def login_sigeduc(email: str, senha: str) -> LoginResult:
    """
    Realiza login no SIGEDUC usando Playwright.

    Retornos esperados em status:
        - "login_ok"
        - "credenciais_invalidas"
        - "timeout"
        - "erro"
    """
    email = email.strip()
    senha = senha.strip()

    if not email or not senha:
        return LoginResult(
            success=False,
            status="credenciais_vazias",
            message="Email e senha são obrigatórios.",
        )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=PLAYWRIGHT_HEADLESS)

            page = browser.new_page()
            page.set_default_timeout(PLAYWRIGHT_TIMEOUT_MS)

            page.goto(
                SIGEDUC_LOGIN_URL,
                wait_until="domcontentloaded",
                timeout=PLAYWRIGHT_TIMEOUT_MS,
            )

            page.fill("#email", email)
            page.fill("#senha", senha)

            page.click("#submit-btn")

            try:
                page.wait_for_load_state("domcontentloaded", timeout=PLAYWRIGHT_TIMEOUT_MS)
            except PlaywrightTimeoutError:
                pass

            current_url = page.url

            painel_erros = page.locator("#painel-erros")
            if painel_erros.count() > 0 and painel_erros.first.is_visible():
                mensagem = painel_erros.first.inner_text().strip()
                browser.close()

                return LoginResult(
                    success=False,
                    status="credenciais_invalidas",
                    message=mensagem or "Usuário e/ou senha inválidos.",
                    current_url=current_url,
                )

            login_ainda_visivel = (
                page.locator("#email").count() > 0
                and page.locator("#senha").count() > 0
                and page.locator("#submit-btn").count() > 0
            )

            if login_ainda_visivel:
                browser.close()

                return LoginResult(
                    success=False,
                    status="credenciais_invalidas",
                    message="Usuário e/ou senha inválidos.",
                    current_url=current_url,
                )

            link_portal_docente = page.locator("a[href*='verPortalDocente.do']")

            if link_portal_docente.count() > 0:
                link_portal_docente.first.click()

                try:
                    page.wait_for_load_state("domcontentloaded", timeout=PLAYWRIGHT_TIMEOUT_MS)
                except PlaywrightTimeoutError:
                    pass
            else:
                page.goto(
                    SIGEDUC_PORTAL_DOCENTE_URL,
                    wait_until="domcontentloaded",
                    timeout=PLAYWRIGHT_TIMEOUT_MS,
                )

            current_url = page.url

            if "verPortalDocente.do" in current_url or "/portais/docente/" in current_url:
                browser.close()

                return LoginResult(
                    success=True,
                    status="login_ok",
                    message="Login realizado com sucesso.",
                    current_url=current_url,
                )

            browser.close()

            return LoginResult(
                success=False,
                status="erro",
                message="Login não confirmado no portal docente.",
                current_url=current_url,
            )

    except PlaywrightTimeoutError:
        return LoginResult(
            success=False,
            status="timeout",
            message="Tempo limite excedido ao tentar acessar o SIGEDUC.",
        )

    except Exception as exc:
        return LoginResult(
            success=False,
            status="erro",
            message=f"Erro inesperado ao tentar acessar o SIGEDUC: {exc}",
        )