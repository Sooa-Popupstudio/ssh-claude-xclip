const vscode = require('vscode');

function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand('ssh-claude-xclip.pastePath', async () => {
      // 클립보드 API는 항상 로컬(맥)에서 실행 → 데몬이 넣어둔 경로 텍스트를 읽는다
      const text = (await vscode.env.clipboard.readText()).trim();
      const term = vscode.window.activeTerminal;
      if (!term) { return; }
      // 데몬이 붙인 :1 접미사는 떼고 순수 경로만 타이핑 (sendText는 붙여넣기가 아니라
      // 타이핑이라 Claude Code가 [Image #N]으로 변환하지 않는다)
      const m = text.match(/^(\/tmp\/clip-[\w.-]+\.png)/);
      const out = m ? m[1] : text;
      if (out) { term.sendText(out + ' ', false); }
    })
  );
}

module.exports = { activate, deactivate: () => {} };
