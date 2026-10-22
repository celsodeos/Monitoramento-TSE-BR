# Monitor de menções em vídeo

Rotina interna (não publica nada em `docs/`). A cada 6 horas o workflow
`.github/workflows/monitor_midia.yml` lê os vídeos recentes dos canais de `canais.yml`,
baixa as legendas em português (manuais ou automáticas) e procura "Nunes Marques"
a até 60 s de: estudo, levantamento, UERJ, Celso, judicialização/judicializadas,
Lauro Jardim (ocorrência **forte**) ou TSE, lento/lentidão (ocorrência **fraca**).
"Celso de Oliveira Santos" e "Monitor Eleitoral" contam sozinhos.

- `relatorios/AAAA-MM-DD.md` — relatório do dia, com link no minuto exato e trecho da legenda
- `mencoes.csv` — acumulado
- `estado.json` — vídeos já lidos (os sem legenda são retentados até 8 vezes)

Rodar à mão (aba Actions → "Monitor de menções em vídeo" → Run workflow) ou no
computador: `pip install -r monitor_midia/requirements.txt` e
`python monitor_midia/monitorar.py --video ID_DO_VIDEO`.

**Bloqueio do YouTube.** O YouTube costuma recusar servidores de nuvem ("Sign in to
confirm you're not a bot"). Se o job falhar por isso, crie o secret `YT_COOKIES` com o
conteúdo de um `cookies.txt` exportado do navegador (de preferência de uma conta
secundária), ou rode o script no computador.

Legendas automáticas erram nomes: confira sempre o trecho no vídeo antes de citar.
