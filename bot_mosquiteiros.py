import os
import requests
import time
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8723853827:AAFeOqlYT6goT6bbajCWpFmVLNnN2ZjR_H0")
CHAT_ID        = "5303204887"
JSONBIN_KEY    = os.environ.get("JSONBIN_KEY", "$2a$10$/s4UWuZZrxTnJ6UbzbxTju6P/jitCDCIZvr4XQjlS4xTVrKL1qmGq")
JSONBIN_BIN    = os.environ.get("JSONBIN_BIN", "69fbf4d9adc21f119a64af4c")
JSONBIN_URL    = "https://api.jsonbin.io/v3/b/" + JSONBIN_BIN
JB_HEADERS     = {"X-Master-Key": JSONBIN_KEY, "Content-Type": "application/json"}
TG_URL         = "https://api.telegram.org/bot" + TELEGRAM_TOKEN

PRODUTOS_PADRAO = [
    {"id": "MGA-001", "nome": "Mosquiteiro Gigante Aberto",  "estoque": 0, "qty": 0, "custo": 0, "preco": 0},
    {"id": "PES-001", "nome": "Peseira",                      "estoque": 0, "qty": 0, "custo": 0, "preco": 0},
    {"id": "CAL-001", "nome": "Capa de Almofada",             "estoque": 0, "qty": 0, "custo": 0, "preco": 0},
    {"id": "MFI-001", "nome": "Mosquiteiro Filo",             "estoque": 0, "qty": 0, "custo": 0, "preco": 0},
    {"id": "MCP-001", "nome": "Mosquiteiro Casal Padrao",     "estoque": 0, "qty": 0, "custo": 0, "preco": 0},
    {"id": "MGF-001", "nome": "Mosquiteiro Gigante Fechado",  "estoque": 0, "qty": 0, "custo": 0, "preco": 0},
]

def send(chat_id, text):
    try:
        requests.post(TG_URL + "/sendMessage", json={
            "chat_id": chat_id, "text": text, "parse_mode": "Markdown"
        }, timeout=10)
    except Exception as e:
        print("Erro ao enviar mensagem:", e)

def get_updates(offset=None):
    try:
        params = {"timeout": 30}
        if offset:
            params["offset"] = offset
        r = requests.get(TG_URL + "/getUpdates", params=params, timeout=35)
        return r.json().get("result", [])
    except Exception as e:
        print("Erro ao buscar updates:", e)
        return []

def ler_dados():
    try:
        r = requests.get(JSONBIN_URL, headers=JB_HEADERS, timeout=10)
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
        requests.put(JSONBIN_URL, json=dados, headers=JB_HEADERS, timeout=10)
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

def handle(chat_id, text):
    parts = text.strip().split()
    cmd   = parts[0].lower().split("@")[0]
    args  = parts[1:]

    if cmd == "/start":
        send(chat_id,
            "*FinStack Bot Online!*\n\nComandos disponiveis:\n"
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
            "/limpar - Apagar despesas do mes\n"
            "/ajustar [receita|despesas] [valor|zerar] - Ajustar financeiro\n"
            "/zerarvendas - Zerar todas as vendas do mes\n"
            "/zerarvendas [produto] - Zerar vendas de um produto"
        )

    elif cmd == "/estoque":
        dados = garantir_produtos(ler_dados())
        linhas = ["*Estoque Atual*\n"]
        for p in dados["estoque"]:
            qty = p.get("qty", p.get("estoque", 0))
            emoji = "🔴" if qty == 0 else "🟡" if qty < 5 else "🟢"
            linhas.append("{} *{}* - {} un".format(emoji, p["nome"], qty))
        send(chat_id, "\n".join(linhas))

    elif cmd == "/produtos":
        dados = garantir_produtos(ler_dados())
        linhas = ["*Produtos Cadastrados*\n"]
        for i, p in enumerate(dados["estoque"], 1):
            qty = p.get("qty", p.get("estoque", 0))
            margem = ""
            if p.get("custo", 0) > 0 and p.get("preco", 0) > 0:
                m = ((p["preco"] - p["custo"]) / p["preco"]) * 100
                margem = " | Margem: {:.0f}%".format(m)
            linhas.append("{}. *{}*\n   Custo: {} | Venda: {}{}\n   Estoque: {} un".format(
                i, p["nome"], real(p.get("custo", 0)), real(p.get("preco", 0)), margem, qty))
        send(chat_id, "\n".join(linhas))

    elif cmd == "/entrada":
        if len(args) < 2:
            send(chat_id, "Uso: /entrada [produto] [qtd]\nEx: /entrada casal 10")
            return
        try:
            qtd = int(args[-1])
            termo = " ".join(args[:-1])
        except ValueError:
            send(chat_id, "A quantidade deve ser um numero inteiro.")
            return
        dados = garantir_produtos(ler_dados())
        produto = buscar_produto(dados, termo)
        if not produto:
            send(chat_id, "Produto '{}' nao encontrado.".format(termo))
            return
        produto["qty"] = produto.get("qty", produto.get("estoque", 0)) + qtd
        produto["estoque"] = produto["qty"]
        dados["historico"].insert(0, {"tipo": "entrada", "produto_id": produto["id"],
            "produto_nome": produto["nome"], "qtd": qtd,
            "data": datetime.now().isoformat(), "mes": mes_atual()})
        salvar_dados(dados)
        send(chat_id, "*Entrada registrada!*\n{}: +{} un\nTotal: {} un".format(
            produto["nome"], qtd, produto["qty"]))

    elif cmd == "/venda":
        if len(args) < 2:
            send(chat_id, "Uso: /venda [produto] [qtd]\nEx: /venda casal 3")
            return
        try:
            qtd = int(args[-1])
            termo = " ".join(args[:-1])
        except ValueError:
            send(chat_id, "A quantidade deve ser um numero inteiro.")
            return
        dados = garantir_produtos(ler_dados())
        produto = buscar_produto(dados, termo)
        if not produto:
            send(chat_id, "Produto '{}' nao encontrado.".format(termo))
            return
        qty_atual = produto.get("qty", produto.get("estoque", 0))
        if qty_atual < qtd:
            send(chat_id, "Estoque insuficiente! Disponivel: {} un".format(qty_atual))
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
        send(chat_id, "*Venda registrada!*\n{}: -{} un\nReceita: {}\nRestante: {} un".format(
            produto["nome"], qtd, real(receita), produto["qty"]))

    elif cmd == "/custo":
        if len(args) < 2:
            send(chat_id, "Uso: /custo [produto] [valor]\nEx: /custo casal 45.50")
            return
        try:
            valor = float(args[-1].replace(",", "."))
            termo = " ".join(args[:-1])
        except ValueError:
            send(chat_id, "Valor invalido.")
            return
        dados = garantir_produtos(ler_dados())
        produto = buscar_produto(dados, termo)
        if not produto:
            send(chat_id, "Produto '{}' nao encontrado.".format(termo))
            return
        produto["custo"] = valor
        salvar_dados(dados)
        send(chat_id, "*Custo atualizado!*\n{}: {}".format(produto["nome"], real(valor)))

    elif cmd == "/preco":
        if len(args) < 2:
            send(chat_id, "Uso: /preco [produto] [valor]\nEx: /preco casal 89.90")
            return
        try:
            valor = float(args[-1].replace(",", "."))
            termo = " ".join(args[:-1])
        except ValueError:
            send(chat_id, "Valor invalido.")
            return
        dados = garantir_produtos(ler_dados())
        produto = buscar_produto(dados, termo)
        if not produto:
            send(chat_id, "Produto '{}' nao encontrado.".format(termo))
            return
        produto["preco"] = valor
        salvar_dados(dados)
        send(chat_id, "*Preco atualizado!*\n{}: {}".format(produto["nome"], real(valor)))

    elif cmd == "/despesa":
        if len(args) < 2:
            send(chat_id, "Uso: /despesa [valor] [descricao]\nEx: /despesa 500 ADS Facebook")
            return
        try:
            valor = float(args[0].replace(",", "."))
            descricao = " ".join(args[1:])
        except ValueError:
            send(chat_id, "Valor invalido.")
            return
        dados = ler_dados()
        dados["despesas"].insert(0, {"id": int(datetime.now().timestamp() * 1000),
            "valor": valor, "desc": descricao, "descricao": descricao,
            "categoria": "Outros", "data": datetime.now().isoformat(), "mes": mes_atual()})
        salvar_dados(dados)
        send(chat_id, "*Despesa registrada!*\n{}: {}".format(descricao, real(valor)))

    elif cmd == "/despesas":
        dados = ler_dados()
        mes = mes_atual()
        despesas_mes = [d for d in dados["despesas"] if d.get("mes") == mes]
        if not despesas_mes:
            send(chat_id, "Nenhuma despesa registrada este mes.")
            return
        total = sum(d.get("valor", 0) for d in despesas_mes)
        linhas = ["*Despesas de {}*\n".format(mes)]
        for i, d in enumerate(despesas_mes, 1):
            desc = d.get("desc") or d.get("descricao") or "-"
            linhas.append("{}. {}: {}".format(i, desc, real(d.get("valor", 0))))
        linhas.append("\n*Total: {}*".format(real(total)))
        send(chat_id, "\n".join(linhas))

    elif cmd == "/resumo":
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
        send(chat_id, ("*Resumo Financeiro - {}*\n\nReceita: {}\nCusto produtos: {}\n"
            "Despesas: {}\nLucro Liquido: {}\n\nVendas: {} un em {} transacoes"
        ).format(mes, real(receita), real(custo_vendas), real(desp_tot), real(lucro), qtd_vend, len(vendas_mes)))

    elif cmd == "/alerta":
        dados = garantir_produtos(ler_dados())
        baixos = [p for p in dados["estoque"] if p.get("qty", p.get("estoque", 0)) < 5]
        if not baixos:
            send(chat_id, "Todos os produtos com estoque adequado!")
            return
        linhas = ["*Produtos com estoque baixo:*\n"]
        for p in baixos:
            qty = p.get("qty", p.get("estoque", 0))
            emoji = "🔴" if qty == 0 else "🟡"
            linhas.append("{} {}: {} un".format(emoji, p["nome"], qty))
        send(chat_id, "\n".join(linhas))

    elif cmd == "/apagar":
        dados = ler_dados()
        mes = mes_atual()
        despesas_mes = [d for d in dados["despesas"] if d.get("mes") == mes]
        if not args:
            if not despesas_mes:
                send(chat_id, "Nenhuma despesa este mes.")
                return
            linhas = ["*Escolha o numero para apagar:*\n"]
            for i, d in enumerate(despesas_mes, 1):
                desc = d.get("desc") or d.get("descricao") or "-"
                linhas.append("{}. {}: {}".format(i, desc, real(d.get("valor", 0))))
            linhas.append("\nUse: /apagar [numero]")
            send(chat_id, "\n".join(linhas))
            return
        try:
            num = int(args[0])
            if num < 1 or num > len(despesas_mes):
                raise ValueError
        except ValueError:
            send(chat_id, "Numero invalido.")
            return
        despesa_alvo = despesas_mes[num - 1]
        dados["despesas"].remove(despesa_alvo)
        salvar_dados(dados)
        desc = despesa_alvo.get("desc") or despesa_alvo.get("descricao") or "-"
        send(chat_id, "*Apagado:* {}: {}".format(desc, real(despesa_alvo.get("valor", 0))))

    elif cmd == "/ajustar":
        # /ajustar receita 0  ou  /ajustar receita -500
        if len(args) < 2:
            send(chat_id, "Uso: /ajustar [receita|despesas|vendas] [valor ou zerar]\nExemplos:\n/ajustar receita zerar\n/ajustar receita -500\n/ajustar vendas zerar")
            return
        tipo = args[0].lower()
        valor = args[1].lower()
        dados = ler_dados()
        mes = mes_atual()
        if tipo == "receita" or tipo == "vendas":
            if valor == "zerar":
                antes = len(dados["vendas"])
                dados["vendas"] = [v for v in dados["vendas"] if v.get("mes") != mes]
                salvar_dados(dados)
                send(chat_id, "*Receita zerada!*\n{} venda(s) removida(s) do mes {}.".format(antes - len(dados["vendas"]), mes))
            else:
                try:
                    ajuste = float(valor.replace(",", "."))
                    dados["despesas"].insert(0, {
                        "id": int(datetime.now().timestamp() * 1000),
                        "valor": abs(ajuste),
                        "desc": "Ajuste de receita",
                        "descricao": "Ajuste de receita",
                        "categoria": "Ajuste",
                        "data": datetime.now().isoformat(),
                        "mes": mes
                    })
                    salvar_dados(dados)
                    send(chat_id, "*Ajuste registrado!*\nDeducao de {} na receita do mes {}.".format(real(abs(ajuste)), mes))
                except ValueError:
                    send(chat_id, "Valor invalido. Use numero ou 'zerar'.")
        elif tipo == "despesas":
            if valor == "zerar":
                antes = len(dados["despesas"])
                dados["despesas"] = [d for d in dados["despesas"] if d.get("mes") != mes]
                salvar_dados(dados)
                send(chat_id, "*Despesas zeradas!*\n{} despesa(s) removida(s) do mes {}.".format(antes - len(dados["despesas"]), mes))
            else:
                send(chat_id, "Para despesas use: /ajustar despesas zerar")
        else:
            send(chat_id, "Tipo invalido. Use: receita, vendas ou despesas")

    elif cmd == "/limpar":
        dados = ler_dados()
        mes = mes_atual()
        antes = len(dados["despesas"])
        dados["despesas"] = [d for d in dados["despesas"] if d.get("mes") != mes]
        salvar_dados(dados)
        removidas = antes - len(dados["despesas"])
        send(chat_id, "*{} despesa(s) apagada(s)* do mes {}.".format(removidas, mes))

    elif cmd == "/vendas":
        dados = ler_dados()
        mes = mes_atual()
        vendas_mes = [v for v in dados["vendas"] if v.get("mes") == mes]
        if not vendas_mes:
            send(chat_id, "Nenhuma venda registrada este mes.")
            return
        total = sum(v.get("total", 0) for v in vendas_mes)
        linhas = ["*Vendas de {}*\n".format(mes)]
        for i, v in enumerate(vendas_mes, 1):
            linhas.append("{}. {} x{} - {}".format(i, v.get("produto_nome", "-"), v.get("qtd", 1), real(v.get("total", 0))))
        linhas.append("\n*Total: {}*".format(real(total)))
        linhas.append("\nUse /remover venda [numero] para remover")
        send(chat_id, "\n".join(linhas))

    elif cmd == "/remover":
        if len(args) < 2:
            send(chat_id, "Uso: /remover venda [numero]\nEx: /remover venda 2\n\nUse /vendas para ver a lista.")
            return
        if args[0].lower() != "venda":
            send(chat_id, "Uso: /remover venda [numero]")
            return
        try:
            num = int(args[1])
        except ValueError:
            send(chat_id, "Numero invalido.")
            return
        dados = ler_dados()
        dados = garantir_produtos(dados)
        mes = mes_atual()
        vendas_mes = [v for v in dados["vendas"] if v.get("mes") == mes]
        if num < 1 or num > len(vendas_mes):
            send(chat_id, "Numero invalido. Use /vendas para ver a lista.")
            return
        venda_alvo = vendas_mes[num - 1]
        prod = next((p for p in dados["estoque"] if p["id"] == venda_alvo.get("produto_id")), None)
        if prod:
            prod["qty"] = prod.get("qty", prod.get("estoque", 0)) + venda_alvo.get("qtd", 1)
            prod["estoque"] = prod["qty"]
        dados["vendas"].remove(venda_alvo)
        salvar_dados(dados)
        send(chat_id, "*Venda removida!*\n{} x{} - {}\nEstoque devolvido.".format(
            venda_alvo.get("produto_nome", "-"),
            venda_alvo.get("qtd", 1),
            real(venda_alvo.get("total", 0))))

    elif cmd == "/zerarvendas":
        dados = ler_dados()
        dados = garantir_produtos(dados)
        mes = mes_atual()
        if not args:
            # Zera TODAS as vendas do mes
            vendas_mes = [v for v in dados["vendas"] if v.get("mes") == mes]
            # Devolve estoque de todas
            for v in vendas_mes:
                prod = next((p for p in dados["estoque"] if p["id"] == v.get("produto_id")), None)
                if prod:
                    prod["qty"] = prod.get("qty", prod.get("estoque", 0)) + v.get("qtd", 1)
                    prod["estoque"] = prod["qty"]
            total_removido = sum(v.get("total", 0) for v in vendas_mes)
            dados["vendas"] = [v for v in dados["vendas"] if v.get("mes") != mes]
            salvar_dados(dados)
            send(chat_id, "*Todas as vendas zeradas!*\n{} venda(s) removida(s)\nReceita removida: {}\nEstoque devolvido.".format(
                len(vendas_mes), real(total_removido)))
        else:
            # Zera vendas de um produto especifico
            termo = " ".join(args).lower()
            vendas_mes = [v for v in dados["vendas"] if v.get("mes") == mes]
            vendas_prod = [v for v in vendas_mes if termo in v.get("produto_nome", "").lower()]
            if not vendas_prod:
                send(chat_id, "Nenhuma venda encontrada para '{}'.\nUse /vendas para ver a lista.".format(termo))
                return
            qtd_total = sum(v.get("qtd", 1) for v in vendas_prod)
            receita_total = sum(v.get("total", 0) for v in vendas_prod)
            # Devolve estoque
            for v in vendas_prod:
                prod = next((p for p in dados["estoque"] if p["id"] == v.get("produto_id")), None)
                if prod:
                    prod["qty"] = prod.get("qty", prod.get("estoque", 0)) + v.get("qtd", 1)
                    prod["estoque"] = prod["qty"]
            # Remove as vendas do produto
            for v in vendas_prod:
                if v in dados["vendas"]:
                    dados["vendas"].remove(v)
            salvar_dados(dados)
            send(chat_id, "*Vendas removidas!*\n{}\nQtd: {} unidades\nReceita removida: {}\nEstoque devolvido.".format(
                vendas_prod[0].get("produto_nome", "-"), qtd_total, real(receita_total)))

def main():
    print("FinStack Bot iniciando (requests puro)...")
    send(CHAT_ID, "*FinStack Bot Online!*\nBot iniciado com sucesso no Railway.\nMande /start para ver os comandos.")
    offset = None
    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = msg.get("text", "")
                if text and chat_id:
                    print("Mensagem: {} de {}".format(text, chat_id))
                    handle(chat_id, text)
        except Exception as e:
            print("Erro no loop:", e)
            time.sleep(5)

if __name__ == "__main__":
    main()
