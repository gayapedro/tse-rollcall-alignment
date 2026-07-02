# Previsão da Linha de Atuação Parlamentar a partir do Perfil Eleitoral

Trabalho da disciplina **Tópicos em Inteligência Computacional — Aprendizado de
Máquina Supervisionado** (PPGComp/UFBA).

**Pergunta:** é possível prever a linha de atuação (governista × oposição) de um
deputado federal usando apenas os dados do candidato registrados no TSE, **antes**
da eleição?

```
candidato (features TSE, pré-eleição)  ──►  linha de atuação (rótulo, Câmara, pós-eleição)
```

A base é construída do zero a partir de fontes públicas cruas (sem UCI, sem
dataset pronto): API de Dados Abertos da **Câmara dos Deputados** e o repositório
de Dados Eleitorais do **TSE (2022)**.

---

## Etapa inicial: obtenção e integração dos dados

Três scripts, executados **nesta ordem**:

| Ordem | Script | O que faz | Saída |
|---|---|---|---|
| 1 | `coleta_rotulo.py` | Baixa da **Câmara** as votações de plenário (2023–2024), a orientação de bancada e o voto nominal de cada deputado. Calcula o alinhamento de cada deputado com a orientação do bloco *Governo* nas votações **contestadas** (Governo ≠ Oposição). | `rotulo_deputados.csv` |
| 2 | `montar_dataset.py` | Baixa do **TSE** o perfil dos candidatos (`consulta_cand_2022`) e o patrimônio (`bem_candidato_2022`); busca o CPF de cada deputado na API da Câmara; **une TSE × Câmara por CPF** e deriva o rótulo binário. | `dataset_final.csv` |
| 3 | `exportar_csvs.py` | Gera, a partir do cache, os três CSVs finais que documentam a linhagem dos dados. | `tse.csv`, `camara.csv`, `dataset.csv` |

### Linhagem dos dados

```
Câmara (API JSON) ─┐
                   ├─ junção por CPF ─► dataset.csv  (590 deputados, features + rótulo)
TSE (CSV/ZIP)     ─┘
```

| Arquivo | Linhas | Conteúdo |
|---|---|---|
| `tse.csv` | 10.630 | Dado **original do TSE**: todos os candidatos a deputado federal de 2022 (perfil + patrimônio + resultado da eleição) |
| `camara.csv` | 590 | Dado **buscado na API da Câmara**: deputado + CPF + atuação (`pct_alinhamento_gov`) |
| `dataset.csv` | 590 | Base **final integrada** (TSE ⨝CPF Câmara): features do TSE + `rotulo` |

> 590 deputados (acima das 513 cadeiras) inclui suplentes que assumiram o mandato.

---

## Como executar

Requer Python 3 com `scikit-learn`, `pandas`, `numpy`.

```bash
python3 -m venv .venv
.venv/bin/pip install scikit-learn pandas numpy

# etapa inicial (baixa da internet e reconstrói os caches automaticamente):
.venv/bin/python coleta_rotulo.py     # -> rotulo_deputados.csv
.venv/bin/python montar_dataset.py    # -> dataset_final.csv
.venv/bin/python exportar_csvs.py     # -> tse.csv, camara.csv, dataset.csv
```

Os scripts cacheiam os dados brutos em `cache_camara/` e `cache_tse/`
(ignorados pelo git; reconstruídos na primeira execução). A primeira coleta na
Câmara varre milhares de votações e leva alguns minutos; execuções seguintes leem
do cache.

---

## Estrutura do repositório

```
coleta_rotulo.py     # 1. coleta Câmara + cálculo do rótulo
montar_dataset.py    # 2. coleta TSE + junção por CPF
exportar_csvs.py     # 3. exporta tse.csv / camara.csv / dataset.csv
tse.csv              # dado original do TSE
camara.csv           # dado coletado da API da Câmara
dataset.csv          # base final integrada (entrada do pré-processamento)
notebook.ipynb       # pré-processamento + modelagem + validação (executável)
PREPROCESSAMENTO.md  # documentação da etapa de pré-processamento
MODELAGEM.md         # documentação da etapa de modelagem
VALIDACAO.md         # documentação da etapa de validação
```

## Etapas seguintes

A partir de `dataset.csv`, o fluxo segue no `notebook.ipynb`:

- **[Pré-processamento](PREPROCESSAMENTO.md)** — limpeza, exploração, transformação e
  normalização dos dados (seções 1–3 do notebook).
- **[Modelagem](MODELAGEM.md)** — múltiplos algoritmos de classificação comparados por
  acurácia/F1 para escolher o melhor (seção 4 do notebook).
- **[Validação](VALIDACAO.md)** — validação cruzada estratificada repetida, matriz de
  confusão e análise de erros do modelo escolhido (seção 5 do notebook).
