# humanizer-zh（去AI味写作）

去除中文文本中的 AI 生成痕迹，让文字更自然、更像人写的。

## 来源

- 原项目：[op7418/humanizer-zh](https://github.com/op7418/humanizer-zh)（归藏翻译）
- 英文原版：[blader/humanizer](https://github.com/blader/humanizer)
- 规则依据：[Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)（WikiProject AI Cleanup 维护）
- 获取方式：2026-07-25 通过 raw.githubusercontent.com 拉取 main 分支 SKILL.md 全文（485 行），原样打包，未改动规则内容

## 包含内容

- `skills/humanizer-zh/SKILL.md` — 完整技能文件：24 种 AI 写作痕迹的检测与改写规则（内容/语言/风格/交流四大类）、快速检查清单、处理流程、5 维度质量评分表

## 未包含

- 源仓库的 README、LICENSE 等非技能文件（网络受限未拉取，不影响技能运行）
- logo 为本地生成的占位 SVG，非源仓库素材

## 使用

对着需要处理的文稿说「去AI味」「去除 AI 痕迹」「humanize」即可触发；也可以只要求「检测不改写」，先看命中报告。

## 验证

- plugin.json 为手写最小 manifest，字段均指向实际存在的文件
- SKILL.md frontmatter（name/description/allowed-tools）保留源文件原样
