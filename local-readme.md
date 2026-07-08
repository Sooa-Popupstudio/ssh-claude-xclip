# 로컬 설치 (popup-server 팀원용)

GitHub을 거치지 않고, **같은 서버(popup-server)에 있는 원본을 직접 끌어와** 설치하는 방법.
원본 위치: 서버 `/home/sooa/ssh-claude-xclip/`. 사용법은 [README.md](README.md)와 동일.

전제: 맥 `~/.ssh/config`에 서버 별칭(`popup-server`)이 있고 키 인증으로 접속 가능.

```bash
# 맥에서 (한번에 복사 후 붙여넣은 후 enter)
mkdir -p ~/bin && scp popup-server:/home/sooa/ssh-claude-xclip/ssh-claude-xclip-mac.py ~/bin/
scp popup-server:/home/sooa/ssh-claude-xclip/ai.popup.ssh-claude-xclip.plist ~/Library/LaunchAgents/
sed -i '' "s/YOURNAME/$(whoami)/" ~/Library/LaunchAgents/ai.popup.ssh-claude-xclip.plist
launchctl load ~/Library/LaunchAgents/ai.popup.ssh-claude-xclip.plist
scp -r popup-server:/home/sooa/ssh-claude-xclip/ssh-claude-xclip-vscode ~/.vscode/extensions/
# 이후 VS Code 완전 종료(Cmd+Q) 후 다시 실행
```

```bash
# 서버에서 (계정당 1회)
ln -sf /home/sooa/ssh-claude-xclip/ssh-claude-xclip-server ~/.local/bin/xclip
```

설치 확인: 캡쳐 한 번 → "ssh-claude-xclip" 타이틀의 맥 알림에 경로가 뜨면 성공.
서버 별칭이 `popup-server`가 아니면 plist의 `EnvironmentVariables`에
`SSH_CLAUDE_XCLIP_REMOTE=<별칭>` 추가.

제거: 서버 `rm ~/.local/bin/xclip`, 맥 `launchctl unload ~/Library/LaunchAgents/ai.popup.ssh-claude-xclip.plist`
후 plist·`~/bin/ssh-claude-xclip-mac.py`·확장 폴더 삭제.
