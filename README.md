# devsecops-scan

Pipeline de **DevSecOps** no GitHub Actions que executa **SAST, SCA e DAST** automaticamente a cada `push` / `pull request`, bloqueando a entrega (FAIL) quando encontra problemas de segurança.

> ⚠️ A aplicação em `src/` é **propositalmente vulnerável** (uso didático) para que as ferramentas tenham o que detectar.

---

## 1. Sobre o projeto

Uma API Flask minúscula (`src/app.py`) com quatro rotas (`/`, `/greet`, `/user`, `/ping`) que contém vulnerabilidades típicas do OWASP Top 10:

| Vulnerabilidade | Onde | Categoria OWASP |
|---|---|---|
| SQL Injection | `/user` | A03 – Injection |
| XSS refletido | `/greet` | A03 – Injection |
| Command Injection | `/ping` | A03 – Injection |
| Segredo hardcoded | `SECRET_KEY` | A02/A05 |
| MD5 para senhas | `ADMIN_HASH` | A02 – Cryptographic Failures |
| `debug=True` + `0.0.0.0` | `app.run` | A05 – Security Misconfiguration |
| Dependências com CVEs (Flask/Werkzeug/Jinja2 antigos) | `requirements.txt` | A06 – Vulnerable Components |
| Ausência de cabeçalhos de segurança | respostas HTTP | A05 |

A pasta `fixed/` contém a versão **corrigida**, usada para demonstrar a transição de **FAIL → PASS**.

```
devsecops-scan/
├── src/app.py                      # aplicação (vulnerável)
├── tests/                          # testes pytest
├── fixed/                          # versão corrigida (app.py + requirements.txt)
├── requirements.txt
├── requirements-dev.txt
├── zap-rules.tsv                   # regras do ZAP tratadas como FAIL
├── .github/workflows/security.yml  # pipeline
└── README.md
```

## 2. Ferramentas utilizadas e 3. Tipo de análise

| Ferramenta | Tipo | O que analisa |
|---|---|---|
| **Semgrep** | **SAST** | Código-fonte Python (`src/`): injeções, segredos, cripto fraca, configs inseguras |
| **pip-audit** | **SCA** | `requirements.txt`: dependências com CVEs conhecidas (base PyPI/OSV) |
| **OWASP ZAP** (full scan) | **DAST** | Aplicação **em execução**: XSS, SQLi, command injection, cabeçalhos ausentes |
| pytest | Testes | Garante que a correção não quebrou o comportamento |

## 4. Funcionamento da pipeline

**O que dispara?** `push` e `pull_request` na branch `main` (e execução manual via `workflow_dispatch`).

**Em qual etapa ocorre a análise?** Logo após o commit, antes de qualquer deploy. Os jobs rodam em paralelo:

```
Commit → Push
   ↓
GitHub Actions (security.yml)
   ├── tests  (pytest)
   ├── sast   (Semgrep)      → analisa o código
   ├── sca    (pip-audit)    → analisa as dependências
   └── dast   (OWASP ZAP)    → sobe a app e ataca
   ↓
resultado → PASS / FAIL
```

**O que acontece quando há problemas?**
- **Semgrep**: `--error` → qualquer finding encerra o job com erro.
- **pip-audit**: retorna código ≠ 0 se houver dependência vulnerável.
- **ZAP**: regras críticas definidas em `zap-rules.tsv` (XSS, SQLi, command injection, CSP/X-Frame-Options/X-Content-Type-Options ausentes) são tratadas como `FAIL`; demais alertas ficam como aviso no relatório.
- O job `resultado` consolida tudo: se **qualquer** etapa falhar, o pipeline fica **vermelho (FAIL)**, o merge/deploy deve ser bloqueado, e os relatórios ficam disponíveis como *artifacts* (`semgrep-report`, `pip-audit-report`, `zap-report`).

## 5. Resultados

### 5.1 Execução 1 – código vulnerável → ❌ FAIL

**Pipeline executada automaticamente após o push**

<!-- Cole aqui o print da aba Actions mostrando os jobs (vermelho) -->
`docs/img/pipeline-fail.png`

**Semgrep (SAST)**

<!-- print do log do job "SAST - Semgrep" -->
`docs/img/semgrep-fail.png`

**pip-audit (SCA)**

<!-- print do log do job "SCA - pip-audit" -->
`docs/img/pip-audit-fail.png`

**OWASP ZAP (DAST)**

<!-- print do zap-report.html ou do log do job -->
`docs/img/zap-fail.png`

Resumo dos findings (preencha com os números reais da sua execução):

| Ferramenta | Findings | Exemplos | Severidade |
|---|---|---|---|
| Semgrep | _N_ | `subprocess shell=True`, SQL formatada, MD5, `debug=True`, bind `0.0.0.0` | ERROR / WARNING |
| pip-audit | _N_ CVEs em _M_ pacotes | Flask, Werkzeug, Jinja2 | conforme CVE |
| ZAP | _N_ alertas | XSS refletido, SQLi, CSP ausente | High / Medium / Low |

### 5.2 Correção

```bash
cp fixed/app.py src/app.py
cp fixed/requirements.txt requirements.txt
git add -A && git commit -m "fix: corrige vulnerabilidades apontadas pelo pipeline" && git push
```

| Problema | Correção aplicada |
|---|---|
| SQL Injection | Query parametrizada (`?`) |
| XSS refletido | `markupsafe.escape` |
| Command Injection | Validação com `ipaddress` + `subprocess` sem shell |
| Segredo hardcoded | Lido de variável de ambiente |
| MD5 | `generate_password_hash` (Werkzeug) |
| `debug=True` / `0.0.0.0` | Debug via env var, bind `127.0.0.1` |
| Cabeçalhos ausentes | `after_request` com CSP, X-Frame-Options, nosniff |
| Dependências | Versões atualizadas |

### 5.3 Execução 2 – código corrigido → ✅ PASS

<!-- Cole aqui o print da pipeline verde -->
`docs/img/pipeline-pass.png`

## 6. Conclusão

**DevSecOps:** a segurança deixou de ser uma etapa isolada no final do projeto e passou a fazer parte do fluxo de entrega: a mesma pipeline que roda testes executa SAST, SCA e DAST de forma automática, repetível e com resultado objetivo (PASS/FAIL) que bloqueia a entrega.

**Shift Left:** as análises acontecem já no `push`/`pull request`, ou seja, no início do ciclo. SAST e SCA encontram falhas no código e nas dependências *antes* de a aplicação existir em execução; o DAST valida a aplicação ainda no ambiente de CI, antes de qualquer deploy. Como demonstrado nas execuções 1 e 2, o desenvolvedor recebe o feedback em minutos, corrige e comprova a correção, o que é muito mais barato do que descobrir o problema em produção.

## Como reproduzir

1. Crie um repositório no GitHub e envie estes arquivos para a branch `main`.
2. Abra a aba **Actions** e acompanhe a execução (deve terminar em FAIL).
3. Aplique a correção (seção 5.2), faça novo push e verifique o PASS.
4. Capture os prints e salve em `docs/img/`.

Rodar localmente:

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
python src/app.py
```

## Extensões opcionais

- **Docker**: `docker build` + análise da imagem com Trivy no workflow.
- **Terraform**: provisionar a infra e analisar o código com Checkov/tfsec.
