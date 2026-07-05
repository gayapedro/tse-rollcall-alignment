# Modelagem

Esta etapa compara **múltiplos algoritmos de classificação** sobre a base
pré-processada (590 deputados, 125 features após one-hot/normalização) para
decidir empiricamente qual modelo responde melhor à pergunta do trabalho:
prever a linha de atuação (governista × oposição) a partir do perfil TSE
pré-eleição. O código executável está na **seção 4 do `notebook.ipynb`**.

---

## 1. Protocolo experimental

- **Divisão treino/teste:** holdout **estratificado 75/25**
  (442 treino / 148 teste, `random_state=42`). A estratificação preserva a
  proporção de classes (73,7% governista) nos dois conjuntos — importante
  porque a base é desbalanceada (435 × 155).
- **Busca de hiperparâmetros:** `GridSearchCV` com validação cruzada interna
  de 5 partições, **usando somente o conjunto de treino**. O conjunto de
  teste nunca participa da escolha de hiperparâmetros — evita vazamento.
- **Pipeline completo:** cada modelo entra num
  `Pipeline(preprocessador, modelo)`; o pré-processamento (one-hot,
  normalização, imputação) é reajustado dentro de cada partição da validação
  cruzada, também para evitar vazamento.
- **Métricas:** acurácia **e** F1-macro no conjunto de teste. Com a base
  desbalanceada, acurácia sozinha engana: chutar sempre "governista" já dá
  0,736 de acurácia. Por isso o **F1-macro é a métrica decisiva** — dá peso
  igual às duas classes.
- **Baseline:** `DummyClassifier` (classe majoritária) como régua mínima.
  Qualquer modelo útil precisa superá-lo com folga no F1.

> A validação aprofundada (validação cruzada completa, matriz de confusão,
> análise de erros) é a **próxima etapa** do trabalho, separada desta.

## 2. Algoritmos e grades de hiperparâmetros

Quatro algoritmos, cada um com uma grade leve de hiperparâmetros:

| Algoritmo | Grade | Por que este algoritmo |
|---|---|---|
| KNN | `n_neighbors ∈ {3, 5, 9, 15, 21}`, `weights ∈ {uniform, distance}` | Método baseado em distância; depende diretamente da normalização feita no pré-processamento. |
| Árvore de Decisão | `max_depth ∈ {3, 5, 8, None}`, `min_samples_leaf ∈ {1, 5, 10}`, `class_weight=balanced` | Interpretável: as regras aprendidas podem ser lidas e discutidas. |
| Random Forest | `n_estimators ∈ {100, 300}`, `max_depth ∈ {8, None}`, `min_samples_leaf ∈ {1, 5}`, `class_weight=balanced` | *Ensemble* de árvores — testa se reduzir a variância da árvore única via *bagging* melhora a generalização. |
| MLP | `hidden_layer_sizes ∈ {(32,), (64,), (32,16)}`, `alpha ∈ {10⁻³, 10⁻²}`, `max_iter=2000` | Contraste não-linear; com 590 amostras, redes pequenas e regularizadas. |

A busca em grade otimiza `f1_macro` na validação cruzada interna.

## 3. Resultados

Desempenho no conjunto de teste (148 deputados nunca vistos), ordenado por
F1-macro:

| Modelo | Acurácia | F1-macro | Melhores hiperparâmetros |
|---|---|---|---|
| **Árvore de Decisão** | **0,851** | **0,805** | `max_depth=3`, `min_samples_leaf=5` |
| MLP | 0,824 | 0,774 | `hidden_layer_sizes=(32,)`, `alpha=0.01` |
| Random Forest | 0,804 | 0,757 | `n_estimators=100`, `max_depth=8`, `min_samples_leaf=5` |
| KNN | 0,811 | 0,738 | `n_neighbors=15`, `weights=uniform` |
| Baseline (majoritária) | 0,736 | 0,424 | — |

**Melhor sem seleção de atributos: Árvore de Decisão** — melhor F1-macro e melhor
acurácia, e ainda o modelo mais interpretável da comparação. A §3.1 testa se a
seleção de atributos muda o quadro.

### 3.1 Seleção de atributos (SelectKBest)

O fraco desempenho do KNN sugere que 125 colunas esparsas atrapalham modelos
sensíveis à dimensionalidade. Teste: `SelectKBest(f_classif)` **dentro do
pipeline** (refitado por partição — sem vazamento), com `k ∈ {10, 20, 40, todas}`
somado à grade de cada algoritmo:

| Modelo | F1 sem seleção | F1 com seleção | k escolhido |
|---|---|---|---|
| **MLP** | 0,774 | **0,853** | **20** |
| KNN | 0,738 | 0,771 | 40 |
| Árvore de Decisão | 0,805 | 0,805 | todas |
| Random Forest | 0,757 | 0,757 | todas |

- **MLP dispara**: com 20 entradas em vez de 125, a razão amostras/parâmetros
  melhora e a rede passa a árvore (0,853 no holdout, acurácia 0,892).
- **KNN melhora** (+0,033) — confirma a hipótese da dimensionalidade.
- **Árvore e RF escolhem `k=all`**: árvores já fazem seleção implícita por split;
  pré-filtrar não acrescenta.
- As 20 colunas mantidas: partidos e federações dominam, com região/UF e ocupações
  ligadas à segurança pública e ao agro na sequência — coerente com a exploração
  dos dados.

**Modelo escolhido: MLP (`hidden=(32,)`, `alpha=0.01`) + `SelectKBest(k=20)`.**
A árvore permanece como a leitura interpretável do problema (mostra *onde* o sinal
está); o MLP sobre os 20 melhores atributos é quem melhor o explora.

## 4. Leitura dos resultados

- **Todos os modelos superam o baseline com folga** no F1-macro
  (0,74–0,85 contra 0,42): o perfil TSE pré-eleição carrega, sim, sinal
  sobre a linha de atuação futura. A pergunta do trabalho tem resposta
  positiva.
- **A árvore de profundidade 3 mostra onde o sinal está**: a raiz é
  `partido_PL` (candidato do PL → oposição em todas as folhas daquele
  ramo); nos demais partidos, região e idade refinam a decisão.
  **O partido domina a previsão**, com atributos demográficos em papel
  secundário.
- **Random Forest fica atrás da árvore única** — contraintuitivo, mas
  coerente: o *ensemble* serve para reduzir variância, e uma árvore rasa e
  regularizada já tem variância baixa; o sorteio de atributos da floresta
  ainda dilui o sinal, que está concentrado em poucas colunas de partido.
- **Sem seleção, MLP e KNN sofrem com as 125 dimensões**; com
  `SelectKBest(k=20)`, o MLP compacto vira o melhor modelo da comparação
  (holdout 0,853) — a seleção de atributos é o que destrava os modelos
  sensíveis à dimensionalidade.

## 5. Próxima etapa

Validação do modelo escolhido (MLP + SelectKBest): validação cruzada
estratificada repetida (estimativa robusta de desempenho, não um único
holdout), matriz de confusão e análise de erros por classe. Documentada em
[VALIDACAO.md](VALIDACAO.md) e na seção 5 do notebook.
