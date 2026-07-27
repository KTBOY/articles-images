// 把两张 ECharts 图的 base64 内嵌到文章末尾（追加「附：性能数据可视化」小节）
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const dir = path.dirname(fileURLToPath(import.meta.url))
const article = path.join(dir, '..', '01-小程序瀑布流：170行代码干掉布局抖动.md')

function readDataUrl(i) {
  let s = fs.readFileSync(path.join(dir, `chart${i}-base64.json`), 'utf8').trim()
  if (s.startsWith('"')) s = JSON.parse(s)
  if (!s.startsWith('data:image/png;base64,')) throw new Error(`chart${i} 不是合法 data URL`)
  return s
}

const chart1 = readDataUrl(1)
const chart2 = readDataUrl(2)

let md = fs.readFileSync(article, 'utf8')

const MARK = '## 附：性能数据可视化'
// 幂等：已存在则先移除旧小节再追加
const idx = md.indexOf(MARK)
if (idx !== -1) md = md.slice(0, idx).trimEnd() + '\n'

const section = `
${MARK}

上文两组基准数据的图表版（ECharts 绘制，数据来自 \`waterfall-bench.mjs\`，base64 内嵌、无外链依赖）。

耗时曲线印证了前面的结论：取模轮流确实始终更快（虚线），但两条线的绝对差距在 5000 条时也不过 0.01ms——这点开销买不来任何用户可感知的卡顿：

![不同数据量下两种分配策略的耗时对比](${chart1})

而列高差是肉眼可见的差距。取模轮流（橙色）随数据量线性恶化，1000 条时已经差出 2253rpx（约三屏）；最矮列优先（蓝色）始终压在 200rpx 上下：

![随机宽高比场景下两种策略的列高差对比](${chart2})

一句话读图：**耗时上两种策略是"都快"和"更快"的区别，列高上是"整齐"和"瘸腿"的区别**——所以选最矮列优先。
`

md = md.trimEnd() + '\n' + section
fs.writeFileSync(article, md)
console.log('已写入。文章大小：', (fs.statSync(article).size / 1024).toFixed(1), 'KB')
