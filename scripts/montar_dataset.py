#!/usr/bin/env python3
"""
Monta o dataset final supervisionado:  features (TSE, pré-eleição)  +  rótulo (Câmara).

Depende de: rotulo_deputados.csv  (gerado por coleta_rotulo.py)

Etapas:
  1. Para cada deputado do rótulo, busca o CPF na API da Câmara (cacheado).
  2. Baixa/le os CSVs do TSE 2022 (consulta_cand + bem_candidato).
  3. Indexa o TSE por CPF; filtra DEPUTADO FEDERAL.
  4. Join por CPF: features TSE + pct_alinhamento_gov.
  5. Deriva rótulo binário governista/oposição (corte pela mediana).
  6. Salva dataset_final.csv.

Features TSE (todas anteriores ao mandato -> sem leakage):
  partido, uf, regiao, idade, genero, grau_instrucao, cor_raca, ocupacao,
  federacao, patrimonio_total
"""
import urllib.request, json, os, csv, io, zipfile, statistics, sys, time

B = "https://dadosabertos.camara.leg.br/api/v2"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repo
CACHE = os.path.join(ROOT, "cache_camara"); os.makedirs(CACHE, exist_ok=True)
TSE = os.path.join(ROOT, "cache_tse"); os.makedirs(TSE, exist_ok=True)
DADOS = os.path.join(ROOT, "dados"); os.makedirs(DADOS, exist_ok=True)

TSE_URLS = {
    "consulta_cand": "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2022.zip",
    "bem_candidato": "https://cdn.tse.jus.br/estatistica/sead/odsele/bem_candidato/bem_candidato_2022.zip",
}
REGIAO = {  # UF -> região
    "AC":"N","AP":"N","AM":"N","PA":"N","RO":"N","RR":"N","TO":"N",
    "AL":"NE","BA":"NE","CE":"NE","MA":"NE","PB":"NE","PE":"NE","PI":"NE","RN":"NE","SE":"NE",
    "DF":"CO","GO":"CO","MT":"CO","MS":"CO",
    "ES":"SE","MG":"SE","RJ":"SE","SP":"SE",
    "PR":"S","RS":"S","SC":"S",
}


def cpf_do_deputado(did):
    fp = os.path.join(CACHE, f"dep_{did}.json")
    if os.path.exists(fp):
        return json.load(open(fp))["dados"]["cpf"]
    url = f"{B}/deputados/{did}"
    for t in range(4):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            d = json.load(urllib.request.urlopen(req, timeout=40))
            json.dump(d, open(fp, "w"))
            return d["dados"]["cpf"]
        except Exception:
            time.sleep(1.5 * (t + 1))
    return None


def baixar_tse(nome):
    zp = os.path.join(TSE, nome + ".zip")
    if not os.path.exists(zp):
        print(f"baixando TSE {nome}...", flush=True)
        urllib.request.urlretrieve(TSE_URLS[nome], zp)
    return zipfile.ZipFile(zp)


def carregar_consulta_cand():
    """idx CPF -> dict de features (apenas DEPUTADO FEDERAL)."""
    z = baixar_tse("consulta_cand")
    nome = next(n for n in z.namelist() if "BRASIL" in n and n.endswith(".csv"))
    idx = {}
    with z.open(nome) as raw:
        rd = csv.DictReader(io.TextIOWrapper(raw, encoding="latin1"),
                            delimiter=";", quotechar='"')
        for r in rd:
            if r.get("DS_CARGO") != "DEPUTADO FEDERAL":
                continue
            cpf = r["NR_CPF_CANDIDATO"]
            # ano de nascimento -> idade na eleicao (2022)
            try:
                ano_nasc = int(r["DT_NASCIMENTO"].split("/")[-1])
                idade = 2022 - ano_nasc
            except Exception:
                idade = ""
            idx[cpf] = {
                "sq": r.get("SQ_CANDIDATO", ""),
                "partido": r.get("SG_PARTIDO", ""),
                "federacao": r.get("SG_FEDERACAO", "") or "SEM",
                "uf": r.get("SG_UF", ""),
                "regiao": REGIAO.get(r.get("SG_UF", ""), ""),
                "idade": idade,
                "genero": r.get("DS_GENERO", ""),
                "grau_instrucao": r.get("DS_GRAU_INSTRUCAO", ""),
                "cor_raca": r.get("DS_COR_RACA", ""),
                "ocupacao": r.get("DS_OCUPACAO", ""),
            }
    return idx


def carregar_patrimonio():
    """SQ_CANDIDATO -> soma do patrimonio declarado.
    (bem_candidato não tem CPF; chave é o sequencial SQ_CANDIDATO)"""
    z = baixar_tse("bem_candidato")
    nome = next(n for n in z.namelist() if "BRASIL" in n and n.endswith(".csv"))
    soma = {}
    with z.open(nome) as raw:
        rd = csv.DictReader(io.TextIOWrapper(raw, encoding="latin1"),
                            delimiter=";", quotechar='"')
        for r in rd:
            sq = r.get("SQ_CANDIDATO")
            try:
                v = float(r.get("VR_BEM_CANDIDATO", "0").replace(".", "").replace(",", "."))
            except Exception:
                v = 0.0
            if sq:
                soma[sq] = soma.get(sq, 0.0) + v
    return soma


def main():
    rot_fp = os.path.join(DADOS, "rotulo_deputados.csv")
    if not os.path.exists(rot_fp):
        sys.exit("rotulo_deputados.csv ainda não existe — rode coleta_rotulo.py antes.")

    rot = list(csv.DictReader(open(rot_fp)))
    print(f"deputados no rótulo: {len(rot)}", flush=True)

    print("buscando CPFs na Câmara...", flush=True)
    for i, d in enumerate(rot):
        d["cpf"] = cpf_do_deputado(d["idDeputado"])
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(rot)}", flush=True)

    print("carregando TSE...", flush=True)
    feats = carregar_consulta_cand()
    patr = carregar_patrimonio()
    print(f"  TSE deputado federal: {len(feats)} candidatos", flush=True)

    # corte do rótulo binário em 0.5 (interpretável: alinha com Governo na MAIORIA
    # das votações contestadas, onde Governo e Oposição divergem)
    pcts = [float(d["pct_alinhamento_gov"]) for d in rot]
    limiar = 0.5
    print(f"  mediana={statistics.median(pcts):.3f} | corte fixo={limiar} (votações contestadas)", flush=True)

    cols = ["idDeputado","nome","cpf","partido","federacao","uf","regiao","idade",
            "genero","grau_instrucao","cor_raca","ocupacao","patrimonio_total",
            "pct_alinhamento_gov","n_votacoes","rotulo"]
    out = os.path.join(DADOS, "dataset_final.csv")
    casados = 0
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for d in rot:
            cpf = d.get("cpf")
            tf = feats.get(cpf)
            if not tf:
                continue  # não casou no TSE (raro: mudança de cpf, suplente que assumiu)
            casados += 1
            pct = float(d["pct_alinhamento_gov"])
            w.writerow({
                "idDeputado": d["idDeputado"], "nome": d["nome"], "cpf": cpf,
                "partido": tf["partido"], "federacao": tf["federacao"],
                "uf": tf["uf"], "regiao": tf["regiao"], "idade": tf["idade"],
                "genero": tf["genero"], "grau_instrucao": tf["grau_instrucao"],
                "cor_raca": tf["cor_raca"], "ocupacao": tf["ocupacao"],
                "patrimonio_total": round(patr.get(tf["sq"], 0.0), 2),
                "pct_alinhamento_gov": round(pct, 4),
                "n_votacoes": d["n_votacoes"],
                "rotulo": "governista" if pct >= limiar else "oposicao",
            })
    print(f"casados TSE<->Câmara: {casados}/{len(rot)}", flush=True)
    print(f"OK -> {out}", flush=True)


if __name__ == "__main__":
    main()
