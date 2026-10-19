# Judicialização das Eleições e Resposta do TSE em Eleições Presidenciais

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23441914.svg)](https://doi.org/10.5281/zenodo.23441914)

**Como explicar a letargia do TSE nas eleições mais judicializadas da história do Brasil?**

Estudo e base de dados sobre o contencioso de propaganda e campanha no Tribunal Superior Eleitoral (TSE) e nos Tribunais Regionais Eleitorais (TREs) no 1º turno das eleições gerais de 2018, 2022 e 2026. O repositório reúne o código de coleta e tratamento, os dados derivados, a página pública de visualização e o histórico datado de cada extração, para que os resultados possam ser conferidos e reproduzidos.

**Páginas públicas:** [1º turno](https://celsodeos.github.io/Monitoramento-TSE-BR/) · [2º turno](https://celsodeos.github.io/Monitoramento-TSE-BR/segundo-turno/)

Autor: **Celso de Oliveira Santos** · Projeto Monitor Eleitoral

---

## O que o estudo mede

1. **Volume.** Quantos processos foram autuados, de 20/07 ao dia do 1º turno, em toda a Justiça Eleitoral e, no TSE, nas classes ligadas à campanha.
2. **Velocidade.** A proporção de processos com a primeira decisão, sentença ou acórdão em até 3 e em até 10 dias da autuação, no TSE e nos TREs. Três dias aproximam as 72 horas do art. 58, § 2º, da Lei 9.504/1997.
3. **Velocidade por campanha e por gestão.** A comparação entre as ações ajuizadas por uma das duas campanhas presidenciais principais contra a outra, nas presidências de Rosa Weber (2018), Alexandre de Moraes (2022) e Nunes Marques (2026).
4. **Gabinetes.** O mesmo indicador em 2026 por relator efetivo, isto é, por quem assinou a primeira decisão.
5. **Liminares.** A proporção de ações com decisão sobre o pedido liminar, a partir dos andamentos do DataJud.

### Principais resultados (dados extraídos em 14 e 15/10/2026)

| Indicador | 2018 | 2022 | 2026 |
|---|---:|---:|---:|
| Processos no TSE no recorte de campanha | 467 | 518 | 1.206 |
| TSE: decididos em até 3 dias | 40,9% | 28,6% | 11,2% |
| TREs: decididos em até 3 dias | 66,5% | 71,4% | 64,6% |

- **Velocidade por campanha.** Em 2018 e em 2022 não há diferença estatisticamente significativa entre as campanhas. Em 2026 a diferença bruta em até 3 dias é significativa (13,0% contra 5,8%; Fisher, p = 0,022). Ela deixa de ser quando se compara cada relator com ele mesmo (Mantel-Haenszel, p = 0,43): a diferença vem da distribuição dos processos entre os gabinetes.
- **Liminares em 2026.** Houve decisão sobre a liminar em 31,7% das ações de Flávio Bolsonaro contra Lula e em 9,0% das ações de Lula contra Flávio Bolsonaro. A diferença se mantém controlando relator e classe (Mantel-Haenszel, p = 0,008).
- **Liminares em 2022.** Sob Moraes, a diferença não é significativa. Em 2018 o DataJud não traz esses processos.

Os resultados são descritivos e estatísticos. Eles não informam, por si sós, a intenção dos julgadores nem o teor das decisões. Essa verificação está sendo feita em amostra de autos no PJe (ver "Próximas etapas").

---

## Fontes de dados

| Fonte | O que fornece | Acesso |
|---|---|---|
| Portal de Dados Abertos do TSE, grupo "Processual" (SIG) | Processos eleitorais, decisões (com data, tipo e autor) e partes, por eleição | <https://dadosabertos.tse.jus.br/> |
| API Pública do DataJud (CNJ) | Andamentos processuais, codificados pela Tabela Processual Unificada (TPU) | <https://datajud-wiki.cnj.jus.br/api-publica/> |
| Consulta Pública do PJe do TSE | Petições e decisões, para verificação manual por amostra | <https://consultaunificadapje.tse.jus.br/> |

Os arquivos de partes podem ser baixados diretamente em
`https://cdn.tse.jus.br/estatistica/sead/odsele/processual/processos_eleitorais_partes_{ano}.zip`.

---

## Método

- **Recorte temporal.** Processos autuados de 20/07, início do prazo das convenções partidárias (Lei 9.504/1997, art. 8º), até o dia do 1º turno: 07/10/2018, 02/10/2022 e 04/10/2026.
- **Unidade de análise.** O par processo × instância. Para recursos, o prazo conta da distribuição.
- **Prazo.** Dias da autuação ao primeiro ato decisório (decisão, sentença ou acórdão), sem contar despachos. Processos sem decisão contam como não decididos.
- **Recorte de campanha no TSE.** Representações, direitos de resposta, notícias de irregularidade em propaganda, tutelas cautelares antecedentes, ações cassatórias (AIJE, AIME, RCED) e recursos, excluídos os recursos relativos a registro de candidatura.
- **Identificação das campanhas.** Pelas partes principais de cada polo: candidatos a presidente e vice, coligação ou federação nacional, partido nacional e CNPJ de campanha. Ações de aliados e terceiros ficam fora da comparação entre campanhas.
- **Relator efetivo.** O autor da primeira decisão monocrática registrada no SIG (campo "Autor da decisão"). Em 2026 ele coincide com o relator atual em 174 de 178 processos com decisão.
- **Liminares.** Códigos TPU 339 (liminar concedida), 892 (concedida em parte) e 792 (não concedida), entre os processos localizados no DataJud.
- **Testes.** Teste exato de Fisher para a comparação bruta e Mantel-Haenszel estratificado por relator efetivo e classe processual.

### Limitações

- **Cobertura do DataJud.** Em 2026 o DataJud localizou cerca de 64% dos processos do recorte, com atraso de atualização. Em 2018 praticamente não há ações originárias do TSE na base.
- **O que as bases não informam.** Nem o SIG nem o DataJud dizem se houve pedido liminar nem qual foi o teor da decisão.
- **Relator.** O SIG registra o relator atual, depois de redistribuições. Por isso o estudo usa o autor da decisão.
- **Dados de 2026.** Refletem a carga de 14/10/2026. Os números mudam à medida que o TSE registra novas decisões, e o histórico deste repositório documenta essas mudanças.

---

## Estrutura do repositório

```
coleta/
  baixar_sig.py         baixa os pacotes do grupo Processual do TSE (processos, decisões, partes)
  coletar_datajud.py    consulta a API Pública do DataJud, processo a processo
  datajud_tres.py       coleta semanal dos processos dos TREs no DataJud
analise/
  indicadores.py        calcula os indicadores e os testes e grava as tabelas
  enviar_supabase.py    envia as tabelas ao banco no Supabase
  plataformas.py        ações contra plataformas digitais e meios de comunicação
  segundo_turno.py      indicadores do 2º turno (velocidade, gabinetes, liminares)
dados/
  brutos/               arquivos originais do TSE e respostas do DataJud (não versionados)
  derivados/            tabelas do estudo (CSV) e lista de processos para o DataJud
  historico/AAAA-MM-DD/ fotografia de cada carga do TSE, para acompanhar mudanças
docs/
  index.html            página pública do 1º turno (GitHub Pages)
  segundo-turno/        página pública do 2º turno
  dados/                cópia das tabelas lida pela página
.github/workflows/
  coleta.yml            rotina diária de coleta e cálculo
```

### Tabelas em `dados/derivados/`

| Arquivo | Conteúdo |
|---|---|
| `volume.csv` | Processos autuados no recorte, na Justiça Eleitoral e no TSE |
| `tse_tres.csv` | Decididos em até 3 e 10 dias, TSE e TREs |
| `campanhas.csv` | Velocidade por campanha e gestão, com testes de Fisher e Mantel-Haenszel |
| `relatores_2026.csv` | Velocidade e liminares por relator efetivo em 2026 |
| `liminares.csv` | Liminar apreciada e concedida, por campanha (DataJud) |
| `processos_campanhas.csv` | Um processo por linha: ações entre as campanhas, 1º e 2º turnos |
| `numeros_datajud_tse.csv` | Lista de processos consultada no DataJud |
| `plataformas.csv` | Processos com plataforma digital no polo passivo, por empresa, eleição e instância |
| `plataformas_tse.csv` | TSE: liminares e desfechos por plataforma (DataJud) |
| `midia.csv`, `midia_empresas.csv` | Processos contra veículos de comunicação e os veículos mais acionados |
| `2t_volume.csv`, `2t_velocidade.csv`, `2t_relatores.csv`, `2t_liminares.csv`, `2t_meta.json` | 2º turno: volume, velocidade (só ações já observáveis), distribuição e velocidade por gabinete, liminares |
| `meta.json` | Data da carga do TSE e da geração das tabelas |

## Como reproduzir

Requisitos: Python 3.10 ou superior.

```bash
pip install -r requirements.txt
python coleta/baixar_sig.py --anos 2018 2022 2026
python analise/indicadores.py --sem-historico           # gera a lista para o DataJud
python coleta/coletar_datajud.py --entrada dados/derivados/numeros_datajud_tse.csv \
       --saida dados/brutos/datajud/tse.jsonl.gz --falhas dados/brutos/datajud/falhas.csv
python analise/indicadores.py                           # tabelas finais e histórico
```

O script do DataJud usa a chave pública divulgada pelo CNJ e pode ser interrompido e retomado: os processos já consultados são pulados.

## Atualização automática

A rotina `.github/workflows/coleta.yml` roda todo dia às 6h (horário de Brasília) e pode ser disparada à mão na aba **Actions**. Ela baixa os pacotes do TSE, consulta o DataJud, recalcula as tabelas e registra um commit quando algo mudou. Cada carga do TSE ganha uma pasta em `dados/historico/`. Para ver o que mudou entre duas cargas, basta comparar as pastas ou consultar o histórico de commits.

## Banco de dados (Supabase)

As mesmas tabelas ficam também num banco PostgreSQL no Supabase (projeto `monitoramento-tse-br`, região São Paulo), com uma linha em `cargas` para cada extração do TSE. Isso permite consultar o histórico com SQL e comparar cargas.

| Tabela | Conteúdo |
|---|---|
| `cargas` | Cada extração (data da carga do TSE) |
| `volume`, `tse_tres`, `campanhas`, `liminares`, `relatores` | As tabelas de `dados/derivados/`, por carga |
| `processos_campanhas` | Um processo por linha, por carga |
| `ultima_carga` (visão) | A carga mais recente |

A leitura é pública (dados abertos), pela API REST do Supabase:

```
https://wmtjybayqqpjiayjvswd.supabase.co/rest/v1/liminares?select=*&apikey=<chave publicável>
```

A rotina diária envia cada nova carga ao banco (`analise/enviar_supabase.py`), desde que o repositório tenha os segredos `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` em **Settings → Secrets and variables → Actions**. Sem eles, esse passo é ignorado.

### Coleta semanal dos TREs

A rotina `.github/workflows/tres_semanal.yml` roda aos domingos às 7h (horário de Brasília) e consulta no DataJud os cerca de 28 mil processos de campanha dos TREs (`coleta/datajud_tres.py`). O resultado fica em `dados/derivados/datajud_tres_status.csv`, um processo por linha, e o resumo por eleição em `dados/derivados/liminares_tres.csv`. A cada semana são consultados os processos novos, todos os da eleição mais recente e os ainda não localizados. Se o tempo máximo da execução for atingido, a coleta para, salva o que obteve e continua na execução seguinte.

## Versões congeladas

Os dados do TSE mudam a cada carga. Para que os resultados publicados possam ser conferidos, cada artigo tem uma versão congelada, com os arquivos brutos usados, as tabelas e as somas de verificação (SHA-256):

| Versão | Artigo | Dados | Página e DOI |
|---|---|---|---|
| `v1.0-1T` | *Como explicar a letargia do TSE nas eleições mais judicializadas da história do Brasil?* (1º turno) | carga do TSE de 14/10/2026; DataJud de 15/10/2026 — [`versoes/v1.0/`](versoes/v1.0/) | [v1](https://celsodeos.github.io/Monitoramento-TSE-BR/v1/) · DOI [10.5281/zenodo.23441914](https://doi.org/10.5281/zenodo.23441914) |
| `v.1.0-2T` (pasta `v2.0-2T`) | *Estatísticas – Judicialização das Eleições e Resposta do TSE: 2º turno* (2º turno de 2026 em curso) | carga do TSE de 18/10/2026 — [`versoes/v2.0-2T/`](versoes/v2.0-2T/) | [v2](https://celsodeos.github.io/Monitoramento-TSE-BR/segundo-turno/v2/) · DOI [10.5281/zenodo.23455041](https://doi.org/10.5281/zenodo.23455041) |

Os brutos da v1.0 reproduzem exatamente as tabelas do artigo com o código da tag `v1.0-1T` (instruções em `versoes/v1.0/LEIAME.md`).

## Visualização

A página em `docs/` apresenta os gráficos e as tabelas do estudo e abre em qualquer navegador, sem login. Ela lê as tabelas de `docs/dados/`, então se atualiza junto com a coleta. Os números citados no texto da página referem-se à carga de 14/10/2026.

---

## Referências normativas

- Constituição Federal, art. 77 (dois turnos nas eleições presidenciais).
- Lei 9.504/1997 (Lei das Eleições):
  - art. 2º, § 1º (2º turno no último domingo de outubro);
  - art. 8º (convenções de 20/07 a 05/08);
  - art. 58, § 2º (direito de resposta: decisão em até 72 horas);
  - art. 96, §§ 3º e 4º (juízes auxiliares e recurso ao Plenário).
- Resolução TSE nº 23.547/2017 (representações e direito de resposta nas eleições de 2018), art. 2º.
- Resolução TSE nº 23.608/2019 (representações, reclamações e pedidos de direito de resposta), art. 2º, II e § 4º.
- Portaria TSE nº 235, de 20/05/2026 (DJE-TSE nº 81, de 22/05/2026).

## Próximas etapas

- Verificação, no PJe, de uma amostra estratificada de 80 processos: pedido liminar, distribuição por prevenção, destino da liminar e referendo do Plenário.
- Liminares do 2º turno de 2026, à medida que o DataJud registrar os andamentos.
- Ações contra meios de comunicação e plataformas digitais.

## Como citar

> SANTOS, Celso de Oliveira. *Como explicar a letargia do TSE nas eleições mais judicializadas da história do Brasil?* Monitor Eleitoral, 2026. Dados e código (v1.0-1T): Zenodo, 2026. DOI: <https://doi.org/10.5281/zenodo.23441914>.

## Autor

**Celso de Oliveira Santos**: advogado e consultor, professor de Direito e pesquisador em estágio pós-doutoral no Programa de Pós-Graduação da Faculdade de Direito da UERJ. Mestre pela USP e doutor pela UERJ em Direito Internacional e Comparado.

- Currículo Lattes: <http://lattes.cnpq.br/8981314196162452>
- ORCID: <https://orcid.org/0000-0002-8759-0538>
- Contato: osantoscelso@gmail.com

## Licença

A definir. Sugestão: código sob licença MIT; dados derivados e textos sob CC BY 4.0. Os dados de origem são públicos e pertencem às respectivas fontes (TSE e CNJ).
