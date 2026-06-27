#!/usr/bin/env python3
"""
Exporta os 3 CSVs da linhagem de dados:

  tse.csv      -> dados ORIGINAIS do TSE (candidatos a deputado federal, 2022)
  camara.csv   -> dados buscados na API da Câmara (deputado + atuação/voto)
  dataset.csv  -> base final supervisionada (junção TSE + Câmara, features + rótulo)

Lê do cache local (cache_tse/, cache_camara/, rotulo_deputados.csv). Sem rede.
"""
import os, csv, io, zipfile, json, statistics

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(ROOT, "cache_camara")
TSE = os.path.join(ROOT, "cache_tse")

REGIAO = {
    "AC":"N","AP":"N","AM":"N","PA":"N","RO":"N","RR":"N","TO":"N",
    "AL":"NE","BA":"NE","CE":"NE","MA":"NE","PB":"NE","PE":"NE","PI":"NE","RN":"NE","SE":"NE",
    "DF":"CO","GO":"CO","MT":"CO","MS":"CO",
    "ES":"SE","MG":"SE","RJ":"SE","SP":"SE",
    "PR":"S","RS":"S","SC":"S",
}


def zopen(nome):
    z = zipfile.ZipFile(os.path.join(TSE, nome + ".zip"))
    arq = next(n for n in z.namelist() if "BRASIL" in n and n.endswith(".csv"))
    return csv.DictReader(io.TextIOWrapper(z.open(arq), encoding="latin1"),
                          delimiter=";", quotechar='"')


def patrimonio_por_sq():
    soma = {}
    for r in zopen("bem_candidato"):
        sq = r.get("SQ_CANDIDATO")
        try:
            v = float(r.get("VR_BEM_CANDIDATO", "0").replace(".", "").replace(",", "."))
        except Exception:
            v = 0.0
        if sq:
            soma[sq] = soma.get(sq, 0.0) + v
    return soma


def gerar_tse():
    """Todos os candidatos a DEPUTADO FEDERAL no TSE 2022 (dado de origem)."""
    patr = patrimonio_por_sq()
    cols = ["cpf","sq_candidato","nome","partido","federacao","uf","regiao",
            "idade","genero","grau_instrucao","cor_raca","ocupacao",
            "patrimonio_total","situacao_eleicao"]
    out = os.path.join(ROOT, "tse.csv")
    porcpf = {}
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in zopen("consulta_cand"):
            if r.get("DS_CARGO") != "DEPUTADO FEDERAL":
                continue
            cpf = r["NR_CPF_CANDIDATO"]; sq = r.get("SQ_CANDIDATO", "")
            try:
                idade = 2022 - int(r["DT_NASCIMENTO"].split("/")[-1])
            except Exception:
                idade = ""
            linha = {
                "cpf": cpf, "sq_candidato": sq, "nome": r.get("NM_CANDIDATO",""),
                "partido": r.get("SG_PARTIDO",""),
                "federacao": r.get("SG_FEDERACAO","") or "SEM",
                "uf": r.get("SG_UF",""), "regiao": REGIAO.get(r.get("SG_UF",""),""),
                "idade": idade, "genero": r.get("DS_GENERO",""),
                "grau_instrucao": r.get("DS_GRAU_INSTRUCAO",""),
                "cor_raca": r.get("DS_COR_RACA",""), "ocupacao": r.get("DS_OCUPACAO",""),
                "patrimonio_total": round(patr.get(sq, 0.0), 2),
                "situacao_eleicao": r.get("DS_SIT_TOT_TURNO",""),
            }
            w.writerow(linha)
            porcpf[cpf] = linha
    print(f"tse.csv -> {sum(1 for _ in open(out))-1} linhas")
    return porcpf


def gerar_camara():
    """Deputados eleitos + atuação medida na API da Câmara (com CPF)."""
    rot = list(csv.DictReader(open(os.path.join(ROOT, "rotulo_deputados.csv"))))
    cols = ["idDeputado","nome","cpf","partido","uf","n_votacoes","pct_alinhamento_gov"]
    out = os.path.join(ROOT, "camara.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for d in rot:
            dep = json.load(open(os.path.join(CACHE, f"dep_{d['idDeputado']}.json")))
            w.writerow({
                "idDeputado": d["idDeputado"], "nome": d["nome"],
                "cpf": dep["dados"]["cpf"], "partido": d["partido"], "uf": d["uf"],
                "n_votacoes": d["n_votacoes"],
                "pct_alinhamento_gov": d["pct_alinhamento_gov"],
            })
    print(f"camara.csv -> {sum(1 for _ in open(out))-1} linhas")
    return rot


def gerar_dataset(tse_por_cpf, rot):
    """Junção final por CPF: features TSE + rótulo Câmara."""
    cols = ["idDeputado","nome","cpf","partido","federacao","uf","regiao","idade",
            "genero","grau_instrucao","cor_raca","ocupacao","patrimonio_total",
            "pct_alinhamento_gov","n_votacoes","rotulo"]
    out = os.path.join(ROOT, "dataset.csv")
    n = 0
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for d in rot:
            dep = json.load(open(os.path.join(CACHE, f"dep_{d['idDeputado']}.json")))
            cpf = dep["dados"]["cpf"]; tf = tse_por_cpf.get(cpf)
            if not tf:
                continue
            pct = float(d["pct_alinhamento_gov"])
            w.writerow({
                "idDeputado": d["idDeputado"], "nome": d["nome"], "cpf": cpf,
                "partido": tf["partido"], "federacao": tf["federacao"], "uf": tf["uf"],
                "regiao": tf["regiao"], "idade": tf["idade"], "genero": tf["genero"],
                "grau_instrucao": tf["grau_instrucao"], "cor_raca": tf["cor_raca"],
                "ocupacao": tf["ocupacao"], "patrimonio_total": tf["patrimonio_total"],
                "pct_alinhamento_gov": round(pct, 4), "n_votacoes": d["n_votacoes"],
                "rotulo": "governista" if pct >= 0.5 else "oposicao",
            })
            n += 1
    print(f"dataset.csv -> {n} linhas")


if __name__ == "__main__":
    tse = gerar_tse()
    rot = gerar_camara()
    gerar_dataset(tse, rot)
