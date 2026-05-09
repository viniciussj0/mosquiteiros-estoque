import os
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8723853827:AAFeOqlYT6goT6bbajCWpFmVLNnN2ZjR_H0")
CHAT_ID        = "5303204887"
JSONBIN_KEY    = os.environ.get("JSONBIN_KEY", "$2a$10$/s4UWuZZrxTnJ6UbzbxTju6P/jitCDCIZvr4XQjlS4xTVrKL1qmGq")
JSONBIN_BIN    = os.environ.get("JSONBIN_BIN", "69fbf4d9adc21f119a64af4c")
JSONBIN_URL    = "https://api.jsonbin.io/v3/b/" + JSONBIN_BIN
HEADERS        = {"X-Master-Key": JSONBIN_KEY, "Content-Type": "application/json"}

PRODUTOS_PADRAO = [
    {"id": "MGA-001", "nome": "Mosquiteiro Gigante Aberto",  "estoque": 0, "qty": 0, "custo": 0, "preco": 0},
    {"id": "PES-001", "nome": "Peseira",                      "estoque": 0, "qty": 0, "custo": 0, "preco": 0},
    {"id": "CAL-001", "nome": "Capa de Almofada",             "estoque": 0, "qty": 0, "custo": 0, "preco": 0},
    {"id": "MFI-001", "nome": "Mosquiteiro Filo",             "estoque": 0, "qty": 0, "custo": 0, "preco": 0},
    {"id": "MCP-001", "nome": "Mosquiteiro Casal Padrao",     "estoque": 0, "qty": 0, "custo": 0, "preco": 0},
    {"id": "MGF-001", "nome": "Mosquiteiro Gigante Fechado",  "estoque": 0, "qty": 0, "custo": 0, "preco": 0},
]

def ler_dados():
    try:
        r = requests.get(JSONBIN_URL, headers=HEADERS, timeout=10)
        record = r.json().get("record", {})
        record.setdefault("despesas", [])
        record.setdefault("estoque", [])
        record.setdefault("vendas", [])
        record.setdefault("historico", [])
        return record
    except Exception as e:
        print("Erro ao ler JSONBin:", e)
        return {"despesas": [], "estoque": [], "vendas": [], "historico": []}

def salvar_dados(dados):
    try:
        for p in dados.get("estoque", []):
            p["estoque"] = p.get("qty", p.get("estoque", 0))
            p["qty"] = p["estoque"]
        requests.put(JSONBIN_URL, json=dados, headers=HEADERS, timeout=10)
    except Exception as e:
        print("Erro ao salvar JSONBin:", e)

def garantir_produtos(dados):
    ids = [p["id"] for p in dados["estoque"]]
    for p in PRODUTOS_PADRAO:
        if p["id"] not in ids:
            dados["estoque"].append(dict(p))
    for p in dados["estoque"]:
        if "qty" not in p:
            p["qty"] = p.get("estoque", 0)
        if "estoque" not in p:
            p["estoque"] = p.get("qty", 0)
    return dados

def buscar_produto(dados, termo):
    termo = termo.lower()
    for p in dados["estoque"]:
        if termo in p["nome"].lower() or termo in p["id"].lower():
            return p
    return None

def mes_atual():
    return datetime.now().strftime("%Y-%m")

def real(valor):
    return "R$ {:,.2f}".format(valor).replace(",", "X").replace(".", ",").replace("X", ".")

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    texto = ("*FinStack Bot Online!*\n\nComandos disponiveis:\n"
        "/estoque - Ver estoque atual\n"
        "/produtos - Listar produtos\n"
        "/entrada [produto] [qtd] - Registrar entrada\n"
        "/venda [produto] [qtd] - Registrar venda\n"
        "/custo [produto] [valor] - Atualizar custo\n"
        "/preco [produto] [valor] - Atualizar preco\n"
        "/despesa [valor] [desc] - Adicionar despesa\n"
        "/despesas - Ver despesas do mes\n"
        "/resumo - Resumo financeiro\n"
        "/alerta - Produtos com estoque baixo\n"
        "/apagar [numero] - Apagar despesa\n"
        "/limpar - Apagar todas as despesas do mes")
    await update.message.reply_text(texto, parse_mode="Markdown")

async def cmd_estoque(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    dados = garantir_produtos(ler_dados())
    linhas = ["*Estoque Atual*\n"]
    for p in dados["estoque"]:
        qty = p.get("qty", p.get("estoque", 0))
        emoji = "🔴" if qty == 0 else "🟡" if qty < 5 else "🟢"
        linhas.append("{} *{}* - {} un".format(emoji, p["nome"], qty))
    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")

async def cmd_produtos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    dados = garantir_produtos(ler_dados())
    linhas = ["*Produtos Cadastrados*\n"]
    for i, p in enumerate(dados["estoque"], 1):
        qty = p.get("qty", p.get("estoque", 0))
        margem = ""
        if p.get("custo", 0) > 0 and p.get("preco", 0) > 0:
            m = ((p["preco"] - p["custo"]) / p["preco"]) * 100
            margem = " | Margem: {:.0f}%".format(m)
        linhas.append("{}. *{}* ({})\n   Custo: {} | Venda: {}{}\n   Estoque: {} un".format(
            i, p["nome"], p["id"], real(p.get("custo", 0)), real(p.get("preco", 0)), margem, qty))
    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")

async def cmd_entrada(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("Uso: /entrada [produto] [qtd]\nEx: /entrada casal 10")
        return
    try:
        qtd = int(args[-1])
        termo = " ".join(args[:-1])
    except ValueError:
        await update.message.reply_text("A quantidade deve ser um numero inteiro.")
        return
    dados = garantir_produtos(ler_dados())
    produto = buscar_produto(dados, termo)
    if not produto:
        await update.message.reply_text("Produto '{}' nao encontrado.".format(termo))
        return
    produto["qty"] = produto.get("qty", produto.get("estoque", 0)) + qtd
    produto["estoque"] = produto["qty"]
    dados["historico"].insert(0, {"tipo": "entrada", "produto_id": produto["id"],
        "produto_nome": produto["nome"], "qtd": qtd,
        "data": datetime.now().isoformat(), "mes": mes_atual()})
    salvar_dados(dados)
    await update.message.reply_text(
        "*Entrada registrada!*\n{}: +{} un\nTotal: {} un".format(produto["nome"], qtd, produto["qty"]),
        parse_mode="Markdown")

async def cmd_venda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("Uso: /venda [produto] [qtd]\nEx: /venda casal 3")
        return
    try:
        qtd = int(args[-1])
        termo = " ".join(args[:-1])
    except ValueError:
        await update.message.reply_text("A quantidade deve ser um numero inteiro.")
        return
    dados = garantir_produtos(ler_dados())
    produto = buscar_produto(dados, termo)
    if not produto:
        await update.message.reply_text("Produto '{}' nao encontrado.".format(termo))
        return
    qty_atual = produto.get("qty", produto.get("estoque", 0))
    if qty_atual < qtd:
        await update.message.reply_text("Estoque insuficiente! Disponivel: {} un".format(qty_atual))
        return
    produto["qty"] = qty_atual - qtd
    produto["estoque"] = produto["qty"]
    receita = produto.get("preco", 0) * qtd
    dados["vendas"].append({"produto_id": produto["id"], "produto_nome": produto["nome"],
        "qtd": qtd, "preco_unitario": produto.get("preco", 0), "total": receita, "pgto": "Telegram",
        "data": datetime.now().isoformat(), "mes": mes_atual()})
    dados["historico"].insert(0, {"tipo": "venda", "produto_id": produto["id"],
        "produto_nome": produto["nome"], "qtd": qtd, "total": receita,
        "data": datetime.now().isoformat(), "mes": mes_atual()})
    salvar_dados(dados)
    await update.message.reply_text(
        "*Venda registrada!*\n{}: -{} un\nReceita: {}\nRestante: {} un".format(
            produto["nome"], qtd, real(receita), produto["qty"]), parse_mode="Markdown")

async def cmd_custo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("Uso: /custo [produto] [valor]\nEx: /custo casal 45.50")
        return
    try:
        valor = float(args[-1].replace(",", "."))
        termo = " ".join(args[:-1])
    except ValueError:
        await update.message.reply_text("Valor invalido.")
        return
    dados = garantir_produtos(ler_dados())
    produto = buscar_produto(dados, termo)
    if not produto:
        await update.message.reply_text("Produto '{}' nao encontrado.".format(termo))
        return
    produto["custo"] = valor
    salvar_dados(dados)
    await update.message.reply_text(
        "*Custo atualizado!*\n{}: {}".format(produto["nome"], real(valor)), parse_mode="Markdown")

async def cmd_preco(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("Uso: /preco [produto] [valor]\nEx: /preco casal 89.90")
        return
    try:
        valor = float(args[-1].replace(",", "."))
        termo = " ".join(args[:-1])
    except ValueError:
        await update.message.reply_text("Valor invalido.")
        return
    dados = garantir_produtos(ler_dados())
    produto = buscar_produto(dados, termo)
    if not produto:
        await update.message.reply_text("Produto '{}' nao encontrado.".format(termo))
        return
    produto["preco"] = valor
    salvar_dados(dados)
    await update.message.reply_text(
        "*Preco atualizado!*\n{}: {}".format(produto["nome"], real(valor)), parse_mode="Markdown")

async def cmd_despesa(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("Uso: /despesa [valor] [descricao]\nEx: /despesa 500 ADS Facebook")
        return
    try:
        valor = float(args[0].replace(",", "."))
        descricao = " ".join(args[1:])
    except ValueError:
        await update.message.reply_text("Valor invalido.")
        return
    dados = ler_dados()
    dados["despesas"].insert(0, {"id": int(datetime.now().timestamp() * 1000),
        "valor": valor, "desc": descricao, "descricao": descricao,
        "categoria": "Outros", "data": datetime.now().isoformat(), "mes": mes_atual()})
    salvar_dados(dados)
    await update.message.reply_text(
        "*Despesa registrada!*\n{}: {}".format(descricao, real(valor)), parse_mode="Markdown")

async def cmd_despesas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    dados = ler_dados()
    mes = mes_atual()
    despesas_mes = [d for d in dados["despesas"] if d.get("mes") == mes]
    if not despesas_mes:
        await update.message.reply_text("Nenhuma despesa registrada este mes.")
        return
    total = sum(d.get("valor", 0) for d in despesas_mes)
    linhas = ["*Despesas de {}*\n".format(mes)]
    for i, d in enumerate(despesas_mes, 1):
        desc = d.get("desc") or d.get("descricao") or "-"
        linhas.append("{}. {}: {}".format(i, desc, real(d.get("valor", 0))))
    linhas.append("\n*Total: {}*".format(real(total)))
    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")

async def cmd_resumo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    dados = garantir_produtos(ler_dados())
    mes = mes_atual()
    vendas_mes   = [v for v in dados["vendas"]   if v.get("mes") == mes]
    despesas_mes = [d for d in dados["despesas"] if d.get("mes") == mes]
    receita      = sum(v.get("total", 0) for v in vendas_mes)
    desp_tot     = sum(d.get("valor", 0) for d in despesas_mes)
    qtd_vend     = sum(v.get("qtd", 0)   for v in vendas_mes)
    custo_vendas = 0
    for v in vendas_mes:
        prod = next((p for p in dados["estoque"] if p["id"] == v.get("produto_id")), None)
        if prod:
            custo_vendas += prod.get("custo", 0) * v.get("qtd", 0)
    lucro = receita - desp_tot - custo_vendas
    texto = ("*Resumo Financeiro - {}*\n\nReceita: {}\nCusto produtos: {}\n"
        "Despesas: {}\nLucro Liquido: {}\n\nVendas: {} un em {} transacoes"
    ).format(mes, real(receita), real(custo_vendas), real(desp_tot), real(lucro), qtd_vend, len(vendas_mes))
    await update.message.reply_text(texto, parse_mode="Markdown")

async def cmd_alerta(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    dados = garantir_produtos(ler_dados())
    baixos = [p for p in dados["estoque"] if p.get("qty", p.get("estoque", 0)) < 5]
    if not baixos:
        await update.message.reply_text("Todos os produtos com estoque adequado!")
        return
    linhas = ["*Produtos com estoque baixo:*\n"]
    for p in baixos:
        qty = p.get("qty", p.get("estoque", 0))
        emoji = "🔴" if qty == 0 else "🟡"
        linhas.append("{} {}: {} un".format(emoji, p["nome"], qty))
    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")

async def cmd_apagar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    dados = ler_dados()
    mes = mes_atual()
    despesas_mes = [d for d in dados["despesas"] if d.get("mes") == mes]
    if not ctx.args:
        if not despesas_mes:
            await update.message.reply_text("Nenhuma despesa este mes.")
            return
        linhas = ["*Escolha o numero para apagar:*\n"]
        for i, d in enumerate(despesas_mes, 1):
            desc = d.get("desc") or d.get("descricao") or "-"
            linhas.append("{}. {}: {}".format(i, desc, real(d.get("valor", 0))))
        linhas.append("\nUse: /apagar [numero]")
        await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")
        return
    try:
        num = int(ctx.args[0])
        if num < 1 or num > len(despesas_mes):
            raise ValueError
    except ValueError:
        await update.message.reply_text("Numero invalido.")
        return
    despesa_alvo = despesas_mes[num - 1]
    dados["despesas"].remove(despesa_alvo)
    salvar_dados(dados)
    desc = despesa_alvo.get("desc") or despesa_alvo.get("descricao") or "-"
    await update.message.reply_text(
        "*Apagado:* {}: {}".format(desc, real(despesa_alvo.get("valor", 0))), parse_mode="Markdown")

async def cmd_limpar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    dados = ler_dados()
    mes = mes_atual()
    antes = len(dados["despesas"])
    dados["despesas"] = [d for d in dados["despesas"] if d.get("mes") != mes]
    salvar_dados(dados)
    removidas = antes - len(dados["despesas"])
    await update.message.reply_text(
        "*{} despesa(s) apagada(s)* do mes {}.".format(removidas, mes), parse_mode="Markdown")

def main():
    print("FinStack Bot iniciando...")
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
    print("Bot rodando! Aguardando comandos...")
    app.run_polling()

if __name__ == "__main__":
    main()
