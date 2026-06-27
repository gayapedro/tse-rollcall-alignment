#!/usr/bin/env python3
"""
Coleta o RÓTULO (linha de atuação) a partir da Câmara dos Deputados.

Estratégia:
  1. Lista votações de plenário (PLEN) numa janela de datas.
  2. Para cada votação, baixa a orientação de bancada; mantém apenas as que têm
     orientação do bloco "Governo" com voto direcional (Sim/Não/Obstrução).
  3. Para cada votação mantida, baixa o voto nominal de cada deputado.
  4. Agrega por deputado: pct de votos alinhados com a orientação do Governo.
  5. Salva tudo em cache (JSON) para re-execução barata.

Saída: rotulo_deputados.csv  (idDeputado, nome, partido, uf, n_votacoes,
        pct_alinhamento_gov)
"""
import urllib.request, json, calendar, os, csv, time, sys

B = "https://dadosabertos.camara.leg.br/api/v2"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache_camara")
os.makedirs(CACHE, exist_ok=True)

ANOS = [2023, 2024]          # janela do mandato (expandir se precisar de sinal)
MIN_VOTOS = 50               # votação precisa ser nominal de verdade


def get(path, cache_key=None):
    """GET com cache em disco. cache_key=None => não cacheia (listas voláteis)."""
    fp = os.path.join(CACHE, cache_key + ".json") if cache_key else None
    if fp and os.path.exists(fp):
        try:
            with open(fp) as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            os.remove(fp)  # cache corrompido (escrita interrompida) -> refaz
    url = B + path
    for tentativa in range(4):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            data = json.load(urllib.request.urlopen(req, timeout=40))["dados"]
            if fp:
                tmp = fp + ".tmp"
                with open(tmp, "w") as f:
                    json.dump(data, f)
                os.replace(tmp, fp)  # escrita atômica: nunca deixa arquivo parcial
            return data
        except Exception as e:
            if tentativa == 3:
                print(f"  ! falha {url}: {e}", file=sys.stderr)
                return None
            time.sleep(1.5 * (tentativa + 1))


def listar_votacoes_plen():
    ids = []
    for ano in ANOS:
        for m in range(1, 13):
            last = calendar.monthrange(ano, m)[1]
            pg = 1
            while True:
                d = get(f"/votacoes?dataInicio={ano}-{m:02d}-01"
                        f"&dataFim={ano}-{m:02d}-{last:02d}&itens=100&pagina={pg}")
                if not d:
                    break
                ids += [v["id"] for v in d if v.get("siglaOrgao") == "PLEN"]
                pg += 1
                if pg > 20:
                    break
            print(f"  listado {ano}-{m:02d}: {len(ids)} PLEN acumulados", flush=True)
    return ids


def main():
    print("listando votações PLEN...", flush=True)
    plen = listar_votacoes_plen()
    print(f"  {len(plen)} votações de plenário em {ANOS}", flush=True)

    # acumula por deputado: [alinhados, total]
    agg = {}     # idDep -> [alinhados, total]
    meta = {}    # idDep -> (nome, partido, uf)
    usadas = 0

    for i, vid in enumerate(plen):
        ori = get(f"/votacoes/{vid}/orientacoes", cache_key=f"ori_{vid}")
        if not ori:
            continue
        gov = next((o for o in ori if o.get("siglaPartidoBloco") == "Governo"), None)
        opo = next((o for o in ori if o.get("siglaPartidoBloco") == "Oposição"), None)
        if not gov or gov.get("orientacaoVoto") not in ("Sim", "Não", "Obstrução"):
            continue
        # só votações CONTESTADAS: Governo e Oposição com orientações divergentes.
        # (votações consensuais inflam o alinhamento e não discriminam linha de atuação)
        if not opo or opo.get("orientacaoVoto") == gov.get("orientacaoVoto"):
            continue
        votos = get(f"/votacoes/{vid}/votos", cache_key=f"votos_{vid}")
        if not votos or len(votos) < MIN_VOTOS:
            continue
        usadas += 1
        alvo = gov["orientacaoVoto"]
        for v in votos:
            dep = v["deputado_"]
            did = dep["id"]
            agg.setdefault(did, [0, 0])
            meta[did] = (dep["nome"], dep["siglaPartido"], dep["siglaUf"])
            agg[did][1] += 1
            if v["tipoVoto"] == alvo:
                agg[did][0] += 1
        if (i + 1) % 100 == 0:
            print(f"  ...{i+1}/{len(plen)} varridas, {usadas} úteis", flush=True)

    print(f"votações úteis (Governo + nominal): {usadas}", flush=True)
    print(f"deputados com voto registrado: {len(agg)}", flush=True)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rotulo_deputados.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idDeputado", "nome", "partido", "uf",
                    "n_votacoes", "pct_alinhamento_gov"])
        for did, (al, tot) in sorted(agg.items()):
            nome, part, uf = meta[did]
            w.writerow([did, nome, part, uf, tot, round(al / tot, 4) if tot else 0])
    print(f"OK -> {out}", flush=True)


if __name__ == "__main__":
    main()
