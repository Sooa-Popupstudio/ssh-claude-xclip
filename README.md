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
- Finder에서 이미지 파일을 복사(⌘C)해도 똑같이 동작한다 — 여러 장을 한 번에 복사하면 전부
  업로드되고, ⌘⇧V로 경로가 한꺼번에 타이핑된다. (여러 장 동시 첨부는 ⌘⇧V 경로 방식으로만
  확실하고, ⌘V 단일 첨부·Ctrl+V는 한 장씩.)
- 업로드 파일은 서버 `/tmp`에 있어 재부팅 때 자동 삭제 — 정리 불필요,
  오래 볼 이미지는 딴 데 저장할 것.

## 설치법

**0) SSH 별칭 등록 (맥에서, vscode 상에서 왼쪽 하단에 이미 ssh:popups-server로 설정이 되어 있다면 스킵)**

맥 `~/.ssh/config`에 서버가 `popup-server`라는 별칭으로 등록되어 있어야 한다.

```bash
code ~/.ssh/config
```

열린 파일에 Host 부분을 popup-server로 저장한다

```
Host popup-server
    HostName 43.200.38.93
```

**1) 로컬에서**

```bash
git clone https://github.com/Sooa-Popupstudio/ssh-claude-xclip.git /tmp/ssh-claude-xclip
cd /tmp/ssh-claude-xclip

mkdir -p ~/bin && cp ssh-claude-xclip-mac.py ~/bin/
cp ai.popup.ssh-claude-xclip.plist ~/Library/LaunchAgents/
sed -i '' "s/YOURNAME/$(whoami)/" ~/Library/LaunchAgents/ai.popup.ssh-claude-xclip.plist
launchctl load ~/Library/LaunchAgents/ai.popup.ssh-claude-xclip.plist

cp -r ssh-claude-xclip-vscode ~/.vscode/extensions/
```

**2) 서버에서**
```bash
git clone https://github.com/Sooa-Popupstudio/ssh-claude-xclip.git ~/ssh-claude-xclip
ln -sf ~/ssh-claude-xclip/ssh-claude-xclip-server ~/.local/bin/xclip
```

설치 확인: 캡쳐 한 번 → "ssh-claude-xclip" 타이틀의 맥 알림에 경로가 뜨면 성공.

## 업데이트

이미 설치한 사람은 **맥에서** 아래 한 줄이면 최신으로 갱신된다 (파일 덮어쓰기 + 데몬 재기동).
실행 후 VS Code에서 `Developer: Reload Window`로 확장까지 반영:

```bash
curl -fsSL https://raw.githubusercontent.com/Sooa-Popupstudio/ssh-claude-xclip/main/ssh-claude-xclip-update | bash
```

서버 쪽(가짜 xclip)도 갱신하려면 **서버에서** 같은 한 줄을 실행하거나 `git -C ~/ssh-claude-xclip pull`.
(스크립트가 맥/서버를 자동 판별한다. plist는 사용자명이 박혀 있어 덮지 않으니, plist가 바뀐 릴리스면 그때만 수동 재설치.)

제거: 서버 `rm ~/.local/bin/xclip`, 맥 `launchctl unload ~/Library/LaunchAgents/ai.popup.ssh-claude-xclip.plist`
후 plist·`~/bin/ssh-claude-xclip-mac.py`·확장 폴더 삭제.

## 버전

- **v1** — 스크린샷 캡쳐(⌃⌘⇧4)나 클립보드에 복사한 이미지를 서버로 자동 업로드 →
  ⌘V로 `[Image #N]` 첨부, ⌘⇧V로 경로 타이핑. (PNG)
- **v2** — **jpg·jpeg** 지원 추가, **Finder에서 이미지 파일을 복사(⌘C)해 붙여넣기**까지 지원.
  여러 장을 한 번에 복사하면 전부 업로드되고 ⌘⇧V로 경로가 한꺼번에 타이핑된다.
