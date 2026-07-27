// 瀑布流分配算法基准测试：最矮列优先 vs 取模轮流
// 模拟组件 _distribute 的核心逻辑，比较两种策略的耗时与列高平衡度

const RATIOS = [0.72, 0.86, 1.0, 1.16, 1.3]
const COL_W = 345 // 两列、gap 20rpx 时的单列宽
const TITLE_H = 56

function makeItems(n) {
  const items = []
  for (let i = 0; i < n; i++) {
    items.push({ h: Math.round(COL_W * RATIOS[i % RATIOS.length]) + TITLE_H })
  }
  return items
}

// 策略 A：最矮列优先（组件采用的方式）
function shortestFirst(items, nCols) {
  const cols = Array.from({ length: nCols }, () => ({ h: 0, count: 0 }))
  for (const it of items) {
    let min = 0
    for (let i = 1; i < nCols; i++) if (cols[i].h < cols[min].h) min = i
    cols[min].h += it.h
    cols[min].count++
  }
  return cols
}

// 策略 B：按索引取模轮流分配
function roundRobin(items, nCols) {
  const cols = Array.from({ length: nCols }, () => ({ h: 0, count: 0 }))
  items.forEach((it, i) => {
    cols[i % nCols].h += it.h
    cols[i % nCols].count++
  })
  return cols
}

function gap(cols) {
  const hs = cols.map((c) => c.h)
  return Math.max(...hs) - Math.min(...hs)
}

function bench(fn, items, nCols, rounds = 200) {
  // 预热 + 15 轮取中位数，压掉 JIT / GC 带来的抖动
  for (let i = 0; i < 50; i++) fn(items, nCols)
  const samples = []
  for (let r = 0; r < 15; r++) {
    const t0 = performance.now()
    for (let i = 0; i < rounds; i++) fn(items, nCols)
    samples.push((performance.now() - t0) / rounds)
  }
  samples.sort((a, b) => a - b)
  return samples[7]
}

console.log('N\t列数\t最矮列耗时(ms)\t轮流耗时(ms)\t最矮列高差(rpx)\t轮流列高差(rpx)')
for (const n of [50, 200, 500, 1000, 2000, 5000]) {
  for (const cols of [2, 3]) {
    const items = makeItems(n)
    const tA = bench(shortestFirst, items, cols)
    const tB = bench(roundRobin, items, cols)
    const gA = gap(shortestFirst(items, cols))
    const gB = gap(roundRobin(items, cols))
    console.log(`${n}\t${cols}\t${tA.toFixed(4)}\t\t${tB.toFixed(4)}\t\t${gA}\t\t${gB}`)
  }
}

// 随机比例场景（更接近真实接口返回的图片，宽高比不规律）
console.log('\n随机宽高比场景（0.6~1.5 随机，取 100 次平均列高差）：')
for (const n of [50, 200, 1000]) {
  let sumA = 0
  let sumB = 0
  for (let r = 0; r < 100; r++) {
    const items = []
    for (let i = 0; i < n; i++) {
      items.push({ h: Math.round(COL_W * (0.6 + Math.random() * 0.9)) + TITLE_H })
    }
    sumA += gap(shortestFirst(items, 2))
    sumB += gap(roundRobin(items, 2))
  }
  console.log(`N=${n}: 最矮列平均高差 ${(sumA / 100).toFixed(0)}rpx，轮流平均高差 ${(sumB / 100).toFixed(0)}rpx`)
}

// setData 数据量：整体重建 vs 只追加新页时传输的 cols JSON 体积
console.log('\nsetData 传输量估算（cols 序列化后字节数）：')
function buildCols(n) {
  const cols = [ { list: [], h: 0 }, { list: [], h: 0 } ]
  for (let i = 0; i < n; i++) {
    const h = Math.round(COL_W * RATIOS[i % RATIOS.length])
    let min = cols[0].h <= cols[1].h ? 0 : 1
    cols[min].list.push({
      _wfId: i, _h: h, _loaded: false,
      _src: `https://cdn.example.com/img/photo_${i}_large.jpg`,
      _fallback: `https://cdn.example.com/img/photo_${i}_thumb.jpg`,
      _title: `图片标题 ${i}`,
      _raw: { url: `https://cdn.example.com/img/photo_${i}_large.jpg`, title: `图片标题 ${i}` },
    })
    cols[min].h += h + TITLE_H
  }
  return cols
}
for (const pages of [1, 5, 10, 25]) {
  const n = pages * 20
  const size = Buffer.byteLength(JSON.stringify(buildCols(n)))
  console.log(`累计 ${n} 条（第 ${pages} 页）: cols 全量约 ${(size / 1024).toFixed(1)} KB`)
}
