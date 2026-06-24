"""
The Sort Engine — Backend Flask para Vercel
Algoritmos de ordenação e busca com dados do Banco Mundial
+ Persistência em CSV e Pickle usando /tmp (Vercel serverless)
"""

from flask import Flask, jsonify, request
import csv, pickle, time, os, json, random, io
import urllib.request

app = Flask(__name__)

@app.after_request
def add_cors(r):
    r.headers["Access-Control-Allow-Origin"]  = "*"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return r

# No Vercel, /tmp é o único diretório gravável (persiste durante a execução)
DATA_DIR = "/tmp/dados"
os.makedirs(DATA_DIR, exist_ok=True)

FILES = {
    "csv": os.path.join(DATA_DIR, "dados.csv"),
    "pkl": os.path.join(DATA_DIR, "dados.pkl"),
}

# ══════════════════════════════════════════════
#  ALGORITMOS DE ORDENAÇÃO
# ══════════════════════════════════════════════

def bubble_sort(arr):
    a = arr[:]
    steps, comps, swaps = [], 0, 0
    n = len(a)
    for i in range(n):
        for j in range(n - i - 1):
            comps += 1
            if a[j]["value"] > a[j+1]["value"]:
                a[j], a[j+1] = a[j+1], a[j]
                swaps += 1
            steps.append({"array": [x["name"] for x in a], "values": [x["value"] for x in a],
                           "comparing": [j, j+1], "sorted": list(range(n - i, n))})
    return a, steps, comps, swaps

def selection_sort(arr):
    a = arr[:]
    steps, comps, swaps = [], 0, 0
    n = len(a)
    for i in range(n):
        min_idx = i
        for j in range(i+1, n):
            comps += 1
            if a[j]["value"] < a[min_idx]["value"]: min_idx = j
            steps.append({"array": [x["name"] for x in a], "values": [x["value"] for x in a],
                           "comparing": [i, j], "sorted": list(range(i))})
        if min_idx != i:
            a[i], a[min_idx] = a[min_idx], a[i]; swaps += 1
    return a, steps, comps, swaps

def insertion_sort(arr):
    a = arr[:]
    steps, comps, swaps = [], 0, 0
    for i in range(1, len(a)):
        key = a[i]; j = i - 1
        while j >= 0 and a[j]["value"] > key["value"]:
            comps += 1; a[j+1] = a[j]; swaps += 1; j -= 1
            steps.append({"array": [x["name"] for x in a], "values": [x["value"] for x in a],
                           "comparing": [j+1, j+2], "sorted": list(range(i))})
        a[j+1] = key
    return a, steps, comps, swaps

def merge_sort(arr):
    a = arr[:]
    steps, comps_box, swaps_box = [], [0], [0]
    def _merge(lst, lo, mid, hi):
        left = lst[lo:mid+1]; right = lst[mid+1:hi+1]
        i = j = 0; k = lo
        while i < len(left) and j < len(right):
            comps_box[0] += 1
            if left[i]["value"] <= right[j]["value"]: lst[k] = left[i]; i += 1
            else: lst[k] = right[j]; j += 1; swaps_box[0] += 1
            k += 1
            steps.append({"array": [x["name"] for x in lst], "values": [x["value"] for x in lst],
                           "comparing": [lo, hi], "sorted": []})
        while i < len(left):  lst[k] = left[i];  i += 1; k += 1
        while j < len(right): lst[k] = right[j]; j += 1; k += 1
    def _ms(lst, lo, hi):
        if lo < hi:
            mid = (lo + hi) // 2; _ms(lst, lo, mid); _ms(lst, mid+1, hi); _merge(lst, lo, mid, hi)
    _ms(a, 0, len(a)-1)
    return a, steps, comps_box[0], swaps_box[0]

def quick_sort(arr):
    a = arr[:]
    steps, comps_box, swaps_box = [], [0], [0]
    def _qs(lst, lo, hi):
        if lo < hi:
            pivot = lst[hi]["value"]; i = lo - 1
            for j in range(lo, hi):
                comps_box[0] += 1
                if lst[j]["value"] <= pivot:
                    i += 1; lst[i], lst[j] = lst[j], lst[i]; swaps_box[0] += 1
                steps.append({"array": [x["name"] for x in lst], "values": [x["value"] for x in lst],
                               "comparing": [j, hi], "pivot": hi, "sorted": []})
            lst[i+1], lst[hi] = lst[hi], lst[i+1]; swaps_box[0] += 1
            p = i + 1; _qs(lst, lo, p-1); _qs(lst, p+1, hi)
    _qs(a, 0, len(a)-1)
    return a, steps, comps_box[0], swaps_box[0]

def heap_sort(arr):
    a = arr[:]
    steps, comps, swaps = [], 0, 0
    n = len(a)
    def heapify(lst, size, root):
        nonlocal comps, swaps
        largest = root; l = 2*root+1; r = 2*root+2
        if l < size:
            comps += 1
            if lst[l]["value"] > lst[largest]["value"]: largest = l
        if r < size:
            comps += 1
            if lst[r]["value"] > lst[largest]["value"]: largest = r
        if largest != root:
            lst[root], lst[largest] = lst[largest], lst[root]; swaps += 1
            steps.append({"array": [x["name"] for x in lst], "values": [x["value"] for x in lst],
                           "comparing": [root, largest], "sorted": []})
            heapify(lst, size, largest)
    for i in range(n//2-1, -1, -1): heapify(a, n, i)
    for i in range(n-1, 0, -1):
        a[0], a[i] = a[i], a[0]; swaps += 1; heapify(a, i, 0)
    return a, steps, comps, swaps

SORTERS = {
    "bubble": bubble_sort, "selection": selection_sort, "insertion": insertion_sort,
    "merge": merge_sort, "quick": quick_sort, "heap": heap_sort,
}

# ══════════════════════════════════════════════
#  DADOS — Banco Mundial
# ══════════════════════════════════════════════

WB_SOURCES = {
    "world_bank_gdp":        ("NY.GDP.MKTP.CD", 1e9,  "PIB (US$ bilhões)"),
    "world_bank_life":       ("SP.DYN.LE00.IN", 1,    "Expectativa de Vida"),
    "world_bank_population": ("SP.POP.TOTL",    1e6,  "População (milhões)"),
    "world_bank_gdp_pc":     ("NY.GDP.PCAP.CD", 1,    "PIB per Capita (US$)"),
}

FALLBACK = [
    {"name":"EUA","value":25463.0},{"name":"China","value":17963.2},
    {"name":"Japão","value":4231.1},{"name":"Alemanha","value":4072.2},
    {"name":"Índia","value":3385.1},{"name":"Reino Unido","value":3070.7},
    {"name":"França","value":2782.9},{"name":"Canadá","value":2139.8},
    {"name":"Brasil","value":2081.2},{"name":"Itália","value":2010.4},
    {"name":"Austrália","value":1693.0},{"name":"Coreia do Sul","value":1665.2},
    {"name":"Espanha","value":1418.3},{"name":"México","value":1322.8},
    {"name":"Indonésia","value":1319.1},{"name":"Países Baixos","value":1008.0},
    {"name":"Suíça","value":807.7},{"name":"Turquia","value":905.9},
    {"name":"Polônia","value":688.2},{"name":"Suécia","value":585.9},
    {"name":"Irlanda","value":529.3},{"name":"Israel","value":527.5},
    {"name":"Argentina","value":632.8},{"name":"Bélgica","value":579.2},
    {"name":"Noruega","value":579.2},{"name":"Emirados Árabes","value":499.2},
    {"name":"Nigéria","value":477.4},{"name":"Áustria","value":471.4},
    {"name":"Bangladesh","value":460.2},{"name":"Singapura","value":466.8},
    {"name":"Tailândia","value":495.4},{"name":"Malásia","value":407.0},
    {"name":"Dinamarca","value":395.1},{"name":"Egito","value":387.1},
    {"name":"Vietnã","value":362.6},{"name":"Colômbia","value":343.7},
    {"name":"Romênia","value":301.4},{"name":"Chile","value":301.0},
    {"name":"Republica Tcheca","value":296.3},{"name":"Iraque","value":264.2},
    {"name":"Finlândia","value":267.3},{"name":"Nova Zelândia","value":246.7},
    {"name":"Peru","value":242.6},{"name":"Portugal","value":237.7},
    {"name":"Cazaquistão","value":220.6},{"name":"Grécia","value":218.2},
    {"name":"Hungria","value":188.5},{"name":"Ucrânia","value":160.5},
    {"name":"Etiópia","value":126.8},{"name":"Angola","value":124.5},
]

_REGION_WORDS = {
    "income","world","ibrd","ida ","oecd","euro area","fragile","dividend",
    "blend","total","caribbean","sub-saharan","latin","north africa","south asia",
    "east asia","pacific (excluding","& pacific","europe & central",
    "middle east &","north america","small states","heavily indebted",
}
def _is_region(name):
    n = name.lower()
    return any(w in n for w in _REGION_WORDS)

def fetch_world_bank(indicator, divisor, size):
    url = (f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
           f"?format=json&per_page=300&mrv=1&date=2022")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = json.loads(resp.read().decode())
        items = []
        for entry in raw[1] or []:
            if not entry.get("value"): continue
            name = entry.get("country", {}).get("value", "")
            iso3 = entry.get("countryiso3code", "")
            if not iso3 or len(iso3) != 3: continue
            if _is_region(name): continue
            items.append({"name": name, "value": round(entry["value"] / divisor, 2)})
        if not items: raise ValueError("vazio")
        items.sort(key=lambda x: x["value"], reverse=True)
        return items[:size]
    except Exception:
        return [d.copy() for d in FALLBACK[:size]]

# ══════════════════════════════════════════════
#  PERSISTÊNCIA — CSV e Pickle (usando /tmp)
# ══════════════════════════════════════════════

def salvar_csv(dados):
    with open(FILES["csv"], "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "value"])
        w.writeheader()
        w.writerows(dados)

def carregar_csv():
    rows = []
    with open(FILES["csv"], encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({"name": r["name"], "value": float(r["value"])})
    return rows

def salvar_pickle(dados):
    with open(FILES["pkl"], "wb") as f:
        pickle.dump(dados, f)

def carregar_pickle():
    with open(FILES["pkl"], "rb") as f:
        return pickle.load(f)

def hexdump(caminho, n=256):
    with open(caminho, "rb") as f: raw = f.read(n)
    linhas = []
    for i in range(0, len(raw), 16):
        chunk = raw[i:i+16]
        h = " ".join(f"{b:02x}" for b in chunk)
        a = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        linhas.append(f"{i:04x}  {h:<48}  {a}")
    return "\n".join(linhas)

def trecho_texto(caminho, n=800):
    with open(caminho, encoding="utf-8", errors="replace") as f:
        return f.read(n)

def tamanho_kb(caminho):
    try:    return round(os.path.getsize(caminho) / 1024, 3)
    except: return None

# ══════════════════════════════════════════════
#  ENDPOINTS
# ══════════════════════════════════════════════

@app.route("/api/dados")
def ep_dados():
    source = request.args.get("source", "world_bank_gdp")
    size   = min(int(request.args.get("size", 16)), 50)
    if source not in WB_SOURCES:
        return jsonify({"ok": False, "erro": "fonte inválida"}), 400
    indicator, divisor, label = WB_SOURCES[source]
    dados = fetch_world_bank(indicator, divisor, size)
    return jsonify({"ok": True, "dados": dados, "label": label, "fonte": "api"})

@app.route("/api/sort")
def ep_sort():
    source    = request.args.get("source", "world_bank_gdp")
    algorithm = request.args.get("algorithm", "bubble")
    size      = min(int(request.args.get("size", 16)), 50)
    offline   = request.args.get("offline", "false").lower() == "true"
    fmt       = request.args.get("fmt", "csv")

    if offline:
        if fmt == "pkl" and os.path.exists(FILES["pkl"]):
            dados = carregar_pickle()
        elif os.path.exists(FILES["csv"]):
            dados = carregar_csv()
        else:
            return jsonify({"ok": False, "erro": "Nenhum arquivo salvo. Salve primeiro."}), 404
        dados = dados[:size]; fonte = "disco"
    else:
        indicator, divisor, _ = WB_SOURCES.get(source, WB_SOURCES["world_bank_gdp"])
        dados = fetch_world_bank(indicator, divisor, size); fonte = "api"

    fn = SORTERS.get(algorithm)
    if not fn: return jsonify({"ok": False, "erro": "algoritmo inválido"}), 400

    t0 = time.perf_counter()
    sorted_arr, steps, comps, swaps = fn(dados)
    elapsed = round((time.perf_counter() - t0) * 1000, 2)

    return jsonify({"ok": True, "fonte": fonte, "sorted": sorted_arr,
                    "steps": steps[:500], "total_steps": len(steps),
                    "comparisons": comps, "swaps": swaps,
                    "time_ms": elapsed, "algorithm": algorithm, "size": len(dados)})

@app.route("/api/busca")
def ep_busca():
    source  = request.args.get("source", "world_bank_gdp")
    alvo    = request.args.get("q", "")
    tipo    = request.args.get("tipo", "substring")
    offline = request.args.get("offline", "false").lower() == "true"
    fmt     = request.args.get("fmt", "csv")
    size    = min(int(request.args.get("size", 16)), 50)

    if offline:
        if fmt == "pkl" and os.path.exists(FILES["pkl"]): dados = carregar_pickle()
        elif os.path.exists(FILES["csv"]): dados = carregar_csv()
        else: return jsonify({"ok": False, "erro": "Salve primeiro."}), 404
        dados = dados[:size]
    else:
        indicator, divisor, _ = WB_SOURCES.get(source, WB_SOURCES["world_bank_gdp"])
        dados = fetch_world_bank(indicator, divisor, size)

    def busca_linear(arr, q, tipo):
        passos, encontrados = 0, []
        ql = q.lower()
        for i, item in enumerate(arr):
            passos += 1
            nome = item["name"].lower()
            if (ql in nome) if tipo == "substring" else (nome == ql):
                encontrados.append({"index": i, "item": item})
        return passos, encontrados

    def busca_binaria(arr, q):
        try: alvo_f = float(q)
        except: return 0, []
        s = sorted(arr, key=lambda x: x["value"])
        lo, hi, passos, encontrado = 0, len(s)-1, 0, None
        while lo <= hi:
            mid = (lo + hi) // 2; passos += 1
            v = s[mid]["value"]
            if abs(v - alvo_f) < 0.01: encontrado = {"index": mid, "item": s[mid]}; break
            elif v < alvo_f: lo = mid + 1
            else: hi = mid - 1
        return passos, [encontrado] if encontrado else []

    t0 = time.perf_counter()
    pl, rl = busca_linear(dados, alvo, tipo)
    pb, rb = busca_binaria(dados, alvo)
    elapsed = round((time.perf_counter() - t0) * 1000, 3)
    return jsonify({"ok": True, "linear": {"passos": pl, "encontrados": rl},
                    "binaria": {"passos": pb, "encontrados": rb},
                    "time_ms": elapsed, "total": len(dados)})

@app.route("/api/comparar")
def ep_comparar():
    source  = request.args.get("source", "world_bank_gdp")
    size    = min(int(request.args.get("size", 16)), 50)
    algos   = request.args.getlist("algo") or list(SORTERS.keys())
    offline = request.args.get("offline", "false").lower() == "true"
    fmt     = request.args.get("fmt", "csv")

    if offline:
        if fmt == "pkl" and os.path.exists(FILES["pkl"]): dados_base = carregar_pickle()
        elif os.path.exists(FILES["csv"]): dados_base = carregar_csv()
        else: return jsonify({"ok": False, "erro": "Salve primeiro."}), 404
        dados_base = dados_base[:size]
    else:
        indicator, divisor, _ = WB_SOURCES.get(source, WB_SOURCES["world_bank_gdp"])
        dados_base = fetch_world_bank(indicator, divisor, size)

    resultado = {}
    for algo in algos:
        fn = SORTERS.get(algo)
        if not fn: continue
        t0 = time.perf_counter()
        _, _, comps, swaps = fn(dados_base[:])
        resultado[algo] = {"comparisons": comps, "swaps": swaps,
                           "time_ms": round((time.perf_counter() - t0) * 1000, 2)}
    return jsonify({"ok": True, "resultados": resultado, "size": len(dados_base)})

@app.route("/api/salvar", methods=["POST"])
def ep_salvar():
    dados = request.json.get("dados", [])
    if not dados:
        return jsonify({"ok": False, "erro": "Nenhum dado enviado"}), 400
    metricas = {}
    for fmt, fn in [("csv", salvar_csv), ("pkl", salvar_pickle)]:
        t0 = time.perf_counter()
        fn(dados)
        metricas[fmt] = {"tempo_ms": round((time.perf_counter() - t0) * 1000, 3),
                         "tamanho_kb": tamanho_kb(FILES[fmt])}
    return jsonify({"ok": True, "metricas": metricas, "registros": len(dados)})

@app.route("/api/offline")
def ep_offline():
    fmt = request.args.get("fmt", "csv")
    caminho = FILES.get(fmt)
    if not caminho:
        return jsonify({"ok": False, "erro": "Formato inválido"}), 400
    if not os.path.exists(caminho):
        return jsonify({"ok": False,
                        "erro": f"'{caminho}' não existe. Salve primeiro."}), 404
    fn = carregar_csv if fmt == "csv" else carregar_pickle
    t0 = time.perf_counter()
    dados = fn()
    elapsed = round((time.perf_counter() - t0) * 1000, 3)
    return jsonify({"ok": True, "dados": dados, "fmt": fmt,
                    "tempo_ms": elapsed, "fonte": "disco"})

@app.route("/api/painel")
def ep_painel():
    resultado = {}
    for fmt, caminho in FILES.items():
        if not os.path.exists(caminho):
            resultado[fmt] = {"disponivel": False}; continue
        fn = carregar_csv if fmt == "csv" else carregar_pickle
        t0 = time.perf_counter(); fn()
        resultado[fmt] = {"disponivel": True, "tamanho_kb": tamanho_kb(caminho),
                          "tempo_leitura_ms": round((time.perf_counter() - t0) * 1000, 3)}
    return jsonify(resultado)

@app.route("/api/inspecionar")
def ep_inspecionar():
    resultado = {}
    for fmt, caminho in FILES.items():
        if not os.path.exists(caminho):
            resultado[fmt] = {"disponivel": False}; continue
        resultado[fmt] = {"disponivel": True, "eh_binario": fmt == "pkl",
                          "texto": trecho_texto(caminho) if fmt != "pkl" else None,
                          "hexdump": hexdump(caminho), "tamanho_kb": tamanho_kb(caminho)}
    return jsonify(resultado)

if __name__ == "__main__":
    print("✅  Rodando em http://localhost:5000")
    app.run(debug=True, port=5000)
