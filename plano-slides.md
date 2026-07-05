# Plano de Slides — Apresentação (10 min + 5 min perguntas)

13 slides no PPTX (template IC). Slides âncora: **3 (problema), 9–10 (resultados), 11 (conclusão)**.
Se apertar o tempo, cortar detalhe dos slides 4 e 8 — nunca dos âncora.

Versão apresentada = **notebook.ipynb** (MODELAGEM.md + VALIDACAO.md):
KNN / Árvore / RF / MLP com GridSearchCV **+ seleção de atributos (SelectKBest)**;
vencedor **MLP (32,) + SelectKBest(20)**, F1 real 0.832 ± 0.059.

---

## Slide 1 — Título
- "Previsão da Linha de Atuação Parlamentar a partir do Perfil Eleitoral"
- Francisco e Pedro; fontes: API Câmara + TSE 2022.

## Slide 2 — Agenda
- Problema · Base de dados · Pré-processamento · Modelos · Validação · Resultados · Conclusão.

## Slide 3 — Problema ⭐
- **"Dado um candidato X (dados TSE, pré-eleição), conseguimos prever sua linha de atuação (governista × oposição) na Câmara?"**
- `candidato (features TSE) → modelo → governista / oposição`
- Features antes da eleição, rótulo depois. Base construída do zero — sem UCI/Kaggle.

## Slide 4 — Base de dados
- API Câmara (JSON): deputados, CPF, votações, orientação de bancada.
- TSE 2022 (CSV): perfil do candidato + bens declarados.
- Integração por **CPF** (chave exata); bens por `SQ_CANDIDATO`; **590/590 (100%)**, inclui suplentes.

## Slide 5 — Pré-processamento: rótulo
- Só votações de plenário contestadas (Governo e Oposição divergem): 380 de 453.
- `pct_alinhamento_gov`; corte 0.5 → **435 governista × 155 oposição**.

## Slide 6 — Pré-processamento: features
- 8 categóricas + 2 numéricas (idade, patrimônio). 125 colunas após one-hot.
- Anti-leakage: nada pós-eleição em X; voto nunca vira feature.
- Pipeline sklearn: imputação → one-hot → StandardScaler, fit só no treino de cada fold.

## Slide 7 — Modelos
- Baseline (DummyClassifier) + 4 algoritmos com **GridSearchCV**: KNN, Árvore, RF, MLP.
- **Seleção de atributos**: `SelectKBest(f_classif)` dentro do pipeline, k ∈ {10, 20, 40, todas} na grade.
- Seleção em holdout estratificado 75/25; tuning só no treino (CV interna 5-fold), sem vazamento.

## Slide 8 — Validação
- Validação cruzada estratificada **10-fold repetida 3× → 30 medições** (média ± dp).
- Pipeline inteiro (pré-proc **+ seletor**) refitado em cada fold.
- Matriz de confusão via `cross_val_predict` (590 previstos fora do treino).
- F1-macro decide: acurácia engana (chutar governista já dá 0.736).

## Slide 9 — Resultados: seleção de modelos ⭐

| Modelo | F1 sem seleção | F1 com seleção | k |
|---|---|---|---|
| **MLP** | 0.774 | **0.853** | **20** |
| Árvore de Decisão | 0.805 | 0.805 | todas |
| KNN | 0.738 | 0.771 | 40 |
| Random Forest | 0.757 | 0.757 | todas |
| Baseline | 0.424 | — | — |

- Vencedor: **MLP (32 neurônios) + SelectKBest(20)**.
- História: seleção destrava os modelos sensíveis à dimensionalidade (MLP e KNN);
  árvore e RF escolhem k=todas porque árvores já selecionam sozinhas a cada split.

## Slide 10 — Resultados: validação robusta ⭐
- **F1-macro 0.832 ± 0.059** em 10-fold ×3 (holdout 0.853 era otimista — bom ponto pra falar).
- Matriz (590): VP 410 / FN 25 / FP 46 / VN 109 — 94% dos governistas, 70% da oposição.
- Erros caem de 125 (árvore) para 71; UNIÃO (18) e PL (16) lideram — legendas divididas.

## Slide 11 — Conclusão ⭐
- Sim, é previsível: F1 real 0.83 vs baseline 0.42.
- O partido domina — raiz da árvore é `partido_PL`; 20 colunas bastam (partidos,
  federações, região/UF, ocupações de segurança e agro).
- Seleção de atributos destrava o MLP (0.77 → 0.85); árvore e RF já selecionam sozinhas.
- Limite estrutural: legenda dividida → perfil TSE não separa.

## Slide 12 — Limitações e futuro
- Rótulo relativo ao mandato → alternativa: fidelidade partidária.
- Tuning usou 75% da base → leve viés otimista (validação aninhada fora do escopo).
- Clustering e Senado como extensões. Reprodutível (notebook, cache, seed 42).

## Slide 13 — Muito obrigado!

---

## Perguntas prováveis da banca
- **Por que corte 0.5 e não mediana?** Interpretável: alinha com o Governo na *maioria* das votações contestadas; mediana forçaria balanceamento artificial.
- **Por que só votações contestadas?** Consensuais inflam alinhamento e não discriminam.
- **Leakage?** X só tem dados TSE pré-eleição; pipeline (inclusive o SelectKBest) refitado por fold; teste nunca participa do tuning.
- **Por que a seleção ajuda o MLP e não a árvore/RF?** Árvores selecionam implicitamente a cada split. MLP com 125 entradas e 442 amostras de treino tem razão amostras/parâmetros ruim; com 20 entradas, a rede compacta generaliza.
- **Por que o holdout deu mais que a validação cruzada?** Divisão única pode dar sorte; 30 medições estimam o desempenho real (0.853 ficou acima da média da distribuição).
- **O recall da oposição caiu vs a árvore (70% vs 79%). Por quê?** MLP não usa class_weight; ganha F1-macro total (0.832 vs 0.758) com leve deslocamento pró-majoritária. Trade-off consciente, guiado pela métrica de decisão.
- **Diferença de 10 vs 5 folds? Leave-one-out?** 10 folds: menos viés pessimista, fold ainda com ~15 oposição. LOO: 590 ajustes, sem estratificação, F1 indefinido.
- **Fizeram remoção manual de features?** Não — a seleção é aprendida (SelectKBest com k na grade) e validada, não uma escolha a priori.
