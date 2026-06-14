from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

ML_APP_ID     = "1201355025627006"
ML_APP_SECRET = "euZzNNUy4ZkmDI1acA3fxY47PULTvVuZ"
REDIRECT_URI  = "https://viniciussj0.github.io/mosquiteiros-estoque/estoque.html"

CORS_ORIGIN = "https://viniciussj0.github.io"

def cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"]  = CORS_ORIGIN
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp

@app.after_request
def after(resp):
    return cors_headers(resp)

# Troca o code OAuth pelo access_token
@app.route("/ml/token", methods=["POST", "OPTIONS"])
def ml_token():
    if request.method == "OPTIONS":
        return jsonify({})
    code = request.json.get("code")
    if not code:
        return jsonify({"error": "code obrigatorio"}), 400
    resp = requests.post("https://api.mercadolibre.com/oauth/token", data={
        "grant_type":    "authorization_code",
        "client_id":     ML_APP_ID,
        "client_secret": ML_APP_SECRET,
        "code":          code,
        "redirect_uri":  REDIRECT_URI
    })
    return jsonify(resp.json()), resp.status_code

# Perfil do usuário
@app.route("/ml/me", methods=["GET", "OPTIONS"])
def ml_me():
    if request.method == "OPTIONS":
        return jsonify({})
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    resp = requests.get("https://api.mercadolibre.com/users/me",
                        headers={"Authorization": f"Bearer {token}"})
    return jsonify(resp.json()), resp.status_code

# Anúncios ativos do vendedor
@app.route("/ml/anuncios/<user_id>", methods=["GET", "OPTIONS"])
def ml_anuncios(user_id):
    if request.method == "OPTIONS":
        return jsonify({})
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    r1 = requests.get(
        f"https://api.mercadolibre.com/users/{user_id}/items/search?status=active&limit=100",
        headers={"Authorization": f"Bearer {token}"}
    )
    ids = r1.json().get("results", [])
    if not ids:
        return jsonify({"items": []})
    items = []
    for i in range(0, min(len(ids), 60), 20):
        batch = ids[i:i+20]
        r2 = requests.get(
            f"https://api.mercadolibre.com/items?ids={','.join(batch)}",
            headers={"Authorization": f"Bearer {token}"}
        )
        for entry in r2.json():
            if entry.get("code") == 200:
                b = entry["body"]
                items.append({
                    "id":    b["id"],
                    "title": b["title"],
                    "price": b.get("price", 0),
                    "listing_type_id": b.get("listing_type_id", "gold_special"),
                    "category_id": b.get("category_id", ""),
                    "thumbnail": b.get("thumbnail", "")
                })
    return jsonify({"items": items})

# Taxa real por categoria + preço (endpoint listing_prices)
def get_taxa_categoria(token, category_id, price, listing_type):
    """Busca a comissão real da categoria via API ML"""
    try:
        url = f"https://api.mercadolibre.com/sites/MLB/listing_prices?price={price}&category_id={category_id}&listing_type_id={listing_type}"
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
        data = r.json()
        # data pode ser lista ou dict
        if isinstance(data, list):
            for item in data:
                if item.get("listing_type_id") == listing_type:
                    sale_fee = item.get("sale_fee_amount", 0)
                    sale_pct = item.get("sale_fee_details", {}).get("percentage_fee", 0)
                    fixed    = item.get("sale_fee_details", {}).get("fixed_fee", 0)
                    return {"fee_amount": sale_fee, "percentage": sale_pct, "fixed_fee": fixed}
        elif isinstance(data, dict):
            sale_fee = data.get("sale_fee_amount", 0)
            details  = data.get("sale_fee_details", {})
            return {"fee_amount": sale_fee, "percentage": details.get("percentage_fee", 0), "fixed_fee": details.get("fixed_fee", 0)}
    except Exception as e:
        print("Erro taxa categoria:", e)
    return None

# Custos estimados completos (igual simulador ML) — taxa REAL por categoria
@app.route("/ml/custos/<item_id>", methods=["GET", "OPTIONS"])
def ml_custos(item_id):
    if request.method == "OPTIONS":
        return jsonify({})
    token = request.headers.get("Authorization", "").replace("Bearer ", "")

    r_item = requests.get(f"https://api.mercadolibre.com/items/{item_id}",
                          headers={"Authorization": f"Bearer {token}"})
    item_data = r_item.json()

    listing_type = item_data.get("listing_type_id", "gold_special")
    preco        = item_data.get("price", 0)
    category_id  = item_data.get("category_id", "")

    # Buscar taxa REAL das duas modalidades (clássico e premium) pela categoria
    taxas = {}
    for lt_nome, lt_id in [("classico", "gold_special"), ("premium", "gold_pro")]:
        t = get_taxa_categoria(token, category_id, preco, lt_id)
        if t:
            taxas[lt_nome] = t
        else:
            # fallback se a API não retornar
            pct = 0.135 if lt_id == "gold_special" else 0.165
            taxas[lt_nome] = {"fee_amount": preco * pct, "percentage": pct * 100, "fixed_fee": 0}

    # Frete
    r_frete = requests.get(f"https://api.mercadolibre.com/items/{item_id}/shipping_options",
                           headers={"Authorization": f"Bearer {token}"})
    frete_data = r_frete.json()

    return jsonify({
        "item": {
            "id":           item_data.get("id"),
            "title":        item_data.get("title"),
            "price":        preco,
            "listing_type": listing_type,
            "category_id":  category_id,
        },
        "taxas": taxas,
        "frete": frete_data.get("options", [])
    })


# Busca anúncios do vendedor por texto (título ou ID)
@app.route("/ml/buscar/<user_id>", methods=["GET", "OPTIONS"])
def ml_buscar(user_id):
    if request.method == "OPTIONS":
        return jsonify({})
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    q = request.args.get("q", "").strip()

    # Se for um ID de anúncio (MLB...), busca direto
    if q.upper().startswith("MLB"):
        r = requests.get(f"https://api.mercadolibre.com/items/{q.upper()}",
                         headers={"Authorization": f"Bearer {token}"})
        if r.status_code == 200:
            b = r.json()
            return jsonify({"items": [{
                "id": b["id"], "title": b["title"], "price": b.get("price",0),
                "listing_type_id": b.get("listing_type_id","gold_special"),
                "category_id": b.get("category_id",""), "thumbnail": b.get("thumbnail","")
            }]})
        return jsonify({"items": []})

    # Buscar todos os anúncios ativos e filtrar por título
    r1 = requests.get(
        f"https://api.mercadolibre.com/users/{user_id}/items/search?status=active&limit=100",
        headers={"Authorization": f"Bearer {token}"}
    )
    ids = r1.json().get("results", [])
    if not ids:
        return jsonify({"items": []})

    items = []
    for i in range(0, len(ids), 20):
        batch = ids[i:i+20]
        r2 = requests.get(
            f"https://api.mercadolibre.com/items?ids={','.join(batch)}",
            headers={"Authorization": f"Bearer {token}"}
        )
        for entry in r2.json():
            if entry.get("code") == 200:
                b = entry["body"]
                titulo = b.get("title", "")
                # Filtrar por texto (se houver query)
                if not q or q.lower() in titulo.lower():
                    items.append({
                        "id": b["id"], "title": titulo, "price": b.get("price",0),
                        "listing_type_id": b.get("listing_type_id","gold_special"),
                        "category_id": b.get("category_id",""), "thumbnail": b.get("thumbnail","")
                    })
    return jsonify({"items": items})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
