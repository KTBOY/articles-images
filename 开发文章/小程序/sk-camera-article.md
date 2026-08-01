# sk-camera：我把 H5 拍照踩过的坑封进了一个 uni-app 组件

> 相机打不开、拍出来的人脸被压扁、拍完了指示灯还亮着。在 H5 里写过拍照功能的人，大概对这几句不陌生。我被这些问题反复折腾了几个项目，最后决定不再每次现场修，而是收进一个组件里：`sk-camera`。

![图片待上传：组件运行效果 GIF，展示打开相机 → 拍照 → 出图的完整流程（手机 H5 录屏最佳）]()

## 一、H5 拍照到底难在哪

`getUserMedia` 看上去友好，三行代码就能拉起摄像头。但代码一旦上生产，面对成百上千种安卓机型、iOS Safari、微信和 QQ 的内置浏览器，问题会一个接一个冒出来。

### 1. 相机打不开：OverconstrainedError

很多教程这样写约束：

```js
navigator.mediaDevices.getUserMedia({
  video: { width: { min: 1280 }, height: { min: 720 } },
})
```

`min` 是硬性约束。设备摄像头达不到这个分辨率，浏览器不会退让，而是直接抛 `OverconstrainedError`。低端安卓机上几乎必现。

### 2. 拍出来的照片变形

预览用 CSS 把 video 拉伸铺满容器，成像时却按容器尺寸画 canvas。宽高比对不上，人脸就被压扁或者拉长。

### 3. 前置镜像把页面卡死

有些实现为了让自拍成像和预览一致，用 `getImageData` 逐像素翻转。1080p 一张图两百多万像素，JS 单线程跑这个循环，低端机直接白屏。

### 4. 拍完照，摄像头灯还亮着

页面跳走了，组件销毁了，`MediaStream` 的轨道却没有 `stop()`。用户看到状态栏的相机指示灯常亮，第一反应是这个网页在偷拍我。

### 5. 多端 API 是两个世界

同一套业务代码，H5 要用 `getUserMedia`，小程序和 App 只能用原生 `<camera>`。

单看每个都不算大问题。凑到一起，足够让一个拍照需求返工三四次。

## 二、设计：逻辑和视图分开

`sk-camera` 把所有和视图无关的逻辑抽进了一个组合式函数 `useCamera`：

```text
sk-camera/
├── sk-camera.vue        # 纯视图：预览容器、控制栏、插槽、事件透传
├── use-camera.ts        # 核心逻辑：getUserMedia、约束降级、成像、资源释放
├── utils.ts             # 纯函数：约束链构建、错误映射、裁剪坐标换算
└── sk-camera.type.ts    # 完整 TS 类型定义
```

![图片待上传：架构分层示意图，画出 vue（视图层）→ use-camera（逻辑层）→ utils（纯函数层）的依赖关系，可以用 draw.io / excalidraw 画]()

分层带来两个实际好处。`utils.ts` 全是纯函数，约束链和坐标映射可以直接被单测覆盖；不想用我这套 UI 的人，`import { useCamera }` 自己搭界面就行。另外改样式的时候，也不必担心碰坏 WebRTC 那一部分。

## 三、几个关键问题怎么解的

### 1. 约束逐级降级，只用 ideal

打不开相机的根因是约束太硬。策略很简单：全部换成 `ideal`，再构建一条降级链逐级重试。

```ts
export function buildConstraintsChain(facing, resolution) {
  const size = resolvePreset(resolution)
  const chain: MediaStreamConstraints[] = []
  // 后置优先精确匹配，规避部分机型 environment 不生效的问题
  if (facing === 'environment') {
    chain.push({ audio: false, video: { facingMode: { exact: 'environment' }, width: { ideal: size.width }, height: { ideal: size.height } } })
  }
  chain.push({ audio: false, video: { facingMode: facing, width: { ideal: size.width }, height: { ideal: size.height } } })
  chain.push({ audio: false, video: { facingMode: facing, width: { ideal: 1280 }, height: { ideal: 720 } } })
  chain.push({ audio: false, video: { facingMode: facing, width: { ideal: 640 }, height: { ideal: 480 } } })
  chain.push({ audio: false, video: { facingMode: facing } })
  chain.push({ audio: false, video: true }) // 最后的兜底：能开就行
  return chain
}
```

从期望分辨率一路降到 `video: true`，除非设备真的没有摄像头，否则总能开起来。

有个细节值得单独说：权限类错误不参与降级。用户点了拒绝，重试一百次还是拒绝，所以 `NotAllowedError` 直接映射成错误码抛给业务。

### 2. 成像永远用视频的原始分辨率

预览可以随便 `object-fit: cover`。但成像时 canvas 的尺寸必须取 `video.videoWidth / videoHeight`，不能取容器的 CSS 尺寸：

```ts
const full = document.createElement('canvas')
full.width = video.videoWidth   // 原始分辨率，而非 clientWidth
full.height = video.videoHeight
```

宽高比天然一致，变形问题从根上就没了。

### 3. 镜像：一行 ctx.scale(-1, 1)

```ts
if (options.mirror) {
  ctx.translate(vw, 0)
  ctx.scale(-1, 1)   // GPU 加速的变换，耗时接近于 0
}
ctx.drawImage(video, 0, 0, vw, vh)
```

canvas 的 2D 变换走 GPU，和逐像素循环不在一个量级。预览层同时对 video 元素做 `rotateY(180deg)`，保证预览和成像的镜像状态一致：自拍看到什么，拍出来就是什么。

### 4. 固定区域裁剪

证件照、人脸核身这类场景需要只保留取景框里的画面。难点在坐标系：预览是 `object-fit: cover`，屏幕上看到的只是原始画面被裁掉两边后的中间一块，取景框在屏幕上的位置和它在原始画面里的位置对不上。

`crop` 参数用预览可视区域的比例（0~1）作坐标系，内部按 cover 规则映射回原始像素：

```ts
// 预览容器像素 → 原始画面像素
const scale = Math.max(cw / vw, ch / vh)
const offX = (vw * scale - cw) / 2
const offY = (vh * scale - ch) / 2
let nx = (offX + rect.x) / scale
let ny = (offY + rect.y) / scale
```

用起来就很直觉，取景框放在屏幕哪里，`crop` 传一样的比例：

```vue
<!-- 取景框位于预览居中、宽 84%、高 50% -->
<sk-camera :crop="{ x: 0.08, y: 0.25, width: 0.84, height: 0.5 }" @capture="onCapture">
  <template #overlay>
    <!-- 你的取景框图片，用相同比例定位即可完全对齐 -->
  </template>
</sk-camera>
```

![图片待上传：裁剪对照图，左边是带取景框的预览截图，右边是拍照后实际输出的裁剪结果，证明「所见即所得」]()

### 5. 卸载时兜底释放

```ts
onUnmounted(() => {
  stop()          // 停掉所有 MediaStreamTrack
  unmountVideo()  // 移除 video 元素
})
```

业务代码有没有手动调 `stop()` 都不影响，组件卸载时一定会释放摄像头。

### 6. 一套 API 三端可用

条件编译分流：H5 走 `getUserMedia`，小程序和 App 降级为原生 `<camera>`。props、events、methods 保持一致，业务侧不用写两套。

## 四、快速上手

组件遵循 easycom 规范，丢进 `uni_modules` 就能直接用，不需要 import：

```vue
<template>
  <view class="wrap">
    <sk-camera v-if="!img" @capture="onCapture" @error="onError" />
    <image v-else :src="img" mode="widthFix" />
  </view>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
const img = ref('')
const onCapture = (res) => { img.value = res.base64 }
const onError = (e) => uni.showToast({ title: e.message, icon: 'none' })
</script>

<style scoped>
.wrap { height: 100vh; }
</style>
```

![图片待上传：快速上手效果截图，展示相机预览界面（带内置控制栏：关闭/拍照/切换三个按钮）]()

默认 UI 不合口味的话，控制栏和取景框都开了插槽，实例方法也全部暴露：

```vue
<sk-camera ref="cam" :show-controls="false">
  <template #controls="{ capture, switchCamera, facing }">
    <!-- 完全自定义的控制栏 -->
  </template>
</sk-camera>
```

错误处理不用再猜浏览器抛了什么。组件把原生错误统一映射成了固定错误码：

| 错误码 | 含义 |
| --- | --- |
| `INSECURE_CONTEXT` | 非 HTTPS / localhost 环境 |
| `PERMISSION_DENIED` | 用户拒绝授权 |
| `NOT_FOUND` | 没有摄像头 |
| `NOT_READABLE` | 摄像头被其他程序占用 |
| `OVERCONSTRAINED` | 分辨率不支持（已自动降级，仍失败才会抛） |

业务侧一个 `switch(e.code)` 就能给出对应的引导文案。

## 五、踩坑备忘

几个开发过程中记下来的点：

1. `getUserMedia` 必须跑在安全上下文，`https://` 或者 `http://localhost`。局域网 IP 调试需要 HTTPS，`vite-plugin-mkcert` 一行配置就能拿到本地受信任证书。
2. iOS 必须加 `playsinline`，否则视频会强制全屏播放；还要配上 `muted` 和 `autoplay` 才能自动出画面。腾讯 X5 内核额外需要 `x5-playsinline`。
3. 别用 uni 的 `<video>` 组件承载 MediaStream。它是为播放视频文件封装的，属性透传和 `object-fit` 表现都不可控，直接 `document.createElement('video')` 挂原生元素更稳。
4. 切换前后置要先释放旧流。部分机型不允许同时持有两个摄像头流，不先 `stop()` 会切换失败或者黑屏。

## 六、最后

H5 拍照的坑单个都不难，麻烦的是它们分散在权限、约束、成像、坐标系、生命周期这些不同环节，而且只在特定机型上暴露。收敛进组件之后，后面的项目就不用重新踩一遍了。

组件发布在插件市场，源码带完整 TS 类型和注释：

- 插件市场：（此处补充插件市场链接）
- 完整文档：见组件 `readme.md`

![图片待上传：文末引流图，可以是插件市场页面截图，或你的公众号/主页二维码]()

如果你踩到过别的机型坑，欢迎在评论里告诉我，我补进组件。
