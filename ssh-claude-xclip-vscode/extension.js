const vscode = require('vscode');

function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand('ssh-claude-xclip.pastePath', async () => {
      // 클립보드 API는 항상 로컬(맥)에서 실행 → 데몬이 넣어둔 경로 텍스트를 읽는다
      const text = (await vscode.env.clipboard.readText()).trim();
      const term = vscode.window.activeTerminal;
      if (!term) { return; }
      // 데몬이 넣어둔 경로들(파일 여러 개면 여러 줄)을 모두 뽑아 공백으로 이어 타이핑.
      // 확장자는 png까지만 매칭해 :1 접미사를 자연히 떼고, sendText는 붙여넣기가 아니라
      // 타이핑이라 Claude Code가 [Image #N]으로 변환하지 않는다.
      const re = /\/tmp\/clip-[\w.-]+\.(?:png|jpe?g)/gi;
      const paths = text.match(re);
      const out = paths ? paths.join(' ') : text;
      if (out) { term.sendText(out + ' ', false); }
    })
  );
}

module.exports = { activate, deactivate: () => {} };
