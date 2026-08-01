![](https://img2024.cnblogs.com/blog/1963715/202607/1963715-20260729194601642-75347189.png)

> 先交代背景：我写了多年前端，最近公司推全栈，我被「自愿」转型。第一个任务是接手一个 Java 后端模块，技术栈 Spring Boot + MyBatis-Plus（JeecgBoot 脚手架）。而我当时对 Java 的认知还停留在「public static void main」。
>
> 这篇不聊「AI 会不会取代程序员」，就说件具体的事：一个后端零经验的前端，靠一份 36 行的规则文件让 AI 老老实实干活，最后把模块交付上线了。文末附规则模板，可以直接抄走。

## 一、第一天就翻车：AI 写得飞快，我一行都判断不了

任务本身不复杂，一个「检查模块」：现场信息的增删改查 + Excel 导入导出，再加一个远程巡查功能，检查人员在网页上看现场摄像头实时画面、截图、写巡查记录。两个 Controller，十来个接口。

放在前端，这就是个「列表页 + 详情页」的工作量。我心想有 AI 在，后端还不是随便写？于是我打开对话框，敲下了那句经典的：

> 「帮我写一个现场信息的分页查询接口。」

AI 唰唰唰给了我一百多行代码，Controller、Service、Mapper 一应俱全，看起来专业极了。我复制粘贴，编译——报错。让 AI 修，它重写了一版，这次编译过了，但它把项目里已有的分页工具类扔了，自己手写了一套 `limit offset`；再让它加个查询条件，它又顺手把上一轮改的东西覆盖了一半。

三个小时后，我盯着满屏改了又改的代码才反应过来：我根本没有能力判断它写得对不对。

前端的活我扫一眼就知道 AI 有没有胡来，那是我的主场。Java 这边不一样，它说什么就是什么，跑偏了我也看不出来，等看出来的时候，已经攒了一堆自己读不懂的代码。

这就是 vibe coding 的真实体验：顺的时候很爽，出问题的时候我连从哪查都不知道。

![](https://img2024.cnblogs.com/blog/1963715/202607/1963715-20260729194550015-165373349.png)

## 二、转折点：别调教自己，去调教 AI

翻车之后我复盘，问题不在 AI 的代码能力，它写的每一段单独看都没毛病。问题在协作方式：

- 我没让它先摸清项目里有什么，它只能重复造轮子；
- 没等方案就让它开写，写错了推倒重来，上下文越滚越乱；
- 验证这件事我根本没提，它就默认「能编译 = 能用」，有时候连编译都没跑过。

说白了，我把 AI 当成了搜索引擎的加强版。它更接近一个需要管理的初级工程师：能力不差，但没有边界感，你不给流程，它就自由发挥。

于是我在项目里加了一份规则文件（我用的 AI 编辑器支持项目级 rules，Cursor、Qoder、Claude Code 之类的都有等价机制），全文 36 行，核心就四步：

```markdown
# SuperProgramming 开发流程（项目级规则，全程自动生效）

## 1. brainstorming（动手前必做）
- 先澄清需求与影响范围；信息不足先问，不臆测。
- 探查现有代码，确认能否复用已有能力，避免重复造轮子。
- 给出简短设计大纲，等用户确认后再写代码。

## 2. writing-plans
- 把改动拆成小步，尽量按方法/函数粒度。
- 先查「是否有可复用的现成方法」，再定实现方案。
- 明确列出要改的文件与关键改动点。

## 3. implementing
- 能测的先写测试（TDD）——纯逻辑用 JUnit 单测。
- 每个改动完成后自查：空值 / 边界 / 异常 / 命名 / 风格一致性。
- 编译验证跑通再交付；没法本地验证的点，明确列出来，不假装测过。

## 4. closing-the-loop
- 收尾给出：改动清单 + 风险 + 待用户验证项 + 可复用经验。
- 只有用户明确要求时才 git commit，绝不擅自提交。

## 核心约束
- 没有大纲不写代码。
- 一个功能 = 一次评审 + 一次测试，不攒到最后统一处理。
- bug 修复 / 重构也要重新走该流程，这是个循环。
- 源码是最终事实：缓存和文档可能过期，一切以代码为准。
```

![](https://img2024.cnblogs.com/blog/1963715/202607/1963715-20260729194404289-611850373.png)

画成流程图就是一个转不停的圈。任何改动都得完整走一遍，修 bug 和重构也不例外：

```mermaid
flowchart LR
    A[brainstorming<br/>澄清需求 · 探查现有代码<br/>给出设计大纲] --> B[writing-plans<br/>拆小步 · 列文件清单<br/>先找可复用方法]
    B --> C[implementing<br/>先测试后实现<br/>自查边界 · 编译验证]
    C --> D[closing-the-loop<br/>改动清单 + 风险<br/>+ 待验证项]
    D -.修 bug / 调整 / 重构.-> A
```

这份规则生效之后，AI 的行为肉眼可见地变了。同样是「写个分页查询接口」，它的第一反应不再是甩代码，而是：

> 「我先看了下项目，发现已有 `QueryGenerator` 统一处理分页和查询条件，场地数据在 `t_room_info` 表里已经维护，不需要新建。我的方案是：VO 层加四个扩展字段（场地类型、摄像头数、今日待检场次、人员配置状态），列表查询后批量回填，避免 N+1 查询。确认后我开始写。」

看到这段话我才反应过来，这份规则约束的其实是我自己。它让每次协作都从设计共识开始，而不是先甩一堆代码过来。实现细节我这个新手看不懂，但设计大纲看得懂，方向对不对我判断得出来。

## 三、实战：检查模块是怎么被一步步啃下来的

有了流程，接下来就是拿真需求练。挑几个有代表性的场景说说，每一个都是「AI 出方案 → 我拍板 → AI 实现 → 一起验证」这么滚出来的。

### 场景 1：Excel 导入，我才知道「先探查现有代码」是干什么用的

排班数据是业务部门发的 Excel，需要批量导入。我原本的想象是「解析 Excel → 插库」两步完事，AI 在 brainstorming 阶段泼了盆冷水：

- Excel 里只有「现场地点」的中文名（比如 *1号楼101*），但后续摄像头绑定要靠场地编号关联，导入时必须按名称去 `t_room_info` 回填编号；
- 名称对不上的数据怎么办？静默丢弃还是整批报错？（我们最后选了导入拦截 + 明确提示）；
- 重复导入同一批数据怎么办？要做重复校验。

最终落地的导入接口是这样的（EasyPoi 解析 + 回填场地编号，省略了日志）：

```java
@PostMapping("/importExcel")
public Result<?> importExcel(@RequestParam("file") MultipartFile file) {
    if (file == null || file.isEmpty()) return Result.error("上传文件为空！");
    String name = file.getOriginalFilename();
    if (name == null || (!name.endsWith(".xls") && !name.endsWith(".xlsx"))) {
        return Result.error("仅支持 .xls 或 .xlsx 格式！");
    }
    ImportParams params = new ImportParams();
    params.setTitleRows(1);  // 第 0 行是分组标题
    params.setHeadRows(1);   // 第 1 行是表头，第 2 行起才是数据
    try {
        List<SiteInfo> list =
                ExcelImportUtil.importExcel(file.getInputStream(), SiteInfo.class, params);
        if (list == null || list.isEmpty()) return Result.error("未读取到有效数据！");
        service.fillRoomCode(list);  // 关键一步：按现场地点回填场地编号
        service.saveBatch(list);
        return Result.ok("文件导入成功！数据行数：" + list.size());
    } catch (Exception e) {
        return e.getMessage() != null && e.getMessage().contains("Duplicate entry")
                ? Result.error("文件导入失败：有重复数据！")
                : Result.error("文件导入失败：" + e.getMessage());
    }
}
```

`fillRoomCode` 的思路是先一次性查出场地档案，在内存里建好索引再逐行回填，不在循环里逐条查库：

```java
// 一次性查出涉及的场地档案，按名称建索引（重名取第一条）
Map<String, RoomInfo> byName = roomInfoService.list(qw).stream()
        .collect(Collectors.toMap(RoomInfo::getRoomName, ri -> ri, (a, b) -> a));
for (SiteInfo site : list) {
    RoomInfo info = byName.get(site.getRoomName());
    if (info != null) {
        site.setRoomCode(info.getRoomCode()); // 回填场地编号
    } else {
        log.warn("场地[{}]在 t_room_info 未匹配到，无法回填", site.getRoomName());
    }
}
```

这三个问题放在以前，大概率要等测试甚至用户用起来才会炸。规则要求它先探查、先问、不臆测，坑就被挪到了写代码之前。

### 场景 2：详情接口聚合摄像头视频流，我全程没写一行 SQL

远程巡查的详情页要展示：现场信息 + 任务状态（未开始/进行中/已结束）+ 该场地绑定的所有摄像头及视频流地址。数据横跨现场信息表和摄像头管理表，还要根据当前时间实时计算任务状态。

按四步流程走下来，AI 给的方案是详情 VO 聚合两张表的数据，任务状态由任务时间动态算。最终的详情接口实现五步各干一件事，读起来像流水账，对我这种新手刚好：

```java
public RemoteInspectionDetailVo getCurrentSiteDetail(String id, String roomCode,
                                                     HttpServletRequest request) {
    // 1. 查现场：id 优先；id 为空时按场地编号取最新一条
    SiteInfo site;
    if (StringUtils.isNotBlank(id)) {
        site = siteInfoMapper.selectById(id);
    } else {
        site = siteInfoMapper.selectOne(new LambdaQueryWrapper<SiteInfo>()
                .eq(SiteInfo::getRoomCode, roomCode)
                .orderByDesc(SiteInfo::getCreateTime).last("LIMIT 1"));
    }
    if (site == null) return null;

    RemoteInspectionDetailVo vo = new RemoteInspectionDetailVo();
    // 2. 现场基础字段整体拷贝进 VO
    BeanUtils.copyProperties(site, vo);
    // 3. 任务状态实时计算：解析 "09:55~11:35" 和当前时间比较，1未开始/2进行中/3已结束
    vo.setTaskStatus(computeTaskStatus(site.getTaskTime()));
    // 4. 聚合该场地绑定的摄像头视频流（来自 t_camera_mgr）
    vo.setCameraVideoStreamVoList(
            cameraMgrService.queryVideoStreamList(site.getRoomCode(), request));
    // 5. 回显已保存的巡查记录（备注、提交状态、截图列表）
    fillSavedInspection(vo, site.getId());
    return vo;
}
```

实现完 AI 还主动补了一个 JUnit 单测覆盖 `computeTaskStatus` 的边界（开始前一分钟、结束后一分钟这种）。我做的事情只有两件：确认方案、跑测试。

### 场景 3：保存巡查结果的 upsert，AI 问了一个我没想到的问题

检查人员看完监控要保存巡查记录（备注 + 截图列表 + 是否提交）。我提需求时只说了「保存」，AI 在 brainstorming 阶段反问：

> 「同一个现场巡查多次，是每次新增一条记录，还是一个现场只保留一条最新的？这决定了接口是 insert 还是 upsert。」

我拿着这个问题去找产品，答案是后者——一个现场一条记录，重复保存覆盖。于是接口设计成按现场 ID 做 1:1 upsert，主记录「有则更新、无则新增」，截图子表整体覆盖，整个方法包在一个事务里：

```java
@Transactional(rollbackFor = Exception.class)
public void saveInspection(RemoteInspectionSaveDTO dto) {
    // 1. 按现场 id 查已有主记录：有则更新，无则新增（1:1 upsert）
    RemoteInspection entity = remoteInspectionMapper.selectOne(
            new LambdaQueryWrapper<RemoteInspection>()
                    .eq(RemoteInspection::getSiteInfoId, dto.getSiteInfoId())
                    .last("LIMIT 1"));
    boolean isUpdate = entity != null;
    if (!isUpdate) entity = new RemoteInspection();

    entity.setSiteInfoId(dto.getSiteInfoId())
            .setIsSubmit(dto.getIsSubmit())
            .setRemark(dto.getRemark());   // ……其余快照字段同理，覆盖式保存
    if (isUpdate) remoteInspectionMapper.updateById(entity);
    else remoteInspectionMapper.insert(entity);

    // 2. 截图子表整体覆盖：先删旧，再插新
    remoteInspectionImageMapper.delete(new LambdaQueryWrapper<RemoteInspectionImage>()
            .eq(RemoteInspectionImage::getInspectionId, entity.getId()));
    for (RemoteInspectionSaveDTO.ImageItem item : dto.getImageList()) {
        remoteInspectionImageMapper.insert(new RemoteInspectionImage()
                .setInspectionId(entity.getId())
                .setImageUrl(item.getUrl())
                .setImageTime(parseImageTime(item.getTime())));
    }
}
```

如果你的场景只有单表、且给 `site_info_id` 建了唯一索引，也可以直接用 MySQL 一条 SQL 搞定：

```sql
INSERT INTO t_remote_inspection (site_info_id, remark, is_submit)
VALUES (#{siteInfoId}, #{remark}, #{isSubmit})
ON DUPLICATE KEY UPDATE remark = VALUES(remark), is_submit = VALUES(is_submit);
```

我们最后选了应用层 upsert 而不是这条 SQL，原因有两个：一是还要级联处理截图子表，反正逃不掉事务；二是 `ON DUPLICATE KEY UPDATE` 依赖唯一索引，对当时的我来说，「先查再判断」的代码谁都看得懂，可维护性优先。这个问题要是没提前问，上线后大概要返一次工。

### 场景 4：Long 精度丢失，前端经验第一次派上用场

联调时前端同事（也就是上周的我自己）反馈：详情接口传 id 查不到数据。我几乎条件反射地反应过来：JavaScript 的 Number 只有 53 位安全整数，Java 的 Long 是 64 位，雪花算法生成的 19 位 id 传到浏览器，后三位直接归零了。

这是前端圈的经典坑，我踩过。解法是让后端把 Long 序列化成字符串返回，两种写法：

```java
// 方式一：字段级注解（本项目的用法，老项目改动最小，只影响标注的字段）
@TableId(type = IdType.ASSIGN_ID)            // 雪花算法生成 19 位 Long id
@JsonFormat(shape = JsonFormat.Shape.STRING) // 序列化时转成字符串给前端
@ApiModelProperty(value = "主键编号")
private Long id;
```

```java
// 方式二：全局配置（新项目推荐，一次解决所有 Long 字段，不用挨个加注解）
@Configuration
public class JacksonConfig {
    @Bean
    public Jackson2ObjectMapperBuilderCustomizer longToStringCustomizer() {
        return builder -> builder
                .serializerByType(Long.class, ToStringSerializer.instance)
                .serializerByType(Long.TYPE, ToStringSerializer.instance);
    }
}
```

老项目慎用方式二：全局转字符串会波及所有接口的 Long 字段，已上线的前端如果拿它做过数字运算就会出问题，我们这个项目就是因为这个原因选了方式一，只给主键字段加注解。

前端转全栈的便宜在这里占到了：接口的坑我大多在消费端摔过。分页结构怎么设计前端才好用，时间格式要不要统一，错误提示怎么给才能直接 toast，这些不用等联调磨一轮，我自己就能定下来。

### 场景 5：环境的坑，AI 替我记住了

这个老项目必须用 JDK 8 编译，代码里用了 `sun.misc.BASE64Encoder`，JDK 9+ 直接编译失败。这种事我第一次撞上时排查了半天，然后做了一件事：把它写进规则文件。

```markdown
## 核心约束（追加）
- 本项目必须用 JDK 8 编译
```

从此每一轮对话，AI 都会用 JDK 8 跑一遍 `mvn compile` 再交付。这份规则文件后来慢慢变成了一份坑位备忘录：环境限制、踩过的雷，撞见一次就往里加一条。

## 四、交付结果，以及一些实话

最终这个模块交付的内容：

| 项             | 结果                                                             |
| -------------- | ---------------------------------------------------------------- |
| 接口数量       | 13 个（CRUD + Excel 导入导出 + 树查询 + 详情聚合 + upsert 保存） |
| 我手写的代码量 | 不到 10%，主要是配置和个别业务判断的微调                         |
| 我的角色       | 需求澄清、方案拍板、验收测试、联调                               |
| 返工次数       | 立规则前：一个接口反复改 3 小时；立规则后：接近零返工            |
| 附赠产出       | AI 顺手生成的接口对接文档，前端同事直接照着调                    |

也说点实话，避免这篇看起来像 AI 吹：

1. AI 没让我省掉学 Java 这一步。为了看懂它的设计大纲，我把 MyBatis-Plus 的条件构造器、Spring 的依赖注入、事务边界都补了一遍，只不过是带着真实问题去学的，比啃书快得多。
2. 数据库和部署环境的问题它替不了你。连不上测试库、Redis 配置不对、防火墙拦了端口，这些还得自己爬。规则里那句「没法本地验证的点要明确列出来，不假装测过」，就是被这类问题逼出来的。
3. 规则不是一次写好的。我这 36 行是两周里边踩边加出来的，你的项目该有你自己的版本。

## 五、抄作业：这份规则怎么迁移到你的项目

不管用哪个 AI 编辑器，核心就三件事。

第一，给 AI 立流程，别只给需求。最小可用版就四句话：动手前先给设计大纲；写之前先找项目里能复用的东西；写完必须编译或测试验证；收尾列出改动清单和没验证的点。

第二，把项目的隐性知识写下来。JDK 版本、必须复用的工具类、团队的命名习惯、不许动的祖传代码，全塞进规则。AI 每开一轮对话都是从零开始，只有规则文件会一直跟着。

第三，判断的活你干，写的活它干。转型期真正卡人的是判断，不是动手。设计大纲是新手最抓得住的判断点，实现看不懂可以先放着，方案看得懂就不会跑偏。

---

写这篇的时候我又翻了翻两个月前那段「三小时改不出一个接口」的对话记录。AI 没帮我跳过学 Java，但确实把「从零到能交付」的周期压掉了一大截，前提是你得先学会管它。

后面打算接着写这个模块里摄像头视频流接入的具体实现，那块坑更多。你要是也在转全栈，评论区聊聊你踩过的坑。
