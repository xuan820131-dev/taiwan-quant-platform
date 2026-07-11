# Taiwan Quant Platform（TQP）

台股法人籌碼、量化研究、回測與自動化分析平台。

## 專案目標

- 整合 TWSE／TPEx 官方市場資料
- 研究外資、投信、自營商與三大法人同步籌碼
- 建立法本比、法量比、FBI、法人成本與法人資金流因子
- 進行產業輪動、盤後選股、隔日當沖與策略回測
- 發展 Dashboard、AI 每日報告、LINE Bot 與 n8n Agent

## 開發要求

- 使用繁體中文文件與重要註解
- 寫程式前先確認官方 API 與欄位結構
- 不猜測資料單位或欄位名稱
- 優先小步修改，保持模組化與可維護性
- 所有策略必須回測，並納入交易成本與流動性

## AI 閱讀順序

1. `README.md`
2. `AI_CONTEXT.md`
3. `PROJECT_RULES.md`
4. `ROADMAP.md`
5. `docs/QUANT_RESEARCH.md`

## 目錄

```text
taiwan-quant-platform/
├── README.md
├── AI_CONTEXT.md
├── PROJECT_RULES.md
├── ROADMAP.md
├── .gitignore
├── docs/
│   └── QUANT_RESEARCH.md
├── src/
├── data/
├── output/
├── tests/
├── config/
└── scripts/
```

## 目前狀態

專案處於基礎建設階段。第一優先是整理既有程式、確認官方資料來源、建立統一資料模型與回測骨架。
