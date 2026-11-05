import asyncio
import json
from html import escape
from urllib.parse import urlencode

from pyscript import document, window
from pyodide.http import pyfetch
from pyodide.ffi import create_proxy

API_URL = "https://itunes.apple.com/search"
LIMITE = 12

# ---------- Elementos da página ----------
form = document.querySelector("#search-form")
campo = document.querySelector("#search-input")
status = document.querySelector("#status")
grade = document.querySelector("#grid")
painel_album = document.querySelector("#album-view")
lista_lib = document.querySelector("#lib-list")
lista_albuns = document.querySelector("#album-list")
contador_lib = document.querySelector("#lib-count")
contador_albuns = document.querySelector("#album-count")
form_album = document.querySelector("#album-form")
campo_album = document.querySelector("#album-input")
botao_tema = document.querySelector("#theme-btn")
sidebar = document.querySelector("#sidebar")
player = document.querySelector("#player")
np_capa = document.querySelector("#np-capa")
np_nome = document.querySelector("#np-nome")
np_artista = document.querySelector("#np-artista")


# ---------- Armazenamento (localStorage guarda tudo no navegador) ----------
def carregar(chave, padrao):
    try:
        texto = window.localStorage.getItem(chave)
        return json.loads(texto) if texto else padrao
    except Exception:
        return padrao


def guardar(chave, valor):
    try:
        window.localStorage.setItem(chave, json.dumps(valor))
    except Exception:
        pass


# biblioteca: {id: {id, nome, artista, capa, audio}}
# albuns:     {nome_do_album: [id, id, ...]}
biblioteca = carregar("biblioteca", {})
albuns = carregar("albuns", {})
resultados_atuais = {}   # músicas da última busca
vista = "busca"          # "busca" ou o nome de um álbum


# ---------- Chamada à API ----------
async def buscar_musicas(termo):
    """Faz o pedido à API do iTunes e devolve a lista de resultados.

    `await` pausa ESTA função até a resposta chegar, sem travar a página.
    """
    params = urlencode({"term": termo, "entity": "song", "limit": LIMITE})
    resposta = await pyfetch(f"{API_URL}?{params}")
    if not resposta.ok:
        raise RuntimeError(f"Erro HTTP {resposta.status}")
    dados = await resposta.json()
    return dados["results"]


def simplificar(m):
    """Guarda só os 4 campos que importam (+ um id) de cada música."""
    capa = m.get("artworkUrl100", "").replace("100x100", "300x300")
    return {
        "id": str(m.get("trackId", m.get("previewUrl", ""))),
        "nome": m.get("trackName", "Sem título"),
        "artista": m.get("artistName", "Artista desconhecido"),
        "capa": capa,
        "audio": m.get("previewUrl", ""),
    }


# ---------- HTML dos componentes ----------
def html_card(m):
    salva = m["id"] in biblioteca
    classe = "btn-salvar ativo" if salva else "btn-salvar"
    texto = "✓ Na biblioteca" if salva else "＋ Salvar na biblioteca"
    return f"""
    <article class="card">
      <div class="capa"><img src="{escape(m['capa'])}" alt="Capa do álbum" loading="lazy"></div>
      <h3 title="{escape(m['nome'])}">{escape(m['nome'])}</h3>
      <p>{escape(m['artista'])}</p>
      <audio controls preload="none" src="{escape(m['audio'])}"></audio>
      <button class="{classe}" data-acao="salvar" data-id="{escape(m['id'])}">{texto}</button>
    </article>"""


def html_item_biblioteca(m):
    opcoes = "".join(
        f'<option value="{escape(nome)}">{escape(nome)}</option>' for nome in albuns
    )
    select = ""
    if albuns:
        select = (
            f'<select data-acao="add-album" data-id="{escape(m["id"])}" title="Adicionar a um álbum">'
            f'<option value="">＋ Álbum</option>{opcoes}</select>'
        )
    return f"""
    <li class="item">
      <button class="play" data-acao="tocar" data-id="{escape(m['id'])}" title="Tocar">▶</button>
      <img src="{escape(m['capa'])}" alt="">
      <div class="info"><strong>{escape(m['nome'])}</strong><span>{escape(m['artista'])}</span></div>
      {select}
      <button class="icone pequeno" data-acao="remover-lib" data-id="{escape(m['id'])}" title="Remover da biblioteca">✕</button>
    </li>"""


def html_item_album(m):
    return f"""
    <li class="item">
      <button class="play" data-acao="tocar" data-id="{escape(m['id'])}" title="Tocar">▶</button>
      <img src="{escape(m['capa'])}" alt="">
      <div class="info"><strong>{escape(m['nome'])}</strong><span>{escape(m['artista'])}</span></div>
      <button class="icone pequeno" data-acao="remover-do-album" data-id="{escape(m['id'])}" title="Tirar do álbum">✕</button>
    </li>"""


# ---------- Renderização ----------
def renderizar_biblioteca():
    contador_lib.textContent = str(len(biblioteca))
    if not biblioteca:
        lista_lib.innerHTML = (
            '<li class="vazio">Nenhuma música salva ainda.<br>'
            "Use “Salvar” nos resultados da busca.</li>"
        )
        return
    lista_lib.innerHTML = "".join(html_item_biblioteca(m) for m in biblioteca.values())


def renderizar_albuns():
    contador_albuns.textContent = str(len(albuns))
    if not albuns:
        lista_albuns.innerHTML = '<li class="vazio">Crie seu primeiro álbum acima.</li>'
        return
    itens = ""
    for nome, ids in albuns.items():
        classe = "album-link ativo" if nome == vista else "album-link"
        itens += (
            f'<li><button class="{classe}" data-acao="abrir-album" data-nome="{escape(nome)}">'
            f'<span class="album-icone">♫</span>'
            f'<span class="album-nome">{escape(nome)}</span>'
            f'<span class="album-qtd">{len(ids)}</span></button></li>'
        )
    lista_albuns.innerHTML = itens


def renderizar_painel_album():
    if vista == "busca":
        return
    ids = albuns.get(vista, [])
    itens = "".join(html_item_album(biblioteca[i]) for i in ids if i in biblioteca)
    vazio = (
        '<li class="vazio">Álbum vazio. Use o menu “＋ Álbum” nas músicas '
        "da sua biblioteca (barra lateral).</li>"
    )
    painel_album.innerHTML = f"""
    <div class="album-topo">
      <div class="album-arte">♫</div>
      <div class="album-titulo">
        <span class="rotulo">ÁLBUM</span>
        <h2>{escape(vista)}</h2>
        <p>{len(ids)} músicas</p>
      </div>
      <button class="perigo" data-acao="excluir-album">Excluir álbum</button>
    </div>
    <ul class="lista grande">{itens or vazio}</ul>"""


def mostrar_vista():
    na_busca = vista == "busca"
    grade.hidden = not na_busca
    status.hidden = not na_busca
    painel_album.hidden = na_busca
    renderizar_albuns()
    renderizar_painel_album()


def atualizar_botao_card(id_):
    """Atualiza só o botão do card (sem refazer a grade, para não parar o áudio)."""
    botao = document.querySelector(f'[data-acao="salvar"][data-id="{id_}"]')
    if botao is None:
        return
    if id_ in biblioteca:
        botao.className = "btn-salvar ativo"
        botao.textContent = "✓ Na biblioteca"
    else:
        botao.className = "btn-salvar"
        botao.textContent = "＋ Salvar na biblioteca"


# ---------- Ações ----------
def alternar_biblioteca(id_):
    if id_ in biblioteca:
        del biblioteca[id_]
        for ids in albuns.values():      # tira a música dos álbuns também
            if id_ in ids:
                ids.remove(id_)
    elif id_ in resultados_atuais:
        biblioteca[id_] = resultados_atuais[id_]
    guardar("biblioteca", biblioteca)
    guardar("albuns", albuns)
    atualizar_botao_card(id_)
    renderizar_biblioteca()
    mostrar_vista()


def tocar(id_):
    musica = biblioteca.get(id_)
    if musica is None:
        return
    player.src = musica["audio"]
    player.play()
    np_capa.innerHTML = f'<img src="{escape(musica["capa"])}" alt="">'
    np_nome.textContent = musica["nome"]
    np_artista.textContent = musica["artista"]


def adicionar_ao_album(nome, id_):
    ids = albuns.setdefault(nome, [])
    if id_ not in ids:
        ids.append(id_)
    guardar("albuns", albuns)
    renderizar_biblioteca()
    mostrar_vista()


def criar_album(evento):
    global vista
    evento.preventDefault()
    nome = campo_album.value.strip()
    if not nome:
        return
    if nome not in albuns:
        albuns[nome] = []
        guardar("albuns", albuns)
    campo_album.value = ""
    vista = nome
    renderizar_biblioteca()   # atualiza os menus "＋ Álbum"
    mostrar_vista()


def ao_clicar(evento):
    """Um único 'ouvinte' de cliques para a página toda (delegação de eventos)."""
    global vista
    alvo = evento.target.closest("[data-acao]")
    if alvo is None:
        return
    acao = alvo.getAttribute("data-acao")
    id_ = alvo.getAttribute("data-id")

    if acao == "salvar":
        alternar_biblioteca(id_)
    elif acao == "tocar":
        tocar(id_)
    elif acao == "remover-lib":
        alternar_biblioteca(id_)
    elif acao == "remover-do-album":
        if id_ in albuns.get(vista, []):
            albuns[vista].remove(id_)
            guardar("albuns", albuns)
            mostrar_vista()
    elif acao == "abrir-album":
        vista = alvo.getAttribute("data-nome")
        mostrar_vista()
        sidebar.classList.remove("open")
    elif acao == "excluir-album":
        if window.confirm(f"Excluir o álbum “{vista}”?"):
            albuns.pop(vista, None)
            guardar("albuns", albuns)
            vista = "busca"
            renderizar_biblioteca()
            mostrar_vista()
    elif acao == "ir-busca":
        vista = "busca"
        mostrar_vista()
        sidebar.classList.remove("open")
    elif acao == "menu":
        sidebar.classList.toggle("open")


def ao_mudar(evento):
    """Escuta os menus '＋ Álbum' da biblioteca."""
    alvo = evento.target
    if alvo.getAttribute("data-acao") == "add-album" and alvo.value:
        adicionar_ao_album(alvo.value, alvo.getAttribute("data-id"))


def pausar_outros(evento):
    """Quando um áudio começa a tocar, pausa todos os outros."""
    for a in document.querySelectorAll("audio"):
        if not a.isSameNode(evento.target):
            a.pause()


# ---------- Busca ----------
def ao_enviar(evento):
    # Função NORMAL (não async): o preventDefault precisa rodar na hora,
    # antes de o navegador recarregar a página.
    evento.preventDefault()
    asyncio.ensure_future(ao_buscar())


async def ao_buscar():
    global vista, resultados_atuais
    termo = campo.value.strip()
    if not termo:
        status.textContent = "Digite o nome de um artista ou música."
        return

    vista = "busca"
    mostrar_vista()
    grade.innerHTML = ""
    status.textContent = "Buscando músicas…"

    try:
        resultados = await buscar_musicas(termo)
    except Exception:
        status.textContent = "Erro ao buscar. Verifique sua internet e tente de novo."
        return

    # Só mantém músicas que têm prévia de áudio
    musicas = [simplificar(m) for m in resultados if m.get("previewUrl")]

    if not musicas:
        status.textContent = "Não encontramos resultados."
        return

    resultados_atuais = {m["id"]: m for m in musicas}
    status.textContent = f"{len(musicas)} resultados para “{termo}”"
    grade.innerHTML = "".join(html_card(m) for m in musicas)


# ---------- Modo escuro / claro ----------
def aplicar_tema(tema):
    document.documentElement.setAttribute("data-theme", tema)
    guardar("tema", tema)


def alternar_tema(evento):
    atual = document.documentElement.getAttribute("data-theme")
    aplicar_tema("light" if atual == "dark" else "dark")


# ---------- Ligando tudo ----------
form.addEventListener("submit", create_proxy(ao_enviar))
form_album.addEventListener("submit", create_proxy(criar_album))
document.addEventListener("click", create_proxy(ao_clicar))
document.addEventListener("change", create_proxy(ao_mudar))
# 'play' não "borbulha", então escutamos na fase de captura (True)
document.addEventListener("play", create_proxy(pausar_outros), True)
botao_tema.addEventListener("click", create_proxy(alternar_tema))

tema_salvo = carregar("tema", None)
if tema_salvo:
    document.documentElement.setAttribute("data-theme", tema_salvo)

renderizar_biblioteca()
mostrar_vista()
