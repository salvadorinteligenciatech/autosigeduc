import re
from dataclasses import dataclass
from typing import Any

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.config.settings import (
    PLAYWRIGHT_HEADLESS,
    PLAYWRIGHT_TIMEOUT_MS,
    SIGEDUC_DOCENTE_DADOS_URL,
    SIGEDUC_LOGIN_URL,
    SIGEDUC_PORTAL_DOCENTE_URL,
)


@dataclass
class LoginResult:
    success: bool
    status: str
    message: str
    current_url: str = ""


@dataclass
class ProfessorDataResult:
    success: bool
    status: str
    message: str
    data: dict[str, Any] | None = None
    current_url: str = ""


@dataclass
class AvaliacoesNavigationResult:
    success: bool
    status: str
    message: str
    data: dict[str, Any] | None = None
    current_url: str = ""


def _normalizar_texto(texto: str | None) -> str:
    """
    Remove quebras de linha e espaços duplicados.
    """
    return " ".join((texto or "").split())


def _extrair_turno_abreviado(id_turma: str) -> str:
    """
    Extrai o turno abreviado a partir do id_turma para exibição na turma.
    """
    id_turma = (id_turma or "").upper()

    if "NOTT" in id_turma:
        return "Not"

    if "VESP" in id_turma:
        return "Vesp"

    if "VES" in id_turma:
        return "Vesp"

    if "MAT" in id_turma:
        return "Mat"

    return ""


def _extrair_turno(id_turma: str) -> str:
    """
    Extrai o nome completo do turno a partir do id_turma.
    """
    turno_abreviado = _extrair_turno_abreviado(id_turma)

    if turno_abreviado == "Mat":
        return "Matutino"

    if turno_abreviado == "Vesp":
        return "Vespertino"

    if turno_abreviado == "Not":
        return "Noturno"

    return ""


def _montar_turma(id_turma: str, ano_serie_outros: str) -> str:
    """
    Monta o nome amigável da turma com indicação de turno.
    Exemplo:
        ano_serie_outros = "1ª SÉRIE - ITINERÁRIO..."
        id_turma = "EMMAT1PTA"
        retorno = "1ª SÉRIE A - Mat"
    """
    base = (ano_serie_outros or "").split("-")[0].strip()
    sufixo = (id_turma or "").strip()[-1:] if id_turma else ""
    turno_abreviado = _extrair_turno_abreviado(id_turma)

    if base and sufixo:
        turma = f"{base} {sufixo}"
    else:
        turma = base or sufixo

    if turma and turno_abreviado:
        return f"{turma} - {turno_abreviado}"

    return turma



def _extrair_id_turma_componente(onclick: str | None) -> str:
    """
    Extrai o idTurmaComponente do onclick do botão Lançar Resultados.
    """
    if not onclick:
        return ""

    match = re.search(r"'idTurmaComponente'\s*:\s*'([^']+)'", onclick)

    if match:
        return match.group(1)

    return ""


def _extrair_turmas_docente(page: Page) -> list[dict[str, Any]]:
    """
    Extrai as turmas da tabela principal do portal docente.
    """
    table = page.locator("table[id$=':turmasProfessorTable']")

    if table.count() == 0:
        return []

    turmas = []
    rows = table.first.locator("tr")

    for row_index in range(rows.count()):
        row = rows.nth(row_index)
        cells = row.locator("td")

        if cells.count() < 8:
            continue

        id_turma = _normalizar_texto(cells.nth(0).inner_text())
        ano = _normalizar_texto(cells.nth(1).inner_text())
        escola = _normalizar_texto(cells.nth(2).inner_text())
        oferta_ensino = _normalizar_texto(cells.nth(3).inner_text())
        ano_serie_outros = _normalizar_texto(cells.nth(4).inner_text())
        periodicidade = _normalizar_texto(cells.nth(5).inner_text())
        componente = _normalizar_texto(cells.nth(6).inner_text())
        qtd_estudantes_texto = _normalizar_texto(cells.nth(7).inner_text())

        onclick_lancar_resultados = ""

        if cells.count() > 8:
            link_lancar_resultados = cells.nth(8).locator("a")

            if link_lancar_resultados.count() > 0:
                onclick_lancar_resultados = (
                    link_lancar_resultados.first.get_attribute("onclick") or ""
                )

        id_turma_componente = _extrair_id_turma_componente(
            onclick_lancar_resultados
        )

        try:
            qtd_estudantes = int(qtd_estudantes_texto)
        except ValueError:
            qtd_estudantes = None

        turmas.append(
            {
                "row_index": row_index,
                "id_turma": id_turma,
                "turma": _montar_turma(id_turma, ano_serie_outros),
                "turno": _extrair_turno(id_turma),
                "ano": ano,
                "escola": escola,
                "oferta_ensino": oferta_ensino,
                "ano_serie_outros": ano_serie_outros,
                "periodicidade": periodicidade,
                "componente": componente,
                "qtd_estudantes": qtd_estudantes,
                "id_turma_componente": id_turma_componente,
                "tem_lancar_resultados": bool(id_turma_componente),
            }
        )

    return turmas

def _extrair_status_unidades_avaliacoes(page: Page) -> dict[str, Any]:
    """
    Extrai o status das unidades na página
    Diário de Classe Digital > Gerenciar Grupos de Avaliação da Unidade.

    Usa os links 'Gerenciar Avaliações da Unidade', que trazem no onclick:
        - idGrupoAvaliacao
        - unidade

    Quando idGrupoAvaliacao é "0", a unidade ainda não possui avaliações cadastradas.
    """
    caption = ""

    captions = page.locator("caption")
    if captions.count() > 0:
        caption = _normalizar_texto(captions.first.inner_text())

    unidades = []
    links_gerenciar = page.locator("a[title='Gerenciar Avaliações da Unidade']")

    for index in range(links_gerenciar.count()):
        link = links_gerenciar.nth(index)
        onclick = link.get_attribute("onclick") or ""

        unidade_match = re.search(r"'unidade'\s*:\s*'([^']+)'", onclick)
        grupo_match = re.search(r"'idGrupoAvaliacao'\s*:\s*'([^']+)'", onclick)

        unidade = unidade_match.group(1) if unidade_match else str(index + 1)
        id_grupo_avaliacao = grupo_match.group(1) if grupo_match else ""

        unidades.append(
            {
                "unidade": unidade,
                "id_grupo_avaliacao": id_grupo_avaliacao,
                "tem_avaliacoes": bool(
                    id_grupo_avaliacao and id_grupo_avaliacao != "0"
                ),
                "onclick": onclick,
            }
        )

    total_unidades = len(unidades)
    unidades_com_avaliacoes = sum(
        1 for unidade in unidades if unidade.get("tem_avaliacoes")
    )
    unidades_sem_avaliacoes = total_unidades - unidades_com_avaliacoes

    return {
        "caption": caption,
        "total_unidades": total_unidades,
        "unidades_com_avaliacoes": unidades_com_avaliacoes,
        "unidades_sem_avaliacoes": unidades_sem_avaliacoes,
        "unidades": unidades,
    }


def abrir_cadastro_avaliacoes_turma_sigeduc(
    email: str,
    senha: str,
    id_turma_componente: str,
) -> AvaliacoesNavigationResult:
    """
    Realiza login no SIGEDUC, acessa Diário > Gerenciar Avaliações das Unidades,
    busca as turmas e seleciona a turma pelo idTurmaComponente.

    Esta etapa apenas posiciona a automação na tela da turma selecionada.
    O cadastro/verificação das avaliações será implementado em uma etapa posterior.
    """
    email = email.strip()
    senha = senha.strip()
    id_turma_componente = str(id_turma_componente or "").strip()

    if not email or not senha:
        return AvaliacoesNavigationResult(
            success=False,
            status="credenciais_vazias",
            message="Email e senha são obrigatórios.",
        )

    if not id_turma_componente:
        return AvaliacoesNavigationResult(
            success=False,
            status="id_turma_componente_vazio",
            message="O id_turma_componente da turma não foi informado.",
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
                page.wait_for_load_state(
                    "domcontentloaded",
                    timeout=PLAYWRIGHT_TIMEOUT_MS,
                )
            except PlaywrightTimeoutError:
                pass

            current_url = page.url

            painel_erros = page.locator("#painel-erros")
            if painel_erros.count() > 0 and painel_erros.first.is_visible():
                mensagem = painel_erros.first.inner_text().strip()
                browser.close()

                return AvaliacoesNavigationResult(
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

                return AvaliacoesNavigationResult(
                    success=False,
                    status="credenciais_invalidas",
                    message="Usuário e/ou senha inválidos.",
                    current_url=current_url,
                )

            link_portal_docente = page.locator("a[href*='verPortalDocente.do']")

            if link_portal_docente.count() > 0:
                link_portal_docente.first.click()

                try:
                    page.wait_for_load_state(
                        "domcontentloaded",
                        timeout=PLAYWRIGHT_TIMEOUT_MS,
                    )
                except PlaywrightTimeoutError:
                    pass
            else:
                page.goto(
                    SIGEDUC_PORTAL_DOCENTE_URL,
                    wait_until="domcontentloaded",
                    timeout=PLAYWRIGHT_TIMEOUT_MS,
                )

            page.wait_for_timeout(1000)
            current_url = page.url

            diario_menu = page.locator(
                "td.ThemeOfficeMainItem",
                has_text="Diário",
            )

            if diario_menu.count() == 0:
                browser.close()

                return AvaliacoesNavigationResult(
                    success=False,
                    status="menu_diario_nao_encontrado",
                    message="Não foi possível localizar o menu Diário no portal docente.",
                    current_url=current_url,
                )

            diario_menu.first.hover()
            page.wait_for_timeout(1000)

            gerenciar_avaliacoes = page.locator(
                "td.ThemeOfficeMenuItemText",
                has_text="Gerenciar Avaliações das Unidades",
            )

            if gerenciar_avaliacoes.count() == 0:
                browser.close()

                return AvaliacoesNavigationResult(
                    success=False,
                    status="menu_avaliacoes_nao_encontrado",
                    message="Não foi possível localizar a opção Gerenciar Avaliações das Unidades.",
                    current_url=current_url,
                )

            gerenciar_avaliacoes.first.click(no_wait_after=True)
            page.wait_for_timeout(3000)

            buscar_button = page.locator("#formAjustesTurma\\:btConfirmarAjustes")

            if buscar_button.count() == 0:
                browser.close()

                return AvaliacoesNavigationResult(
                    success=False,
                    status="botao_buscar_nao_encontrado",
                    message="Não foi possível localizar o botão Buscar na tela Consultar Turma.",
                    current_url=page.url,
                )

            buscar_button.first.click(no_wait_after=True)
            page.wait_for_timeout(5000)

            seletor_turma = (
                f"a[onclick*='idTurmaComponente'][onclick*='{id_turma_componente}']"
            )
            link_turma = page.locator(seletor_turma)

            if link_turma.count() == 0:
                total_links = page.locator("a[onclick*='idTurmaComponente']").count()
                browser.close()

                return AvaliacoesNavigationResult(
                    success=False,
                    status="turma_nao_encontrada",
                    message=(
                        "A turma não foi encontrada na tela de avaliações. "
                        f"id_turma_componente={id_turma_componente}. "
                        f"Links de turma encontrados: {total_links}."
                    ),
                    current_url=page.url,
                    data={
                        "id_turma_componente": id_turma_componente,
                        "total_links_turma": total_links,
                    },
                )

            link_turma.first.click(no_wait_after=True)
            page.wait_for_timeout(5000)

            final_url = page.url
            final_title = page.title()
            status_unidades = _extrair_status_unidades_avaliacoes(page)

            browser.close()

            return AvaliacoesNavigationResult(
                success=True,
                status="turma_selecionada",
                message="Turma selecionada com sucesso na tela de avaliações.",
                current_url=final_url,
                data={
                    "id_turma_componente": id_turma_componente,
                    "page_title": final_title,
                    "status_unidades": status_unidades,
                },
            )

    except PlaywrightTimeoutError:
        return AvaliacoesNavigationResult(
            success=False,
            status="timeout",
            message="Tempo limite excedido ao acessar o cadastro de avaliações.",
        )

    except Exception as exc:
        return AvaliacoesNavigationResult(
            success=False,
            status="erro",
            message=f"Erro inesperado ao acessar o cadastro de avaliações: {exc}",
        )


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
def coletar_dados_docente_sigeduc(email: str, senha: str) -> ProfessorDataResult:
    """
    Realiza login no SIGEDUC, acessa a página docente e extrai os dados das turmas.

    Esta função abre uma sessão Playwright própria e fecha o navegador ao final.
    """
    email = email.strip()
    senha = senha.strip()

    if not email or not senha:
        return ProfessorDataResult(
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
                page.wait_for_load_state(
                    "domcontentloaded",
                    timeout=PLAYWRIGHT_TIMEOUT_MS,
                )
            except PlaywrightTimeoutError:
                pass

            current_url = page.url

            painel_erros = page.locator("#painel-erros")
            if painel_erros.count() > 0 and painel_erros.first.is_visible():
                mensagem = painel_erros.first.inner_text().strip()
                browser.close()

                return ProfessorDataResult(
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

                return ProfessorDataResult(
                    success=False,
                    status="credenciais_invalidas",
                    message="Usuário e/ou senha inválidos.",
                    current_url=current_url,
                )

            page.goto(
                SIGEDUC_DOCENTE_DADOS_URL,
                wait_until="domcontentloaded",
                timeout=PLAYWRIGHT_TIMEOUT_MS,
            )

            current_url = page.url

            if "docente.jsf" not in current_url:
                browser.close()

                return ProfessorDataResult(
                    success=False,
                    status="erro",
                    message="Não foi possível acessar a página de dados do docente.",
                    current_url=current_url,
                )

            turmas = _extrair_turmas_docente(page)

            escolas = sorted(
                {
                    turma["escola"]
                    for turma in turmas
                    if turma.get("escola")
                }
            )

            turnos = sorted(
                {
                    turma["turno"]
                    for turma in turmas
                    if turma.get("turno")
                }
            )

            componentes = sorted(
                {
                    turma["componente"]
                    for turma in turmas
                    if turma.get("componente")
                }
            )

            turmas_nome = sorted(
                {
                    turma["turma"]
                    for turma in turmas
                    if turma.get("turma")
                }
            )

            data = {
                "turmas": turmas,
                "resumo": {
                    "total_turmas": len(turmas),
                    "escolas": escolas,
                    "turnos": turnos,
                    "componentes": componentes,
                    "turmas": turmas_nome,
                },
            }

            browser.close()

            if not turmas:
                return ProfessorDataResult(
                    success=True,
                    status="sem_turmas",
                    message="Nenhuma turma foi encontrada para este professor.",
                    data=data,
                    current_url=current_url,
                )

            return ProfessorDataResult(
                success=True,
                status="dados_coletados",
                message="Dados do professor carregados com sucesso.",
                data=data,
                current_url=current_url,
            )

    except PlaywrightTimeoutError:
        return ProfessorDataResult(
            success=False,
            status="timeout",
            message="Tempo limite excedido ao tentar carregar os dados do SIGEDUC.",
        )

    except Exception as exc:
        return ProfessorDataResult(
            success=False,
            status="erro",
            message=f"Erro inesperado ao carregar os dados do SIGEDUC: {exc}",
        )