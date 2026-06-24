# The Sort Engine — Algoritmos de Busca Interativos

Projeto de ordenação e busca com dados reais do Banco Mundial
\+ Camada de persistência em **CSV** (texto) e **Pickle** (binário).

---

## Como executar

```bash
pip install flask
python backend.py
# Abrir http://localhost:5000
```

Ou pressione **F5** no VSCode (já configurado).

---

## Funcionalidades

### Algoritmos de ordenação (visualizados passo a passo)
| Algoritmo | Melhor | Médio | Pior |
|-----------|--------|-------|------|
| Bubble Sort | O(n) | O(n²) | O(n²) |
| Selection Sort | O(n²) | O(n²) | O(n²) |
| Insertion Sort | O(n) | O(n²) | O(n²) |
| Merge Sort | O(n log n) | O(n log n) | O(n log n) |
| Quick Sort | O(n log n) | O(n log n) | O(n²) |
| Heap Sort | O(n log n) | O(n log n) | O(n log n) |

### Busca
- **Linear** — O(n), busca por nome (substring)
- **Binária** — O(log n), busca por valor numérico exato

### Fontes de dados (Banco Mundial)
- PIB (US$ bilhões)
- Expectativa de Vida
- População (milhões)
- PIB per Capita (US$)

---

## Camada de Persistência (nova)

### Formatos

| Formato | Módulo | Tipo | Arquivo |
|---------|--------|------|---------|
| CSV | `csv.DictWriter` / `DictReader` | Texto legível | `dados/dados.csv` |
| Pickle | `pickle.dump` / `pickle.load` | Binário Python | `dados/dados.pkl` |

### Endpoints novos

| Rota | Descrição |
|------|-----------|
| `GET /api/dados` | Busca dataset da API do Banco Mundial |
| `POST /api/salvar` | Grava em CSV **e** Pickle simultaneamente |
| `GET /api/offline?fmt=csv` | Lê do disco sem internet |
| `GET /api/offline?fmt=pkl` | Lê Pickle do disco |
| `GET /api/painel` | Tamanho KB + tempo de leitura dos dois formatos |
| `GET /api/inspecionar` | Texto legível + hexdump de cada arquivo |

### Endpoints originais (agora com suporte offline)

| Rota | Parâmetros extras |
|------|-------------------|
| `GET /api/sort` | `&offline=true&fmt=csv\|pkl` |
| `GET /api/comparar` | `&offline=true&fmt=csv\|pkl` |
| `GET /api/busca` | `&offline=true&fmt=csv\|pkl` |

---

## CSV vs Pickle — Análise

**CSV**
- Texto puro, abre em Excel/LibreOffice
- Requer conversão de tipos na leitura (tudo vira string)
- Menor overhead para dados simples

**Pickle**
- Binário Python nativo, preserva tipos automaticamente
- Mais rápido para leitura de objetos complexos
- Exclusivo do Python (não portável para outras linguagens)

---

## Estrutura

```
sort_engine/
├── backend.py          ← Flask: ordenação, busca, persistência
├── requirements.txt    ← flask
├── README.md
├── static/
│   └── index.html      ← Frontend completo (fiel ao original)
├── dados/              ← Criado ao salvar
│   ├── dados.csv
│   └── dados.pkl
└── .vscode/
    ├── settings.json
    └── launch.json     ← F5 para iniciar
```
