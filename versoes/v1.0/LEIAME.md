# Monitoramento-TSE-BR — versão 1.0 (dados do artigo sobre o 1º turno)

**Estudo:** SANTOS, Celso de Oliveira. *Como explicar a letargia do TSE nas eleições mais judicializadas da história do Brasil?* Monitor Eleitoral, 2026.

Esta é a versão congelada dos dados que fundamentam o artigo. Os pacotes do TSE são substituídos diariamente na fonte; os arquivos abaixo são os que estavam disponíveis nas datas indicadas e não serão alterados.

## Conteúdo

| Pasta | Conteúdo | Data da extração |
|---|---|---|
| `brutos/sig/<ano>/processos_eleitorais_<ano>.csv` | Processos eleitorais (exportação do SIG/TSE, grupo Processual) | carga do TSE de 14/10/2026 (04h30 a 06h01) |
| `brutos/sig/<ano>/processos_eleitorais_decisoes_<ano>.csv` | Decisões (data, tipo e autor) | carga de 14/10/2026 |
| `brutos/sig/<ano>/processos_eleitorais_recursos_<ano>.csv` | Recursos | carga de 14/10/2026 |
| `brutos/sig/<ano>/processos_eleitorais_partes_<ano>.zip` | Partes (pacote original do Portal de Dados Abertos do TSE) | gerado pelo TSE em 15/10/2026 |
| `brutos/datajud/datajud_tse_2026-10-15.jsonl.gz` | Respostas da API Pública do DataJud (CNJ) para os processos do TSE | consulta de 15/10/2026 |
| `brutos/datajud/numeros_datajud.csv` | Lista de processos consultados no DataJud | 15/10/2026 |
| `derivados/` | Tabelas do estudo (volume, velocidade TSE × TREs, campanhas, relatores, liminares, processo a processo) | geradas a partir dos brutos acima |
| `planilhas/` | Planilha de seletividade (processo a processo e testes), velocidade por relator, composição do TSE e amostra para verificação no PJe | 15/10/2026 |

Os CSV do SIG usam separador `;` e codificação latin-1. A integridade de cada arquivo pode ser conferida pelo `SHA256SUMS.txt`.

## Como reproduzir

O código está no repositório https://github.com/celsodeos/Monitoramento-TSE-BR, na versão marcada como `v1.0-artigo1`. Copie os brutos para `dados/brutos/<ano>/{processo,decisoes,partes}/` (descompactando as partes) e o arquivo do DataJud para `dados/brutos/datajud/`, e rode `python analise/indicadores.py`. As tabelas resultantes coincidem com as de `derivados/`.

## Fontes

- Tribunal Superior Eleitoral. Portal de Dados Abertos, grupo Processual. https://dadosabertos.tse.jus.br/
- Conselho Nacional de Justiça. API Pública do DataJud. https://datajud-wiki.cnj.jus.br/api-publica/

## Autor

Celso de Oliveira Santos — Lattes: http://lattes.cnpq.br/8981314196162452 · ORCID: https://orcid.org/0000-0002-8759-0538 · osantoscelso@gmail.com
