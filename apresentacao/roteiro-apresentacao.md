# Roteiro de Apresentação — 10 min + 5 min de perguntas

**Divisão sugerida:** Pedro apresenta a primeira metade (problema + dados,
slides 1–6, ~4,5 min); Francisco a segunda (modelos + resultados, slides 7–13,
~5 min). Troca de apresentador na transição "dados prontos → modelagem".
Se preferirem inverter, o roteiro funciona igual — só trocar os nomes.

**Regra de ouro do tempo:** os slides 9, 10 e 11 são o coração. Se estiver
estourando, corte fala dos slides 4, 5 e 8 — nunca dos três finais.

---

## Slide 1 — Título `(20s · Pedro)`

> "Bom dia. Eu sou o Pedro, este é o Francisco, e o nosso trabalho pergunta se
> dá pra prever o comportamento de um deputado federal antes mesmo de ele ser
> eleito — usando só a ficha de candidatura."

**Dica:** não ler o título. Uma frase de gancho e avança.

## Slide 2 — Agenda `(20s · Pedro)`

> "O caminho: definimos o problema, mostramos como construímos a base do zero,
> o pré-processamento, os modelos que comparamos, como validamos e o que
> encontramos."

**Dica:** correr o dedo pela lista, sem ler item por item.

## Slide 3 — Problema ⭐ `(60s · Pedro)`

> "A pergunta é essa: dado um candidato X, com o que ele declarou ao TSE
> **antes** da eleição — partido, idade, patrimônio, ocupação — conseguimos
> prever a linha de atuação dele na Câmara: governista ou oposição?
> O ponto central do desenho é temporal: as features são todas pré-eleição,
> e o rótulo vem do comportamento de voto **depois**, em plenário. É um
> problema de classificação supervisionada legítimo, sem resposta escondida
> nas features.
> E um destaque: não usamos nenhum dataset pronto. A base foi construída do
> zero, cruzando duas fontes públicas cruas."

**Dica:** essa é a frase que a banca precisa guardar: _features antes,
rótulo depois_.

## Slide 4 — Base de dados `(50s · Pedro)`

> "As duas fontes: a API de Dados Abertos da Câmara — deputados, CPF, votações
> nominais e a orientação de bancada — e os arquivos brutos do TSE de 2022,
> com o perfil e os bens de cada candidato.
> O cruzamento é por CPF, que existe nos dois lados — chave exata, sem fuzzy
> match por nome. O arquivo de bens não tem CPF, então o patrimônio entra por
> um sequencial interno do TSE.
> Resultado: 590 de 590 deputados casados, 100%. São mais que 513 porque
> incluímos suplentes que assumiram na legislatura."

**Dica:** se perguntarem por que 590 > 513, a resposta já está dada aqui.

## Slide 5 — Pré-processamento: rótulo `(50s · Pedro)`

> "O rótulo é 100% objetivo, sem julgamento nosso. A API da Câmara publica,
> votação a votação, a orientação oficial do bloco Governo. Usamos só as
> votações **contestadas** — aquelas em que Governo e Oposição orientaram
> diferente — porque votação consensual não separa ninguém: todo mundo vota
> junto. Das 453 votações com orientação, sobram 380.
> Para cada deputado, calculamos o percentual de alinhamento com o Governo e
> cortamos em 0,5: alinhou na maioria, governista. Ficou 435 contra 155 —
> desbalanceado, e isso guia as escolhas de métrica que o Francisco vai
> mostrar."

## Slide 6 — Pré-processamento: features `(50s · Pedro)`

> "As features: oito categóricas — partido, federação, UF, região, gênero,
> instrução, cor/raça, ocupação — e duas numéricas, idade e patrimônio total.
> Depois do one-hot, 125 colunas.
> Regra anti-vazamento: nenhuma variável posterior à eleição entra no X, e o
> voto nunca vira feature. E o pipeline inteiro — imputação, one-hot,
> normalização — é reajustado dentro de cada partição do treino, então o teste
> nunca vaza para o ajuste.
> Guardem esse número, 125 colunas — ele volta já já. Com a base pronta, o
> Francisco assume a modelagem."

**→ TROCA DE APRESENTADOR**

## Slide 7 — Modelos `(60s · Francisco)`

> "Comparamos quatro algoritmos contra um baseline que sempre chuta a classe
> majoritária — se um modelo não bate isso com folga, não aprendeu nada.
> Os quatro: KNN, baseado em distância; Árvore de Decisão, o mais
> interpretável; Random Forest; e um MLP pequeno e regularizado.
> Nenhum roda com default cego: busca em grade de hiperparâmetros, com
> validação cruzada interna usando só o treino.
> E tem um ingrediente a mais: **seleção de atributos**. Um SelectKBest entra
> dentro do pipeline, e o número de colunas mantidas — 10, 20, 40 ou todas —
> vira mais um hiperparâmetro da grade. Como ele é refitado a cada partição,
> não há vazamento. Lembram das 125 colunas? A hipótese é que nem todas
> ajudam."

## Slide 8 — Validação `(50s · Francisco)`

> "Usamos validação cruzada
> estratificada de 10 folds, repetida três vezes — 30 medições, média e
> desvio. Dez folds porque o treino fica com 90% da base e cada fold de teste
> ainda tem uns 15 casos de oposição.
> Importante: o pipeline **inteiro**, incluindo o seletor de atributos, é
> reajustado em cada fold.
> E a métrica decisiva é F1-macro: com 74% de governistas, acurácia engana —
> chutar 'governista' para todo mundo já dá 0,736."

## Slide 9 — Resultados: seleção ⭐ `(90s · Francisco)`

> "Aqui o efeito da seleção de atributos, no holdout — 148 deputados que
> nenhum modelo viu. Duas leituras:
> Primeiro: todo mundo bate o baseline com folga. A pergunta do trabalho tem
> resposta positiva.
> Segundo, e mais interessante: a seleção **separa os modelos em dois
> grupos**. Árvore e Random Forest escolhem 'todas as colunas' — árvore já
> faz seleção implícita a cada split, não tem o que pré-filtrar. Já os modelos
> sensíveis à dimensionalidade destravam: o KNN melhora, e o MLP salta de
> 0,774 para **0,853** com apenas 20 colunas — e vira o vencedor.
> Faz sentido: uma rede com 125 entradas para 442 amostras de treino é
> parâmetro demais; com 20 entradas, a conta fecha.
> Modelo final: MLP de 32 neurônios sobre as 20 melhores colunas."

**Dica:** dar 5s de silêncio pra plateia ler a tabela antes de falar.

## Slide 10 — Resultados: validação robusta ⭐ `(90s · Francisco)`

> "Agora o número honesto. Na validação cruzada repetida, o F1 real é 0,832,
> com desvio de 0,06. O holdout tinha dado 0,853 — estava otimista, acima da
> média das 30 medições. É exatamente pra expor isso que a validação existe.
> A matriz cobre os 590 deputados, cada um previsto por um modelo que não o
> viu no treino: 94% de acerto nos governistas, 70% na oposição.
> Os erros caem de 125, do melhor modelo sem seleção, para 71. E o padrão dos
> erros se mantém: UNIÃO e PL lideram — o UNIÃO é uma bancada 73% governista
> que vota dividida, e a ficha de candidatura não separa os dois grupos.
> O limite é estrutural: quando o partido não determina a posição, a
> demografia não resolve."

## Slide 11 — Conclusão ⭐ `(60s · Francisco)`

> "Fechando: sim, a linha de atuação é previsível a partir da ficha de
> candidatura — F1 de 0,83 contra 0,42 do chute.
> O sinal vem majoritariamente do partido e da federação: a raiz da árvore
> interpretável é 'candidato do PL', e as 20 colunas selecionadas são quase
> todas de partido, federação e região — mais ocupações como policial militar
> e produtor agropecuário.
> E nós não ficamos na suposição: rodamos uma ablação com o mesmo protocolo,
> removendo a filiação das features. Sem partido e federação, o F1 despenca
> de 0,83 para 0,52, quase no baseline — ou seja, o sinal **é** a filiação;
> demografia e geografia sozinhas não sustentam a previsão.
> A seleção de atributos foi o que destravou o MLP; árvore e floresta já
> selecionam sozinhas.
> E sabemos exatamente onde o modelo para de funcionar: nas legendas
> divididas."

## Slide 12 — Limitações e futuro `(40s · Francisco)`

> "Limitações que já mapeamos: o rótulo é relativo ao mandato — 'governista'
> depende de quem governa. A alternativa que generaliza é fidelidade
> partidária, e o pipeline já está pronto pra ela: só troca o cálculo do alvo.
> Registramos também que o tuning usou 75% da base, um leve viés otimista.
> Clustering do padrão de votação e Senado ficam como extensões. E tudo é
> reprodutível: notebook, cache dos dados crus, semente fixa."

## Slide 13 — Obrigado `(10s · Francisco)`

> "Obrigado! Perguntas?"

---

## Banco de respostas para as perguntas (5 min)

**"Por que corte 0,5 e não a mediana?"** _(Pedro)_

> 0,5 tem leitura direta: o deputado alinhou com o Governo na maioria das
> votações em que os blocos divergiram. Mediana balancearia as classes
> artificialmente e o rótulo perderia significado político. O desbalanceamento
> que sobra a gente trata na modelagem, não no rótulo.

**"Por que só votações contestadas?"** _(Pedro)_

> Votação consensual não discrimina: governista e oposição votam igual. Ela só
> infla o alinhamento de todo mundo. Sinal está onde os blocos divergem.

**"Como garantem que não há vazamento?"** _(Pedro)_

> Três camadas: X só tem dados do TSE anteriores à eleição; o voto — origem do
> rótulo — nunca vira feature; e o pré-processamento **e o seletor de
> atributos** são refitados dentro de cada partição de treino — o teste nunca
> participa nem do tuning nem da escolha das colunas.

**"Por que a seleção ajuda o MLP e não a árvore ou a floresta?"** _(Francisco)_

> Árvore seleciona implicitamente: cada split escolhe a melhor coluna. O grid
> confirmou — escolheu 'todas'. O MLP não tem esse mecanismo: 125 entradas
> para 442 amostras é razão amostras/parâmetros ruim; com 20 entradas a rede
> compacta generaliza. O KNN melhora pelo mesmo motivo: distância em 20
> dimensões informativas discrimina melhor que em 125 esparsas.

**"Por que o holdout deu mais que a validação cruzada?"** _(Francisco)_

> Divisão única é uma amostra de tamanho 1 — pode dar sorte. As 30 medições
> mostram que 0,853 estava acima da média da distribuição. O valor que
> defendemos é o da validação: 0,832 ± 0,059.

**"A diferença entre MLP e árvore é estatisticamente significativa?"** _(Francisco)_

> Sim. As 30 medições da validação cruzada usam as mesmas partições para os
> dois modelos, então aplicamos teste pareado: t = 6,8 com p ≈ 2×10⁻⁷, e o
> Wilcoxon confirma. A diferença de 0,073 no F1 não é flutuação de divisão —
> está na seção 5 do notebook.

**"O recall da oposição caiu em relação à árvore (70% vs 79%). Por quê?"** _(Francisco)_

> A árvore usava class_weight=balanced, que equilibra as classes; o MLP não.
> O F1-macro total sobe de 0,758 para 0,832 — ganho grande — ao custo de um
> leve deslocamento pró-majoritária. Trade-off consciente, guiado pela métrica
> de decisão do trabalho. Colocar reweighting no MLP é refinamento futuro.

**"Por que 10 folds? Por que não leave-one-out?"** _(Francisco)_

> Dez folds: treino com 90% (menos viés pessimista) e ~15 casos de oposição
> por fold, métrica bem definida. Leave-one-out: 590 ajustes por avaliação,
> sem estratificação, F1 indefinido em fold de uma amostra.

**"Por que não Naive Bayes, SVM ou Regressão Logística?"** _(Francisco)_

> Naive Bayes assume independência condicional entre features — o one-hot viola
> isso de forma gritante: as colunas de um mesmo atributo são mutuamente
> exclusivas, e partido, federação e região são correlacionadíssimas. SVM e
> Logística aprendem fronteiras sobre o mesmo espaço em que o MLP já atua como
> contraste não-linear regularizado. A comparação já cobre quatro famílias:
> distância (KNN), regras (árvore), ensemble (RF) e rede neural (MLP) —
> adicionar mais modelos multiplicaria a grade sem hipótese nova.

**"Vocês removeram alguma feature manualmente?"** _(Francisco)_

> Não. A seleção é aprendida e validada: SelectKBest com k na grade de
> hiperparâmetros, refitado por fold. O dado decide quantas e quais colunas
> ficam — no vencedor, 20.

**"Isso não é só prever pelo partido?"** _(Francisco)_

> Essencialmente sim — e nós medimos nos dois sentidos. Rodamos a ablação com o
> mesmo protocolo (seção 6 do notebook): sem a feature partido, o F1 cai de
> 0,83 para 0,57; sem partido e federação, para 0,52 — pouco acima do baseline
> de 0,42. E o inverso: um modelo treinado **só** com o partido dá 0,829 —
> estatisticamente igual ao completo (0,832). As demais colunas que a seleção
> mantém são proxies do partido. O formulário do TSE prevê a linha de atuação
> _porque_ contém a filiação — e demonstrar isso com número é parte do
> resultado.

**"O rótulo não fica preso a este mandato?"** _(qualquer um)_

> Fica, e está registrado como limitação. Fidelidade partidária resolve —
> orientação do próprio partido existe em qualquer mandato — e o pipeline é o
> mesmo, só muda o cálculo do alvo. As features do TSE não dependem do
> mandato, então todo o trabalho pesado é reaproveitável.

**"E se o candidato trocar de partido depois de eleito?"** _(honesta)_

> Usamos o partido da candidatura, que é o que existe antes da eleição — é a
> premissa do problema. Migração partidária vira ruído no rótulo, e
> provavelmente é parte dos erros nas legendas divididas.

---

## Checklist pré-apresentação

- [ ] Cronometrar um ensaio completo — meta: 9 min (folga de 1).
- [ ] Testar o PPTX no computador/projetor da sala (fonte Questrial embutida?
      Se abrir sem a fonte, conferir se nada quebrou).
- [ ] Quem controla o passador de slides: quem está falando.
- [ ] Abrir o `notebook.ipynb` numa aba, caso a banca peça pra ver código.
- [ ] Saber de cabeça os 4 números: **0.853 / 0.832±0.059 / 0.424 / 94–70%**.
