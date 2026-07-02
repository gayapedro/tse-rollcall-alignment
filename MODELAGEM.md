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

**Modelo escolhido: Árvore de Decisão** — melhor F1-macro e melhor acurácia,
e ainda o modelo mais interpretável da comparação.

## 4. Leitura dos resultados

- **Todos os modelos superam o baseline com folga** no F1-macro
  (0,74–0,81 contra 0,42): o perfil TSE pré-eleição carrega, sim, sinal
  sobre a linha de atuação futura. A pergunta do trabalho tem resposta
  positiva.
- **A árvore vencedora tem profundidade 3**: pouquíssimas regras capturam
  quase todo o sinal. A raiz da árvore é `partido_PL` (candidato do PL →
  oposição em todas as folhas daquele ramo); nos demais partidos, região e
  idade refinam a decisão. **O partido domina a previsão**, com atributos
  demográficos em papel secundário.
- **Random Forest fica atrás da árvore única** — contraintuitivo, mas
  coerente: o *ensemble* serve para reduzir variância, e uma árvore rasa e
  regularizada já tem variância baixa; o sorteio de atributos da floresta
  ainda dilui o sinal, que está concentrado em poucas colunas de partido.
- **MLP não compensa a complexidade**: com apenas 442 amostras de treino,
  a rede não encontra estrutura não-linear que a árvore simples já não
  capture.
- **KNN é o mais fraco** em F1: distâncias em espaço esparso de one-hot
  (125 dimensões, maioria zeros) discriminam mal os vizinhos.

## 5. Próxima etapa

Validação do modelo escolhido: validação cruzada estratificada repetida
(estimativa robusta de desempenho, não um único holdout), matriz de
confusão e análise de erros por classe. Documentada em
[VALIDACAO.md](VALIDACAO.md) e na seção 5 do notebook.
