# 配图生成记录（guizang-material-illustration）

## superprogramming-four-step-loop.png

- 概念：SuperProgramming 四步闭环，强调「任何改动都得完整走一遍，修 bug 和重构也不例外」
- 结构：Cycle（循环图）
- 配色：IKB Blue `#002FA7`（技术流程默认色）
- 比例：16:9（1792x1024）
- 输出路径：`开发文章/java/图片/superprogramming-four-step-loop.png`
- 旧版：`superprogramming-four-step-loop-neon-old.png`（深色霓虹 + 英文标签，不符合 Guizang 视觉系统，已弃用，可删）

### 最终 prompt

```text
Use case: stylized-concept.
Asset type: 16:9 labeled material illustration for a technical article graphic about an AI-assisted development workflow that never stops looping.

Primary request: A four-step development loop shown as a simple cycle. Four small physical model objects sit at the four positions of a circular arrow path, connected by one continuous thick circular arrow that clearly flows clockwise and returns to the start: at top-center a small 3D lightbulb block on a low pedestal (requirement clarification), at right a small 3D clipboard tablet with a short checklist of three ticked lines (step-by-step plan), at bottom-center a small 3D code block plate showing abstract angle-bracket marks and a tiny test tick badge (test-first implementation), at left a small 3D shield-and-document block (wrap-up and review). Inside the circle center place one small gear model to signal continuous repetition. Add one extra thinner curved return arrow along the outside of the left segment, pointing from the shield block back up to the lightbulb, to show that even a bug fix or refactor must run the whole loop again. The four objects should be equal in visual weight so no single step looks dominant.

Chinese labels: Add five short Simplified Chinese labels as clean printed callouts inside the illustration: "澄清需求" near the top-center lightbulb, "拆解计划" near the right clipboard, "先测后写" near the bottom-center code block, "收尾复盘" near the left shield, and "改动重来" placed on a small white callout plate beside the outer return arrow on the left. Keep every label horizontal, large, high-contrast dark ink text, correctly written Simplified Chinese, and away from all edges.

Style/medium: clean Swiss editorial 3D vector-like illustration, off-white studio background, black ink outlines, refined light gray physical surfaces, one vivid IKB blue accent (#002FA7) used only for the circular arrows, the return arrow, and small connector dots. Soft studio light with mild contact shadows, no dramatic gradients. Objects feel like small physical desk models, not flat app UI.

Composition/framing: 16:9 composition, the whole cycle centered horizontally and vertically, subject fills the frame naturally, generous safe margins on all sides, full subject visible, nothing cropped.

Lighting/mood: crisp studio light, calm analytical mood.

Constraints: no extra words beyond the five specified Chinese labels, no English text, no numbers, no logo, no watermark, no poster frame, no page title, no legend box, no decorative blobs, no gradient background, no dark background, no neon glow.
```

### 备注

- 左上区域出现了两条近似平行的蓝色箭头（主循环 + 外侧回流），视觉上略重复但语义正确，保留。
- 若后续要与文章其他配图统一，`cover-frontend-to-fullstack-ai.png` 和 `vibe-coding-vs-rules.png` 仍是旧风格，需要一起重做才算一套。
