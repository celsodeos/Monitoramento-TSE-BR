# Monitoramento-TSE-BR — versão 2.0-2T (dados do 2º turno)

**Estudo:** SANTOS, Celso de Oliveira. *Estatísticas – Judicialização das Eleições e Resposta do TSE: 2º turno.* Monitor Eleitoral, 2026.

Versão congelada dos dados do 2º turno das eleições presidenciais de 2018, 2022 e 2026. Os pacotes do TSE são substituídos diariamente na fonte; os arquivos abaixo são os que estavam disponíveis na data indicada e não serão alterados. **O 2º turno de 2026 ainda estava em curso** (votação em 25/10/2026): os números de 2026 descrevem as ações autuadas até 2026-10-16 (222 ações), com a carga do TSE de 2026-10-18 05:30:24.

A versão do 1º turno (v1.0-1T) continua em `versoes/v1.0/`, DOI 10.5281/zenodo.23441914.

## Conteúdo

| Pasta | Conteúdo |
|---|---|
| `brutos/<ano>/processo_eleitoral_<ano>.zip` | Processos eleitorais (pacote original do Portal de Dados Abertos do TSE, grupo Processual) |
| `brutos/<ano>/processos_eleitorais_decisoes_<ano>.zip` | Decisões (data, tipo e autor) |
| `brutos/<ano>/processos_eleitorais_partes_<ano>.zip` | Partes |
| `derivados/2t_volume.csv` | Ações entre as campanhas presidenciais no TSE, por eleição e autora |
| `derivados/2t_velocidade.csv` | Decididas em até 3 e 10 dias; testes de Fisher e Mantel-Haenszel |
| `derivados/2t_relatores.csv` | 2026: ações e velocidade por relator efetivo e campanha ré |
| `derivados/2t_meta.json` | Data da carga, última autuação considerada, teste qui-quadrado de distribuição entre relatores |
| `derivados/processos_campanhas.csv` | Processo a processo (1º e 2º turnos) |

A integridade de cada arquivo pode ser conferida pelo `SHA256SUMS.txt` (`sha256sum -c SHA256SUMS.txt`).

## Definições

- Período: do dia seguinte ao 1º turno até o dia do 2º turno (CF, art. 77, *caput*; Lei 9.504/1997, art. 2º, § 1º): 08 a 28/10/2018, 03 a 30/10/2022 e 05 a 25/10/2026.
- Universo: ações originárias do TSE (representação, direito de resposta, notícia de irregularidade em propaganda, AIJE, tutela cautelar antecedente) com uma campanha presidencial principal no polo ativo e a outra no passivo.
- Prazo: da autuação ao primeiro ato decisório (decisão, sentença ou acórdão). Três dias aproximam as 72 horas do art. 58, § 2º, da Lei 9.504/1997. Em 2026, só entram no cálculo as ações que já tinham 3 (ou 10) dias de tramitação na data da carga.
- Relator efetivo: autor da primeira decisão monocrática registrada no SIG; sem decisão, o relator atual.

## Como reproduzir

Código: https://github.com/celsodeos/Monitoramento-TSE-BR, versão `v2.0-2T`. Descompacte os brutos em `dados/brutos/<ano>/{processo,decisoes,partes}/` e rode `python analise/indicadores.py --sem-historico` e `python analise/segundo_turno.py`.

## Fontes

- Tribunal Superior Eleitoral. Portal de Dados Abertos, grupo Processual. https://dadosabertos.tse.jus.br/

## Autor

Celso de Oliveira Santos — Lattes: http://lattes.cnpq.br/8981314196162452 · ORCID: https://orcid.org/0000-0002-8759-0538 · osantoscelso@gmail.com
