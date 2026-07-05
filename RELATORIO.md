# Previsão da Linha de Atuação Parlamentar a partir do Perfil Eleitoral

**Tópicos em Inteligência Computacional — Aprendizado de Máquina Supervisionado**
Trabalho Final · Equipe de 2

---

## 1. Problema e pergunta de pesquisa

**É possível prever a linha de atuação de um deputado federal usando apenas os
dados do candidato registrados no TSE, antes da eleição?**

Formulação supervisionada:

```
candidato (features TSE, pré-eleição)  ──►  linha de atuação (rótulo, Câmara, pós-eleição)
```

O rótulo inicial é **governista × oposição**, derivado do comportamento de voto
do deputado em plenário.

## 2. Originalidade dos dados

Conforme exigência do enunciado, **não** se usa base do UCI nem dataset pronto da
internet. A base é construída do zero a partir de duas fontes públicas cruas:

| Fonte | Tipo | Conteúdo usado |
|---|---|---|
| API Dados Abertos da Câmara dos Deputados | REST JSON | deputados, CPF, votações nominais, orientação de bancada |
| Repositório de Dados Eleitorais do TSE (2022) | CSV em massa (ZIP) | perfil do candidato (`consulta_cand`) e bens declarados (`bem_candidato`) |

## 3. Integração das fontes (linkage)

- **Câmara ↔ TSE:** junção por **CPF** (presente nos dois lados; chave exata, sem
  *fuzzy match* por nome).
- **`consulta_cand` ↔ `bem_candidato`:** o arquivo de bens não possui CPF; a junção
  do patrimônio usa o sequencial **`SQ_CANDIDATO`**.
- Taxa de casamento: **590/590 deputados** (100%).

> O número 590 (> 513 cadeiras) inclui suplentes que assumiram durante a
> legislatura 57.

## 4. Pré-processamento

### 4.1 Filtragem (definição da amostra)
- TSE: apenas `DS_CARGO = DEPUTADO FEDERAL`.
- Câmara: apenas votações de **plenário (PLEN)** com voto nominal (> 50 votos).
- Apenas votações **contestadas**: orientação do bloco *Governo* diferente da
  orientação do bloco *Oposição*. Votações consensuais inflam o alinhamento e não
  discriminam a linha de atuação, por isso são descartadas
  (de 453 votações com orientação de Governo, **380 são contestadas**).

### 4.2 Engenharia do rótulo (variável-alvo)
1. Para cada votação contestada, lê-se a orientação oficial do bloco *Governo*.
2. Para cada deputado, calcula-se `pct_alinhamento_gov` = proporção de votos
   coincidentes com a orientação do Governo.
3. Binarização com corte **0.5** (interpretável: o deputado alinha com o Governo
   na *maioria* das votações em que Governo e Oposição divergem):
   - `governista` se `pct_alinhamento_gov >= 0.5`
   - `oposicao` caso contrário.

Distribuição resultante: **435 governista / 155 oposição** (desbalanceado, refletindo
a composição real da base governista na legislatura).

### 4.3 Engenharia de features (todas anteriores à eleição)
- `idade` — derivada de `DT_NASCIMENTO` (ano da eleição − ano de nascimento).
- `regiao` — derivada de `SG_UF` (mapa UF → N/NE/CO/SE/S).
- `patrimonio_total` — soma de `VR_BEM_CANDIDATO` por candidato (vírgula decimal
  BR convertida para float).
- `federacao` ausente (`#NULO`) tratada como categoria `"SEM"`.

### 4.4 Transformações (pipeline scikit-learn)
- Imputação: categóricas → moda; numéricas → mediana.
- Codificação: `OneHotEncoder(handle_unknown="ignore")` nas 8 variáveis categóricas.
- Escala: `StandardScaler` nas numéricas (`idade`, `patrimonio_total`).
- Tudo encapsulado em `Pipeline`, garantindo que o `fit` ocorra **apenas no treino**
  de cada *fold* (sem vazamento de dados).

### 4.5 Prevenção de vazamento (*leakage*)
- O vetor de features X contém **exclusivamente** dados do TSE anteriores à eleição.
- O comportamento de voto (origem do rótulo) **nunca** é usado como feature.
- Experimento de robustez: treino **com** e **sem** a feature `partido`.

## 5. Conjunto final

`dataset_final.csv` — 590 linhas, colunas:

```
idDeputado, nome, cpf, partido, federacao, uf, regiao, idade, genero,
grau_instrucao, cor_raca, ocupacao, patrimonio_total,
pct_alinhamento_gov, n_votacoes, rotulo
```

Features usadas no modelo:
- Categóricas (8): `partido, federacao, uf, regiao, genero, grau_instrucao, cor_raca, ocupacao`
- Numéricas (2): `idade, patrimonio_total`

## 6. Modelos

- **Baseline** — `DummyClassifier` (classe majoritária), referência obrigatória.
- **KNN** — `n_neighbors ∈ {3,5,9,15,21}` (ímpares, sem empate), `weights ∈ {uniform, distance}`.
- **Árvore de Decisão** — `max_depth ∈ {3,5,8,None}`, `min_samples_leaf ∈ {1,5,10}`, `class_weight=balanced`.
- **Random Forest** — `n_estimators ∈ {100,300}`, `max_depth ∈ {8,None}`, `min_samples_leaf ∈ {1,5}`.
- **MLP** — `hidden ∈ {(32,),(64,),(32,16)}`, `alpha ∈ {10⁻³,10⁻²}`, `max_iter=2000`.

Todos com **GridSearchCV** (F1-macro, CV interna 5-fold, só no treino) e seleção
em *holdout* estratificado 75/25.

**Seleção de atributos:** `SelectKBest(f_classif)` dentro do pipeline, com
`k ∈ {10, 20, 40, todas}` somado à grade — refitado por partição, sem vazamento.

## 7. Validação

- **Validação cruzada estratificada 10-fold, repetida 3×** → 30 medições
  (média ± desvio padrão).
- Métricas: acurácia e **F1 (macro)** — em base desbalanceada, F1 e a matriz de
  confusão são mais informativos que a acurácia.
- Matriz de confusão sobre os **590 deputados** via `cross_val_predict`
  (cada deputado previsto por um modelo que não o viu no treino).
- Análise de erros por partido.

## 8. Resultados

### 8.1 Efeito da seleção de atributos (F1-macro, holdout 25%)

| Modelo | F1 sem seleção | F1 com seleção | k escolhido |
|---|---|---|---|
| **MLP** | 0.774 | **0.853** | **20** |
| Árvore de Decisão | 0.805 | 0.805 | todas |
| KNN | 0.738 | 0.771 | 40 |
| Random Forest | 0.757 | 0.757 | todas |
| Baseline (majoritária) | 0.424 | — | — |

**Modelo escolhido: MLP (`hidden=(32,)`, `alpha=0.01`) + `SelectKBest(k=20)`.**
A seleção destrava os modelos sensíveis à dimensionalidade (MLP, KNN); árvore e
floresta escolhem `k=todas` porque árvores já selecionam implicitamente por split.

### 8.2 Validação robusta (10-fold ×3)

| Medida | Valor |
|---|---|
| Acurácia (30 medições) | **0.877 ± 0.042** |
| F1-macro (30 medições) | **0.832 ± 0.059** |

Matriz de confusão (590 deputados, `cross_val_predict`):

```
                 pred: governista   pred: oposicao
governista             410                25
oposicao                46               109
```

Acerto de 94% nos governistas e 70% na oposição; 71 erros no total (contra 125
da árvore sem seleção, F1 0.758 ± 0.052 no mesmo protocolo).

### 8.3 Atributos selecionados (k = 20)

Colunas de **partido** (PL, PT, MDB, NOVO, PDT, PSD, REPUBLICANOS...) e
**federação** (PT/PC do B/PV, PSOL/REDE, sem federação) dominam, seguidas de
**região/UF** (S, NE; RS, SC, BA, MT, RO) e de **ocupações** (policial militar,
militar reformado, produtor agropecuário). Na leitura interpretável (árvore de
decisão, profundidade 3), a raiz é `partido_PL`.

## 9. Discussão e conclusão

**A linha de atuação é previsível a partir do perfil do candidato — e o
partido/federação é o preditor dominante.** O F1 real (validação cruzada
repetida) é **0.832 ± 0.059**, contra 0.424 do baseline. Vinte colunas bastam, e
quase todas são de filiação partidária; demografia (região, ocupação, idade)
tem papel secundário.

Dois achados metodológicos valorizam o trabalho: (1) o holdout único (0.853) era
otimista em relação à validação repetida — evidência direta de por que validação
cruzada importa; (2) a seleção de atributos separa os algoritmos em dois grupos:
árvores não se beneficiam (selecionam sozinhas), enquanto MLP e KNN destravam.

O limite do modelo é estrutural, não estatístico: os erros se concentram nas
legendas **divididas** (UNIÃO com 18 dos 71 erros; PL com 16) — quando o partido
não determina a posição, o perfil pré-eleição não é suficiente.

## 10. Limitações e trabalhos futuros

- **Rótulo relativo ao mandato:** "governista" depende de quem governa. Uma
  alternativa que generaliza entre legislaturas é a **fidelidade partidária**
  (alinhamento com a orientação do próprio partido), que independe de qual
  partido está no poder. Mesmo *pipeline*, apenas troca o cálculo do alvo.
- **Etapa não-supervisionada (descartada por tempo):** um *clustering* do padrão
  de votação poderia revelar linhas de atuação inesperadas, além do eixo
  Governo×Oposição.
- Inclusão do **Senado** (81 senadores) como extensão.

## 11. Reprodutibilidade

```
coleta_rotulo.py    # Câmara: votações contestadas -> rotulo_deputados.csv
montar_dataset.py   # CPF + TSE (consulta_cand + bens) -> dataset_final.csv
notebook.ipynb      # limpeza, exploração, transformação, modelagem (+ seleção), validação
```

Dados crus ficam em `cache_camara/` e `cache_tse/` (cacheados em disco; re-execução
não refaz downloads). Ambiente Python em `.venv/` (scikit-learn + pandas).
Semente aleatória fixa (`random_state=42`).
