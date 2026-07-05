# Validação

A modelagem ([MODELAGEM.md](MODELAGEM.md)) escolheu o **MLP**
(`hidden_layer_sizes=(32,)`, `alpha=0.01`) com **`SelectKBest(k=20)`** no
pipeline, com base num **holdout único** — uma estimativa que depende de uma
divisão particular dos dados. Esta etapa mede o desempenho do modelo de forma
robusta e analisa os erros. O código executável está na **seção 5 do
`notebook.ipynb`**.

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
- **Pipeline completo dentro de cada fold:** pré-processamento **e seletor de
  atributos** são refitados no treino de cada partição — sem vazamento.
- **Hiperparâmetros fixados** nos encontrados na modelagem. Ressalva
  metodológica registrada no notebook: como o tuning usou 75% da base, há um
  pequeno viés otimista; a alternativa rigorosa (validação aninhada) foi
  dispensada pelo escopo.
- A **matriz de confusão** usa `cross_val_predict` com 10 folds estratificados:
  cada deputado é previsto por um modelo que não o viu no treino, permitindo
  analisar os 590 casos.

## 2. Resultados

| Medida                               | Valor             |
| ------------------------------------ | ----------------- |
| Acurácia (30 medições)               | **0,877 ± 0,042** |
| F1-macro (30 medições)               | **0,832 ± 0,059** |
| Sensibilidade/revocação (governista) | 0,943             |
| Especificidade (acerto na oposição)  | 0,703             |
| Precisão (governista)                | 0,899             |

Matriz de confusão (590 deputados, classe positiva = governista):
VP = 410, FN = 25, FP = 46, VN = 109.

Referência no mesmo protocolo (recomputada na seção 5 do notebook): a Árvore
de Decisão sem seleção fica em F1 **0,758 ± 0,052** — a seleção de atributos +
MLP ganha ~0,07 de F1. A diferença é **estatisticamente significativa** num
teste pareado sobre as 30 medições (mesmas partições): _t_ pareado = 6,80,
p ≈ 1,8×10⁻⁷ (Wilcoxon: p ≈ 4,7×10⁻⁷).

## 3. Leitura dos resultados

- **O holdout da modelagem era otimista.** A validação cruzada estima o
  desempenho real em acurácia ~0,88 e F1 ~0,83; o holdout (0,892 / 0,853)
  caiu acima da média das 30 medições. É exatamente para expor isso que a
  validação usa várias divisões: uma divisão única pode dar sorte. A conclusão
  qualitativa não muda — bem acima do baseline (F1 0,424).
- **Compromisso entre as classes:** o MLP acerta 94% dos governistas e 70% da
  oposição — recorte diferente da árvore com `class_weight=balanced` (~79% em
  cada classe). O F1-macro total sobe de 0,758 para 0,832 ao custo de um leve
  deslocamento pró-classe majoritária; escolha consciente, guiada pela métrica
  de decisão do trabalho.
- **O erro se concentra em legendas divididas:** dos 71 erros (contra 125 da
  árvore), UNIÃO (18) e PL (16) respondem por quase metade — a bancada do
  UNIÃO é 73% governista mas vota dividida, e o perfil TSE não separa os dois
  grupos. O limite é estrutural: **quando o partido não determina a posição, o
  perfil demográfico pré-eleição não é suficiente**.

## 4. Conclusão do trabalho

É possível prever a linha de atuação (governista × oposição) de um deputado
federal usando apenas os dados de candidatura do TSE, com F1-macro real de
**0,832 ± 0,059** (contra 0,42 do chute na classe majoritária). O sinal
preditivo vem majoritariamente do **partido/federação** do candidato; a
seleção de atributos mostrou que 20 colunas bastam, e um MLP compacto sobre
elas é quem melhor explora esse sinal. Atributos demográficos têm papel
secundário e não resolvem os casos em que a própria legenda é dividida.
