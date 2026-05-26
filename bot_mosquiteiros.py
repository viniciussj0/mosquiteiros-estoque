import requests
import json
from datetime import datetime, timezone

# ============================================================
# CONFIGURAÇÕES
# ============================================================
TELEGRAM_TOKEN = "8723853827:AAFeOqlYT6goT6bbajCWpFmVLNnN2ZjR_H0"
CHAT_ID = "5303204887"

SUPABASE_URL = "https://wjgpgmpjfkotzkxmazgf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndqZ3BnbXBqZmtvdHpreG1hemdmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk4MTYzNjEsImV4cCI6MjA5NTM5MjM2MX0.aD7NVdnqUvhnKTOPz72R8zbVylAs7a15Z0Lq032YRsg"

API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# ============================================================
# HELPERS SUPABASE
# ============================================================
def sb_get(table, params=""):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if params:
        url += "?" + params
    r = requests.get(url, headers=HEADERS)
    return r.json() if r.ok else []

def sb_post(table, data):
    r = requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS, json=data)
    return r.json() if r.ok else None

def sb_patch(table, match, data):
    params = "&".join([f"{k}=eq.{v}" for k, v in match.items()])
    r = requests.patch(f"{SUPABASE_URL}/rest/v1/{table}?{params}", headers=HEADERS, json=data)
    return r.ok

def sb_delete(table, match):
    params = "&".join([f"{k}=eq.{v}" for k, v in match.items()])
    r = requests.delete(f"{SUPABASE_URL}/rest/v1/{table}?{params}", headers=HEADERS)
    return r.ok

def mes_atual():
    return datetime.now(timezone.utc).strftime("%Y-%m")

def now_iso():
    return datetime.now(timezone.utc).isoformat()

# ============================================================
# TELEGRAM
# ============================================================
def send(chat_id, text):
    requests.post(f"{API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    })

def get_updates(offset=None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    r = requests.get(f"{API_URL}/getUpdates", params=params)
    return r.json().get("result", []) if r.ok else []

# ============================================================
# BUSCA PRODUTO
# ============================================================
def find_produto(nome_parcial):
    produtos = sb_get("estoque", "order=nome")
    nome_parcial = nome_parcial.lower()
    for p in produtos:
        if nome_parcial in p["nome"].lower() or nome_parcial in p["id"].lower():
            return p
    return None

# ============================================================
# COMANDOS
# ============================================================
def cmd_start(chat_id):
    send(chat_id, """🦟 <b>FinStack Bot</b>

<b>ESTOQUE</b>
/estoque — Ver estoque atual
/produtos — Listar com preços
/entrada [produto] [qtd] — Registrar entrada
/venda [produto] [qtd] — Registrar venda
/devolucao [produto] [qtd] — Registrar devolução
/alerta — Produtos com estoque baixo

<b>FINANCEIRO</b>
/despesa [valor] [desc] — Adicionar despesa
/despesas — Ver despesas do mês
/resumo — Resumo financeiro
/vendas — Ver vendas do mês

<b>EDIÇÃO</b>
/custo [produto] [valor] — Atualizar custo
/preco [produto] [valor] — Atualizar preço
/apagar [id] — Apagar despesa
/limpar — Apagar despesas do mês
/remover venda [id] — Remover venda
/zerarvendas — Zerar vendas do mês""")

def cmd_estoque(chat_id):
    produtos = sb_get("estoque", "order=nome")
    if not produtos:
        send(chat_id, "❌ Nenhum produto encontrado.")
        return
    linhas = ["📦 <b>ESTOQUE ATUAL</b>\n"]
    for p in produtos:
        emoji = "🔴" if p["qty"] == 0 else "🟡" if p["qty"] <= 3 else "🟢"
        cores_info = ""
        if p.get("cores"):
            cores = p["cores"] if isinstance(p["cores"], list) else json.loads(p["cores"])
            if cores:
                cores_info = " (" + ", ".join([f"{c['nome']}: {c['qty']}" for c in cores]) + ")"
        linhas.append(f"{emoji} <b>{p['nome']}</b>: {p['qty']} un{cores_info}")
    send(chat_id, "\n".join(linhas))

def cmd_produtos(chat_id):
    produtos = sb_get("estoque", "order=nome")
    linhas = ["🏷️ <b>PRODUTOS E PREÇOS</b>\n"]
    for p in produtos:
        margem = ((p["preco"] - p["custo"]) / p["preco"] * 100) if p["preco"] > 0 else 0
        linhas.append(f"<b>{p['nome']}</b>\n  Custo: R${p['custo']:.2f} | Preço: R${p['preco']:.2f} | Margem: {margem:.0f}%")
    send(chat_id, "\n".join(linhas))

def cmd_entrada(chat_id, args):
    if len(args) < 2:
        send(chat_id, "❌ Uso: /entrada [produto] [qtd]")
        return
    try:
        qtd = int(args[-1])
        nome = " ".join(args[:-1])
    except:
        send(chat_id, "❌ Quantidade inválida.")
        return
    p = find_produto(nome)
    if not p:
        send(chat_id, f"❌ Produto '{nome}' não encontrado.")
        return
    nova_qty = p["qty"] + qtd
    sb_patch("estoque", {"id": p["id"]}, {"qty": nova_qty, "updated_at": now_iso()})
    sb_post("historico", {
        "tipo": "entrada", "produto_id": p["id"], "produto_nome": p["nome"],
        "qtd": qtd, "total": qtd * p["custo"], "data": now_iso(), "mes": mes_atual()
    })
    send(chat_id, f"✅ Entrada registrada!\n<b>{p['nome']}</b>: +{qtd} un\nEstoque: {nova_qty} un")

def cmd_venda(chat_id, args):
    if len(args) < 2:
        send(chat_id, "❌ Uso: /venda [produto] [qtd]")
        return
    try:
        qtd = int(args[-1])
        nome = " ".join(args[:-1])
    except:
        send(chat_id, "❌ Quantidade inválida.")
        return
    p = find_produto(nome)
    if not p:
        send(chat_id, f"❌ Produto '{nome}' não encontrado.")
        return
    if p["qty"] < qtd:
        send(chat_id, f"❌ Estoque insuficiente. Disponível: {p['qty']} un")
        return
    nova_qty = p["qty"] - qtd
    total = qtd * p["preco"]
    sb_patch("estoque", {"id": p["id"]}, {"qty": nova_qty, "updated_at": now_iso()})
    sb_post("vendas", {
        "produto_id": p["id"], "produto_nome": p["nome"], "qtd": qtd,
        "preco_unitario": p["preco"], "total": total, "pgto": "PIX",
        "data": now_iso(), "mes": mes_atual()
    })
    sb_post("historico", {
        "tipo": "venda", "produto_id": p["id"], "produto_nome": p["nome"],
        "qtd": qtd, "total": total, "pgto": "PIX", "data": now_iso(), "mes": mes_atual()
    })
    send(chat_id, f"✅ Venda registrada!\n<b>{p['nome']}</b>: {qtd} un\nTotal: R${total:.2f}\nEstoque: {nova_qty} un")

def cmd_devolucao(chat_id, args):
    if len(args) < 2:
        send(chat_id, "❌ Uso: /devolucao [produto] [qtd]")
        return
    try:
        qtd = int(args[-1])
        nome = " ".join(args[:-1])
    except:
        send(chat_id, "❌ Quantidade inválida.")
        return
    p = find_produto(nome)
    if not p:
        send(chat_id, f"❌ Produto '{nome}' não encontrado.")
        return
    nova_qty = p["qty"] + qtd
    total = qtd * p["preco"]
    sb_patch("estoque", {"id": p["id"]}, {"qty": nova_qty, "updated_at": now_iso()})
    sb_post("historico", {
        "tipo": "devolucao", "produto_id": p["id"], "produto_nome": p["nome"],
        "qtd": qtd, "total": -total, "data": now_iso(), "mes": mes_atual()
    })
    send(chat_id, f"↩️ Devolução registrada!\n<b>{p['nome']}</b>: +{qtd} un\nEstoque: {nova_qty} un")

def cmd_custo(chat_id, args):
    if len(args) < 2:
        send(chat_id, "❌ Uso: /custo [produto] [valor]")
        return
    try:
        valor = float(args[-1].replace(",", "."))
        nome = " ".join(args[:-1])
    except:
        send(chat_id, "❌ Valor inválido.")
        return
    p = find_produto(nome)
    if not p:
        send(chat_id, f"❌ Produto '{nome}' não encontrado.")
        return
    sb_patch("estoque", {"id": p["id"]}, {"custo": valor, "updated_at": now_iso()})
    send(chat_id, f"✅ Custo atualizado!\n<b>{p['nome']}</b>: R${valor:.2f}")

def cmd_preco(chat_id, args):
    if len(args) < 2:
        send(chat_id, "❌ Uso: /preco [produto] [valor]")
        return
    try:
        valor = float(args[-1].replace(",", "."))
        nome = " ".join(args[:-1])
    except:
        send(chat_id, "❌ Valor inválido.")
        return
    p = find_produto(nome)
    if not p:
        send(chat_id, f"❌ Produto '{nome}' não encontrado.")
        return
    sb_patch("estoque", {"id": p["id"]}, {"preco": valor, "updated_at": now_iso()})
    send(chat_id, f"✅ Preço atualizado!\n<b>{p['nome']}</b>: R${valor:.2f}")

def cmd_despesa(chat_id, args):
    if len(args) < 2:
        send(chat_id, "❌ Uso: /despesa [valor] [descrição]")
        return
    try:
        valor = float(args[0].replace(",", "."))
        desc = " ".join(args[1:])
    except:
        send(chat_id, "❌ Valor inválido.")
        return
    sb_post("despesas", {
        "valor": valor, "descricao": desc,
        "categoria": "Geral", "data": now_iso(), "mes": mes_atual()
    })
    send(chat_id, f"✅ Despesa registrada!\n💸 R${valor:.2f} — {desc}")

def cmd_despesas(chat_id):
    mes = mes_atual()
    despesas = sb_get("despesas", f"mes=eq.{mes}&order=data.desc")
    if not despesas:
        send(chat_id, f"📋 Nenhuma despesa em {mes}.")
        return
    total = sum(d["valor"] for d in despesas)
    linhas = [f"💸 <b>DESPESAS {mes}</b>\n"]
    for d in despesas:
        linhas.append(f"#{d['id']} R${d['valor']:.2f} — {d.get('descricao', '')}")
    linhas.append(f"\n<b>Total: R${total:.2f}</b>")
    send(chat_id, "\n".join(linhas))

def cmd_resumo(chat_id):
    mes = mes_atual()
    hoje = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    vendas = sb_get("vendas", f"mes=eq.{mes}")
    despesas = sb_get("despesas", f"mes=eq.{mes}")
    receita = sum(v["total"] for v in vendas)
    total_despesas = sum(d["valor"] for d in despesas)
    lucro = receita - total_despesas
    produtos = sb_get("estoque", "order=nome")
    valor_estoque = sum(p["qty"] * p["custo"] for p in produtos)
    send(chat_id, f"""📊 <b>RESUMO FINANCEIRO</b>
📅 {hoje} | Mês: {mes}

💰 Receita: R${receita:.2f}
💸 Despesas: R${total_despesas:.2f}
📈 Lucro: R${lucro:.2f}

🏪 Valor em estoque: R${valor_estoque:.2f}
🛒 Vendas no mês: {len(vendas)} pedidos""")

def cmd_vendas(chat_id):
    mes = mes_atual()
    vendas = sb_get("vendas", f"mes=eq.{mes}&order=data.desc")
    if not vendas:
        send(chat_id, f"🛒 Nenhuma venda em {mes}.")
        return
    total = sum(v["total"] for v in vendas)
    linhas = [f"🛒 <b>VENDAS {mes}</b>\n"]
    for v in vendas:
        data = v["data"][:10] if v.get("data") else ""
        linhas.append(f"#{v['id']} {data} — {v['produto_nome']} x{v['qtd']} R${v['total']:.2f}")
    linhas.append(f"\n<b>Total: R${total:.2f}</b>")
    send(chat_id, "\n".join(linhas))

def cmd_alerta(chat_id):
    produtos = sb_get("estoque", "qty=lte.3&order=qty")
    if not produtos:
        send(chat_id, "✅ Todos os produtos com estoque OK!")
        return
    linhas = ["⚠️ <b>ESTOQUE BAIXO</b>\n"]
    for p in produtos:
        emoji = "🔴" if p["qty"] == 0 else "🟡"
        linhas.append(f"{emoji} {p['nome']}: {p['qty']} un")
    send(chat_id, "\n".join(linhas))

def cmd_apagar(chat_id, args):
    if not args:
        send(chat_id, "❌ Uso: /apagar [id]")
        return
    try:
        id_desp = int(args[0])
    except:
        send(chat_id, "❌ ID inválido.")
        return
    ok = sb_delete("despesas", {"id": id_desp})
    send(chat_id, f"✅ Despesa #{id_desp} apagada!" if ok else "❌ Erro ao apagar.")

def cmd_limpar(chat_id):
    mes = mes_atual()
    despesas = sb_get("despesas", f"mes=eq.{mes}")
    for d in despesas:
        sb_delete("despesas", {"id": d["id"]})
    send(chat_id, f"✅ {len(despesas)} despesas de {mes} removidas!")

def cmd_remover_venda(chat_id, args):
    if not args:
        send(chat_id, "❌ Uso: /remover venda [id]")
        return
    try:
        id_venda = int(args[-1])
    except:
        send(chat_id, "❌ ID inválido.")
        return
    vendas = sb_get("vendas", f"id=eq.{id_venda}")
    if not vendas:
        send(chat_id, "❌ Venda não encontrada.")
        return
    v = vendas[0]
    p = find_produto(v["produto_id"])
    if p:
        sb_patch("estoque", {"id": p["id"]}, {"qty": p["qty"] + v["qtd"], "updated_at": now_iso()})
    sb_delete("vendas", {"id": id_venda})
    send(chat_id, f"✅ Venda #{id_venda} removida! Estoque reposto.")

def cmd_zerarvendas(chat_id, args):
    mes = mes_atual()
    if args:
        nome = " ".join(args)
        p = find_produto(nome)
        if not p:
            send(chat_id, f"❌ Produto '{nome}' não encontrado.")
            return
        vendas = sb_get("vendas", f"mes=eq.{mes}&produto_id=eq.{p['id']}")
        for v in vendas:
            sb_delete("vendas", {"id": v["id"]})
        send(chat_id, f"✅ Vendas de '{p['nome']}' em {mes} zeradas!")
    else:
        vendas = sb_get("vendas", f"mes=eq.{mes}")
        for v in vendas:
            sb_delete("vendas", {"id": v["id"]})
        send(chat_id, f"✅ Todas as vendas de {mes} zeradas!")

# ============================================================
# PROCESSAMENTO DE MENSAGENS
# ============================================================
def process(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    if not text.startswith("/"):
        return
    parts = text.split()
    cmd = parts[0].lower().split("@")[0]
    args = parts[1:]

    if cmd == "/start": cmd_start(chat_id)
    elif cmd == "/estoque": cmd_estoque(chat_id)
    elif cmd == "/produtos": cmd_produtos(chat_id)
    elif cmd == "/entrada": cmd_entrada(chat_id, args)
    elif cmd == "/venda": cmd_venda(chat_id, args)
    elif cmd == "/devolucao": cmd_devolucao(chat_id, args)
    elif cmd == "/custo": cmd_custo(chat_id, args)
    elif cmd == "/preco": cmd_preco(chat_id, args)
    elif cmd == "/despesa": cmd_despesa(chat_id, args)
    elif cmd == "/despesas": cmd_despesas(chat_id)
    elif cmd == "/resumo": cmd_resumo(chat_id)
    elif cmd == "/vendas": cmd_vendas(chat_id)
    elif cmd == "/alerta": cmd_alerta(chat_id)
    elif cmd == "/apagar": cmd_apagar(chat_id, args)
    elif cmd == "/limpar": cmd_limpar(chat_id)
    elif cmd == "/remover": cmd_remover_venda(chat_id, args)
    elif cmd == "/zerarvendas": cmd_zerarvendas(chat_id, args)

# ============================================================
# MAIN LOOP
# ============================================================
def main():
    print("🤖 FinStack Bot iniciado (Supabase)")
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            if "message" in update:
                try:
                    process(update["message"])
                except Exception as e:
                    print(f"Erro: {e}")

if __name__ == "__main__":
    main()
