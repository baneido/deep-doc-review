# Report template (RUN/report.md)

Write in the report language (default Japanese). Japanese headings shown; English equivalents in brackets.

```markdown
# Deep Review レポート: <文書タイトル>  [Deep Review report]

- 対象: `<DOC path>`（<N> 行） / 実行日時: <YYYY-MM-DD HH:MM TZ> / 所要時間: <m> 分
- 実行環境: <Claude Code | Codex CLI> (<model if known>) / 深さ: <quick|standard|thorough>
- 区間: <S> / レビュージョブ: <M>（並列 | 逐次） / 外部情報による裏取り: <未実施 | 実施（web）>

## 判定 [Verdict]
**<要大幅修正 major_revision | 要軽微修正 minor_revision | 受理可 accept | 差し戻し reject>**

## 総評 [Overall assessment]
<3–6 sentences>

## 優先対応事項 [Top priorities]
1. F1: <short action>
2. ...

## 良い点 [Strengths]
- ...

## 指摘事項 [Findings]（重大度順 / 棄却を除く）
| ID | 重大度 | 種類 | 行 | 概要 | 再検証 |
|---|---|---|---|---|---|
| F1 | critical | contradiction | L30, L39 | ... | confirmed |

### F1 [critical / contradiction] L0030–L0039 — <one-line title>
- **引用**: 「<quote>」
- **問題**: <issue>
- **根拠**: <evidence — recomputation or conflicting lines>
- **修正案**: <suggestion>
- **関連箇所**: L0089 / **検出**: S3#A, S4#C（支持 3） / **再検証**: confirmed — <verify_note>

## 再検証で棄却された指摘（参考） [Rejected by re-verification]
- F9: <issue> — 棄却理由: <verify_note>

## 分割と予算配分 [Segmentation & budget]
| 区間 | 行 | 種類 | 難易度 | パス | 理由 |
|---|---|---|---|---|---|

## 制約 [Limitations]
- <e.g. scope limited to sections 3–5; web grounding not performed; sequential mode (no subagents)>
```
