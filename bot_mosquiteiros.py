import os
import json
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ─── CONFIGURAÇÕES ───────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8723853827:AAFeOqlYT6goT6bbajCWpFmVLNnN2ZjR_H0")
CHAT_ID        = "5303204887"

JSONBIN_KEY = os.environ.get("JSONBIN_KEY", "$2a$10$/s4UWuZZrxTnJ6UbzbxTju6P/jitCDCIZvr4XQjlS4xTVrKL1qmGq")
JSONBIN_BIN = os.environ.get("JSONBIN_BIN", "69fbf4d9adc21f119a64af4c")
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN}"
HEADERS     = {"X-Master-Key": JSONBIN_KEY, "Content-Type": "application/json"}

# ─── JSONBIN: LER / SALVAR ────────────────────────────────────────────────────
def ler_dados():
    try:
        r = requests.get(JSONBIN_URL, headers=HEADERS, timeout=10)
        record = r.json().get("record", {})
        record.setdefault("despesas", [])
        record.setdefault("estoque", [])
        record.setdefault("vendas", [])
        return record
    except Exception as e:
        print(f"Erro ao ler JSONBin: {e}")
        return {"despesas": [], "estoque": [], "vendas": []}

def salvar_dados(dados):
    try:
        requests.put(JSONBIN_URL, json=dados, headers=HEADERS, timeout=10)
    except Exception as e:
        print(f"Erro ao salvar JSONBin: {e}")

# ─── PRODUTOS PADRÃO ─────────────────────────────────────────────────────────
PRODUTOS_PADRAO = [
    {"id": "MGA-001", "nome": "Mosquiteiro Gigante Aberto",  "estoque": 0, "custo": 0, "preco": 0},
    {"id": "PES-001", "nome": "Peseira",                      "estoque": 0, "custo": 0, "preco": 0},
    {"id": "CAL-001", "nome": "Capa de Almofada",             "estoque": 0, "custo": 0, "preco": 0},
    {"id": "MFI-001", "nome": "Mosquiteiro Filo",             "estoque": 0, "custo": 0, "preco": 0},
    {"id": "MCP-001", "nome": "Mosquiteiro Casal Padrão",     "estoque": 0, "custo": 0, "preco": 0},
    {"id": "MGF-001", "nome": "Mosquiteiro Gigante Fechado",  "estoque": 0, "custo": 0, "preco": 0},
]

def garantir_produtos(dados):
    ids_existentes = [p["id"] for p in dados["estoque"]]
    for p in PRODUTOS_PADRAO:
        if p["id"] not in ids_existentes:
            dados["estoque"].append(dict(p))
    return dados

def buscar_produto(dados, termo):
    termo = termo.lower()
    for p in dados["estoque"]:
        if termo in p["nome"].lower() or termo in p["id"].lower():
            return p
    return None

def mes_atual():
    return datetime.now().strftime("%Y-%m")

def formatar_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ─── COMANDOS ────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    texto = (
        "🦟 *Bot Mosquiteiros — Online!*\n\n"
        "Comandos disponíveis:\n"
        "/estoque — Ver estoque atual\n"
        "/produtos — Listar produtos\n"
        "/entrada [produto] [qtd] — Registrar entrada\n"
        "/venda [produto] [qtd] — Registrar venda\n"
        "/custo [produto] [valor] — Atualizar custo\n"
        "/preco [produto] [valor] — Atualizar preço\n"
        "/despesa [valor] [descrição] — Adicionar despesa\n"
        "/despesas — Ver despesas do mês\n"
        "/resumo — Resumo financeiro\n"
        "/alerta — Produtos com estoque baixo\n"
        "/apagar [número] — Apagar despesa\n"
        "/limpar — Apagar todas as despesas do mês"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")

async def cmd_estoque(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    dados = garantir_produtos(ler_dados())
    linhas = ["📦 *Estoque Atual*\n"]
    for p in dados["estoque"]:
        emoji = "🔴" if p["estoque"] == 0 else "🟡" if p["estoque"] < 5 else "🟢"
        linhas.append(f"{emoji} *{p['nome']}* — {p['estoque']} un")
    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")

async def cmd_produtos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    dados = garantir_produtos(ler_dados())
    linhas = ["🛍 *Produtos Cadastrados*\n"]
    for i, p in enumerate(dados["estoque"], 1):
        margem = ""
        if p["custo"] > 0 and p["preco"] > 0:
            m = ((p["preco"] - p["custo"]) / p["preco"]) * 100
            margem = f" | Margem: {m:.0f}%"
        linhas.append(
            f"{i}. *{p['nome']}* ({p['id']})\n"
            f"   Custo: {formatar_real(p['custo'])} | Venda: {formatar_real(p['preco'])}{margem}\n"
            f"   Estoque: {p['estoque']} un"
        )
    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")

async def cmd_entrada(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("❌ Uso: /entrada [produto] [qtd]\nEx: /entrada casal 10")
        return
    try:
        qtd = int(args[-1])
        termo = " ".join(args[:-1])
    except ValueError:
        await update.message.reply_text("❌ A quantidade deve ser um número inteiro.")
        return
    dados = garantir_produtos(ler_dados())
    produto = buscar_produto(dados, termo)
    if not produto:
        await update.message.reply_text(f"❌ Produto '{termo}' não encontrado.")
        return
    produto["estoque"] += qtd
    salvar_dados(dados)
    await update.message.reply_text(
        f"✅ *Entrada registrada!*\n{produto['nome']}: +{qtd} un\nTotal: {produto['estoque']} un",
        parse_mode="Markdown"
    )

async def cmd_venda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("❌ Uso: /venda [produto] [qtd]\nEx: /venda casal 3")
        return
    try:
        qtd = int(args[-1])
        termo = " ".join(args[:-1])
    except ValueError:
        await update.message.reply_text("❌ A quantidade deve ser um número inteiro.")
        return
    dados = garantir_produtos(ler_dados())
    produto = buscar_produto(dados, termo)
    if not produto:
        await update.message.reply_text(f"❌ Produto '{termo}' não encontrado.")
        return
    if produto["estoque"] < qtd:
        await update.message.reply_text(f"⚠️ Estoque insuficiente! Disponível: {produto['estoque']} un")
        return
    produto["estoque"] -= qtd
    receita = produto["preco"] * qtd
    dados["vendas"].append({
        "produto_id": produto["id"],
        "produto_nome": produto["nome"],
        "qtd": qtd,
        "preco_unitario": produto["preco"],
        "total": receita,
        "data": datetime.now().isoformat(),
        "mes": mes_atual()
    })
    salvar_dados(dados)
    await update.message.reply_text(
        f"✅ *Venda registrada!*\n{produto['nome']}: -{qtd} un\n"
        f"Receita: {formatar_real(receita)}\nEstoque restante: {produto['estoque']} un",
        parse_mode="Markdown"
    )

async def cmd_custo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("❌ Uso: /custo [produto] [valor]\nEx: /custo casal 45.50")
        return
    try:
        valor = float(args[-1].replace(",", "."))
        termo = " ".join(args[:-1])
    except ValueError:
        await update.message.reply_text("❌ Valor inválido.")
        return
    dados = garantir_produtos(ler_dados())
    produto = buscar_produto(dados, termo)
    if not produto:
        await update.message.reply_text(f"❌ Produto '{termo}' não encontrado.")
        return
    produto["custo"] = valor
    salvar_dados(dados)
    await update.message.reply_text(
        f"✅ Custo atualizado!\n*{produto['nome']}*: {formatar_real(valor)}", parse_mode="Markdown"
    )

async def cmd_preco(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("❌ Uso: /preco [produto] [valor]\nEx: /preco casal 89.90")
        return
    try:
        valor = float(args[-1].replace(",", "."))
        termo = " ".join(args[:-1])
    except ValueError:
        await update.message.reply_text("❌ Valor inválido.")
        return
    dados = garantir_produtos(ler_dados())
    produto = buscar_produto(dados, termo)
    if not produto:
        await update.message.reply_text(f"❌ Produto '{termo}' não encontrado.")
        return
    produto["preco"] = valor
    salvar_dados(dados)
    await update.message.reply_text(
        f"✅ Preço atualizado!\n*{produto['nome']}*: {formatar_real(valor)}", parse_mode="Markdown"
    )

async def cmd_despesa(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("❌ Uso: /despesa [valor] [descrição]\nEx: /despesa 500 ADS Facebook")
        return
    try:
        valor = float(args[0].replace(",", "."))
        descricao = " ".join(args[1:])
    except ValueError:
        await update.message.reply_text("❌ Valor inválido.")
        return
    dados = ler_dados()
    dados["despesas"].append({
        "id": int(datetime.now().timestamp() * 1000),
        "valor": valor,
        "desc": descricao,
        "descricao": descricao,
        "categoria": "Outros",
        "data": datetime.now().isoformat(),
        "mes": mes_atual()
    })
    salvar_dados(dados)
    await update.message.reply_text(
        f"✅ *Despesa registrada!*\n{descricao}: {formatar_real(valor)}", parse_mode="Markdown"
    )

async def cmd_despesas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    dados = ler_dados()
    mes = mes_atual()
    despesas_mes = [d for d in dados["despesas"] if d.get("mes") == mes]
    if not despesas_mes:
        await update.message.reply_text("📭 Nenhuma despesa registrada este mês.")
        return
    total = sum(d["valor"] for d in despesas_mes)
    linhas = [f"💸 *Despesas de {mes}*\n"]
    for i, d in enumerate(despesas_mes, 1):
        linhas.append(f"{i}. {d['descricao']}: {formatar_real(d['valor'])}")
    linhas.append(f"\n*Total: {formatar_real(total)}*")
    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")

async def cmd_resumo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    dados = garantir_produtos(ler_dados())
    mes = mes_atual()
    vendas_mes   = [v for v in dados["vendas"]   if v.get("mes") == mes]
    despesas_mes = [d for d in dados["despesas"] if d.get("mes") == mes]
    receita  = sum(v["total"] for v in vendas_mes)
    despesas = sum(d["valor"] for d in despesas_mes)
    qtd_vend = sum(v["qtd"]   for v in vendas_mes)
    custo_vendas = 0
    for v in vendas_mes:
        prod = next((p for p in dados["estoque"] if p["id"] == v["produto_id"]), None)
        if prod:
            custo_vendas += prod["custo"] * v["qtd"]
    lucro_real = receita - despesas - custo_vendas
    texto = (
        f"📊 *Resumo Financeiro — {mes}*\n\n"
        f"💰 Receita: {formatar_real(receita)}\n"
        f"🏷 Custo produtos: {formatar_real(custo_vendas)}\n"
        f"💸 Despesas: {formatar_real(despesas)}\n"
        f"━━━━━━━━━━━━━━\n"
        f"✅ Lucro Líquido: {formatar_real(lucro_real)}\n\n"
        f"📦 Vendas: {qtd_vend} un em {len(vendas_mes)} transações"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")

async def cmd_alerta(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    dados = garantir_produtos(ler_dados())
    baixos = [p for p in dados["estoque"] if p["estoque"] < 5]
    if not baixos:
        await update.message.reply_text("✅ Todos os produtos com estoque adequado!")
        return
    linhas = ["⚠️ *Produtos com estoque baixo:*\n"]
    for p in baixos:
        emoji = "🔴" if p["estoque"] == 0 else "🟡"
        linhas.append(f"{emoji} {p['nome']}: {p['estoque']} un")
    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")

async def cmd_apagar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    dados = ler_dados()
    mes = mes_atual()
    despesas_mes = [d for d in dados["despesas"] if d.get("mes") == mes]
    if not ctx.args:
        if not despesas_mes:
            await update.message.reply_text("📭 Nenhuma despesa este mês.")
            return
        linhas = ["🗑 *Escolha o número para apagar:*\n"]
        for i, d in enumerate(despesas_mes, 1):
            linhas.append(f"{i}. {d['descricao']}: {formatar_real(d['valor'])}")
        linhas.append("\nUse: /apagar [número]")
        await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")
        return
    try:
        num = int(ctx.args[0])
        if num < 1 or num > len(despesas_mes):
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Número inválido.")
        return
    despesa_alvo = despesas_mes[num - 1]
    dados["despesas"].remove(despesa_alvo)
    salvar_dados(dados)
    await update.message.reply_text(
        f"✅ Apagado: *{despesa_alvo['descricao']}*: {formatar_real(despesa_alvo['valor'])}",
        parse_mode="Markdown"
    )

async def cmd_limpar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    dados = ler_dados()
    mes = mes_atual()
    antes = len(dados["despesas"])
    dados["despesas"] = [d for d in dados["despesas"] if d.get("mes") != mes]
    salvar_dados(dados)
    removidas = antes - len(dados["despesas"])
    await update.message.reply_text(f"🗑 *{removidas} despesa(s) apagada(s)* do mês {mes}.", parse_mode="Markdown")

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print("🦟 Bot Mosquiteiros iniciando...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("estoque",  cmd_estoque))
    app.add_handler(CommandHandler("produtos", cmd_produtos))
    app.add_handler(CommandHandler("entrada",  cmd_entrada))
    app.add_handler(CommandHandler("venda",    cmd_venda))
    app.add_handler(CommandHandler("custo",    cmd_custo))
    app.add_handler(CommandHandler("preco",    cmd_preco))
    app.add_handler(CommandHandler("despesa",  cmd_despesa))
    app.add_handler(CommandHandler("despesas", cmd_despesas))
    app.add_handler(CommandHandler("resumo",   cmd_resumo))
    app.add_handler(CommandHandler("alerta",   cmd_alerta))
    app.add_handler(CommandHandler("apagar",   cmd_apagar))
    app.add_handler(CommandHandler("limpar",   cmd_limpar))
    print("✅ Bot rodando! Aguardando comandos...")
    app.run_polling()

if __name__ == "__main__":
    main()
