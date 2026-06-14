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

@app.route("/options")
def options_handler():
    return cors_headers(jsonify({}))

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
    # Buscar IDs
    r1 = requests.get(
        f"https://api.mercadolibre.com/users/{user_id}/items/search?status=active&limit=100",
        headers={"Authorization": f"Bearer {token}"}
    )
    ids = r1.json().get("results", [])
    if not ids:
        return jsonify({"items": []})
    # Buscar detalhes em lote (máx 20 por vez)
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
                    "thumbnail": b.get("thumbnail", "")
                })
    return jsonify({"items": items})

# Opções de frete para um item
@app.route("/ml/frete/<item_id>", methods=["GET", "OPTIONS"])
def ml_frete(item_id):
    if request.method == "OPTIONS":
        return jsonify({})
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    resp = requests.get(
        f"https://api.mercadolibre.com/items/{item_id}/shipping_options",
        headers={"Authorization": f"Bearer {token}"}
    )
    return jsonify(resp.json()), resp.status_code

# Custos estimados completos (igual simulador ML)
@app.route("/ml/custos/<item_id>", methods=["GET", "OPTIONS"])
def ml_custos(item_id):
    if request.method == "OPTIONS":
        return jsonify({})
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    # Item details + shipping em paralelo
    r_item  = requests.get(f"https://api.mercadolibre.com/items/{item_id}",
                           headers={"Authorization": f"Bearer {token}"})
    r_frete = requests.get(f"https://api.mercadolibre.com/items/{item_id}/shipping_options",
                           headers={"Authorization": f"Bearer {token}"})
    
    item_data  = r_item.json()
    frete_data = r_frete.json()
    
    listing_type = item_data.get("listing_type_id", "gold_special")
    preco        = item_data.get("price", 0)
    
    # Comissão por tipo de anúncio
    comissao_pct = {
        "gold_pro":     0.19,
        "gold_special": 0.135,
        "gold":         0.16,
        "silver":       0.10,
        "bronze":       0.05,
        "free":         0.0
    }.get(listing_type, 0.135)
    
    return jsonify({
        "item": {
            "id":            item_data.get("id"),
            "title":         item_data.get("title"),
            "price":         preco,
            "listing_type":  listing_type,
            "comissao_pct":  comissao_pct,
            "comissao_val":  preco * comissao_pct,
        },
        "frete": frete_data.get("options", [])
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
