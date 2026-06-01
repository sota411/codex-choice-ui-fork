# Codex CLI 自分用改造版

OpenAI Codex CLI を自分用に調整した fork です。

## 主な変更

- `request_user_input` の `Other` を既定表示しないように変更
- 自由記入が必要な場合だけ `isOther: true` で `Custom answer` を表示
- Plan Mode の選択肢ルールを 2-6 択前提に調整

## 動作確認

```bash
cd codex-rs
```

```bash
just test -p codex-core request_user_input
```

```bash
just test -p codex-tui request_user_input
```

## ライセンス

元リポジトリと同じく Apache-2.0 License です。
