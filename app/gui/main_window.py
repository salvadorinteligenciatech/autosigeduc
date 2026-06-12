import tkinter as tk
from tkinter import messagebox, ttk

from app.services.access_control_service import verificar_acesso
from app.services.auth_service import autenticar_no_sigeduc
from app.services.professor_data_service import carregar_dados_professor


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("AutoSIGEDUC")
        self.geometry("900x600")
        self.minsize(800, 500)

        self.email_var = tk.StringVar()
        self.senha_var = tk.StringVar()

        self.current_user_email = None
        self.current_user_password = None

        self._show_login_screen()

    def _clear_window(self):
        """
        Remove todos os elementos atuais da janela.
        """
        for widget in self.winfo_children():
            widget.destroy()

    def _show_login_screen(self):
        """
        Tela inicial de login.
        """
        self._clear_window()

        container = tk.Frame(self)
        container.pack(expand=True)

        title_label = tk.Label(
            container,
            text="AutoSIGEDUC",
            font=("Arial", 24, "bold")
        )
        title_label.pack(pady=(0, 10))

        instruction_label = tk.Label(
            container,
            text="Informe o seu login e senha do sistema SIGEDUC",
            font=("Arial", 14)
        )
        instruction_label.pack(pady=(0, 25))

        email_label = tk.Label(
            container,
            text="Email:",
            font=("Arial", 12),
            anchor="w"
        )
        email_label.pack(fill="x")

        email_entry = tk.Entry(
            container,
            textvariable=self.email_var,
            font=("Arial", 12),
            width=35
        )
        email_entry.pack(pady=(5, 15))

        senha_label = tk.Label(
            container,
            text="Senha:",
            font=("Arial", 12),
            anchor="w"
        )
        senha_label.pack(fill="x")

        senha_entry = tk.Entry(
            container,
            textvariable=self.senha_var,
            font=("Arial", 12),
            width=35,
            show="*"
        )
        senha_entry.pack(pady=(5, 25))

        entrar_button = tk.Button(
            container,
            text="ENTRAR",
            font=("Arial", 12, "bold"),
            width=20,
            command=self._on_entrar_click
        )
        entrar_button.pack()

    def _on_entrar_click(self):
        email = self.email_var.get().strip()
        senha = self.senha_var.get().strip()

        if not email or not senha:
            messagebox.showwarning(
                "Campos obrigatórios",
                "Informe o email e a senha para continuar."
            )
            return

        status_acesso = verificar_acesso(email)

        if status_acesso == "email_nao_encontrado":
            messagebox.showwarning(
                "E-mail não encontrado",
                "Verificar o e-mail digitado."
            )
            return

        if status_acesso == "usuario_bloqueado":
            messagebox.showerror(
                "Usuário bloqueado",
                "Usuário bloqueado."
            )
            return

        if status_acesso == "erro_consulta":
            messagebox.showerror(
                "Erro de conexão",
                "Não foi possível consultar a lista de usuários autorizados."
            )
            return

        if status_acesso == "usuario_ativo":
            resultado_login = autenticar_no_sigeduc(email, senha)

            if not resultado_login.success:
                messagebox.showerror(
                    "Erro no login do SIGEDUC",
                    resultado_login.message
                )
                return

            self.current_user_email = email
            self.current_user_password = senha
            self._show_main_screen()

    def _show_main_screen(self):
        """
        Tela principal após login autorizado.
        """
        self._clear_window()

        main_container = tk.Frame(self)
        main_container.pack(fill="both", expand=True)

        nav_bar = tk.Frame(main_container, bg="#eeeeee", height=50)
        nav_bar.pack(side="top", fill="x")

        content_area = tk.Frame(main_container)
        content_area.pack(side="top", fill="both", expand=True)

        self.content_area = content_area

        carregar_button = tk.Button(
            nav_bar,
            text="Carregar os meus dados",
            font=("Arial", 11),
            command=self._show_carregar_dados_placeholder
        )
        carregar_button.pack(side="left", padx=10, pady=10)

        resumo_button = tk.Button(
            nav_bar,
            text="Resumo",
            font=("Arial", 11),
            command=self._show_resumo_placeholder
        )
        resumo_button.pack(side="left", padx=10, pady=10)

        lancar_notas_button = tk.Button(
            nav_bar,
            text="Lançar notas",
            font=("Arial", 11),
            command=self._show_lancar_notas_placeholder
        )
        lancar_notas_button.pack(side="left", padx=10, pady=10)

        user_label = tk.Label(
            nav_bar,
            text=f"Usuário: {self.current_user_email}",
            font=("Arial", 10),
            bg="#eeeeee"
        )
        user_label.pack(side="right", padx=15)

        self._show_resumo_placeholder()

    def _clear_content_area(self):
        """
        Limpa apenas a área central da tela principal.
        """
        for widget in self.content_area.winfo_children():
            widget.destroy()

    def _create_scrollable_content_area(self):
        """
        Cria uma área central com scroll vertical.
        Retorna o frame interno onde os elementos da tela devem ser inseridos.
        """
        self._clear_content_area()

        canvas = tk.Canvas(self.content_area)
        scrollbar = tk.Scrollbar(
            self.content_area,
            orient="vertical",
            command=canvas.yview
        )

        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda event: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas_window = canvas.create_window(
            (0, 0),
            window=scrollable_frame,
            anchor="nw"
        )

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _resize_scrollable_frame(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind("<Configure>", _resize_scrollable_frame)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        return scrollable_frame

    def _show_resumo_placeholder(self):
        scrollable_content = self._create_scrollable_content_area()

        title = tk.Label(
            scrollable_content,
            text="Resumo",
            font=("Arial", 22, "bold")
        )
        title.pack(pady=(80, 20))

        description = tk.Label(
            scrollable_content,
            text="Placeholder da tela de resumo dos dados carregados.",
            font=("Arial", 14)
        )
        description.pack()

        self._add_spacer_content(scrollable_content, quantidade=30)

    def _show_carregar_dados_placeholder(self):
        scrollable_content = self._create_scrollable_content_area()

        title = tk.Label(
            scrollable_content,
            text="Carregar os meus dados",
            font=("Arial", 22, "bold")
        )
        title.pack(pady=(40, 15))

        description = tk.Label(
            scrollable_content,
            text="Clique no botão abaixo para carregar os dados vinculados ao professor.",
            font=("Arial", 14)
        )
        description.pack(pady=(0, 20))

        carregar_button = tk.Button(
            scrollable_content,
            text="CARREGAR",
            font=("Arial", 12, "bold"),
            width=20,
            command=self._on_carregar_dados_click
        )
        carregar_button.pack(pady=(0, 25))

        self.dados_container = tk.Frame(scrollable_content)
        self.dados_container.pack(fill="both", expand=True, padx=40)

        self.escolas_container = self._create_section(
            self.dados_container,
            "Escolas:"
        )

        self.turnos_container = self._create_section(
            self.dados_container,
            "Turnos:"
        )

        self.disciplinas_container = self._create_section(
            self.dados_container,
            "Disciplinas:"
        )

        self.turmas_container = self._create_section(
            self.dados_container,
            "Turmas:"
        )

    def _create_section(self, parent, title_text):
        section = tk.Frame(parent)
        section.pack(fill="x", pady=8)

        title = tk.Label(
            section,
            text=title_text,
            font=("Arial", 12, "bold"),
            anchor="w"
        )
        title.pack(fill="x")

        values_container = tk.Frame(section)
        values_container.pack(fill="x", padx=(25, 0), pady=(5, 0))

        placeholder = tk.Label(
            values_container,
            text="—",
            font=("Arial", 12),
            anchor="w",
            relief="sunken",
            padx=8,
            pady=4
        )
        placeholder.pack(fill="x", pady=2)

        return values_container

    def _clear_section_values(self, section_container):
        for widget in section_container.winfo_children():
            widget.destroy()

    def _fill_section_values(self, section_container, values):
        self._clear_section_values(section_container)

        if not values:
            values = ["Nenhuma informação encontrada"]

        for value in values:
            value_label = tk.Label(
                section_container,
                text=value,
                font=("Arial", 12),
                anchor="w",
                relief="sunken",
                padx=8,
                pady=4
            )
            value_label.pack(fill="x", pady=2)

    def _on_carregar_dados_click(self):
        """
        Carrega os dados reais do professor no SIGEDUC e atualiza a tela.
        """
        if not self.current_user_email or not self.current_user_password:
            messagebox.showerror(
                "Sessão inválida",
                "Não foi possível identificar o usuário logado. Faça login novamente."
            )
            return

        self._fill_section_values(self.escolas_container, ["Carregando..."])
        self._fill_section_values(self.turnos_container, ["Carregando..."])
        self._fill_section_values(self.disciplinas_container, ["Carregando..."])
        self._fill_section_values(self.turmas_container, ["Carregando..."])

        self.update_idletasks()

        resultado = carregar_dados_professor(
            email=self.current_user_email,
            senha=self.current_user_password,
        )

        if not resultado.success:
            messagebox.showerror(
                "Erro ao carregar dados",
                resultado.message
            )

            self._fill_section_values(self.escolas_container, [])
            self._fill_section_values(self.turnos_container, [])
            self._fill_section_values(self.disciplinas_container, [])
            self._fill_section_values(self.turmas_container, [])
            return

        data = resultado.data or {}
        resumo = data.get("resumo", {})

        escolas = resumo.get("escolas", [])
        turnos = resumo.get("turnos", [])
        disciplinas = resumo.get("componentes", [])
        turmas = resumo.get("turmas", [])

        self._fill_section_values(self.escolas_container, escolas)
        self._fill_section_values(self.turnos_container, turnos)
        self._fill_section_values(self.disciplinas_container, disciplinas)
        self._fill_section_values(self.turmas_container, turmas)

        messagebox.showinfo(
            "Dados carregados",
            f"{resultado.message}\n\nTotal de turmas encontradas: {resumo.get('total_turmas', 0)}"
        )

    def _show_lancar_notas_placeholder(self):
        scrollable_content = self._create_scrollable_content_area()

        title = tk.Label(
            scrollable_content,
            text="Lançar notas",
            font=("Arial", 22, "bold")
        )
        title.pack(pady=(80, 20))

        description = tk.Label(
            scrollable_content,
            text="Placeholder da tela de lançamento de notas.",
            font=("Arial", 14)
        )
        description.pack()

        self._add_spacer_content(scrollable_content, quantidade=30)
 
    def _add_spacer_content(self, parent, quantidade=20):
        """
        Conteúdo temporário apenas para testar o scroll.
        Depois podemos remover.
        """
        for i in range(1, quantidade + 1):
            label = tk.Label(
                parent,
                text=f"Linha de teste do scroll {i}",
                font=("Arial", 11),
                anchor="w"
            )
            label.pack(fill="x", padx=40, pady=4)