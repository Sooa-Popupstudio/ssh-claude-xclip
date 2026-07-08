# ssh-claude-xclip

맥에서 캡쳐한 스크린샷을 SSH 너머 서버의 Claude Code에 바로 붙여넣는 도구.
서버에 리스닝 포트를 열지 않는 **포트리스** 구조 — 맥 데몬이 캡쳐 즉시 서버 `/tmp`로
밀어올려두고(push), 서버의 가짜 xclip이 그 파일을 클립보드인 척 내준다.

## 뭐가 되나

캡쳐(⌃⌘⇧4) 한 번이면 자동 업로드까지 끝나고, 키에 따라:

| 키 | 결과 | 용도 |
|---|---|---|
| **Ctrl+V** | `[Image #N]` 첨부 | Claude에게 이미지 직접 보여주기 |
| **Cmd+Shift+V** | `/tmp/clip-....png ` 경로 타이핑 | **⌘클릭으로 열어서 확인**, 경로로 참조 |
| Cmd+V | `[Image #N]` 첨부 (경로가 자동 변환됨) | Ctrl+V와 사실상 동일 |
| (다른 앱에서 Cmd+V) | 이미지 그대로 | Slack 등 기존 사용 안 깨짐 |

- 핫키·수동 명령 불필요: 캡쳐하면 데몬이 감지해 서버 `/tmp/clip-YYYYmmdd-HHMMSS.png`로
  자동 업로드하고, 맥 알림으로 경로를 띄움 (알림 = 붙여넣기 준비 완료 신호)
- `/tmp`라 서버 재부팅(하루 2번) 때 자동 삭제 — 정리 불필요, 오래 볼 이미지는 딴 데 저장

## 구조

```
[맥 클립보드] ← 상주 데몬(ssh-claude-xclip-mac.py, launchd)이 감시
      └→ 새 이미지 감지 → ssh로 서버 /tmp/clip-*.png 업로드 → 클립보드에 "이미지+경로" 병기
                                        │
   서버 Claude Code가 Ctrl+V → 가짜 xclip(ssh-claude-xclip-server)이 /tmp의 최신 파일을 읽음
   Cmd+Shift+V → 미니 VS Code 확장(ssh-claude-xclip-vscode)이 경로를 터미널에 타이핑
```

원리:

- **push 선행**: 데몬이 이미지 복사를 감지할 때마다 평범한 아웃바운드 `ssh`로 서버 `/tmp`에
  미리 올려둔다. 그래서 붙여넣기 시점엔 서버 로컬 파일만 읽으면 되고, 리스닝 포트·역터널·
  포트 충돌·터널 유지 관리가 전부 없다.
- **xclip 가로채기**: Claude Code(서버)는 Ctrl+V를 받으면 `xclip`이라는 고정된 명령으로
  클립보드를 읽는다. 서버는 헤드리스라 클립보드가 없으므로, PATH 앞순위(`~/.local/bin/xclip`)에
  가짜 xclip을 심링크해 그 호출을 가로채고 `/tmp/clip-*.png` 중 **내 소유의 최신 파일**을 내준다.
  안전장치: 10분 지난 파일은 "클립보드 비어 있음" 취급(데몬이 죽었을 때 옛 이미지 오첨부 방지),
  업로드 진행 중이면 최대 3초 대기, PNG 끝 8바이트(IEND)로 완결성 확인.
- **경로는 타이핑으로**: Claude Code는 붙여넣어진 텍스트가 실존하는 이미지 경로면 무조건
  `[Image #N]`으로 변환한다(끄는 설정 없음). 경로를 텍스트로 남기려면 붙여넣기가 아니라
  타이핑이어야 해서, 미니 확장이 `terminal.sendText`로 경로를 타이핑한다.
  (참고: 데몬 환경변수 `SSH_CLAUDE_XCLIP_PATH_SUFFIX=":1"`을 주면 Cmd+V 붙여넣기도 경로
  텍스트로 남는다 — `:1`이 붙으면 존재하지 않는 파일명이 되어 변환 검사를 피함.)
- 텍스트 클립보드는 이 도구와 무관 — 터미널이 직접 붙여넣으므로 원래대로 동작.

## 구성 파일 (서버 `/home/sooa/ssh-claude-xclip/`)

| 파일 | 역할 | 설치 위치 |
|---|---|---|
| `ssh-claude-xclip-mac.py` | 맥 상주 데몬 (클립보드 감시 → 자동 업로드) | 맥 `~/bin/` |
| `ai.popup.ssh-claude-xclip.plist` | 데몬 launchd 등록 | 맥 `~/Library/LaunchAgents/` |
| `ssh-claude-xclip-server` | 가짜 xclip (서버) | 서버 `~/.local/bin/xclip` (심링크) |
| `ssh-claude-xclip-vscode/` | 미니 VS Code 확장 (Cmd+Shift+V 경로 타이핑) | 맥 `~/.vscode/extensions/` |

## 설치

전제: 맥 `~/.ssh/config`에 서버 별칭(`popup-server`)이 있고 키 인증으로 접속 가능.

```bash
# ── 맥에서 ──────────────────────────────────────────────
# 1) 데몬 + launchd 등록
mkdir -p ~/bin && scp popup-server:/home/sooa/ssh-claude-xclip/ssh-claude-xclip-mac.py ~/bin/
scp popup-server:/home/sooa/ssh-claude-xclip/ai.popup.ssh-claude-xclip.plist ~/Library/LaunchAgents/
sed -i '' "s/YOURNAME/$(whoami)/" ~/Library/LaunchAgents/ai.popup.ssh-claude-xclip.plist
launchctl load ~/Library/LaunchAgents/ai.popup.ssh-claude-xclip.plist

# 2) 미니 확장 (Cmd+Shift+V 경로 타이핑 — Ctrl+V만 쓸 거면 생략 가능)
scp -r popup-server:/home/sooa/ssh-claude-xclip/ssh-claude-xclip-vscode ~/.vscode/extensions/
# 이후 VS Code 완전 종료(Cmd+Q) 후 다시 실행
```

```bash
# ── 서버에서 (계정당 1회) ──────────────────────────────
ln -sf /home/sooa/ssh-claude-xclip/ssh-claude-xclip-server ~/.local/bin/xclip
```

서버 별칭이 `popup-server`가 아니면: plist의 `EnvironmentVariables`에
`SSH_CLAUDE_XCLIP_REMOTE=<별칭>` 추가.

## 검증 (순서대로, 어디서 실행하는지 주의)

```bash
# 맥: 캡쳐(⌃⌘⇧4) → "ssh-claude-xclip" 타이틀의 맥 알림에 경로가 뜨는지 확인 (= 업로드 완료)

# 서버: 업로드 확인
ls -t /tmp/clip-*.png | head -1        # → 방금 캡쳐한 파일

# 서버: 가짜 xclip 확인
xclip -selection clipboard -t TARGETS -o               # → TARGETS + image/png
xclip -selection clipboard -t image/png -o | file -    # → PNG image data

# 최종: Claude Code에서 Ctrl+V → [Image #N] / Cmd+Shift+V → 경로 타이핑
```

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| Ctrl+V 해도 아무 반응 없음 | 마지막 업로드가 10분 경과(신선도 가드) 또는 데몬 죽음 | 다시 캡쳐. `ls -t /tmp/clip-*.png`로 새 파일이 생기는지 확인 — 안 생기면 맥에서 `launchctl list \| grep ssh-claude-xclip` |
| 캡쳐 직후 바로 Ctrl+V 하면 빈손 | 업로드(1~2초)가 안 끝남. 3초까진 기다려주지만 그 이상이면 포기 | **맥 알림 뜬 뒤** 붙여넣기 |
| 엉뚱한(예전) 이미지가 붙음 | 데몬이 죽은 뒤 10분 안에 Ctrl+V → 최신 파일이 이전 캡쳐 | 맥에서 데몬 재기동 (`launchctl unload` 후 `load`) |
| 맥 알림이 안 뜸 | 집중 모드 / 스크립트 알림 차단 | 알림 설정에서 Script Editor 허용. 업로드 여부는 서버 `ls /tmp/clip-*`로 확인 |
| 붙여넣은 경로가 `[Image #N]`으로 변함 | Claude Code의 경로 자동 첨부 (끄기 불가). 의도된 동작 | 경로가 필요하면 Cmd+Shift+V(타이핑) |
| ⌘클릭이 안 먹음 | 문서 속 자리표시자(`....`)를 클릭했거나 TUI 줄바꿈으로 경로가 쪼개짐. Claude Code 입력창 안은 재렌더링 때문에 불안정할 수 있음 | 셸에서 `ls -t /tmp/clip-*.png \| head -1` 출력을 클릭 |
| `ssh popup-server ...` → 이름 해석 실패 | 서버에서 실행함 (별칭은 맥 config에만 있음) | 맥 터미널에서 실행 |

환경변수 (기본값으로 충분, 필요시 조정):

| 변수 | 기본 | 어디서 | 뜻 |
|---|---|---|---|
| `SSH_CLAUDE_XCLIP_REMOTE` | `popup-server` | 맥 데몬 | 업로드 대상 ssh 별칭 |
| `SSH_CLAUDE_XCLIP_PATH_SUFFIX` | (없음) | 맥 데몬 | 경로 텍스트 뒤 접미사 (`:1`이면 Cmd+V도 경로로 남음) |
| `SSH_CLAUDE_XCLIP_MAX_AGE` | `600` | 서버 xclip | 이 초수보다 오래된 clip 파일은 무시 |
| `SSH_CLAUDE_XCLIP_WAIT` | `3` | 서버 xclip | 업로드 완료를 기다리는 최대 초수 |

## 여러 명이 같이 쓸 때

가짜 xclip은 `/tmp`를 최신순으로 훑되 **자기 소유 파일만** 집는다 (`[ -O ]` 검사).
동료가 방금 올린 캡쳐가 더 최신이어도 내 Ctrl+V에는 내 캡쳐가 붙는다.
각자 할 일: 맥 설치(위) + 서버에서 자기 계정에 심링크 1회.

## 참고한 프로젝트

기존 도구들을 참고해서, 맘에 드는 부분은 가져오고 맘에 안 드는 부분은 재조합/재구현했다.

| 원본 | 가져온 것 | 다르게 한 것 |
|---|---|---|
| [cc-clip](https://github.com/ShunmeiCho/cc-clip) (Go) | launchd 상주 데몬, PATH 앞순위 가짜 xclip으로 Claude Code의 호출 규격(`-selection clipboard -t TARGETS/-t image/png` + `-o`)을 가로채는 셔밍, doctor식 단계별 검증 절차 | cc-clip은 "붙여넣기 시점에 SSH 역터널로 로컬 클립보드를 pull"하는 구조 (전용 포트 + Bearer 토큰 + 원격 바이너리 배포 + Xvfb/X11 브릿지). 우리는 터널·포트를 없애고 의존성 0인 파이썬 데몬 + 짧은 bash 스크립트로 축소 |
| [clipaste](https://github.com/hqhq1025/clipaste) (Rust) | 클립보드 **감시** 데몬이 스크린샷을 감지하면 자동 파일화하고, 클립보드에 "이미지 + 경로 텍스트" 두 표현을 병기하는 아이디어 | clipaste는 파일을 **로컬** temp에 두고 원격에선 역시 터널로 pull. 우리는 감지 즉시 **서버로 선제 push**하고 서버 경로를 병기 — 이 뒤집기가 포트리스를 가능하게 한 핵심 |
| [Image Paste for Remote SSH](https://marketplace.visualstudio.com/items?itemName=asfeng.claude-code-image-paste) (VS Code 확장) | `terminal.sendText` **타이핑**은 Claude Code의 `[Image #N]` 변환을 피한다는 발견, `extensionKind: ["ui"]`, `"when": "terminalFocus"` 키바인딩 패턴 | 키를 누르는 순간에야 업로드해서 느리고 저장 경로·파일명이 고정 → 업로드는 데몬이 캡쳐 즉시 미리 해두고, 확장은 경로 타이핑만 하는 20줄짜리로 재구현 |

세 도구 모두 "붙여넣기 순간 당겨오기(pull)" 아니면 "누르는 순간 올리기"인데, 이 도구는
**캡쳐 순간 미리 올려두기(push)** 로 뒤집어 포트·터널·토큰 없이 동작하는 게 차별점.

## 주의점

- 공용 `/tmp`라 다른 계정도 파일을 볼 수 있다 — 민감 화면 유의.
- 가짜 xclip은 Claude Code의 내부 구현(xclip 호출 규격)에 기대므로, Claude Code 업데이트로
  깨질 수 있다. 깨지면 `xclip -selection clipboard -t TARGETS -o`부터 다시 진단.
- macOS 전용, 이미지(PNG)만.
- 제거: 서버 `rm ~/.local/bin/xclip`, 맥 `launchctl unload ~/Library/LaunchAgents/ai.popup.ssh-claude-xclip.plist`
  후 plist·`~/bin/ssh-claude-xclip-mac.py`·확장 폴더 삭제.
