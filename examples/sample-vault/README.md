# claude-obsidian 샘플 볼트 · 구조 분석 및 Windows(.venv) 설치·운영 가이드

> 포크한 `claude-obsidian` v2.2.0 을 **WSL·Docker 없이, Windows 11 + `.venv` Python** 만으로 운영하기 위한 가이드입니다.
> 이 포크는 업스트림에 없는 **옵트인 Windows 쓰기 모드**(`claude_obsidian/winfd.py`)와 PowerShell 운영 스크립트(`scripts/windows/`)를 추가했습니다.

## 1. 개요

Claude Code 로 **Obsidian 위키**를 만들고 운영하는 로컬 우선 도구입니다(Karpathy *LLM Wiki* 패턴).
원본을 보존하고, 출처가 인용된 연결형 노트로 정리하며, 모든 쓰기는 **승인 해시 기반 트랜잭션**으로 수행합니다.

핵심 원칙: **제품(코드, 이 저장소)과 볼트(지식 데이터)는 반드시 분리**합니다. 제품 트리 안(`examples/`, `templates/` 포함)은 볼트로 거부됩니다(`PLUGIN_TREE_IS_NOT_VAULT`).

## 2. 소스 구조

```text
claude-obsidian/                 ← 제품 저장소 (볼트 아님)
├── AGENTS.md, WIKI.md           에이전트 지침, 볼트 스키마
├── .claude-plugin/plugin.json   Claude Code 플러그인 매니페스트
├── skills/                      15개 스킬 (<name>/SKILL.md) — 지식 동작의 유일한 구현 위치
├── agents/                      verifier, wiki-ingest, wiki-lint 서브에이전트
├── hooks/hooks.json             SessionStart/Stop 훅 (python3 를 직접 실행)
├── claude_obsidian/             표준 라이브러리 전용 Python 코어
│   ├── transaction.py           잠금·저널·백업·복구 엔진
│   ├── winfd.py                 [포크 추가] Windows 가상 디렉터리 핸들(옵트인)
│   ├── cli.py, vault_ops.py     CLI, init/adopt/migrate
│   ├── capture.py, ledgers.py   원본 캡처, 출처/주장 원장
│   └── lint_engine.py ...
├── scripts/
│   ├── claude-obsidian.py       통합 CLI
│   ├── windows/                 [포크 추가] PowerShell 운영 스크립트
│   └── setup-*.sh, retrieve.py  bash 확장(Windows 기본 흐름에서는 불필요)
├── templates/vault/             init 이 복사하는 시드
├── examples/sample-vault/       이 디렉터리(합성 데이터 예제)
├── docs/, config/, tests/
```

### 15개 스킬

| 분류 | 스킬 | 용도 |
|---|---|---|
| 핵심 | `wiki` | 볼트 초기화/채택, 진단, 라우팅 |
| | `save` | 선택한 답변 1건 저장 |
| | `wiki-ingest` | `inbox/` 원본 → 연결 페이지 + 출처 기록 |
| | `wiki-query` | 볼트 근거만으로 읽기 전용 답변 |
| | `wiki-lint` | 깨진 링크·고아·메타 누락 점검 |
| 확장 | `autoresearch` `canvas` `defuddle` `wiki-fold` `wiki-mode` `wiki-retrieve` `wiki-cli` | 웹 리서치(명시 동의), Canvas, 웹 정리, 로그 롤업, 분류 방식, BM25 검색, Obsidian CLI |
| 참조 | `obsidian-markdown` `obsidian-bases` `think` | 문법·Bases·사고 루프 |

호출 형식: `/claude-obsidian:wiki-lint`

## 3. 볼트 구조

```text
my-wiki/
├── .claude-obsidian.json    볼트 식별(schema claude-obsidian.workspace.v1)
├── .gitignore               .vault-meta/, .mcp.json, Obsidian 세션 상태 제외
├── .obsidian/               최소 Obsidian 설정
├── .raw/                    불변 원본 + .manifest.json
├── inbox/                   원본 투입구(자동 삭제 없음)
├── .vault-meta/             잠금·저널·인덱스 (Git 제외)
└── wiki/  index.md · overview.md · hot.md · log.md · sources/ concepts/ entities/ questions/ · meta/ledgers/
```

페이지는 평탄한 YAML(`type` `title` `status` `created` `updated` `tags`, 필요 시 `sources` `claim_ids`)과 `[[위키링크]]` 를 씁니다. 이 샘플은 합성 데이터이며 `Example Source ↔ Source-grounded notes ↔ Example Maintainer ↔ What supports source-grounded notes` 로 연결됩니다.

## 4. 이 환경의 운영 모델 (중요)

| 항목 | 내용 |
|---|---|
| 실행 환경 | Windows 11 네이티브, `E:\apps\claude-obsidian\.venv` (Python ≥ 3.11), WSL/Docker 없음 |
| 업스트림 제약 | 네이티브 Windows 는 읽기 전용(디렉터리 디스크립터 잠금 불가 → `UNSUPPORTED_PLATFORM`) |
| 이 포크의 해법 | `CLAUDE_OBSIDIAN_ALLOW_REDUCED_WRITES=1` 일 때만 **경로 기반 가상 핸들**로 쓰기 허용 (`scripts/windows/co.ps1` 이 자동 설정) |
| 유지되는 것 | 승인 해시, 단일 트랜잭션, 저널/백업/롤백, 원자적 교체(`os.replace`), 심볼릭 링크·정션 거부 |
| 약해지는 것 | 디렉터리를 *열어 고정*하지 못해 검사 시점과 사용 시점 사이의 경로 바꿔치기(TOCTOU)를 막지 못함 → **단일 사용자 로컬 볼트 전용** |
| 지원 안 함 | `checkpoint`(→ 일반 `git commit`), `legacy_lock`, bash `setup-*.sh`, 심볼릭 링크 필요 테스트 |
| 저장소 분리 | **포크(제품)** = `kdkim2000/claude-obsidian`, **볼트** = 별도 private 저장소(예: `kdkim2000/my-wiki`) |

> 제품 포크에는 볼트 데이터를 절대 푸시하지 않습니다(공개 배포물 오염 방지).

## 5. 설치 (PowerShell)

사전 조건: Windows 용 Python 3.11+, Git, GitHub CLI(`gh auth login`), Claude Code, (선택) Obsidian.

```powershell
cd E:\apps\claude-obsidian

# 1) .venv 준비: 존재 확인/생성, 버전 검사, .venv\Scripts\python3.exe 생성
powershell -ExecutionPolicy Bypass -File scripts\windows\setup-venv.ps1

# 2) 동작 확인 (읽기 전용; 제품 트리 안의 샘플은 볼트로 거부되는 것이 정상)
powershell -ExecutionPolicy Bypass -File scripts\windows\co.ps1 doctor --vault E:\vaults\my-wiki
```

`python3.exe` 가 필요한 이유: 훅(`hooks/hooks.json`)과 스킬 지침이 `python3` 를 직접 호출하는데, Windows Python 은 `python.exe` 만 제공합니다. `setup-venv.ps1` 이 venv 안에 복사본을 만들고, 실행 스크립트가 `.venv\Scripts` 를 PATH 맨 앞에 둡니다. `pip install` 은 필요 없습니다(표준 라이브러리 전용).

### 5.1 새 볼트 만들기 (드라이런 → 해시 확인 → 적용)

```powershell
mkdir E:\vaults
$G = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
# 계획 확인: 출력 JSON 의 changed_paths 와 approved_plan_sha256 검토
scripts\windows\co.ps1 init E:\vaults\my-wiki --generated-at $G --operation-id init-reviewed
# 같은 $G / operation-id 로 검토한 해시만 적용
scripts\windows\co.ps1 init E:\vaults\my-wiki --generated-at $G --operation-id init-reviewed `
  --approved-plan-sha256 <해시> --apply
```

볼트는 **NTFS 의 제품 트리 밖**(예: `E:\vaults\my-wiki`)에 두세요. FAT/exFAT·일부 네트워크 공유는 `UNSAFE_VAULT_IDENTITY` 로 거부됩니다. 기존 Obsidian 볼트는 `adopt <경로>` 로 같은 방식(드라이런→승인→`--apply`)으로 채택하고, 구버전 레이아웃은 `migrate --vault <경로>` 를 사용합니다.

### 5.2 샘플 체험

```powershell
Copy-Item -Recurse examples\sample-vault E:\vaults\sample
scripts\windows\co.ps1 doctor --vault E:\vaults\sample   # ok: true
scripts\windows\co.ps1 lint   --vault E:\vaults\sample   # issues_found: 0
```

Obsidian 에서 *Open folder as vault* 로 연 뒤 그래프를 확인합니다.

## 6. GitHub 저장소 구성

```powershell
# (한 번) 볼트를 private 저장소로 — 푸시 전 반드시 .gitignore 확인
cd E:\vaults\my-wiki
git init -b main
git add -A ; git status --short          # .vault-meta/ 가 목록에 없어야 함
git commit -m "init: claude-obsidian vault"
gh repo create kdkim2000/my-wiki --private --source . --remote origin --push
```

- 위키 내용(원본 자료·개인 노트)이 들어가므로 **private** 를 기본으로 합니다. 공개 전에는 `.raw/` 와 `inbox/` 내용을 검토하세요.
- 다른 PC: `gh repo clone kdkim2000/my-wiki E:\vaults\my-wiki` 후 `co.ps1 doctor --vault ...`.
- 제품 포크는 코드 변경만 푸시합니다. 업스트림(`AgriciDaniel/...`)으로의 push/태그/이슈는 소유자 승인 없이 하지 않습니다.

## 7. 일상 운영

```powershell
scripts\windows\claude-vault.ps1 -Vault E:\vaults\my-wiki     # 볼트에서 Claude Code + 플러그인 시작
```

| 단계 | Claude Code 입력 | 설명 |
|---|---|---|
| 시작/진단 | `/claude-obsidian:wiki` | 상태 확인, 라우팅 |
| 투입 | 파일을 `inbox\` 에 복사 | 원본 투입구 |
| 캡처(선택) | `co.ps1 capture plan/apply --vault ...` | `.raw\` 에 불변·해시 사본 |
| 수집 | `/claude-obsidian:wiki-ingest` | 페이지 + 출처/주장 원장 |
| 질의 | `/claude-obsidian:wiki-query 질문` | 볼트 근거로만 답변 |
| 저장 | `/claude-obsidian:save` | 선택한 답변 1건 저장 |
| 점검 | `/claude-obsidian:wiki-lint` | 상태 보고(수정 안 함) |
| 동기화 | `scripts\windows\vault-sync.ps1 -Vault ... -Message "..." -Push` | lint → 변경 확인 → 커밋 → (확인 후) 푸시 |

원본 지원 범위: 로컬 파일 바이트 캡처, 이미지 메타데이터, **PDF/EPUB 은 메타·해시만**, URL/YouTube/OCR 은 외부 러너 + 명시 동의 필요.

권장 루틴: 수시로 ingest/save → 작업 후 `vault-sync.ps1` 로 커밋 → 주 1회 `wiki-lint` → 월 1회 `wiki-fold` 로 로그 롤업 → 대형 ingest/migrate 전에는 커밋/백업.

주요 CLI(`co.ps1 <명령>`): `doctor`, `init/adopt/migrate`, `lint [--as-of] [--exclude]`, `capture plan/apply`, `transaction inspect/apply/recover`, `mode get/set`, `package validate`, `release build/audit`.

### 볼트 선택 우선순위
`--vault` → `CLAUDE_OBSIDIAN_VAULT` → 가장 가까운 `.claude-obsidian.json` → 모호하지 않은 상위 볼트. 불확실하면 쓰지 않고 종료합니다.

## 8. 신규 컨텐츠 → 위키 구성과 활용

폴더를 감시해 자동 갱신하는 방식이 아니라, **Claude 가 초안을 만들고 사람이 승인해 한 번에 적용하는 반자동 흐름**입니다.

```text
inbox\ 에 투입 → (capture) → wiki-ingest → 검토(inspect) → 승인 후 apply → lint → git 동기화
```

### 8.1 구성 절차

1. **투입:** 파일을 `E:aults\my-wiki\inbox\` 에 복사하거나 텍스트를 대화에 붙여 넣습니다. 볼트 밖 경로는 출처 근거로 인정되지 않습니다. URL 은 도메인·요청 수를 명시 승인해야 합니다.
2. **캡처(외부 파일일 때):** `co.ps1 capture plan --vault ...` → `capture apply`(승인 해시 + `--apply`). `.raw\captured\` 에 해시 기반 읽기 전용 사본이 생기고, 이후 주장은 이 사본을 인용합니다.
3. **위키 구성:** `claude-vault.ps1 -Vault E:aults\my-wiki` 로 시작한 뒤 `/claude-obsidian:wiki-ingest`(또는 "inbox 의 새 파일 ingest 해줘"). Claude 의 동작:

| 순서 | 동작 |
|---|---|
| 범위 합의 | 입력·읽을 기존 페이지 수(기본 소스당 5개)·생성 페이지 수 예산 설정 |
| 분석 | SHA-256 으로 중복 확인, 종류(코드·논문·결정·대화·웹·데이터) 분류 후 맞는 방식으로 추출 |
| 가치 판단 | 새 종합·연결이 있을 때만 페이지 생성(요약을 위한 요약 금지) |
| 연결 | `hot.md`·`index.md`·관련 페이지만 읽고 기존 페이지 재사용, `[[위키링크]]` 로 연결 |
| 출처·주장 기록 | `wiki/meta/ledgers/` 원장에 권위·신선도·상태 기록, 상충 근거도 유지 |
| 번들 작성 | 모든 변경을 `operation_type: ingest` 트랜잭션 번들 1개로 병합 |

   결과물: `wiki/sources/` 출처 요약, `concepts/` `entities/` `questions/` 페이지, 인덱스·MOC 항목, `log.md` 배치 로그, 갱신된 `hot.md`.
4. **검토·적용:** Claude 가 변경 경로·예산·해시를 보여 주면 확인 후 `transaction apply --approved-plan-sha256 <해시>` 가 **한 번만** 실행됩니다. 대상이 바뀌었으면 덮어쓰지 않고 충돌로 중단, 실패 시 롤백, 중단된 작업은 `transaction recover`.
5. **점검·동기화:** `/claude-obsidian:wiki-lint` 후 `scripts\windowsault-sync.ps1 -Vault ... -Message "ingest: 자료명" -Push`.

### 8.2 활용

| 목적 | 방법 | 특징 |
|---|---|---|
| 질문 | `/claude-obsidian:wiki-query 질문` | 볼트 근거만 사용(읽기 전용), 페이지 인용, 근거 없으면 거절 |
| 깊이 선택 | quick / standard / deep | quick=`hot.md`·`index.md`, deep=상충 근거·출처까지 |
| 답변 보존 | `/claude-obsidian:save` | 지정한 답변 1건만 저장(대화 전체 저장 안 함) |
| 검색 강화 | `/claude-obsidian:wiki-retrieve` | 로컬 BM25 인덱스(원격 임베딩은 별도 동의) |
| 주제 조사 | `/claude-obsidian:autoresearch 주제` | 웹 조사 초안 생성, 정식 병합은 별도 승인 |
| 시각화 | `canvas` 스킬, Obsidian 그래프 뷰 | 지식 지도 |
| 정리 | `wiki-lint` 주 1회, `wiki-fold` 월 1회 | 깨진 링크·고아·메타 누락 점검, 로그 롤업 |
| 분류 방식 | `mode set para` 등 | 새 노트 위치만 변경, 기존 노트 이동 없음 |

ingest 가 연결된 페이지와 원장을 만들고 query·save 가 그 위에 분석을 더하며, 다음 ingest 는 이 기존 페이지를 읽고 연결합니다. 이 순환으로 위키가 점점 촘촘해집니다.

### 8.3 주의점

- **PDF·이미지:** 내장 추출이 없어 PDF/EPUB 은 메타·해시만 기록됩니다. 텍스트로 변환(`pdf-to-markdown` 스킬 등)해 `inbox\` 에 넣으세요.
- **웹 페이지:** `defuddle` 로 Markdown 정리 후 ingest(외부 도구·네트워크 동의 필요).
- **자료 속 지시문**은 무시되고 근거로만 사용됩니다.
- **신뢰도:** 고위험 주장은 독립 출처 2개가 있어야 `accepted`, 부족하면 `provisional`/`unsupported` 로 표시됩니다.
- **실행 환경:** 스킬이 `python3` 를 호출하므로 반드시 `claude-vault.ps1` 로 시작하세요(PATH·쓰기 모드 환경변수 설정). 일반 터미널의 `claude` 는 쓰기가 거부될 수 있습니다.
- 첫 실행은 작은 문서 1개로 시험하세요(Claude Code 세션에서의 end-to-end ingest 는 아직 검증되지 않았습니다).

## 9. 안전·보안 규칙

- 고위험 주장은 독립 출처 2개. 증거 위치·인용·페이지 번호·신뢰도를 지어내지 않습니다.
- `.raw/` 원본은 생성 전용. `inbox/` 는 자동 삭제하지 않습니다.
- 외부 통신(웹 리서치·URL 수집·원격 임베딩), 파괴적 복구, 연구 결과의 정식 병합은 **명시 동의**가 필요합니다.
- 세션 컨텍스트 주입은 기본 꺼짐. `CLAUDE_OBSIDIAN_SESSION_CONTEXT=1` 을 직접 설정할 때만 `wiki/hot.md` 가 컨텍스트에 들어갑니다(프로젝트 밖 볼트는 `CLAUDE_OBSIDIAN_SESSION_CONTEXT_VAULT` 도 필요).
- 훅은 지식을 쓰지 않고, 복구가 필요할 때 경로·내용 없는 경고만 냅니다.
- `.vault-meta/`, `.mcp.json` 은 커밋하지 마세요(`.gitignore` 기본값).

## 10. 장애 대응

```powershell
scripts\windows\co.ps1 transaction recover --vault E:\vaults\my-wiki
# 활성 작성자가 없음을 확인한 뒤에만 --force-stale-lock
```

| 증상 | 조치 |
|---|---|
| `UNSUPPORTED_PLATFORM` | `co.ps1`/`claude-vault.ps1` 로 실행(옵트인 환경변수 자동 설정) |
| `PLUGIN_TREE_IS_NOT_VAULT` | 제품 트리 밖의 복사본/별도 볼트 사용 |
| `UNSAFE_VAULT_IDENTITY` | NTFS 볼륨으로 이동 |
| `PLAN_CHANGED` | 같은 환경에서 드라이런 재실행 후 새 해시 사용 |
| 종료 코드 75 / `LOCK_TIMEOUT` | 다른 작업 진행 중 → 대기 또는 `transaction recover` |
| 훅이 동작하지 않음 | `.venv\Scripts\python3.exe` 존재 및 PATH 앞쪽 확인(`setup-venv.ps1`) |
| `checkpoint` 거부 | Windows 미지원 → `vault-sync.ps1`(일반 git) 사용 |
| 롤백 | 커밋 단위로 `git revert`/`git restore`, 중단된 작업은 `transaction recover` |

## 11. 업그레이드·제거

- 포크 업데이트 후 구볼트는 `migrate` 를 드라이런으로 확인한 뒤 적용합니다. 제품과 볼트는 독립적으로 업그레이드합니다.
- 제거: 플러그인/저장소만 삭제하면 되며 볼트(노트·원본·원장)는 그대로 유지됩니다.

## 12. 포크 개발·검증

```powershell
scripts\windows\run-tests.ps1 -Reduced     # tests\test_*.py 전체(옵트인 모드 켬)
.venv\Scripts\python.exe tests\test_windows_reduced_writes.py   # Windows 쓰기 모드 전용 시나리오
```

- 네이티브 Windows 에서는 심볼릭 링크 권한(WinError 1314), bash, `fcntl` 이 필요한 일부 스위트가 **업스트림 설계상** 실패합니다. 핵심 확인: `test_windows_reduced_writes`, `test_windows_compat`, `test_cli_approval`, `test_contracts`.
- `RELEASE_MANIFEST.json`/`SHA256SUMS` 는 파일 해시를 고정합니다. 배포 대상 파일을 바꿨다면 릴리스 빌드 전에 갱신·감사(`release build/audit`)하세요. 푸시·태그·릴리스는 소유자 승인 후에만 수행합니다.

## 13. 참고 문서

`README.md`(루트) · `docs/install-guide.md` · `docs/windows-wsl.md`(네이티브 저하 모드 절 포함) · `docs/methodology-modes-guide.md` · `docs/compound-vault-guide.md` · `skills/wiki/references/` · `WIKI.md`
