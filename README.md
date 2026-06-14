# fable-ish

> **"fable-ish" = "Fable처럼(-ish)".**
> 관찰 가능한 검증으로 통과하기 전에는, 완료를 인정하지 않는다.

[![license](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![platform](https://img.shields.io/badge/platform-Claude%20Code-7c3aed.svg)](https://claude.com/claude-code)

`fable-ish`는 Anthropic이 최근 선보인 코딩 모델 **Fable**이 보여준 *검증 규율*을 **Claude Code** 훅으로 재현한 플러그인입니다. Fable의 강함은 "똑똑한 모델이 코드를 잘 쓴다"가 아니라 **루프**에 있습니다 — 작업의 위험에 맞춰 탈출 조건을 매 순간 새로 세우고, 그 조건이 *관찰 가능한 검증*으로 통과되기 전에는 완료를 인정하지 않습니다. fable-ish는 그 규율을 가벼운 훅 3개로 흉내 냅니다(그래서 `-ish`).

[English](./README-EN.md)

> **원작자 & 포팅.** 원본 `fable-ish`는 **플라잉따릉이 (Agent Korea)** 가 Fable의 동작 방식을 역설계해 **Codex**용 플러그인으로 만들었습니다. 이 저장소는 그 플러그인을 **Claude Code**로 포팅한 버전입니다 (포팅: chrisryugj). 플러그인 이름·스킬·워크플로는 원본 그대로 보존했습니다.

---

## 🔁 Fable 루프, 한 문장으로

> 목표 설정 → 근거 수집 → 작업 단위 정의 → **탈출 기준 설정** → 구현 → **검증** → 반례 탐색 → 기준 재조정 → 통과하면 탈출, 아니면 반복.

핵심은 *고정 체크리스트*("테스트 통과")가 아니라 **동적 탈출 조건**입니다. 위험이 낮으면 정적 검증 하나로 충분하고, 인증·DB·배포처럼 위험이 크면 더 강한 증명을 탈출 기준으로 요구합니다. fable-ish는 이 판단을 매 작업마다 강제합니다.

---

## 💡 fable-ish가 하는 일

LLM은 종종 검증 없이 "다 됐습니다"라고 보고합니다. fable-ish는 그 습관에 **마찰**을 넣습니다. 단 3개의 라이프사이클 훅으로:

- **🏷️ 작업 분류** — 들어온 요청을 `quick` / `normal` / `deep` / `blocked` 로 나눠, 거기에 맞는 검증 깊이를 컨텍스트로 주입합니다.
- **📒 증거 기록** — 어떤 파일이 바뀌었는지, 어떤 검증 명령이 돌았는지, 실패가 있었는지를 작은 JSON 장부(ledger)에 남깁니다. 검증이 *바뀐 파일을 실제로 커버했는지*(`direct`/`generic`/`uncertain`)까지 추적합니다.
- **🚦 완료 게이트** — 코드를 바꿨는데 성공한 검증 증거가 없으면, 종료 시점에 "검증부터 하라"고 되돌립니다 (무한 루프 방지를 위해 최대 2회).

한 줄 원칙: **관찰하지 않은 검증을 했다고 주장하지 마라.**

---

## ⚡ 설치

이 저장소는 단일 플러그인이자 마켓플레이스(`.claude-plugin/marketplace.json`)입니다.

**로컬에서 바로 (클론만 하면 됨):**

```text
/plugin marketplace add /path/to/fable-ish
/plugin install fable-ish
```

**GitHub 공개 후 (저장소를 push했다면):**

```text
/plugin marketplace add chrisryugj/fable-ish
/plugin install fable-ish
```

설치 후 **Claude Code를 재시작**하세요. 플러그인에 번들된 훅은 **자동으로 신뢰되지 않습니다.** `/hooks`를 열어 훅 정의를 검토하고 신뢰해야 게이트가 작동합니다.

> **요구사항**: 훅은 표준 라이브러리만 쓰는 Python 스크립트입니다. `python3`가 PATH에 있어야 합니다. Windows에서 `python3`가 없다면 `python`을 쓰거나 `hooks/hooks.json`의 `command` 항목을 맞게 바꿔주세요.

---

## ▶️ 사용법 — 한 번 설치하면 알아서 흐릅니다

설치하고 `/hooks`에서 신뢰하면 **그 뒤로는 자동**입니다. 따로 켤 필요가 없습니다.

- **자동 (훅):** 모든 프롬프트가 `quick`/`normal`/`deep`/`blocked`로 분류되고, 코드를 바꿨는데 검증이 없으면 종료 시점에 되돌립니다. 당신이 할 일은 없습니다.
- **명시 호출 (스킬):** `/fable-ish <작업>` 슬래시 커맨드로 직접 부르거나, *"fable-ish로 끝까지 구현해"* 같은 자연어, 또는 복잡·검증이 필요한 작업이면 Claude가 알아서 스킬을 부릅니다. (`fablish` 오타도 같은 스킬로 인식)

훅이 비활성/미신뢰 상태여도 스킬은 재사용 가능한 지침으로 계속 동작하지만, 기계적 게이트는 돌지 않습니다.

> **참고**: 비밀 파일·위험 명령의 *하드 차단*은 이 플러그인이 아니라 네이티브 `permissions.deny`로 거세요 (아래 [설계 노트](#️-설계-노트--왜-명령-차단-훅이-없나요) 참고).

---

## 🔧 작동 방식

| 훅 | 역할 |
|----|------|
| `UserPromptSubmit` | 요청을 `quick`/`normal`/`deep`/`blocked`로 분류하고, 기대 검증 깊이를 짧은 컨텍스트로 주입 |
| `PostToolUse` | 바뀐 파일·경로, 검증 명령, 커버리지 관계(`direct`/`generic`/`uncertain`), 실패를 JSON 장부에 기록 (`CLAUDE_PLUGIN_DATA`, 없으면 OS 임시 디렉토리) |
| `Stop` | `normal`/`deep` 작업이 파일을 바꿨는데 성공한 검증이 없으면 종료를 막음 (최대 2회, `stop_hook_active` 시 즉시 양보) |

스킬(`skills/fable-ish/SKILL.md`)은 사람이 읽는 워크플로 지침 레이어로, 모드별 작업 루프·검증 사다리·최종 보고 형식을 안내합니다.

---

## 🛡️ 설계 노트 — 왜 "명령 차단 훅"이 없나요?

원본에는 위험한 셸 명령과 비밀 파일 편집을 정규식으로 막는 `PreToolUse`/`PermissionRequest` 훅이 있었습니다. 이 포팅에서는 **의도적으로 제거**했습니다.

정규식으로 셸의 *의도*를 판정하는 건 지는 싸움입니다. 원본 룰셋을 실측해보니 위험 명령 16개 중 **4개만** 막혔습니다 — `rm -r -f`(플래그 분리), `rm --recursive --force`, `$VAR -rf`, base64 파이프 `eval`, `git -C . push`, 그리고 진짜 파괴적인 `dd`·`mkfs`·fork bomb이 전부 빠져나갔고, 반대로 빌드 캐시 정리나 릴리스 `npm publish` 같은 정상 작업은 **과차단**됐습니다. 변수 확장·따옴표·glob·인코딩이 표면 패턴을 무력화하므로, 정규식을 조여봐야 오탐만 늘어납니다.

Claude Code에는 이걸 위한 더 강한 **네이티브 장치**가 이미 있습니다. 하드 제한은 설정의 `permissions.deny`로 거세요 — 명령이 파싱되고, 사용자 승인 단계도 적용됩니다:

```json
{
  "permissions": {
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Write(./.env)",
      "Bash(rm -rf:*)",
      "Bash(dd:*)",
      "Bash(mkfs:*)",
      "Bash(git push:*)"
    ]
  }
}
```

진짜 격리가 필요하면 정규식 매칭이 아니라 **샌드박스 / 권한 모드(`bypassPermissions` 회피) / 승인 / 리뷰**에 의존하세요. fable-ish는 훅이 진짜 잘하는 일 — 작업이 완료로 보고되기 전에 *검증되도록* 하는 일 — 에 집중합니다.

---

## ⚠️ 한계

검증 게이트는 규율 보조 장치이지 보안 경계가 아닙니다.

- 분류는 휴리스틱입니다. 모드는 보장이 아니라 힌트로 받아들이세요.
- `PostToolUse`는 이미 끝난 명령의 부작용을 되돌릴 수 없습니다.
- 훅은 실행 전 검토·신뢰가 필요합니다.
- 종료 차단은 무한 루프 방지를 위해 의도적으로 최대 2회로 제한됩니다.

---

## 🧪 개발 / 검증

플러그인 루트에서:

```bash
python3 -m json.tool .claude-plugin/plugin.json
python3 -m json.tool hooks/hooks.json
python3 -m py_compile hooks/*.py scripts/*.py
python3 tests/test_hooks.py
```

각 훅 스크립트에는 `CLAUDE_PLUGIN_DATA`를 임시 디렉토리로 지정한 뒤 샘플 입력을 파이프로 넣어볼 수 있습니다.

---

## 🙏 크레딧

- **원작자 (Codex용 원본):** **플라잉따릉이 (Agent Korea)** — Fable 하니스 역설계, 검증 게이트 설계와 원본 구현
- **Claude Code 포팅:** chrisryugj

원본은 Codex 플러그인으로 만들어졌고, 이 저장소는 플러그인 이름·워크플로를 그대로 둔 채 Claude Code(훅·매니페스트·도구)에 맞게 옮긴 것입니다. 포팅 과정에서 upstream 0.1.1/0.1.2의 개선(`stop_hook_active` 처리, 한국어 분류 확장, 커버리지 추적, 새 프롬프트 리셋 픽스)을 함께 반영했습니다.

---

## 📄 라이선스

[MIT](./LICENSE) — © 플라잉따릉이 (Agent Korea) and contributors.
