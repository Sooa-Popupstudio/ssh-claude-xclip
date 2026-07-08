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

# Finder에서 복사(⌘C)한 "이미지 파일"만 취급 — 이 확장자들만 업로드 대상.
# 실측으로 Claude Code 첨부가 확인된 포맷만 둔다 (png/jpg 확인, heic는 미첨부라 제외).
IMG_EXTS = (".png", ".jpg", ".jpeg")

# ── JXA 조각들 ──────────────────────────────────────────────
JXA_COUNT = "ObjC.import('AppKit'); $.NSPasteboard.generalPasteboard.changeCount"

# 클립보드의 이미지 "데이터"를 PNG 파일로 저장 (파일 복사는 watcher (1)분기에서 먼저
# 처리하므로, 여기 도달하는 file-url은 이미지 아닌 파일이라 SKIP)
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

# 클립보드에 담긴 파일 URL을 "전부" 읽어 로컬 경로 목록(줄바꿈 구분)으로 반환.
# stringForType로 첫 항목만 보던 걸 pasteboardItems(item 배열) 순회로 바꿔 N개를 다 집는다.
JXA_FILE_URLS = """
ObjC.import('AppKit')
function run() {
  const pb = $.NSPasteboard.generalPasteboard
  const items = pb.pasteboardItems
  if (items.isNil()) return ''
  const out = []
  for (let i = 0; i < items.count; i++) {
    const u = items.objectAtIndex(i).stringForType('public.file-url')
    if (u.isNil()) continue
    const url = $.NSURL.URLWithString(u)
    if (url.isNil() || url.path.isNil()) continue
    out.push(ObjC.unwrap(url.path))
  }
  return out.join('\\n')
}
"""

# 클립보드를 "경로 텍스트(여러 줄)"만으로 다시 채움 → 새 changeCount 반환.
# 파일 복사는 원본이 이미 파일이라 이미지 데이터를 다시 넣을 필요 없이 경로만 남긴다.
JXA_SET_TEXT = """
ObjC.import('AppKit')
function run(argv) {
  const pb = $.NSPasteboard.generalPasteboard
  pb.clearContents
  pb.setStringForType(argv[0], 'public.utf8-plain-text')
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

def upload(local_path, rpath):
    with open(local_path, "rb") as f:
        subprocess.run(["ssh", REMOTE, f"cat > {rpath}"],
                       stdin=f, capture_output=True, timeout=60, check=True)

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

            # (1) Finder에서 이미지 "파일"을 복사(⌘C) — 여러 개면 전부 업로드하고
            #     경로를 여러 줄로 병기 (⌘⇧V가 다 타이핑, ⌘V는 텍스트로 붙음)
            files = [p for p in jxa(JXA_FILE_URLS).splitlines()
                     if p.lower().endswith(IMG_EXTS) and os.path.isfile(p)]
            if files:
                ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                rpaths = []
                for i, lp in enumerate(files):
                    ext = os.path.splitext(lp)[1].lower()
                    rpath = f"/tmp/clip-{ts}-{i}{ext}"
                    upload(lp, rpath)
                    rpaths.append(rpath)
                text = "\n".join(rp + PATH_SUFFIX for rp in rpaths)
                last = jxa(JXA_SET_TEXT, text) or last
                continue

            # (2) 이미지 "데이터"가 클립보드에 (스크린샷 캡쳐, 브라우저 이미지 복사 등)
            #     — 기존 단일 흐름: 임시 PNG로 뽑아 업로드하고 이미지+경로 병기
            tmp = tempfile.mktemp(suffix=".png")
            if jxa(JXA_GRAB, tmp) != "OK":
                continue
            name = "clip-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".png"
            rpath = f"/tmp/{name}"
            upload(tmp, rpath)
            # 클립보드에 이미지 + 경로 텍스트를 함께 담고, 우리가 만든 변경은 무시
            last = jxa(JXA_REWRITE, tmp, rpath + PATH_SUFFIX) or last
            os.unlink(tmp)
        except Exception:
            pass

if __name__ == "__main__":
    watcher()
