import sqlite3
import hashlib
import shutil
import os
from datetime import datetime

from kivy.app import App
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle


# ============================================================
# CONFIGURAÇÕES
# ============================================================

DB_NAME = "controle_encomendas.db"


# ============================================================
# BANCO DE DADOS
# ============================================================

def conectar():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()


def criar_banco():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS moradores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            bloco TEXT,
            apartamento TEXT,
            telefone TEXT,
            ativo INTEGER DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS funcionarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            perfil TEXT NOT NULL,
            ativo INTEGER DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS encomendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            morador_id INTEGER NOT NULL,
            codigo TEXT,
            descricao TEXT,
            foto TEXT,
            status TEXT DEFAULT 'PENDENTE',
            data_recebimento TEXT,
            data_entrega TEXT,
            funcionario_recebimento INTEGER,
            funcionario_entrega INTEGER,

            FOREIGN KEY (morador_id)
            REFERENCES moradores(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            encomenda_id INTEGER,
            acao TEXT,
            data TEXT,
            funcionario_id INTEGER,
            observacao TEXT
        )
    """)

    # Usuário administrador padrão
    cursor.execute(
        "SELECT id FROM funcionarios WHERE usuario = ?",
        ("admin",)
    )

    if cursor.fetchone() is None:

        cursor.execute("""
            INSERT INTO funcionarios
            (nome, usuario, senha, perfil)
            VALUES (?, ?, ?, ?)
        """, (
            "Administrador",
            "admin",
            hash_senha("1234"),
            "admin"
        ))

    conn.commit()
    conn.close()


# ============================================================
# COMPONENTES VISUAIS
# ============================================================

def label(text="", size=18, bold=False, color=(0.12, 0.12, 0.12, 1)):
    return Label(
        text=text,
        font_size=dp(size),
        bold=bold,
        color=color,
        halign="left",
        valign="middle"
    )


def botao(text, height=52):
    b = Button(
        text=text,
        size_hint_y=None,
        height=dp(height),
        font_size=dp(16),
        background_normal="",
        background_color=(0.12, 0.47, 0.85, 1),
        color=(1, 1, 1, 1)
    )
    return b


def entrada(hint="", password=False, height=48):
    return TextInput(
        hint_text=hint,
        password=password,
        multiline=False,
        size_hint_y=None,
        height=dp(height),
        font_size=dp(16),
        padding=[dp(12), dp(10)]
    )


class Card(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(5),
            **kwargs
        )

        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bg = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(12)]
            )

        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size


# ============================================================
# LOGIN
# ============================================================

class Login(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(35),
            spacing=dp(15)
        )

        layout.add_widget(Widget())

        titulo = label(
            "📦 CONTROLE DE ENCOMENDAS",
            25,
            True
        )
        titulo.halign = "center"
        layout.add_widget(titulo)

        subtitulo = label(
            "Acesso ao sistema",
            17
        )
        subtitulo.halign = "center"
        layout.add_widget(subtitulo)

        self.usuario = entrada("Usuário")
        self.senha = entrada("Senha", password=True)

        layout.add_widget(self.usuario)
        layout.add_widget(self.senha)

        acessar = botao("🔐 ENTRAR")
        acessar.bind(on_release=self.entrar)
        layout.add_widget(acessar)

        self.mensagem = label("", 14)
        self.mensagem.halign = "center"
        layout.add_widget(self.mensagem)

        layout.add_widget(Widget())

        self.add_widget(layout)

    def entrar(self, *args):

        usuario = self.usuario.text.strip()
        senha = self.senha.text

        conn = conectar()

        funcionario = conn.execute("""
            SELECT *
            FROM funcionarios
            WHERE usuario = ?
            AND senha = ?
            AND ativo = 1
        """, (
            usuario,
            hash_senha(senha)
        )).fetchone()

        conn.close()

        if funcionario:

            app = App.get_running_app()

            app.funcionario_id = funcionario["id"]
            app.funcionario_nome = funcionario["nome"]
            app.funcionario_perfil = funcionario["perfil"]

            self.usuario.text = ""
            self.senha.text = ""
            self.mensagem.text = ""

            self.manager.current = "inicio"

        else:

            self.mensagem.text = "❌ Usuário ou senha inválidos"


# ============================================================
# MENU LATERAL
# ============================================================

class MenuLateral(BoxLayout):

    def __init__(self, **kwargs):

        super().__init__(
            orientation="vertical",
            size_hint_x=None,
            width=dp(230),
            padding=dp(12),
            spacing=dp(8),
            **kwargs
        )

        titulo = label(
            "📦 MENU",
            22,
            True
        )

        self.add_widget(titulo)

        itens = [
            ("🏠 Início", "inicio"),
            ("👤 Moradores", "moradores"),
            ("📦 Nova encomenda", "cadastro"),
            ("🔎 Buscar", "busca"),
            ("⏳ Pendentes", "pendentes"),
            ("📋 Todas", "todas"),
            ("🕘 Histórico", "historico"),
            ("👥 Funcionários", "funcionarios"),
            ("📊 Relatórios", "relatorio"),
        ]

        for texto, tela in itens:

            b = botao(texto, 45)
            b.background_color = (
                0.90,
                0.93,
                0.97,
                1
            )
            b.color = (
                0.10,
                0.10,
                0.10,
                1
            )

            b.bind(
                on_release=lambda btn, t=tela:
                self.ir(t)
            )

            self.add_widget(b)

        self.add_widget(Widget())

        backup = botao("💾 Backup", 45)
        backup.bind(
            on_release=self.backup
        )
        self.add_widget(backup)

        sair = botao("🚪 Sair", 45)
        sair.background_color = (
            0.80,
            0.20,
            0.20,
            1
        )
        sair.bind(
            on_release=self.sair
        )

        self.add_widget(sair)

    def ir(self, tela):

        App.get_running_app().root.current = tela

    def sair(self, *args):

        App.get_running_app().root.current = "login"

    def backup(self, *args):

        try:

            nome = (
                "backup_"
                + datetime.now().strftime("%Y%m%d_%H%M%S")
                + ".db"
            )

            shutil.copy(
                DB_NAME,
                nome
            )

            Popup(
                title="Backup",
                content=label(
                    f"✅ Backup criado:\n{nome}",
                    16
                ),
                size_hint=(0.85, 0.4)
            ).open()

        except Exception as e:

            Popup(
                title="Erro",
                content=label(
                    f"Erro ao criar backup:\n{e}",
                    15
                ),
                size_hint=(0.85, 0.4)
            ).open()


# ============================================================
# TELA BASE
# ============================================================

class TelaBase(Screen):

    def montar(self, titulo):

        principal = BoxLayout(
            orientation="horizontal"
        )

        menu = MenuLateral()
        principal.add_widget(menu)

        area = BoxLayout(
            orientation="vertical",
            padding=dp(18),
            spacing=dp(12)
        )

        cabecalho = label(
            titulo,
            24,
            True
        )

        area.add_widget(
            cabecalho
        )

        self.conteudo = BoxLayout(
            orientation="vertical",
            spacing=dp(10)
        )

        area.add_widget(
            self.conteudo
        )

        principal.add_widget(
            area
        )

        self.add_widget(principal)


# ============================================================
# INÍCIO
# ============================================================

class Inicio(TelaBase):

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.montar(
            "🏠 Painel Principal"
        )

        self.atualizar()

    def on_pre_enter(self):

        self.atualizar()

    def atualizar(self):

        self.conteudo.clear_widgets()

        conn = conectar()

        total = conn.execute(
            "SELECT COUNT(*) FROM encomendas"
        ).fetchone()[0]

        pendentes = conn.execute("""
            SELECT COUNT(*)
            FROM encomendas
            WHERE status = 'PENDENTE'
        """).fetchone()[0]

        entregues = conn.execute("""
            SELECT COUNT(*)
            FROM encomendas
            WHERE status = 'ENTREGUE'
        """).fetchone()[0]

        moradores = conn.execute("""
            SELECT COUNT(*)
            FROM moradores
            WHERE ativo = 1
        """).fetchone()[0]

        conn.close()

        cards = GridLayout(
            cols=2,
            spacing=dp(12),
            size_hint_y=None
        )

        cards.bind(
            minimum_height=cards.setter(
                "height"
            )
        )

        dados = [
            ("📦", "Encomendas", total),
            ("⏳", "Pendentes", pendentes),
            ("✅", "Entregues", entregues),
            ("👤", "Moradores", moradores)
        ]

        for icone, nome, valor in dados:

            c = Card(
                size_hint_y=None,
                height=dp(120)
            )

            c.add_widget(
                label(
                    f"{icone} {nome}",
                    17,
                    True
                )
            )

            c.add_widget(
                label(
                    str(valor),
                    30,
                    True
                )
            )

            cards.add_widget(c)

        self.conteudo.add_widget(cards)

        self.conteudo.add_widget(
            label(
                "\nBem-vindo ao Controle de Encomendas!",
                20,
                True
            )
        )


# ============================================================
# NOVO MORADOR
# ============================================================

class NovoMorador(TelaBase):

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.montar(
            "👤 Cadastrar Morador"
        )

        self.nome = entrada("Nome completo")
        self.bloco = entrada("Bloco")
        self.apartamento = entrada("Apartamento")
        self.telefone = entrada("Telefone")

        self.conteudo.add_widget(
            self.nome
        )
        self.conteudo.add_widget(
            self.bloco
        )
        self.conteudo.add_widget(
            self.apartamento
        )
        self.conteudo.add_widget(
            self.telefone
        )

        salvar = botao(
            "💾 SALVAR MORADOR"
        )

        salvar.bind(
            on_release=self.salvar
        )

        self.conteudo.add_widget(
            salvar
        )

    def salvar(self, *args):

        nome = self.nome.text.strip()

        if not nome:

            self.popup(
                "Informe o nome do morador."
            )
            return

        conn = conectar()

        conn.execute("""
            INSERT INTO moradores
            (nome, bloco, apartamento, telefone)
            VALUES (?, ?, ?, ?)
        """, (
            nome,
            self.bloco.text,
            self.apartamento.text,
            self.telefone.text
        ))

        conn.commit()
        conn.close()

        self.nome.text = ""
        self.bloco.text = ""
        self.apartamento.text = ""
        self.telefone.text = ""

        self.popup(
            "✅ Morador cadastrado!"
        )

    def popup(self, texto):

        Popup(
            title="Moradores",
            content=label(
                texto,
                16
            ),
            size_hint=(0.8, 0.35)
        ).open()


# ============================================================
# LISTA DE MORADORES
# ============================================================

class Moradores(TelaBase):

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.montar(
            "👤 Moradores cadastrados"
        )

    def on_pre_enter(self):

        self.atualizar()

    def atualizar(self):

        self.conteudo.clear_widgets()

        scroll = ScrollView()

        lista = GridLayout(
            cols=1,
            spacing=dp(8),
            size_hint_y=None
        )

        lista.bind(
            minimum_height=lista.setter(
                "height"
            )
        )

        conn = conectar()

        moradores = conn.execute("""
            SELECT *
            FROM moradores
            WHERE ativo = 1
            ORDER BY nome
        """).fetchall()

        conn.close()

        for m in moradores:

            texto = (
                f"👤 {m['nome']}\n"
                f"🏢 Bloco: {m['bloco'] or '-'}   "
                f"Apto: {m['apartamento'] or '-'}\n"
                f"📞 {m['telefone'] or '-'}"
            )

            b = botao(
                texto,
                90
            )

            lista.add_widget(b)

        scroll.add_widget(lista)

        self.conteudo.add_widget(
            scroll
        )

        novo = botao(
            "➕ Novo morador"
        )

        novo.bind(
            on_release=lambda x:
            setattr(
                self.manager,
                "current",
                "novo_morador"
            )
        )

        self.conteudo.add_widget(
            novo
        )


# ============================================================
# SELEÇÃO DE MORADOR
# ============================================================

class Cadastro(TelaBase):

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.montar(
            "📦 Nova encomenda"
        )

        self.morador_id = None

        self.morador_btn = botao(
            "👤 SELECIONAR MORADOR"
        )

        self.morador_btn.bind(
            on_release=self.selecionar_morador
        )

        self.codigo = entrada(
            "Código / etiqueta"
        )

        self.descricao = entrada(
            "Descrição da encomenda"
        )

        self.foto = entrada(
            "Foto (será integrada ao APK)"
        )

        self.conteudo.add_widget(
            self.morador_btn
        )

        self.conteudo.add_widget(
            self.codigo
        )

        self.conteudo.add_widget(
            self.descricao
        )

        self.conteudo.add_widget(
            self.foto
        )

        foto = botao(
            "📷 Adicionar foto"
        )

        foto.bind(
            on_release=self.adicionar_foto
        )

        self.conteudo.add_widget(
            foto
        )

        salvar = botao(
            "📦 REGISTRAR ENCOMENDA"
        )

        salvar.bind(
            on_release=self.salvar
        )

        self.conteudo.add_widget(
            salvar
        )

    def selecionar_morador(self, *args):

        popup_layout = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )

        busca = entrada(
            "🔎 Pesquisar morador"
        )

        popup_layout.add_widget(
            busca
        )

        scroll = ScrollView()

        lista = GridLayout(
            cols=1,
            spacing=dp(5),
            size_hint_y=None
        )

        lista.bind(
            minimum_height=lista.setter(
                "height"
            )
        )

        scroll.add_widget(
            lista
        )

        popup_layout.add_widget(
            scroll
        )

        popup = Popup(
            title="Selecionar morador",
            content=popup_layout,
            size_hint=(0.9, 0.85)
        )

        def carregar(*args):

            lista.clear_widgets()

            conn = conectar()

            termo = busca.text.strip()

            moradores = conn.execute("""
                SELECT *
                FROM moradores
                WHERE ativo = 1
                AND nome LIKE ?
                ORDER BY nome
            """, (
                "%" + termo + "%",
            )).fetchall()

            conn.close()

            for m in moradores:

                b = botao(
                    f"{m['nome']} - "
                    f"Bloco {m['bloco'] or '-'} "
                    f"Apto {m['apartamento'] or '-'}",
                    60
                )

                b.bind(
                    on_release=lambda btn,
                    mor=m:
                    escolher(mor)
                )

                lista.add_widget(b)

        def escolher(morador):

            self.morador_id = morador["id"]

            self.morador_btn.text = (
                "👤 "
                + morador["nome"]
                + " | Bloco "
                + str(morador["bloco"] or "-")
                + " Apto "
                + str(morador["apartamento"] or "-")
            )

            popup.dismiss()

        busca.bind(
            text=carregar
        )

        carregar()

        popup.open()

    def adicionar_foto(self, *args):

        Popup(
            title="Câmera",
            content=label(
                "📷 A integração da câmera "
                "nativa será feita na versão APK.",
                16
            ),
            size_hint=(0.85, 0.4)
        ).open()

    def salvar(self, *args):

        if not self.morador_id:

            self.erro(
                "Selecione um morador."
            )
            return

        codigo = self.codigo.text.strip()

        if not codigo:

            self.erro(
                "Informe o código da encomenda."
            )
            return

        agora = datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )

        app = App.get_running_app()

        conn = conectar()

        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO encomendas
            (
                morador_id,
                codigo,
                descricao,
                foto,
                status,
                data_recebimento,
                funcionario_recebimento
            )
            VALUES (?, ?, ?, ?, 'PENDENTE', ?, ?)
        """, (
            self.morador_id,
            codigo,
            self.descricao.text,
            self.foto.text,
            agora,
            app.funcionario_id
        ))

        encomenda_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO historico
            (
                encomenda_id,
                acao,
                data,
                funcionario_id,
                observacao
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            encomenda_id,
            "RECEBIMENTO",
            agora,
            app.funcionario_id,
            "Encomenda recebida"
        ))

        conn.commit()
        conn.close()

        self.morador_id = None
        self.morador_btn.text = (
            "👤 SELECIONAR MORADOR"
        )
        self.codigo.text = ""
        self.descricao.text = ""
        self.foto.text = ""

        self.erro(
            "✅ Encomenda registrada!"
        )

    def erro(self, texto):

        Popup(
            title="Encomendas",
            content=label(
                texto,
                16
            ),
            size_hint=(0.8, 0.35)
        ).open()


# ============================================================
# BUSCA
# ============================================================

class Busca(TelaBase):

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.montar(
            "🔎 Buscar encomenda"
        )

        self.campo = entrada(
            "Código ou nome do morador"
        )

        self.conteudo.add_widget(
            self.campo
        )

        pesquisar = botao(
            "🔎 PESQUISAR"
        )

        pesquisar.bind(
            on_release=self.buscar
        )

        self.conteudo.add_widget(
            pesquisar
        )

        self.resultados = GridLayout(
            cols=1,
            spacing=dp(8),
            size_hint_y=None
        )

        self.resultados.bind(
            minimum_height=self.resultados.setter(
                "height"
            )
        )

        scroll = ScrollView()

        scroll.add_widget(
            self.resultados
        )

        self.conteudo.add_widget(
            scroll
        )

    def buscar(self, *args):

        self.resultados.clear_widgets()

        termo = self.campo.text.strip()

        conn = conectar()

        resultados = conn.execute("""
            SELECT
                encomendas.*,
                moradores.nome AS morador,
                moradores.bloco,
                moradores.apartamento
            FROM encomendas
            JOIN moradores
            ON moradores.id = encomendas.morador_id
            WHERE encomendas.codigo LIKE ?
            OR moradores.nome LIKE ?
            ORDER BY encomendas.id DESC
        """, (
            "%" + termo + "%",
            "%" + termo + "%"
        )).fetchall()

        conn.close()

        for e in resultados:

            texto = (
                f"📦 {e['codigo']}\n"
                f"👤 {e['morador']}\n"
                f"🏢 Bloco {e['bloco'] or '-'} "
                f"Apto {e['apartamento'] or '-'}\n"
                f"📌 Status: {e['status']}\n"
                f"📅 Recebida: {e['data_recebimento']}"
            )

            b = botao(
                texto,
                110
            )

            if e["status"] == "PENDENTE":

                b.bind(
                    on_release=lambda btn,
                    eid=e["id"]:
                    self.confirmar_entrega(eid)
                )

            self.resultados.add_widget(b)

    def confirmar_entrega(self, encomenda_id):

        popup_layout = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(10)
        )

        popup_layout.add_widget(
            label(
                "Confirmar entrega desta encomenda?",
                17
            )
        )

        confirmar = botao(
            "✅ CONFIRMAR ENTREGA"
        )

        cancelar = botao(
            "Cancelar"
        )

        popup_layout.add_widget(
            confirmar
        )

        popup_layout.add_widget(
            cancelar
        )

        popup = Popup(
            title="Confirmar entrega",
            content=popup_layout,
            size_hint=(0.85, 0.45)
        )

        confirmar.bind(
            on_release=lambda x:
            self.entregar(
                encomenda_id,
                popup
            )
        )

        cancelar.bind(
            on_release=popup.dismiss
        )

        popup.open()

    def entregar(self, encomenda_id, popup):

        agora = datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )

        app = App.get_running_app()

        conn = conectar()

        conn.execute("""
            UPDATE encomendas
            SET
                status = 'ENTREGUE',
                data_entrega = ?,
                funcionario_entrega = ?
            WHERE id = ?
        """, (
            agora,
            app.funcionario_id,
            encomenda_id
        ))

        conn.execute("""
            INSERT INTO historico
            (
                encomenda_id,
                acao,
                data,
                funcionario_id,
                observacao
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            encomenda_id,
            "ENTREGA",
            agora,
            app.funcionario_id,
            "Encomenda entregue"
        ))

        conn.commit()
        conn.close()

        popup.dismiss()

        self.buscar()


# ============================================================
# PENDENTES
# ============================================================

class Pendentes(TelaBase):

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.montar(
            "⏳ Encomendas pendentes"
        )

    def on_pre_enter(self):

        self.atualizar()

    def atualizar(self):

        self.conteudo.clear_widgets()

        scroll = ScrollView()

        lista = GridLayout(
            cols=1,
            spacing=dp(8),
            size_hint_y=None
        )

        lista.bind(
            minimum_height=lista.setter(
                "height"
            )
        )

        conn = conectar()

        encomendas = conn.execute("""
            SELECT
                encomendas.*,
                moradores.nome AS morador,
                moradores.bloco,
                moradores.apartamento
            FROM encomendas
            JOIN moradores
            ON moradores.id = encomendas.morador_id
            WHERE encomendas.status = 'PENDENTE'
            ORDER BY encomendas.id DESC
        """).fetchall()

        conn.close()

        for e in encomendas:

            texto = (
                f"📦 {e['codigo']}\n"
                f"👤 {e['morador']}\n"
                f"🏢 Bloco {e['bloco'] or '-'} "
                f"Apto {e['apartamento'] or '-'}\n"
                f"📅 {e['data_recebimento']}"
            )

            b = botao(
                texto,
                105
            )

            b.bind(
                on_release=lambda btn,
                eid=e["id"]:
                Busca.confirmar_entrega(
                    self,
                    eid
                )
            )

            lista.add_widget(b)

        scroll.add_widget(lista)

        self.conteudo.add_widget(
            scroll
        )


# ============================================================
# TODAS
# ============================================================

class Todas(TelaBase):

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.montar(
            "📋 Todas as encomendas"
        )

    def on_pre_enter(self):

        self.atualizar()

    def atualizar(self):

        self.conteudo.clear_widgets()

        scroll = ScrollView()

        lista = GridLayout(
            cols=1,
            spacing=dp(8),
            size_hint_y=None
        )

        lista.bind(
            minimum_height=lista.setter(
                "height"
            )
        )

        conn = conectar()

        encomendas = conn.execute("""
            SELECT
                encomendas.*,
                moradores.nome AS morador
            FROM encomendas
            JOIN moradores
            ON moradores.id = encomendas.morador_id
            ORDER BY encomendas.id DESC
        """).fetchall()

        conn.close()

        for e in encomendas:

            texto = (
                f"📦 {e['codigo']}\n"
                f"👤 {e['morador']}\n"
                f"📌 {e['status']}\n"
                f"📅 Recebida: "
                f"{e['data_recebimento']}"
            )

            if e["data_entrega"]:

                texto += (
                    f"\n✅ Entregue: "
                    f"{e['data_entrega']}"
                )

            lista.add_widget(
                botao(
                    texto,
                    100
                )
            )

        scroll.add_widget(lista)

        self.conteudo.add_widget(
            scroll
        )


# ============================================================
# HISTÓRICO
# ============================================================

class Historico(TelaBase):

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.montar(
            "🕘 Histórico"
        )

    def on_pre_enter(self):

        self.atualizar()

    def atualizar(self):

        self.conteudo.clear_widgets()

        scroll = ScrollView()

        lista = GridLayout(
            cols=1,
            spacing=dp(8),
            size_hint_y=None
        )

        lista.bind(
            minimum_height=lista.setter(
                "height"
            )
        )

        conn = conectar()

        registros = conn.execute("""
            SELECT
                historico.*,
                encomendas.codigo,
                funcionarios.nome AS funcionario
            FROM historico
            LEFT JOIN encomendas
            ON encomendas.id = historico.encomenda_id
            LEFT JOIN funcionarios
            ON funcionarios.id = historico.funcionario_id
            ORDER BY historico.id DESC
        """).fetchall()

        conn.close()

        for h in registros:

            texto = (
                f"📦 Código: {h['codigo']}\n"
                f"⚙️ Ação: {h['acao']}\n"
                f"👤 Funcionário: "
                f"{h['funcionario'] or '-'}\n"
                f"📅 {h['data']}"
            )

            lista.add_widget(
                botao(
                    texto,
                    105
                )
            )

        scroll.add_widget(lista)

        self.conteudo.add_widget(
            scroll
        )


# ============================================================
# FUNCIONÁRIOS
# ============================================================

class Funcionarios(TelaBase):

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.montar(
            "👥 Funcionários"
        )

        self.nome = entrada(
            "Nome"
        )

        self.usuario = entrada(
            "Usuário"
        )

        self.senha = entrada(
            "Senha",
            password=True
        )

        self.perfil = entrada(
            "Perfil: admin / supervisor / porteiro"
        )

        self.conteudo.add_widget(
            self.nome
        )

        self.conteudo.add_widget(
            self.usuario
        )

        self.conteudo.add_widget(
            self.senha
        )

        self.conteudo.add_widget(
            self.perfil
        )

        salvar = botao(
            "👤 CADASTRAR FUNCIONÁRIO"
        )

        salvar.bind(
            on_release=self.salvar
        )

        self.conteudo.add_widget(
            salvar
        )

        self.lista = GridLayout(
            cols=1,
            spacing=dp(8),
            size_hint_y=None
        )

        self.lista.bind(
            minimum_height=self.lista.setter(
                "height"
            )
        )

        scroll = ScrollView()

        scroll.add_widget(
            self.lista
        )

        self.conteudo.add_widget(
            scroll
        )

    def on_pre_enter(self):

        self.atualizar()

    def salvar(self, *args):

        if not self.nome.text.strip():
            return

        perfil = self.perfil.text.strip().lower()

        if perfil not in (
            "admin",
            "supervisor",
            "porteiro"
        ):

            self.mostrar(
                "Perfil inválido."
            )
            return

        try:

            conn = conectar()

            conn.execute("""
                INSERT INTO funcionarios
                (nome, usuario, senha, perfil)
                VALUES (?, ?, ?, ?)
            """, (
                self.nome.text,
                self.usuario.text,
                hash_senha(
                    self.senha.text
                ),
                perfil
            ))

            conn.commit()
            conn.close()

            self.nome.text = ""
            self.usuario.text = ""
            self.senha.text = ""
            self.perfil.text = ""

            self.atualizar()

            self.mostrar(
                "✅ Funcionário cadastrado!"
            )

        except sqlite3.IntegrityError:

            self.mostrar(
                "❌ Este usuário já existe."
            )

    def atualizar(self):

        self.lista.clear_widgets()

        conn = conectar()

        funcionarios = conn.execute("""
            SELECT *
            FROM funcionarios
            WHERE ativo = 1
            ORDER BY nome
        """).fetchall()

        conn.close()

        for f in funcionarios:

            self.lista.add_widget(
                botao(
                    f"👤 {f['nome']} | "
                    f"{f['usuario']} | "
                    f"{f['perfil']}",
                    60
                )
            )

    def mostrar(self, texto):

        Popup(
            title="Funcionários",
            content=label(
                texto,
                16
            ),
            size_hint=(0.8, 0.35)
        ).open()


# ============================================================
# RELATÓRIO
# ============================================================

class Relatorio(TelaBase):

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        self.montar(
            "📊 Relatórios"
        )

    def on_pre_enter(self):

        self.atualizar()

    def atualizar(self):

        self.conteudo.clear_widgets()

        conn = conectar()

        total = conn.execute("""
            SELECT COUNT(*)
            FROM encomendas
        """).fetchone()[0]

        pendentes = conn.execute("""
            SELECT COUNT(*)
            FROM encomendas
            WHERE status = 'PENDENTE'
        """).fetchone()[0]

        entregues = conn.execute("""
            SELECT COUNT(*)
            FROM encomendas
            WHERE status = 'ENTREGUE'
        """).fetchone()[0]

        hoje = datetime.now().strftime(
            "%d/%m/%Y"
        )

        recebidas_hoje = conn.execute("""
            SELECT COUNT(*)
            FROM encomendas
            WHERE data_recebimento LIKE ?
        """, (
            hoje + "%",
        )).fetchone()[0]

        entregues_hoje = conn.execute("""
            SELECT COUNT(*)
            FROM encomendas
            WHERE data_entrega LIKE ?
        """, (
            hoje + "%",
        )).fetchone()[0]

        conn.close()

        dados = [
            ("📦 Total de encomendas", total),
            ("⏳ Pendentes", pendentes),
            ("✅ Entregues", entregues),
            ("📥 Recebidas hoje", recebidas_hoje),
            ("📤 Entregues hoje", entregues_hoje)
        ]

        for nome, valor in dados:

            self.conteudo.add_widget(
                botao(
                    f"{nome}: {valor}",
                    60
                )
            )


# ============================================================
# APLICATIVO
# ============================================================

class ControleEncomendas(App):

    def build(self):

        Window.clearcolor = (
            0.95,
            0.96,
            0.98,
            1
        )

        criar_banco()

        self.funcionario_id = None
        self.funcionario_nome = ""
        self.funcionario_perfil = ""

        sm = ScreenManager()

        sm.add_widget(
            Login(name="login")
        )

        sm.add_widget(
            Inicio(name="inicio")
        )

        sm.add_widget(
            NovoMorador(name="novo_morador")
        )

        sm.add_widget(
            Moradores(name="moradores")
        )

        sm.add_widget(
            Cadastro(name="cadastro")
        )

        sm.add_widget(
            Busca(name="busca")
        )

        sm.add_widget(
            Pendentes(name="pendentes")
        )

        sm.add_widget(
            Todas(name="todas")
        )

        sm.add_widget(
            Historico(name="historico")
        )

        sm.add_widget(
            Funcionarios(name="funcionarios")
        )

        sm.add_widget(
            Relatorio(name="relatorio")
        )

        return sm


# ===========================================================
# EXECUTAR
# ============================================================

if __name__ == "__main__":
    ControleEncomendas().run()

