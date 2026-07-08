# ssh-claude-xclip

맥에서 캡쳐한 스크린샷을 SSH 너머 서버의 Claude Code에 바로 붙여넣는 도구.
서버에 포트를 열지 않는다. 동작 원리·트러블슈팅은 [ARCHITECTURE.md](ARCHITECTURE.md) 참고.

## 사용법

캡쳐(⌃⌘⇧4)하면 자동으로 서버에 업로드된다. **맥 알림이 뜨면 준비 완료** — Claude Code 터미널에서:

| 키 | 결과 | 용도 |
|---|---|---|
| **Cmd+V** | `[Image #N]` 첨부 | Claude에게 이미지 직접 보여주기 |
| **Cmd+Shift+V** | `/tmp/clip-....png ` 경로 타이핑 | **⌘클릭으로 열어서 확인**, 경로로 참조 |

- 캡쳐 외에도 이미지를 클립보드에 복사하면(브라우저 이미지 복사 등) 똑같이 동작한다.
- 업로드 파일은 서버 `/tmp`에 있어 재부팅 때 자동 삭제 — 정리 불필요,
  오래 볼 이미지는 딴 데 저장할 것.

## 설치법

전제: 맥 `~/.ssh/config`에 서버 별칭이 있고 키 인증으로 접속 가능.
별칭이 `popup-server`가 아니면 plist 설치 후 `EnvironmentVariables`에
`SSH_CLAUDE_XCLIP_REMOTE=<별칭>`을 추가한다.

> 같은 서버(popup-server)를 쓰는 팀원은 git 없이 서버 원본에서 바로 설치해도 된다 —
> [local-readme.md](local-readme.md) 참고.

```bash
# ── 맥에서 (한번에 복사 후 붙여넣은 후 enter) ──────────────
git clone https://github.com/Sooa-Popupstudio/ssh-claude-xclip.git /tmp/ssh-claude-xclip
cd /tmp/ssh-claude-xclip

# 1) 데몬 + launchd 등록 (캡쳐 감지 → 자동 업로드 담당)
mkdir -p ~/bin && cp ssh-claude-xclip-mac.py ~/bin/
cp ai.popup.ssh-claude-xclip.plist ~/Library/LaunchAgents/
sed -i '' "s/YOURNAME/$(whoami)/" ~/Library/LaunchAgents/ai.popup.ssh-claude-xclip.plist
launchctl load ~/Library/LaunchAgents/ai.popup.ssh-claude-xclip.plist

# 2) 미니 VS Code 확장 (Cmd+Shift+V 경로 타이핑 담당 — Cmd+V만 쓸 거면 생략 가능)
cp -r ssh-claude-xclip-vscode ~/.vscode/extensions/
# 이후 VS Code 완전 종료(Cmd+Q) 후 다시 실행
```

```bash
# ── 서버에서 (계정당 1회) ──────────────────────────────
git clone https://github.com/Sooa-Popupstudio/ssh-claude-xclip.git ~/ssh-claude-xclip
ln -sf ~/ssh-claude-xclip/ssh-claude-xclip-server ~/.local/bin/xclip
```

설치 확인: 캡쳐 한 번 → "ssh-claude-xclip" 타이틀의 맥 알림에 경로가 뜨면 성공.

제거: 서버 `rm ~/.local/bin/xclip`, 맥 `launchctl unload ~/Library/LaunchAgents/ai.popup.ssh-claude-xclip.plist`
후 plist·`~/bin/ssh-claude-xclip-mac.py`·확장 폴더 삭제.
