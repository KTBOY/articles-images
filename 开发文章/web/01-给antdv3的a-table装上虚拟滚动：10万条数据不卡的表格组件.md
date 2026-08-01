> 组件已开源，`npm i antdv-faster-table`，MIT 协议，欢迎白嫖。要求宿主项目已安装 `vue >= 3.2` 和 `ant-design-vue >= 3.2`。

## 起因：antdv 3.x 的表格，数据一多就废

维护的后台系统里有几个「导出前预览」性质的页面：用户查一次数据，几千到几万条，产品要求不分页、整页滚着看。用的是 ant-design-vue 3.x 的 `a-table`，数据一超过两三千条，首次渲染肉眼可见地白屏一两秒，滚动的时候掉帧掉到怀疑人生。

原因不复杂：`a-table` 是全量渲染的，5000 条数据就是 5000 个 `<tr>`，每行再乘上列数的 `<td>`，DOM 节点轻松上十万。浏览器要布局、要绘制，卡是必然的。

antd 的 React 版在 4.x 之后给 Table 内置了 `virtual` 属性，但 **ant-design-vue 3.x 没有**（4.x 才有，而我们这种老项目升级 antdv 大版本的成本远大于收益）。社区方案要么是重写一套表格（样式、插槽、rowSelection 全得重新对齐），要么侵入性太强。

所以我自己写了一个：**外面看是 `a-table`，里面偷偷做了虚拟滚动**。组件核心代码不到 300 行，最后抽成了 npm 包 `antdv-faster-table`。

先看效果，同屏 5000 条不分页，左边是这个组件，右边是原生 `a-table`：

> 【图片占位 1】请上传：**性能对比 GIF**（跑 `npm run dev` 打开示例站的「性能对比」页，录一段左右两个表格同时滚动的屏，左侧 FasterTable 流畅、右侧原生 a-table 卡顿，最好能带上页面顶部显示的「渲染阻塞时长 xxx ms」）

<p align="center"><em>左：FasterTable（虚拟滚动） ｜ 右：原生 a-table（全量渲染 5000 行 DOM）</em></p>

打开 DevTools 看 DOM 数量差异更直观——左边不管数据多少条，`<tr>` 始终只有可视区那二三十个：

> 【图片占位 2】请上传：**DOM 对比截图**（Elements 面板，左右各截一张：FasterTable 的 tbody 里只有 ~30 个 tr + 上下两个占位 tr；原生 a-table 的 tbody 里是密密麻麻 5000 个 tr）

这篇文章聊聊实现里的几个关键决策和踩过的坑。

## 原理：切片渲染 + 占位行撑滚动条

虚拟滚动这个概念本身不新鲜，一句话说完：**只渲染可视区内的几十行，用两个占位元素把滚动条撑到真实高度**。用户滚动时根据 `scrollTop` 算出当前应该显示第几条到第几条，换一批数据渲染。

前提是**行高固定**。行高固定后，一切都是小学算术：

```
startIndex = Math.floor(scrollTop / rowHeight) - buffer
endIndex   = startIndex + Math.ceil(height / rowHeight) + buffer * 2
offsetTop    = startIndex * rowHeight          // 上方占位高度
offsetBottom = (total - endIndex) * rowHeight  // 下方占位高度
```

我把这层计算抽成了一个纯计算的 hook `useVirtualScroll`，不碰任何 DOM，输入是响应式的 `total / rowHeight / height / buffer`，输出是响应式的窗口下标和占位高度——纯函数好单测，也能给其他列表场景复用：

```ts
export function useVirtualScroll(options: UseVirtualScrollOptions) {
  const scrollTop = ref(0);

  // 可视区可容纳行数（含上下缓冲）
  const visibleCount = computed(() => Math.ceil(unref(getHeight) / unref(getRowHeight)) + unref(getBuffer) * 2);

  const startIndex = computed(() => {
    const start = Math.floor(unref(scrollTop) / unref(getRowHeight)) - unref(getBuffer);
    return Math.max(0, start);
  });

  const endIndex = computed(() => Math.min(unref(total), unref(startIndex) + unref(visibleCount)));

  const offsetTop = computed(() => unref(startIndex) * unref(getRowHeight));
  const offsetBottom = computed(() => Math.max(0, (unref(total) - unref(endIndex)) * unref(getRowHeight)));
  // ...
}
```

滚动事件用 rAF 节流，一帧内多次 scroll 只算一次：

```ts
let ticking = false;
function handleScroll(top: number) {
  if (ticking) return;
  ticking = true;
  requestAnimationFrame(() => {
    scrollTop.value = top;
    ticking = false;
  });
}
```

`buffer`（默认上下各 5 行）是防白屏的：快速滚动时，滚动事件和渲染之间总有一帧延迟，多渲染几行缓冲，滚动到的位置就已经有内容了。

## 关键决策：不重写 Table，往 a-table 里「注入」占位行

原理部分谁都会写，难的是**怎么塞进 `a-table` 里**。自己从 `<table>` 开始写一套的话，antdv 表格那些固定列、排序、筛选、rowSelection、bodyCell 插槽全都要重新实现一遍，工程量和后期维护都是无底洞。

我的选择是：**内部就用 `a-table`，只喂给它切片后的几十条数据，然后通过 `components` 属性替换 tbody 的 wrapper，在首尾插入两个占位 `<tr>`**。

`a-table` 有个不太起眼的 `components` 属性，允许替换内部各层的渲染组件。替换 `body.wrapper` 就能接管整个 `<tbody>`：

```ts
/** 占位行：用上下两个占位 tr 撑起完整滚动高度 */
const VirtualBodyWrapper = defineComponent({
  setup(_, { slots }) {
    const spacer = (height: number, key: string) =>
      h('tr', { key, 'aria-hidden': 'true', class: 'faster-table-spacer', style: { height: `${height}px` } },
        [h('td', { colspan: 200, style: { height: `${height}px`, padding: 0, border: 'none' } })]);
    return () => h('tbody', { class: 'ant-table-tbody' },
      [spacer(unref(offsetTop), 'ft-top'), slots.default?.(), spacer(unref(offsetBottom), 'ft-bottom')]);
  },
});

const getComponents = computed(() => {
  if (!unref(getIsVirtual)) return attrs.components as object;
  return { ...(attrs.components as object), body: { wrapper: VirtualBodyWrapper } };
});
```

用 `<tr>` 而不是 `<div>` 做占位，是为了不破坏 table 的合法结构；`colspan: 200` 是偷懒但有效的写法——横跨所有列。滚动时上下占位行的高度实时变化，真实行永远只有可视区那一窗。

这个方案最大的好处是：**排序、固定列、单元格插槽这些能力我一行都没写，全是 `a-table` 自己的**。

> 【图片占位 3】请上传：**原理示意图**（一张简单的示意图：一个滚动容器，顶部一块「上占位行 offsetTop」，中间高亮的「真实渲染的 20~30 行」，底部一块「下占位行 offsetBottom」，右侧标注 scrollTop、可视区高度。用 Excalidraw / draw.io 随手画即可）

## 透传一切：让它用起来「就是 a-table」

组件好不好推广，取决于同事接入时要不要看文档。我的目标是**把 `a-table` 换成 `FasterTable`，其余一个字不用改**。

三件套：

```vue
<script lang="ts">
export default defineComponent({
  name: 'FasterTable',
  inheritAttrs: false, // 属性不落到根 div 上，手动转发
});
</script>
```

属性和事件通过 `useAttrs()` 收集，剔除掉需要拦截处理的几个（`pagination` / `rowSelection` / `scroll`…），其余原样 `v-bind` 给内部的 `a-table`；插槽用动态插槽名全量转发：

```vue
<Table v-bind="getBindValues" :data-source="getRenderData" ...>
  <template #[item]="data" v-for="item in Object.keys($slots)" :key="item">
    <slot :name="item" v-bind="data || {}"></slot>
  </template>
</Table>
```

于是 `bodyCell`、`headerCell`、排序筛选、`@change` 事件……全部照旧。使用方长这样：

```vue
<FasterTable :data-source="dataSource" :columns="columns" :height="500" :pagination="false" />
```

10 万条数据传进去也不卡。还有一个细节：小数据量时虚拟滚动纯属画蛇添足（还带来固定行高的约束），所以加了个 `threshold`（默认 100 条）——当页数据量不超阈值就走原生渲染，行为和 `a-table` 一模一样。虚拟化只在真正需要的时候介入。

> 【图片占位 4】请上传：**基础用法截图**（示例站「基础用法」页，10 万条数据的表格 + 顶部的 scrollToIndex 跳转按钮，截一张静态图即可）

## 坑一：分页条「看不见」全量数据

第一个坑在分页。`a-table` 内置分页的逻辑是基于传给它的 `dataSource` 算总数的——而我传给它的是切片后的可视区几十条，分页条永远显示「共 28 条」，彻底废了。

解法是虚拟模式下**由组件接管分页**：内部维护 `current / pageSize`，先按页对全量数据切片，当页数据超过阈值再做虚拟渲染；`a-table` 自己的分页强制关掉，在同样的位置（右下角）用 `a-pagination` 补一个，`total` 用全量数据的长度：

```ts
// 当前页数据：先按页切片
const getPageData = computed(() => {
  if (!unref(getUseInnerPagination)) return props.dataSource;
  const start = (unref(innerCurrent) - 1) * unref(innerPageSize);
  return props.dataSource.slice(start, start + unref(innerPageSize));
});

// 当页超过阈值才虚拟化，每页 10 条时保持原生行为
const getIsVirtual = computed(() => props.virtual && unref(getPageData).length > props.threshold);
```

对外的行为刻意与 `a-table` 对齐：不传 `pagination` 默认开启，传 `false` 关闭，传对象则配置合并、`current`/`pageSize` 可受控、`onChange` 正常回调。使用者不需要知道这个分页条其实是「贴」上去的。

> 【图片占位 5】请上传：**前端分页截图**（示例站「前端分页」页，5 万条数据，分页条上把每页条数切到 1000 条/页的状态，能看到分页条显示「共 50000 条数据」）

## 坑二：点「全选」只选中了 28 条

第二个坑更隐蔽。测试同学反馈：勾表头的全选框，回调里的 `selectedRowKeys` 只有二十几个。

原因想通了也简单：`a-table` 眼里的「全部」就是我喂给它的可视区切片，它勤勤恳恳地把这 28 行全选了。但用户的预期显然是**当前页的全量数据**。

解法是虚拟模式下重写 `rowSelection.onSelectAll`，自己基于当页全量数据算 keys 再回调出去。但这里还有个二段坑：antdv 在触发 `onSelectAll` 之后，还会紧跟着用「仅已渲染行」的 keys 再调一次 `onChange`，把我刚回调出去的全量结果又覆盖回 28 条。翻了 antdv 源码确认这个调用顺序是固定的之后，用一个标记把紧随其后的那次原生 `onChange` 吞掉：

```ts
let suppressNextSelectionChange = false;
const getRowSelection = computed(() => {
  const rowSelection = attrs.rowSelection as Recordable | undefined;
  if (!rowSelection || !unref(getIsVirtual)) return rowSelection;
  return {
    ...rowSelection,
    onChange: (keys: any[], rows: Recordable[]) => {
      if (suppressNextSelectionChange) {
        suppressNextSelectionChange = false;
        return; // 吞掉 onSelectAll 之后那次只含已渲染行的 onChange
      }
      rowSelection.onChange?.(keys, rows);
    },
    onSelectAll: (selected: boolean) => {
      const pageData = unref(getPageData);
      const keys = selected ? pageData.map((r, i) => getRecordKey(r, i)) : [];
      suppressNextSelectionChange = true;
      rowSelection.onChange?.(keys, selected ? [...pageData] : []);
    },
  };
});
```

这也带出一个使用约束：**虚拟模式下 `rowSelection` 必须受控**（传入 `selectedRowKeys`）。因为行组件滚出可视区就被销毁了，非受控的选中状态存在组件实例上，滚回来就丢了。受控模式下状态在使用方手里，行重建时按 keys 恢复勾选，天然没这个问题。

> 【图片占位 6】请上传：**行选择 GIF**（示例站「行选择 + 插槽」页：点表头全选 → 显示已选 1000 条 → 快速滚动列表 → 勾选状态不丢，录 5~10 秒）

## 坑三：滚动容器会被销毁重建

滚动监听绑在 `a-table` 内部的 `.ant-table-body` 上（组件外层拿不到这个元素，只能 `querySelector`）。上线前自测发现一个场景：当页数据从 50 条（原生渲染）变成 2000 条（虚拟渲染）时，滚动事件失灵了。

原因是 `getIsVirtual` 切换会导致 `components` 变化，`a-table` 内部 DOM 重建，旧的 `.ant-table-body` 连同上面的监听器一起被扔了。处理方式就是老老实实盯着开关重新绑定：

```ts
// 虚拟开关切换后 DOM 会重建，需重新绑定滚动容器
watch(getIsVirtual, () => nextTick(bindScrollListener));
```

类似的还有数据源变化（比如重新查询）：新数据可能比旧数据短，当前页码和滚动位置都可能越界，统一在 `watch(dataSource)` 里重置回第一页、回到顶部。这些都不是什么高深逻辑，但不处理就是一个个「偶现 bug」。

## 诚实的边界

这个组件不是银弹，有三条明确的约束，写在 README 最显眼的位置：

1. **行高必须固定**。虚拟滚动的位置计算全建立在 `rowHeight` 恒定上，单元格内容超长会被裁成单行。动态行高的虚拟滚动要引入高度测量和位置缓存，复杂度翻几倍，对表格这种规整场景不值得；
2. **`rowSelection` 必须受控**，原因上面说了；
3. **不支持虚拟模式下的 `expandedRowRender`**（展开行高度不可控，直接违反第 1 条）。这类场景请设 `virtual="false"` 或降低单页数据量。

另外它是**纯前端方案**：全量数据在内存里，适合「一次查回几千到几十万条、前端切着看」的场景。如果数据大到内存都放不下，那是后端分页/流式加载该解决的问题，不要指望虚拟滚动。

## 打包：产物只有几 KB 的秘密

作为一个「寄生」在 antdv 上的组件，最怕的是使用方问：我项目里已经有 antdv 了，装你这个会不会打进来第二份？

不会，而且这是设计前提：

- `vue` 和 `ant-design-vue` 都声明为 **`peerDependencies`**，安装时不会再下载一份，直接用宿主项目的；
- Vite 库模式构建时两者都 external，产物只有组件自身的几 KB 代码；
- 因此样式、`ConfigProvider` 主题、国际化天然和宿主项目共用一套，不存在「两份 antd 样式打架」。

```ts
// vite.config.ts 关键配置
build: {
  lib: { entry: 'src/index.ts', name: 'AntdvFasterTable' },
  rollupOptions: {
    external: ['vue', 'ant-design-vue'],
  },
},
```

代价也很诚实：宿主项目没装 antdv 的话，这个组件跑不起来。「轻量组件」和「自带 UI 库」之间只能选一个，我选了前者。

## 最后

复盘下来，这个组件里没有什么高深算法，值钱的还是几个取舍：

- **不重写、只包装**：借 `components.body.wrapper` 往 `a-table` 里注入占位行，排序/固定列/插槽零成本继承；
- **`threshold` 按需介入**：小数据量保持原生行为，虚拟化只在需要时启用，固定行高的约束不扩散到不需要它的场景；
- **行为对齐优先于功能堆砌**：分页、全选的语义都刻意和原生 `a-table` 保持一致，接入方甚至感知不到内部换了渲染方式；
- **承认边界**：固定行高、受控选择、不支持展开行，写清楚比藏着掖着好。

核心的 `useVirtualScroll` 是纯计算 hook，也单独导出了，下拉列表、日志流这类场景可以直接拿去用：

```ts
import { useVirtualScroll } from 'antdv-faster-table';

const { startIndex, endIndex, offsetTop, offsetBottom, handleScroll } = useVirtualScroll({
  total: computed(() => list.value.length),
  rowHeight: 48,
  height: 500,
});
```

`npm i antdv-faster-table` 即用，仓库里带了 4 个可跑的示例（基础用法 / 前端分页 / 行选择 / 性能对比），克隆后 `npm run dev` 就能看。遇到问题欢迎提 issue。
