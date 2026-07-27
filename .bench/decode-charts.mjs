// 校验并解码 evaluate_script 导出的 base64 图表
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const dir = path.dirname(fileURLToPath(import.meta.url))

for (const i of [1, 2]) {
  const p = path.join(dir, `chart${i}-base64.json`)
  if (!fs.existsSync(p)) {
    console.log(`chart${i}: 文件不存在 ${p}`)
    continue
  }
  let s = fs.readFileSync(p, 'utf8').trim()
  if (s.startsWith('"')) s = JSON.parse(s)
  console.log(`chart${i}: 前缀=${s.slice(0, 30)} 长度=${s.length}`)
  const b64 = s.replace(/^data:image\/png;base64,/, '')
  fs.writeFileSync(path.join(dir, `chart${i}-preview.png`), Buffer.from(b64, 'base64'))
}
