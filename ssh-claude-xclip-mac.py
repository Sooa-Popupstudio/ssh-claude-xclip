#!/usr/bin/env python3
# ssh-claude-xclip-mac.py — 맥 상주 데몬 (ssh-claude-xclip의 맥 쪽 절반)
#
# 역할 하나: 클립보드 감시. 새 이미지가 들어오면(스크린샷 캡쳐 등)
#   자동으로 서버 /tmp/clip-YYYYmmdd-HHMMSS.png 에 업로드하고,
#   클립보드에 "이미지 + 경로 텍스트"를 함께 담는다.
#   → Ctrl+V: 서버의 가짜 xclip(ssh-claude-xclip-server)이 업로드된 최신 파일을 읽어 [Image #N] 첨부
#   → Cmd+Shift+V: 미니 확장(ssh-claude-xclip-vscode)이 경로를 터미널에 타이핑 (⌘클릭으로 열림)
#
# 설정은 환경변수로: SSH_CLAUDE_XCLIP_REMOTE(기본 popup-server)
# 경로 텍스트 뒤에 붙일 접미사 SSH_CLAUDE_XCLIP_PATH_SUFFIX (기본 없음 → Cmd+V 붙여넣기는 [Image #N]으로 변환됨.
# ":1"(줄번호 문법)로 주면 Cmd+V도 경로 텍스트로 남는다 — 존재하지 않는 파일명이라 변환 회피)
# 의존성 없음 (macOS 기본 python3 + osascript + ssh)
import datetime
import os
import subprocess
import tempfile
import time

REMOTE = os.environ.get("SSH_CLAUDE_XCLIP_REMOTE", "popup-server")
PATH_SUFFIX = os.environ.get("SSH_CLAUDE_XCLIP_PATH_SUFFIX", "")

# ── JXA 조각들 ──────────────────────────────────────────────
JXA_COUNT = "ObjC.import('AppKit'); $.NSPasteboard.generalPasteboard.changeCount"

# 클립보드 이미지를 PNG 파일로 저장 (Finder 파일 복사는 SKIP)
JXA_GRAB = """
ObjC.import('AppKit')
function run(argv) {
  const pb = $.NSPasteboard.generalPasteboard
  if (!pb.stringForType('public.file-url').isNil()) return 'SKIP'
  let data = pb.dataForType('public.png')
  if (data.isNil()) {
    const tiff = pb.dataForType('public.tiff')
    if (tiff.isNil()) return 'SKIP'
    const rep = $.NSBitmapImageRep.imageRepWithData(tiff)
    data = rep.representationUsingTypeProperties(4, $.NSDictionary.dictionary)
    if (data.isNil()) return 'SKIP'
  }
  return data.writeToFileAtomically(argv[0], true) ? 'OK' : 'SKIP'
}
"""

# 클립보드를 "이미지 + 경로 텍스트" 두 표현으로 다시 채움 → 새 changeCount 반환
JXA_REWRITE = """
ObjC.import('AppKit')
function run(argv) {
  const pb = $.NSPasteboard.generalPasteboard
  const data = $.NSData.dataWithContentsOfFile(argv[0])
  pb.clearContents
  pb.setDataForType(data, 'public.png')
  pb.setStringForType(argv[1], 'public.utf8-plain-text')
  return String(pb.changeCount)
}
"""

def jxa(script, *args):
    r = subprocess.run(["osascript", "-l", "JavaScript", "-e", script, *args],
                       capture_output=True, text=True, timeout=15)
    return r.stdout.strip()

def notify(msg):
    subprocess.run(["osascript", "-e",
                    f'display notification "{msg}" with title "ssh-claude-xclip"'],
                   capture_output=True, timeout=5)

# ── 클립보드 감시 → 자동 업로드 + 경로 병기 ─────────────────
def watcher():
    last = jxa(JXA_COUNT)
    while True:
        time.sleep(0.8)
        try:
            cur = jxa(JXA_COUNT)
            if not cur or cur == last:
                continue
            last = cur
            tmp = tempfile.mktemp(suffix=".png")
            if jxa(JXA_GRAB, tmp) != "OK":
                continue
            name = "clip-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".png"
            rpath = f"/tmp/{name}"
            with open(tmp, "rb") as f:
                subprocess.run(["ssh", REMOTE, f"cat > {rpath}"],
                               stdin=f, capture_output=True, timeout=20, check=True)
            # 클립보드에 이미지 + 경로 텍스트를 함께 담고, 우리가 만든 변경은 무시
            last = jxa(JXA_REWRITE, tmp, rpath + PATH_SUFFIX) or last
            os.unlink(tmp)
            notify(rpath)
        except Exception:
            pass

if __name__ == "__main__":
    watcher()
