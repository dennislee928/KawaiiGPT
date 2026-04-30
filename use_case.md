# Use Cases / 使用情境

> **Responsible use only.** This repository is a terminal AI chat interface that can talk to multiple LLM providers.  
> Do not use it for unauthorized access, malware creation, phishing, or any illegal activity.  
> If you are doing security work, keep it **authorized, scoped, and logged**.

---

## English

### What this project is (in practice)

KawaiiGPT is a **terminal chat interface** that can connect to different LLM backends (cloud APIs or local models).  
Because it is a general-purpose chat tool, it may be used in many contexts — including security education and red-team simulation **when properly authorized**.

### Legitimate / defensive use cases

- **Security awareness training content (authorized)**
  - Draft internal training materials, examples of “what to watch out for,” and post-mortems.
  - Generate *benign* sample messages for tabletop exercises (no real targets, no payloads).
- **Red team / purple team simulation support (authorized)**
  - Brainstorm scenarios, engagement plans, and debrief templates.
  - Create role-play scripts for controlled simulations (never real-world impersonation).
- **Developer productivity**
  - Summarize logs, explain errors, produce code snippets for *defensive* tooling, and draft documentation.
- **Research & evaluation**
  - Compare how different providers/models respond to the same prompt.
  - Track quality issues (hallucinations, inconsistency) and build a review checklist.

### Risks & recommended guardrails

- **Hallucination risk**: Treat outputs as suggestions; verify commands, code, and claims before use.
- **Data leakage**: Never paste secrets, tokens, customer data, or sensitive incident details.
- **Abuse potential**: Keep a clear policy for allowed prompts and require approvals for security simulations.

### Suggested discussion topics (for reviews or academia)

- Democratization vs. responsibility: how “easy-to-use” tools change attacker/defender balance.
- Detection signals: linguistic artifacts, consistency patterns, and model fingerprints.
- Operational safety: prompt hygiene, redaction, and auditability.

---

## 繁體中文

### 這個專案在實務上是什麼

KawaiiGPT 是一個可連接多種 LLM 供應商（雲端 API 或本機模型）的**終端機聊天介面**。  
由於它本質上是通用聊天工具，可能被用於各種情境；若涉及資安工作，務必在**合法、授權、明確範圍**內使用。

### 合法／防禦性使用情境

- **資安意識訓練內容（需授權）**
  - 產出內訓教材、注意事項範例、事後檢討（post-mortem）草稿。
  - 生成*無害*的演練訊息，用於桌上推演（不含真實目標、不含有效載荷）。
- **紅隊／紫隊演練支援（需授權）**
  - 協助發想情境、演練腳本、交付報告與復盤模板。
  - 用於受控角色扮演（避免真實世界的冒用／長期偽裝）。
- **研發效率**
  - 協助整理 log、解釋錯誤、產出*防禦性*工具的程式片段、撰寫文件草稿。
- **研究與評估**
  - 以同一 prompt 比較不同供應商／模型的回應差異。
  - 建立品質檢核清單（幻覺、前後不一致、可靠度）。

### 風險與建議護欄

- **幻覺風險**：把輸出當作建議；所有指令、程式與結論都要自行驗證。
- **資料外洩**：不要貼上金鑰、token、客戶資料、或敏感事件細節。
- **濫用風險**：訂定允許/禁止的 prompt 類型；資安演練需走審核與留痕流程。

### 建議的討論題綱（審查／學術）

- 普及化 vs. 責任：低門檻工具如何改變攻防平衡。
- 可偵測訊號：語言特徵、結構一致性與模型指紋。
- 營運安全：prompt 衛生、資料遮罩（redaction）、與稽核性（auditability）。
