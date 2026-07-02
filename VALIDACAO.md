# Validação

A modelagem ([MODELAGEM.md](MODELAGEM.md)) escolheu a **Árvore de Decisão**
(`max_depth=3`, `min_samples_leaf=5`, `class_weight=balanced`) com base num
**holdout único** — uma estimativa que depende de uma divisão particular dos
dados. Esta etapa mede o desempenho do modelo de forma robusta e analisa os
erros. O código executável está na **seção 5 do `notebook.ipynb`**.

---

## 1. Protocolo — validação cruzada estratificada repetida

- **Validação cruzada estratificada com 10 folds:** a base (590 deputados) é
  dividida em 10 partições preservando a proporção de classes (73,7% × 26,3%);
  treina-se em 9 folds e testa-se no décimo, rotacionando. O desempenho é a
  média dos folds.
- **Repetida 3×** com embaralhamentos diferentes → **30 medições**, permitindo
  reportar média ± desvio padrão.
- **Por que 10 folds (e não 5):** treino com 90% dos dados (menos viés
  pessimista) e fold de teste com 59 amostras, das quais ~15 de oposição —
  as métricas por fold continuam bem definidas.
- **Por que não leave-one-out:** 590 ajustes por avaliação, sem estratificação
  e com F1 indefinido em folds de 1 amostra; indicado para bases menores.
- **Hiperparâmetros fixados** nos encontrados na modelagem. Ressalva
  metodológica registrada no notebook: como o tuning usou 75% da base, há um
  pequeno viés otimista; a alternativa rigorosa (validação aninhada) foi
  dispensada pelo escopo.
- A **matriz de confusão** usa `cross_val_predict` com 10 folds estratificados:
  cada deputado é previsto por um modelo que não o viu no treino, permitindo
  analisar os 590 casos.

## 2. Resultados

| Medida | Valor |
|---|---|
| Acurácia (30 medições) | **0,794 ± 0,048** |
| F1-macro (30 medições) | **0,758 ± 0,052** |
| Sensibilidade/revocação (governista) | 0,786 |
| Especificidade (acerto na oposição) | 0,794 |
| Precisão (governista) | 0,914 |

Matriz de confusão (590 deputados, classe positiva = governista):
VP = 342, FN = 93, FP = 32, VN = 123.

## 3. Leitura dos resultados

- **O holdout da modelagem era otimista.** A validação cruzada estima o
  desempenho real em acurácia ~0,79 e F1 ~0,76; o holdout (0,851 / 0,805)
  caiu perto do máximo das 30 medições. É exatamente para expor isso que a
  validação usa várias divisões: uma divisão única pode dar sorte. A conclusão
  qualitativa não muda — bem acima do baseline (F1 0,424).
- **Sem colapso na classe majoritária:** o modelo acerta ~79% de *cada* classe
  (sensibilidade 0,786, especificidade 0,794) — o `class_weight=balanced`
  equilibra as classes ao custo de falsos negativos de governista (93 dos
  125 erros).
- **O erro se concentra em legendas divididas:** o UNIÃO sozinho responde por
  53 dos 125 erros — a bancada é 73% governista mas vota dividida, e o perfil
  TSE não separa os dois grupos. No PL, o modelo erra justamente os ~13% de
  deputados que se alinham ao governo. O limite é estrutural: **quando o
  partido não determina a posição, o perfil demográfico pré-eleição não é
  suficiente**.

## 4. Conclusão do trabalho

É possível prever a linha de atuação (governista × oposição) de um deputado
federal usando apenas os dados de candidatura do TSE, com F1-macro real de
~0,76 (contra 0,42 do chute na classe majoritária). O sinal preditivo vem
majoritariamente do **partido** do candidato; atributos demográficos (região,
idade, patrimônio) têm papel secundário e não resolvem os casos em que a
própria legenda é dividida.
