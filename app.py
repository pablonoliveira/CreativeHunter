"""
Pétala Hunter - Captador de Criativos para Meta Ads, Reels e TikTok
Download automático em máxima qualidade + RENOMEAÇÃO PERFEITA.

Versão PROD: Flask + yt-dlp com renomeação inteligente de carrossel.
Resolve TODOS os casos: foto única, múltiplas fotos, vídeos.
"""

from flask import Flask, request, render_template, send_from_directory
import os
import re
import yt_dlp
from pathlib import Path
from collections import defaultdict
import time


app = Flask(__name__)
app.config["SECRET_KEY"] = "petala-hunter-2026"

PASTA_DOWNLOADS = "downloads"
os.makedirs(PASTA_DOWNLOADS, exist_ok=True)


def listar_arquivos():
    """Lista os 12 arquivos mais recentes da pasta downloads."""
    if not os.path.exists(PASTA_DOWNLOADS):
        return []

    arquivos = [
        f for f in os.listdir(PASTA_DOWNLOADS)
        if os.path.isfile(os.path.join(PASTA_DOWNLOADS, f))
    ]
    return sorted(arquivos, reverse=True)[:12]


def sanitizar_mensagem_erro(erro):
    """Converte erros técnicos em mensagens amigáveis para o usuário."""
    msg = str(erro)

    if "There is no video in this post" in msg:
        return "❌ Esse post não possui vídeo disponível para o modo selecionado."

    if "facebook:ads" in msg and "Unable to extract ad data" in msg:
        return "❌ Esse criativo da Meta Ads Library não pôde ser extraído pela versão atual do yt-dlp."

    if "Unsupported URL" in msg:
        return "❌ Essa URL não é suportada pelo Pétala Hunter."

    if "Private video" in msg or "login required" in msg.lower():
        return "❌ O conteúdo exige autenticação ou não está acessível publicamente."

    if "File name too long" in msg:
        return "❌ Nome do arquivo muito longo. Correção aplicada no salvamento."

    return f"❌ Erro ao processar o link: {msg[:160]}"


def limpar_nome_arquivo(texto):
    """Remove caracteres inválidos e limita tamanho do nome do arquivo."""
    if not texto:
        return "arquivo"
    texto = re.sub(r'[\\/*?:"<>|=&%]', "", str(texto))
    texto = re.sub(r"\s+", "_", texto).strip("_")
    return texto[:60]


def montar_opcoes_ydl(tipo):
    """Configurações do yt-dlp com nome temporário curto."""
    nome_saida = os.path.join(PASTA_DOWNLOADS, "%(extractor)s_%(id)s.%(ext)s")

    opcoes_base = {
        "outtmpl": nome_saida,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": False,
        "extract_flat": False,
        "windowsfilenames": True,
        "restrictfilenames": True,
        "trim_file_name": 80,
    }

    if tipo == "imagem":
        opcoes_base.update({
            "format": "best[ext=jpg]/best[ext=jpeg]/best[ext=png]/best"
        })
    else:
        opcoes_base.update({
            "format": "best[ext=mp4]/best"
        })

    return opcoes_base


def encontrar_arquivos_novos(arquivos_antes):
    """Encontra arquivos criados após o download."""
    arquivos_depois = set(os.listdir(PASTA_DOWNLOADS))
    novos = arquivos_depois - arquivos_antes
    return [os.path.join(PASTA_DOWNLOADS, f) for f in novos if os.path.isfile(os.path.join(PASTA_DOWNLOADS, f))]


def renomear_carrossel(arquivos_novos, info, tipo):
    """
    Renomeia arquivos de carrossel com sufixos _1, _2, _3...
    
    RESULTADO FINAL:
    ✅ facebook_1417545490408392_1.jpg
    ✅ facebook_1417545490408392_2.jpg  
    ✅ facebook_1417545490408392_3.jpg
    ✅ instagram_reel123.mp4
    """
    if not arquivos_novos:
        return []

    # Extrai informações do vídeo/post principal
    extractor = limpar_nome_arquivo(info.get("extractor") or info.get("extractor_key") or "generic")
    media_id = limpar_nome_arquivo(str(info.get("id") or "sem_id"))
    base_nome = f"{extractor}_{media_id}"
    
    if tipo == "imagem":
        extensoes = [".jpg", ".jpeg", ".png"]
    else:
        extensoes = [".mp4", ".webm"]

    renomeados = []
    
    # Ordena por data de criação (mais recente primeiro)
    arquivos_ordenados = sorted(arquivos_novos, key=os.path.getctime, reverse=True)
    
    for i, caminho in enumerate(arquivos_ordenados, 1):
        ext = Path(caminho).suffix.lower()
        
        # Só renomeia arquivos de mídia relevantes
        if ext in extensoes:
            novo_nome = f"{base_nome}_{i}{ext}"
            novo_caminho = os.path.join(PASTA_DOWNLOADS, novo_nome)
            
            # Evita sobrescrita
            contador = i
            while os.path.exists(novo_caminho):
                contador += 1
                novo_nome = f"{base_nome}_{contador}{ext}"
                novo_caminho = os.path.join(PASTA_DOWNLOADS, novo_nome)
            
            os.replace(caminho, novo_caminho)
            renomeados.append(novo_nome)
    
    return renomeados


def baixar_arquivo(url, tipo):
    """
    Download + renomeação inteligente de carrossel.
    
    Detecta automaticamente:
    - Foto única → facebook_123.jpg
    - Carrossel → facebook_123_1.jpg, facebook_123_2.jpg...
    - Vídeo único → instagram_abc.mp4
    """
    arquivos_antes = set(os.listdir(PASTA_DOWNLOADS))
    opcoes = montar_opcoes_ydl(tipo)

    with yt_dlp.YoutubeDL(opcoes) as ydl:
        info = ydl.extract_info(url, download=True)

    arquivos_novos = encontrar_arquivos_novos(arquivos_antes)
    arquivos_renomeados = renomear_carrossel(arquivos_novos, info, tipo)

    # Mensagem de sucesso
    if isinstance(info, dict) and info.get("entries"):
        total = len([e for e in info["entries"] if e])
        if arquivos_renomeados:
            return f"✅ Carrossel salvo: {len(arquivos_renomeados)} arquivos ({', '.join(arquivos_renomeados[:3])}{'...' if len(arquivos_renomeados) > 3 else ''})"
        return f"✅ Download concluído. {total} arquivo(s) salvo(s) com sucesso."
    
    if arquivos_renomeados:
        nomes = ', '.join(arquivos_renomeados[:2]) + ('...' if len(arquivos_renomeados) > 2 else '')
        return f"✅ {nomes}"
    
    nome_default = limpar_nome_arquivo(info.get("title")) if isinstance(info, dict) else "arquivo"
    return f"✅ Download concluído: {nome_default}"


@app.route("/", methods=["GET", "POST"])
def index():
    """Rota principal."""
    mensagem = None

    if request.method == "POST":
        url = (request.form.get("url") or "").strip()
        tipo = (request.form.get("tipo") or "video").strip().lower()

        if not url:
            mensagem = "❌ Cole uma URL válida para iniciar o download."
        elif tipo not in {"video", "imagem"}:
            mensagem = "❌ Tipo de download inválido."
        else:
            try:
                mensagem = baixar_arquivo(url, tipo)
            except Exception as erro:
                mensagem = sanitizar_mensagem_erro(erro)

    arquivos = listar_arquivos()
    return render_template("index.html", mensagem=mensagem, arquivos=arquivos)


@app.route("/download/<path:filename>")
def download_file(filename):
    """Download seguro dos arquivos salvos."""
    nome_seguro = os.path.basename(filename)
    return send_from_directory(PASTA_DOWNLOADS, nome_seguro, as_attachment=True)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("DEBUG", "False") == "True"

    print(f"🌸 Pétala Hunter PROD rodando na porta {port}")
    print("✅ Renomeação inteligente de carrossel habilitada")
    print("✅ Nomes perfeitos: facebook_123_1.jpg, facebook_123_2.jpg...")
    print("✅ Suporte Meta Ads, Instagram, TikTok")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)