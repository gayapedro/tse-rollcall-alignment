# Pré-processamento dos Dados

Documento descreve **apenas** a etapa de pré-processamento: obtenção dos dados,
tratamento de valores ausentes, transformação de atributos e normalização.

---

## 1. Obtenção dos dados

A base é construída do zero a partir de duas fontes públicas cruas (sem aplicação
prévia de algoritmos de Aprendizado de Máquina):

| Fonte                                             | Formato   | Conteúdo                                                                  |
| ------------------------------------------------- | --------- | ------------------------------------------------------------------------- |
| API de Dados Abertos da **Câmara dos Deputados**  | REST/JSON | deputados, CPF, votações nominais, orientação de bancada                  |
| Repositório de Dados Eleitorais do **TSE (2022)** | CSV (ZIP) | perfil do candidato (`consulta_cand`) e bens declarados (`bem_candidato`) |

### 1.1 Coleta na Câmara

- **Período analisado:** 01/01/2023 a 31/12/2024 (os dois primeiros anos da
  **legislatura 57**, mandato 2023–2027, correspondente aos eleitos em 2022).
- Lista de **todas** as votações de **plenário (PLEN)** nesse período.
- Para cada votação: orientação de bancada (`/votacoes/{id}/orientacoes`) e voto
  nominal de cada deputado (`/votacoes/{id}/votos`).
- Dados pessoais e CPF de cada deputado (`/deputados/{id}`).
- Respostas cacheadas em disco (`cache_camara/`) com escrita atômica, evitando
  redownload e arquivos corrompidos.

### 1.2 Coleta no TSE

- Download dos pacotes `consulta_cand_2022.zip` e `bem_candidato_2022.zip`
  (`cache_tse/`).
- Leitura com encoding `latin1`, delimitador `;` e `quotechar` `"`.

### 1.3 Integração (junção das fontes)

- **Câmara ↔ TSE:** junção por **CPF** (presente nas duas fontes; chave exata,
  sem correspondência aproximada por nome).
- **`consulta_cand` ↔ `bem_candidato`:** o arquivo de bens não contém CPF; a soma
  do patrimônio é ligada pelo sequencial **`SQ_CANDIDATO`**.
- Resultado: **590 deputados**, com **100% de casamento** (590/590).

> O total de 590 (acima das 513 cadeiras) inclui suplentes que assumiram o mandato
> durante a legislatura.

### 1.4 Definição da amostra (filtragem de linhas)

Filtros aplicados na coleta, que delimitam quais registros entram na base:

- TSE: apenas candidatos a `DEPUTADO FEDERAL` (descarta demais cargos).
- Câmara: apenas votações de **plenário** com voto nominal (≥ 50 votos).
- Apenas votações **contestadas** (ver §1.5): foram usadas **380 votações
  contestadas** dos dois anos analisados.

### 1.5 O que é uma votação "contestada"

Em cada votação, a liderança de cada bloco partidário divulga uma **orientação de
bancada** oficial — uma instrução de como votar (`Sim`, `Não` ou `Obstrução`). A
API da Câmara publica essas orientações, inclusive as dos blocos **Governo** e
**Oposição**.

Uma votação é **contestada** quando a orientação do Governo é **diferente** da
orientação da Oposição — ou seja, os dois lados disputam o tema:

```
Votação CONTESTADA (usada):          Votação CONSENSUAL (descartada):
  Governo:  Sim                         Governo:  Sim
  Oposição: Não   ← divergem            Oposição: Sim   ← concordam
```

**Por que filtrar:** o rótulo de cada deputado é o quanto ele vota alinhado com o
Governo. Numa votação consensual, _todos_ (até a oposição) votam igual ao Governo,
então o alinhamento não distingue ninguém — é ruído que infla artificialmente o
percentual. Só nas votações **contestadas** o voto do deputado realmente revela seu
lado: votar com o Governo o aproxima de "governista"; votar com a Oposição, de
"oposição".

Das **453** votações de plenário com orientação direcional do Governo
(contadas e impressas por `scripts/coleta_rotulo.py`), são **descartadas**:

- as **consensuais** (Governo = Oposição), e
- as que **não têm orientação da Oposição** (só o Governo orientou).

Restam as **380 contestadas**, que formam a base de cálculo do rótulo
`pct_alinhamento_gov` (ver §3).

## 2. Remoção de linhas com dados ausentes

Após a construção e a junção, a base foi auditada quanto a valores ausentes:

| Verificação                       | Resultado                    |
| --------------------------------- | ---------------------------- |
| Células `NaN`/vazias              | **0** em todas as 16 colunas |
| `idade` inválida (≤ 0 ou > 100)   | 0                            |
| Linhas sem correspondência no TSE | 0 (todas as 590 casaram)     |

**Não houve necessidade de remover linhas**, porque:

1. A junção por CPF é do tipo _inner_ — deputados sem correspondência no TSE
   simplesmente não entrariam na base (não geram linha com campos vazios). Todos
   os 590 casaram, então nenhuma linha órfã foi criada.
2. Os marcadores de ausência do TSE ocorrem em `federacao` (472 × `#NULO`) e,
   pontualmente, em `cor_raca` (1 × `NÃO INFORMADO`). Em `federacao`, o valor
   representa **ausência real e informativa** ("candidato sem federação"), não
   dado faltante — por isso esses marcadores são mantidos como **categoria
   própria** (o One-Hot os codifica como qualquer outro valor), e não removidos
   (ver §3).
3. `patrimonio_total = 0` em 22 candidatos significa **nenhum bem declarado**
   (valor verdadeiro), não dado ausente.

Como salvaguarda, o _pipeline_ de modelagem ainda inclui imputação (moda para
categóricas, mediana para numéricas), de modo que qualquer valor ausente residual
seria preenchido sem descartar a linha — preservando o tamanho da amostra.

## 3. Atributos transformados

Atributos derivados/criados a partir dos campos brutos:

| Atributo final        | Origem                                | Transformação                                                                   |
| --------------------- | ------------------------------------- | ------------------------------------------------------------------------------- |
| `idade`               | `DT_NASCIMENTO` (TSE)                 | `2022 − ano de nascimento`                                                      |
| `regiao`              | `SG_UF` (TSE)                         | mapeamento UF → {N, NE, CO, SE, S}                                              |
| `patrimonio_total`    | `VR_BEM_CANDIDATO` (TSE)              | soma dos bens por candidato; vírgula decimal BR → ponto flutuante               |
| `federacao`           | `SG_FEDERACAO` (TSE)                  | campo vazio → `"SEM"`; `#NULO` mantido como categoria própria ("sem federação") |
| `pct_alinhamento_gov` | votos + orientação _Governo_ (Câmara) | proporção de votos do deputado coincidentes com a orientação do Governo         |
| `rotulo` (alvo)       | `pct_alinhamento_gov`                 | binarização com corte 0.5 → `governista` / `oposicao`                           |

Codificação das variáveis categóricas (no _pipeline_):

- **One-Hot Encoding** (`OneHotEncoder`, `handle_unknown="ignore"`) nas 8
  categóricas: `partido, federacao, uf, regiao, genero, grau_instrucao, cor_raca,
ocupacao`.
- `handle_unknown="ignore"` evita erro quando um _fold_ de validação contém uma
  categoria não vista no treino.

Cardinalidade das categóricas: `partido` (23), `uf` (27), `ocupacao` (50),
`grau_instrucao` (6), `cor_raca` (6), `regiao` (5), `federacao` (4), `genero` (2).

> `grau_instrucao` é ordinal, mas é codificado como nominal (One-Hot): com 6
> níveis, a codificação binária não explode a dimensionalidade e deixa o modelo
> livre para aprender relações **não-monotônicas** com o alvo — uma codificação
> ordinal imporia a suposição de efeito crescente/decrescente.

## 4. Normalização

- As variáveis **numéricas** (`idade`, `patrimonio_total`) são padronizadas com
  **`StandardScaler`** (média 0, desvio-padrão 1). Necessário sobretudo para os
  modelos sensíveis à escala — o KNN (baseado em distância) e o MLP (baseado em
  gradiente); `patrimonio_total` varia de 0 a ~1,6 × 10⁸, o que sem padronização
  dominaria qualquer distância ou gradiente.
- A padronização é executada **dentro do `Pipeline`** do scikit-learn. Assim, em
  cada _fold_ da validação cruzada, o `fit` do escalador usa **apenas o conjunto
  de treino** — evitando vazamento de informação do conjunto de teste para o de
  treino.
- As variáveis categóricas (após One-Hot) não são escaladas (já são binárias 0/1).
- **Por que não transformação log no patrimônio?** Apesar da forte assimetria
  (skewness ≈ 10), optou-se por manter apenas a padronização: modelos de árvore
  são invariantes a transformações monotônicas, a exploração mostrou que as
  numéricas quase não carregam sinal sobre o alvo, e `patrimonio_total` nem
  sobrevive à seleção de atributos do modelo final — a transformação mudaria a
  escala de uma feature que os modelos não usam.

---

## Resumo do fluxo

```
Câmara (JSON)  ─┐
                ├─ junção por CPF / SQ_CANDIDATO ─► dataset_final.csv (590 × 16)
TSE (CSV)      ─┘
       │
       ├─ filtragem: deputado federal · plenário nominal · votações contestadas
       ├─ auditoria de ausentes: 0 NaN → nenhuma linha removida
       ├─ atributos derivados: idade, regiao, patrimonio_total, rotulo
       ├─ One-Hot nas 8 categóricas
       └─ StandardScaler nas 2 numéricas (dentro do pipeline, sem leakage)
```

Scripts correspondentes: `scripts/coleta_rotulo.py` (rótulo/Câmara),
`scripts/montar_dataset.py` (junção + atributos derivados) e `notebook.ipynb`
(One-Hot, imputação e normalização no pipeline — seções 1–3).
