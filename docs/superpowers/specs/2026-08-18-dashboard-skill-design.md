# Dashboard de Referência — Design (v1.2.0)

**Data:** 2026-08-18 · **Aprovado por:** Luis Roquette (abordagem "Gerador Python + HTML")

## Goal

Entregar o consumidor de referência do contrato de métricas (`references/nucleo/metricas.md`): um gerador determinístico (stdlib puro, zero dependências, sem servidor) que transforma um export JSON das duas camadas de armazenamento num dashboard HTML single-file que responde as cinco perguntas do contrato.

## Arquitetura

```
dashboard/dados-exemplo.json   (export de exemplo — forma canônica do input)
scripts/gerar-dashboard.py     (valida input → gera HTML; --self-test com regressão)
dashboard/index.html           (gerado, commitado — abre offline, zero JS)
```

O dashboard não se conecta a banco e não re-implementa o join de atribuição: o export resolve os attribution ids → `slug` antes de emitir o JSON. A dashboard consome o resultado. O formato do input é documentado no próprio README da skill (seção nova "Dashboard de referência").

## Contrato de entrada (`dados.json`)

```json
{
  "links": [
    {"slug": "lp-treinamento", "name": "Treinamento", "destination_url": "https://...",
     "utm_source": "cfgauss", "utm_medium": "referral", "utm_campaign": "lp-treinamento",
     "is_active": true, "expires_at": null, "saude": "healthy"}
  ],
  "daily_aggregates": [
    {"slug": "lp-treinamento", "day": "2026-08-18", "clicks": 12, "last_clicked_at": "2026-08-18T21:00:00Z"}
  ],
  "events": [
    {"slug": "lp-treinamento", "clicked_at": "2026-08-18T21:00:00Z",
     "utm_source": "cfgauss", "utm_medium": "referral", "utm_campaign": "lp-treinamento",
     "referrer_host": "instagram.com", "device": "mobile"}
  ],
  "conversions": [
    {"slug": "lp-treinamento", "type": "lead", "converted_at": "2026-08-18T21:05:00Z"}
  ]
}
```

- `saude`: `healthy | warning | broken` (colunas de saúde da tabela de links).
- `day` no fuso de negócio (America/Sao_Paulo na referência).
- Eventos carregam **snapshot** de UTM — o breakdown de origem usa o snapshot, nunca o UTM atual do link (história imutável).

## Regras codificadas (determinísticas)

1. **`report_date` = maior `day` presente em `daily_aggregates`** — nunca o relógio da máquina; o mesmo input gera o mesmo HTML para sempre.
2. **Ausência ≠ zero:** dia sem linha no agregado → `—`; linha com `clicks: 0` → `0`.
3. **Calendar-fill:** janelas 7/30/90 terminando em `report_date`; todo dia da janela aparece.
4. **Status derivado com precedência:** `pausado` (!is_active) > `expirado` (expires_at < report_date) > `quebrado` (saude broken) > `ativo`. Warning não muda o status (vira alerta visual).
5. **Conversões por slug** por tipo (`lead` | `purchase`).
6. **Export CSV dos links** embutido como `data:` URI no HTML — zero JavaScript, botão funciona offline.
7. Input inválido → erro nomeado + exit 1 (nunca HTML parcial).

## As cinco perguntas → cinco blocos

| Pergunta | Bloco no HTML |
|---|---|
| Cliques por link, por período | Top links com colunas 7/30/90 |
| Cliques por origem/canal | Breakdown por snapshot UTM (source/medium) |
| Conversões por link | Tabela com lead/purchase por slug |
| Status dos links | Tabela com estado derivado + warning visual |
| Série temporal | Grid calendar-filled de 30 dias (top 5 links) + totais 7/30/90 |

## Self-test (padrão do validator)

`python3 scripts/gerar-dashboard.py --self-test` — 8 casos de regressão, determinísticos, exit 1 se qualquer um falhar:

1. Dia ausente → `—`; dia com zero → `0` (ausência ≠ zero).
2. Calendar-fill: janela de 30 dias com agregados cobrindo só 3 dias → 30 células.
3. Editar UTM do link no input → breakdown de origem inalterado (snapshot vence).
4. Filtro 7/30/90 respeitado (contagem difere entre janelas).
5. Conversão conta por slug; link sem conversão → zero explícito, não ausente.
6. Precedência de status (pausado vence expirado vence quebrado).
7. Input inválido → erro nomeado, exit 1.
8. CSV embutido decodifica para as linhas esperadas dos links.

## Visual

Paleta do padrão visual do repo (ink `#1A1524`, lilás `#C9A7FF`, brand `#7B2FBE`), fonte Inter via system stack (sem CDN — offline), barras em CSS puro. UI em inglês (corpo do repo é inglês).

## Arquivos e versionamento

- Criar: `scripts/gerar-dashboard.py`, `dashboard/dados-exemplo.json`, `dashboard/index.html` (gerado), seção no README (estrutura + "Dashboard de referência").
- Alterar: `CHANGELOG.md` (`[1.2.0]` — MINOR, nova capability opcional), árvore de arquivos no README.
- Release: tag `v1.2.0` + GitHub Release + PR → main, conforme `references/versionamento.md`.

## Fora de escopo

- Dashboard de produção do cfgauss-site (o painel `/admin/marketing/tracking-links` já existe — a skill entrega o contrato portátil).
- Heurísticas de bot por canal (regra explícita da skill: é preocupação de integração).
- Export CSV de eventos granulares (proibido pelo contrato — privacidade).
