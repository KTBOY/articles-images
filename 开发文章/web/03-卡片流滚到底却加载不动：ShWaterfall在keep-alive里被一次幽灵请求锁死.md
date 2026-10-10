> 组件已开源：`npm i sh-design`，MIT 协议。[sh-design](https://ktboy.github.io/sh-design/)

先看效果——修复后，keep-alive 返回列表页、继续下滚，卡片一页页自动续载直到「到底了」（下图为动图）：

![sh-waterfall-keepalive-demo](https://img2024.cnblogs.com/blog/1963715/202610/1963715-20261010155731729-1413612774.gif)

> 而修复**前**，同样的操作会死死卡在「已显示 40 条」，滚到底也不再加载——这就是本文要拆解的坑。

## 起因：滚到底，卡片却死活不再加载

后台有个「教室满载分析」页面，卡片流（瀑布流）展示，一次拉 20 条、向下滚动触底自动续拉。用的是我自己维护的组件库 `sh-design` 里的 `ShWaterfall`。

线上反馈一个很诡异的现象：

![sh-waterfall-production-symptom](https://img2024.cnblogs.com/blog/1963715/202610/1963715-20261010155747403-2112789857.png)

> 底部提示「共 145 条，已显示 40 条，向下滚动显示更多数据」，但**鼠标滚轮滚到底，就是不再请求下一页了**。

诡异之处在于——它不是必现。刷新页面重进，一切正常；可一旦**点开某张卡片进详情、再返回列表**，回来后再往下滚，就大概率卡死在"已显示 40 条"。

第一反应是父组件的分页状态机写错了。但顺着排查下来，真正的坑藏在了组件库 `ShWaterfall` 内部的一个"触底锁"里。这篇文章完整记录一次**组件级 bug 的定位与自愈式修复**。

## 先给结论：为什么只有"卡片模式"会中招

这个页面同时有「卡片」和「列表（表格）」两种视图，可以一键切换。诡异的是——**同样的进详情再返回操作，表格模式从来不会卡，只有卡片模式会。**

这不是巧合。触底加载卡死，必须**同时**满足三个条件：

| # | 条件 | 卡片模式 | 表格模式 |
| --- | --- | --- | --- |
| ① | 组件内部有"**消耗式**"触底锁（触发一次就上锁，只能靠数据/loading 变化解锁） | ✅ `ShWaterfall` 的 `armed` | ❌ 表格是服务端分页，翻页点按钮，压根没有这种锁 |
| ② | keep-alive 失活时容器宽度归 0，触发一次"**幽灵 load-more**"把锁白白消耗掉 | ✅ | —（无锁可消耗） |
| ③ | 父组件把这次 `load-more` **吞了**（既不翻 `loading` 也不加数据），导致锁再也等不到复位 | ✅ 失活守卫 `if(!active) return` | — |

三者叠加才触发，缺一个都复现不了。这也解释了为什么它"有时卡有时不卡"——取决于你返回前是不是正好停在触底位置、返回后有没有继续滚。

而表格模式为什么天然免疫？因为它用的是 `advance-table`（服务端分页 + 页码），或者退一步说，就算某些表格用了滚动加载，也是**每次 scroll 事件都按滚动位置现算现判**，没有"发射即消耗"的锁。哪怕失活期间漏触发一次，回到页面再滚一下就重新判定了——**天然自愈**。

> 一句话：**bug 的本质，是 `ShWaterfall` 的 `armed` 锁"复位完全依赖外部配合"，而 keep-alive 恰好制造了一个"外部必然不配合"的场景。**

## 这组件的触底加载：不监听 scroll，交给 IntersectionObserver

要看懂这个 bug，得先看懂 `ShWaterfall` 的触底加载**凭什么这么写**。这里有个很容易被忽略、却是本组件最大卖点的决策：

> **它判断"该不该加载下一页"，压根没有监听 `scroll` 事件，而是用 `IntersectionObserver` 让浏览器替它盯着。**

**传统"滚动加载"几乎都是监听 scroll**：给滚动容器绑一个 `scroll` 回调，用户每滚一下回调就触发一次，在回调里读 `scrollTop / scrollHeight / clientHeight` 算"离底还有多远"，够近了就拉下一页。这个套路能用，但绕不开三个毛病：

- **事件太密**：一次快速滚动，`scroll` 一秒能被触发上百次，每次都要跑一遍判定，不手动节流（`throttle` / `rAF`）就掉帧；
- **读几何 = 可能 reflow**：`getBoundingClientRect` / `scrollTop` 这类属性在"改过样式之后"再读，会强制浏览器同步重排，是滚动卡顿的常见元凶；
- **得先找对"谁在滚"**：容器滚？`window` 滚？某个祖先 `div` 滚？绑错对象直接不触发；而且 `scroll` 不冒泡，跨容器还得 `capture`。

**`ShWaterfall` 没走这条路。** 它在列表底部放一个 1px 的**哨兵元素**，用 `IntersectionObserver` 观察它和视口的相交，**只在"哨兵进入视口"那一刻回调一次去请求下一页**：

```ts
// 组件挂载时绑定：只观察"底部哨兵 vs 视口"的相交，不碰任何 scroll 事件
loadIo = new IntersectionObserver(
  (entries) => {
    if (entries.some((e) => e.isIntersecting)) {
      updateScrollState()
      maybeLoadMore(true) // ← 哨兵进视口，才派发 load-more
    }
  },
  { root, rootMargin: `0px 0px ${threshold}px 0px` }
)
loadIo.observe(sentinel)
```

区别是本质性的——**从"我每一帧主动去问：到底了没？"变成"浏览器替我盯着，到底了才通知我一次"**：

| 维度 | 监听 scroll（传统做法） | IntersectionObserver（本组件） |
| --- | --- | --- |
| **触发频率** | 每秒上百次，必须节流 | 只在"哨兵跨越视口边界"时触发，1 次 |
| **读几何 / reflow** | 每次回调读 `scrollTop`/`rect`，易触发重排 | 相交判定在浏览器内部调度，主线程**零 reflow** |
| **找滚动源** | 必须绑对正在滚动的元素 | **与"谁在滚"解耦**，window / 祖先 / 自身都可靠 |
| **空闲开销** | 一滚就高频跑逻辑 | 不滚、不跨界就**完全静默** |

一句话：这套设计把"**高频轮询式的滚动监听**"换成了"**事件驱动的一次性通知**"，又准又省——这也是 `ShWaterfall` 敢同时支持 `self` / `window` 双滚动模式、还不用你操心"到底谁在滚"的底气所在。

（但请记住这份"优雅"——**这次的 bug，恰恰就埋在它里面**，是一体两面。）

正因为"触底加载完全交给 IO 哨兵"，组件的滚动回调 `onScroll` 就**刻意只干一件事**：更新虚拟列表的可视区间，**不再做触底判定**。这是"与滚动来源解耦"的代价——滚动这条路径，被从触发环节里请了出去。

而 `IntersectionObserver` 是**边沿触发**的：它只在"从不相交 → 相交"那一刻回调。当你从详情页返回，列表滚动位置被 keep-alive 原样保留，哨兵**一直待在视口里**，没有产生新的交叉边 → IO 从此静默。

此刻，如果 `armed` 锁又正好被一次"幽灵请求"卡死（下一节细讲），组件就**没有任何第二条恢复路径**了：

- IO 不动了（哨兵一直在视口内，没有新交叉边）；
- 滚动不归它管（设计上已把触底判定交给了 IO）；
- 数据也没变（根本没在加载）。

> **优势与灾难同源**：正是"不依赖滚动来源"这个优雅设计，把"每次滚动都重新判一次"这张安全网连根拔掉了。传统 scroll 方案看着笨——每次滚动都算一遍、还要节流——但它有个朴素却宝贵的性质：**只要用户还在滚，就永远有机会重新触发，天然不会永久卡死。** `ShWaterfall` 为了优雅，把这个性质让渡了出去。

理解了这个"一体两面"，也就理解了后面修复方案里**第三层**的用意：它把触底检查**重新加回滚动路径**。这看似"退回传统做法"，实则是在保留 IO 全部优势（解耦、零 reflow）的前提下，用 `armed` + `remain` 双重去重补回那张被拔掉的安全网——**优雅和鲁棒，不必二选一。**

## 追根溯源：`armed` 锁是怎么被"幽灵请求"耗死的

先看 `ShWaterfall` 里这个锁的设计。它的初衷很好——防止底部哨兵在视口里反复进出时无脑连发 `load-more`：

```ts
// load-more 触发锁：触发一次后上锁，数据变化 / loading 结束后再解锁
let armed = true

function maybeLoadMore(force = false) {
  if (!armed || props.loading || props.finished) return
  if (!force) {
    const remain = totalHeight.value - (scrollTop.value + viewHeight.value)
    if (remain >= props.threshold) return
  }
  armed = false        // ① 派发即上锁
  emit('load-more')
}
```

解锁只有两个来源：

```ts
// 来源 A：数据变了（父组件真的追加了新数据）
watch([() => props.items, () => props.items.length], ([list, len], [oldList]) => {
  armed = true
  // ...增量布局
})

// 来源 B：loading 从 true 变回 false（父组件真的走完了一次加载）
watch([() => props.loading, () => props.finished], ([loading, finished]) => {
  if (!loading && !finished) {
    armed = true
    // ...补一次触底检查
  }
})
```

注意这两个解锁来源隐含的**强假设**：**父组件收到 `load-more` 后，一定会「追加数据」或「翻转 loading」。** 只要父组件老实干活，锁就一定能被解开。

问题就出在 keep-alive 失活的那一瞬间，这个假设被打破了。

### 失活瞬间发生了什么

当你点开卡片进详情，`ShWaterfall` 所在的列表页被 `<keep-alive>` **失活**（DOM 从文档里摘除、但组件实例缓存保留）。容器一被摘除，它的 `clientWidth` 立刻变成 **0**。而组件里挂了个 `ResizeObserver` 负责响应尺寸变化：

```ts
ro = new ResizeObserver(() => {
  const el = container.value
  if (el.clientWidth !== viewWidth.value) {
    resizeTimer = setTimeout(() => {
      measure()      // viewWidth 被更新为 0
      rebuild()      // 宽度 0 → 算不出列 → totalHeight 归 0
      nextTick(() => maybeLoadMore())   // ⚠️ 触发幽灵检查
    }, 120)
  }
})
```

于是链路走通了：`totalHeight` 变成 0 → `maybeLoadMore()` 里 `remain = 0 - (scrollTop + viewHeight)` 必然算出**负数**，铁定小于 `threshold` → **上锁 `armed=false` 并派发一次 `load-more`**。

可这次 `load-more` 是毫无意义的——组件都不可见了，加载给谁看？更致命的是父组件的处理：

```ts
// 父组件（useCardWaterfall）为避免失活态无限翻页，加了失活守卫
const loadPage = async () => {
  if (!active.value || loading.value || !hasMore.value) return  // ⚠️ 直接吞掉
  // ...
}
```

父组件一看"我正失活呢"，直接 `return`——**不翻 `loading`、不追加 `items`**。于是：

- `armed` 已经被那次幽灵派发置成了 `false`；
- 解锁来源 A（items 变化）没发生；
- 解锁来源 B（loading true→false）也没发生。

**锁，就这么永久卡死在 `false` 了。**

### 返回后为什么救不回来

好，现在你返回卡片列表页。此时锁是 `false`，`maybeLoadMore` 第一行 `if (!armed) return` 直接把所有路径堵死：

- **底部哨兵的 IntersectionObserver**：你返回时列表还停在原来的滚动位置，哨兵一直待在视口里，IO 是**边沿触发**的——没有"从不可见到可见"的新交叉边，就不会再回调；
- **滚动**：`onScroll` 只更新虚拟列表的可视区间，压根不调用 `maybeLoadMore`——**滚动这条路径，从设计上就不负责触发加载**。

三条触发路（IO / 滚动 / 数据变化）全部哑火。于是你滚到底，什么都不会发生。截图里那个"已显示 40 条"，就是这么卡住的。

## 修复：给触底锁装上三层"自愈"

定位清楚了，修复思路也就明确了——**不能把"外部一定配合"当成理所当然，组件要能自己从卡死里恢复。** 我在 `ShWaterfall` 里加了三层防御：

### 第一层：不可见时，根本不消耗锁（治本）

容器宽度归 0（失活 / `display:none`）时，几何判定本来就是失真的，这时候派发 `load-more` 毫无意义。直接跳过，**保持 `armed` 原状**：

```ts
function maybeLoadMore(force = false) {
  // 容器不可见时宽度归 0，几何判定失真：
  // 若照常消耗 armed 派发 load-more，父组件多半会忽略，
  // 而 loading / items 均不变 → armed 再也无法复位，恢复可见后触底永久失效。
  // 故不可见时直接跳过、保持 armed 原状，待重新可见时再评估。
  if (viewWidth.value <= 0) return
  if (!armed || props.loading || props.finished) return
  // ...
}
```

这一层直接从源头掐断了"幽灵派发"——失活期间锁压根不会被消耗，返回时它还是 `true`。

### 第二层：恢复可见时，主动复位并复查（keep-alive 快速自愈）

光有第一层还不够优雅。返回页面时，虽然锁没被消耗，但要不要立刻补加载，取决于 `ResizeObserver` 那个 120ms 防抖回调什么时候跑。干脆用 `onActivated` 钩子主动来一发：

```ts
// keep-alive 恢复可见：立即重测 + 解锁 + 复查触底，
// 不依赖 ResizeObserver 的 120ms 防抖，回到页面瞬间即可续载。
// 非 keep-alive 场景该钩子永不触发，零副作用。
onActivated(() => {
  measure()
  rebuild()
  armed = true
  nextTick(() => {
    updateScrollState()
    maybeLoadMore()
  })
})
```

回到缓存页的瞬间就重测尺寸、解锁、复查触底。对没套 keep-alive 的普通用法，`onActivated` 根本不触发，零副作用。

### 第三层：滚动本身就是一条触发通道（通用兜底）

前两层已经能解决这个具体 bug。但我想让组件更皮实一点——**"滚到底"这个动作，本身就该能触发加载**，不该只依赖 IO 的边沿。于是在滚动的 rAF 回调里补一次非强制检查：

```ts
function onScroll() {
  if (rafId) return
  rafId = requestAnimationFrame(() => {
    rafId = 0
    updateScrollState()
    emit('scroll', { scrollTop: scrollTop.value })
    // 滚动即"用户正在接近底部"的信号，补一次非强制触底复查：
    // 覆盖哨兵一直停在视口内、IO 不再产生新交叉边的场景，
    // 让"滚到底"始终是一条可用的触发通道（armed + remain 双重去重，不会级联）
    maybeLoadMore()
  })
}
```

`maybeLoadMore()`（非 force）里有 `remain >= threshold` 的早退，只有真的快到底部才会触发；再加上 `armed` 去重，绝不会级联刷屏。

## 效果对比

修复前后各录一次同样的操作（滚到底 → 进详情 → 返回 → 继续滚到底）：

![image](https://img2024.cnblogs.com/blog/1963715/202610/1963715-20261010155907093-14729488.png)

- **修复前**：返回后无论怎么滚，底部永远停在「已显示 40 条」：

![image](https://img2024.cnblogs.com/blog/1963715/202610/1963715-20261010155920673-1082703737.png)

- **修复后**：返回后继续下滚，第 3、4、5 页接连加载，直到「已经到底了」：

![image](https://img2024.cnblogs.com/blog/1963715/202610/1963715-20261010155927957-1669560833.png)

## 复盘：四条设计教训

1. **别把"外部契约一定成立"写进内部状态机。** `armed` 锁的复位完全押宝在"父组件一定配合"上，这是典型的乐观假设。健壮的内部锁，必须有一条不依赖外部的复位路径。
2. **虚拟滚动 / 无限加载组件，要考虑 keep-alive 与 `display:none`。** 容器宽度归 0 是这类组件的"暗物质"——它会污染所有基于尺寸的几何计算。凡是 `remain`、`clientWidth` 一类的判定，都得先问一句"我现在真的可见吗"。
3. **触发通道别只留一条边沿。** IO 边沿触发 + 滚动不复查，组合起来就是"错过即永失"。给"滚动"也开一条活的触发通道，鲁棒性天差地别。
4. **一个优雅设计的优势，往往就是它 bug 的来源。** 本次最反直觉的一点：让 `ShWaterfall` 引以为傲的"与滚动来源解耦"，恰恰是"滚动救不回它"的根因——**优势越纯粹，反面就越脆弱**。选型时不只要看"这个设计强在哪"，更要追问一句"它的优势在极端场景下会不会反过来咬我一口"。真正成熟的修复不是推翻优势，而是在保住优势的前提下补一条兜底路（本文第三层）。

## 如果是 AI 写的这段，能躲过这个坑吗？

现在很少人提"古法编程"了——新项目里，像 `IntersectionObserver` 哨兵、虚拟列表、`armed` 去重锁这些，多半是让 AI 生成、改改就上了。那问题来了：**这个 bug，AI 会不会一开始就帮你规避掉？**

我的判断可能反直觉：**大概率不会，甚至 AI 更容易写出这个坑。** 三个原因：

1. **AI 擅长"看起来对"，不擅长"跑起来对"。** 你让 AI 写个无限滚动，它会给你一份教科书级的 IO + 去重锁——触发即上锁、数据变化再解锁，逻辑自洽、命名漂亮。可这个 bug 的根子是一个**乐观假设**（"父组件收到 load-more 后一定会配合"）。这种假设就藏在"看起来对"的代码里，而 AI 从海量"看起来对"的开源代码里学来的，恰恰就是它。
2. **AI 没"运行过你的代码"，也没经历过 keep-alive 失活那一瞬间。** 这个坑要三个条件跨文件、跨运行时叠加才炸：组件的锁 + keep-alive 让宽度归 0 + 父组件的失活守卫吞事件。它不在任何单个函数里，而在**三者的时序缝隙**里。AI 读得到每个函数，却读不到"你返回详情页时浏览器怎么调度那个 ResizeObserver"。
3. **越优雅的抽象，越能把坑藏深。** 前面说过"优势即隐患"。AI 最爱优雅抽象（解耦、事件驱动），于是也最容易把"滚动救不回它"这类反面一起复制进来，且写得天衣无缝。

**那 AI 在这件事上帮到什么？帮在了"人不愿意干"的部分——而这恰恰是它的正确用法：**

- 去啃 `node_modules` 里编译后的 `sh-design.js`，逆向出 `armed` 的复位链路（人很少愿意读压缩产物）；
- 跨 `waterfall.vue` / `useCardWaterfall.ts` / 三个卡片页，把那条"幽灵 load-more"的调用链一路追出来；
- 搭 playground 的 keep-alive 复现、跑 dev、逐帧截图对比

**但真正决定性的两下，是人给的**：一句"这明明还有数据却不更新了，是不是组件的问题？"和一个"只有卡片模式才可能复现吧？"的判断——这俩方向感，AI 当时并没有主动想到。**AI 把三天的体力活压缩成半小时，但"往哪挖"的那两下，还是人的直觉。**

**最后，用更好的AI就能解决！**

---

修复已并入 [sh-design](https://ktboy.github.io/sh-design/)，业务侧无需再自行加"激活脉冲"之类的临时规避。如果你也在自己的组件里踩过类似的"消耗式锁"坑，欢迎交流。
