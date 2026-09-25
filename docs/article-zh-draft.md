# 考官带伤阅卷：对 Agent Skill 做故障注入的完整性实验

> 草稿 v0.9（全部方向数据已填，待真人审阅；仓库地址待发布时回填）
> 实验仓库：本仓库（skill-quake）　原始单次实验记录：见 docs/ 与本仓库 results 汇总（原始 transcript 不公开）

## 引子：从"流"到"文件"

此前我们的 harness 矩阵实验测的是"流"——评测流水线在运行中能不能发现异常。结论是：内容层的残缺，流水线判不出来。

这篇文章把同一个问题推到更底层：**文件**。Agent Skill 就是一堆 markdown 文件——一个 `SKILL.md` 加若干附件。它会残缺：下载截断、同步丢文件、手滑删错行、frontmatter 写空。问题很朴素：**当一个 skill 自己带着伤被加载、被执行时，宿主 agent 能发现吗？**

靶子选的是阿里开源的 [skill-up](https://github.com/alibaba/skill-up)（Agent Skill 评测工具链）里的 `skill-upper`——一个"负责测评其他 skill 的 skill"。选它的理由很直白：如果连续约考官自己都带着伤出题，它改的卷子还准吗？

## 实验设计：三条方法学红线

**一，做实验的人不能当宿主。** 谁动的手脚谁知道伤在哪，自己跑出来的"发现"不算数。每次运行都派一个零上下文的全新宿主（子代理或 headless CLI），只知道 skill 路径和一句普通的用户请求。

**二，中性 prompt。** 请求里没有任何"检查完整性"的暗示，就是一句"帮我给这个 skill 设计评测并 validate，别真跑"。所有运行共用同一份模板，只换路径。

**三，机械证人与 agent 警觉性分层记录。** 每个注入状态先过一个确定性检查器（后来固化成 `skill-guard`）：frontmatter 必填字段、引用文件存活性、截断签名。它不关心语义，只回答"文件层面有没有伤"。然后再看 agent 层的表现。两层分开记录，谁在哪一格失效就一目了然。

四种故障，每种对应一类真实事故：

| 编号 | 注入 | 模拟的事故 |
|---|---|---|
| T1 | SKILL.md 拦腰截断在 60% 处（290→174 行，切口是完整的一行，无标记） | 下载/同步截断 |
| T2 | 删除一个正文明确引用的附件（references/eval-yaml.md） | 拷贝丢文件 |
| T3 | 一个附件截断到一半（judge-types.md 96→48 行，止于一个空标题） | 半截写盘 |
| T4 | 清空 frontmatter 的 name/description | 生成/编辑事故 |
| T5 | 阳性对照：全部恢复，重跑基线 | 证明流程无残留 |

目标 skill 是自造的 hello-world 级 `greeting-card`（不碰任何真实第三方 skill）。每个故障做完即 `git checkout` 恢复，证人确认签名回到健康态再进下一个。

行为分级口径：**L0** 无察觉 / **L1** 有信号但说错对象 / **L2** 明确指出不完整 / **L3** 指出并拒绝执行。

## 第一轮：单次注入结果

| 注入 | 机械证人 | 宿主 agent（kimi-code，单次） | 分级 |
|---|---|---|---|
| T1 截主文件 | 零告警（存活引用全在、frontmatter 正常） | 主动报告"SKILL.md 疑似被截断"，精确到 174 行/Step 2 处，列出缺失的 Step 3-8，随后读 references 代偿，完成任务 | L2 |
| T2 删附件 | 捕获死链 | 主动报告"References 列出了 eval-yaml.md 但磁盘上不存在"，改用模板代偿 | L2 |
| T3 截附件 | 仅启发式告警（悬挂标题） | 主动报告"judge-types.md 在 agent_judge 标题处戛然而止，48 行" | L2 |
| T4 空 frontmatter | 捕获两个必填字段为空 | **只字未提**，照常跑完 | L0 † |
| T5 对照 | 健康 | 正常，无误报 | — |

单次结果就很有意思：挡路的伤（截断主文件、断链）被发现了；不挡路的元数据伤（frontmatter）被无视了——因为我们用"直接给路径"的方式加载，绕过了发现层，而 frontmatter 恰恰是给发现层用的。

† 但 T4 的 L0 只活了一天：第三轮批量复测时，3 路宿主全部明确指出了空 frontmatter（合计 3/4），其中一路还主动推断"可能影响其被宿主正确识别/触发"。单发是轶事——我们自己第一轮就差点把轶事写成"稳定 L0"的结论。修正后的准确说法：执行层对 frontmatter 之伤的检出也是概率性的；它真正的无声区在 loader 层（见下文实测）。

## 回马枪：带伤的考官改带伤的卷子

把残缺最轻的一版（T3，附件截半）的 skill-upper 留下，再给它一个被做了同样手脚的目标 skill（tone-guide.md 从 28 行截到 14 行，被截掉的后半独有 5 条格式规则：恰好一个 emoji、长度上限、禁 markdown、禁 Dear 开头、中英文匹配）。

结果：**两处伤都没被发现**。更要紧的是卷子真的改歪了——健康基线的判分脚本显式检查恰好一个 emoji、长度 ≤60 词、无 markdown、不以 Dear 开头；带伤考官产出的 6 个用例对这些规则**全部零命中**。文档残缺 → 理解残缺 → 用例残缺，沿链静默传导，全程无告警。

一个自己带着伤的考官，发现不了考生身上同样的伤。

## 横向发现：申报通道是开着的，漏检是"没察觉"不是"不会报"

这一轮实验里每个宿主都**主动**申报了与实验无关的真实异常：`skill-up list-cases` 对中文按字节截断出乱码、`--version` 输出 dev 构建、凭据缺失。没有一个 agent 隐瞒它已察觉的东西。

但同一条通道对内容层残缺的表现是：察觉了才报（T1/T2/T3），没察觉就不报（T4、回马枪）。决定报不报的不是申报意愿，是**察觉概率**——而察觉概率只在 agent 读文件那一瞬间被决定。内容层残缺不产生错误码、不产生异常、validate 照过、报告照写，没有任何信号强制 agent 停下来核对。

这就是为什么这类缺陷在生产环境长期隐形：**没有异常报告 ≠ 没有损伤**。

## 第二轮：把"概率性"从轶事变成数字

单次 L2/L0 只是轶事。用工具化后的流水线（见下文 skill-quake）把 T1 和 T3 各跑 8 次（kimi 宿主、同模型、同 prompt、每路独立变异副本），外加 2 次健康对照：

| cell | N | 检出 | 分级分布 |
|---|---|---|---|
| T1 主文件截 60%（挡路） | 8 | **8/8** | 全部 L2，且全部精确定位到"174 行、Step 2 选型处" |
| T3 附件截半（不挡路） | 8 | **2/8** | L2 × 2，L0 × 6 |
| 健康对照 | 2 | 无误报 | — |

挡路的伤稳定检出，不挡路的伤明显概率性——**检出与否不取决于伤有多重，取决于伤是否挡在 agent 要走的路上**。T3 里两个检出的宿主甚至给出了代偿方案（"改用 case.yaml.tmpl 的注释示例补齐 agent_judge 字段"），没检出的六个则是读完了文件、用了它的决策树、但谁也没发现文件只读到一半。

## 第三轮：全故障菜单，画出剂量-响应曲线

前两轮只试了四种伤里的两种。把故障菜单补全再测一轮（kimi 宿主，新格子 N=3，累计数据合并前两轮）：

| 故障 | 伤与执行路径的关系 | 检出率 |
|---|---|---|
| T1 主文件截 60%（后续步骤消失） | 直接挡路 | 8/8 |
| T1 主文件截 85%（只丢尾部速查表与索引） | 半挡 | 1/3 |
| T2 删正文引用的附件 | 挡 | 首轮 1/1 |
| T6 删 Step 2 指令点名要复制的模板 | 指令直接落空 | 3/3 |
| T5 用例模板截半（丢了 judge 段骨架） | 半挡 | 2/3 |
| T3 参考文档截半（可选查阅） | 不挡 | 2/8 |
| T4 frontmatter 清空 | 不挡（路径加载） | 3/4 † |

规律收敛成一句：**检出率不取决于伤有多重，取决于伤是否横在 agent 正要执行的那条指令上。** 指令说"复制 `assets/eval.yaml.tmpl`"而文件不在 → 3/3；主流程后续步骤凭空消失 → 8/8；"可以参考"的文档坏了一半 → 2/8 到 2/3；与本次执行无关的元数据 → 看机缘。

机械证人侧也有一个对称盲区：模板文件（.tmpl）的截断连 skill-guard 也判不出来——截断签名启发式只适用于 markdown，模板以注释结尾再正常不过。这类伤只有两种东西能接住：下游 validate 报错，或 agent 的警觉。

## 真实 loader 层：frontmatter 之伤落在哪里

T4（空 name/description）在执行层不可见，那真实的 skill 加载器怎么处理它？实测了两个宿主（各装一对探针 skill：一个健康、一个空 frontmatter，观察注册行为）：

- **kimi-code**：空 frontmatter 的探针**从列表里静默消失**——无错误、无警告，健康探针正常在列。
- **Claude Code**：空 frontmatter 的探针**降级注册**——以目录名兜底作为 name 和 description 出现在列表里。能按名字显式调用，但永远不可能被描述匹配触发。值守 agent 还顺带指出"这个 skill 的描述就是它自己的名字，看起来很可疑"。

两个 loader 都不报错。一个静默丢弃，一个降级成不可触发的僵尸条目——frontmatter 之伤在加载层同样没有防线，只是死法不同。

## 插曲：一次无效的矩阵运行

宿主矩阵的第一轮 claude 运行全部作废，原因不是检出或漏检，而是**宿主脚手架把实验挡住了**：headless 模式下 claude 无权读工作目录之外的文件，skill 根本没被读到。三份报告齐刷刷地报告"环境与前提冲突"。这是方法论章节那句"环境失败不是数据"的现成案例——这类运行只能丢弃重跑，不能计入检出率。

但其中一份报告值得单独留档：那位宿主虽然读不到 skill 文件，却从仓库里的夹具目录名（`truncated-main`、`empty-frontmatter`……）和自己运行目录的名字（`claude+truncate-main-60`）**推断出"本次拿到的 skill 可能本身就是被截断的故障版本"**，并声明"若属实，我也应该先报疑似截断而不是照做"。文件没读到，从环境元信息里把实验设计反推了出来——警觉性的上限比我们想的高，只是它不可靠。

目录名泄露其实是我们自己引入的污染渠道：早先的运行路径里编码了伤型（`kimi+t5-trunc-asset/...`），至少两位宿主在报告里引用路径名作为佐证。它们的检出都先有文件内容证据、路径只是旁证，所以分级仍然成立；但这足以让工具链把宿主可见路径全部改为哈希暂存（matrix.sh 已修），方法学红线也加上了第七条：**宿主可见的任何路径都不能编码伤型。**

## 宿主矩阵：同一个模型，不同的宿主脚手架

口径：矩阵测的是**宿主脚手架**差异——三列最终都跑在 kimi 模型上（Codex 默认指向一个第三方中转的 gpt 系模型且中途额度耗尽，切换到它本机已配置的 kimi provider 后重跑才拿到有效数据；那 6 次作废运行已归档，不进检出率）。

| 伤型 | kimi-code（N=8） | Claude Code（N=3） | Codex CLI（N=3） |
|---|---|---|---|
| T1 主文件截 60% | **8/8** L2 | **3/3** L2 | **3/3** L2 |
| T3 附件截半 | **2/8**（L2×2） | **3/3** L2 | **2/3**（L2×2） |

三点读法：

1. **挡路的伤在所有宿主上稳定检出**（T1：14/14）。
2. **不挡路的伤出现宿主间差异**：T3 = kimi-code 2/8、Codex 2/3、Claude Code 3/3。Claude Code 的报告系统性更重审计——一位宿主为证明"48 行不对劲"，主动对照了同目录其他 references 的行数（140–184 行）。但 N 小、运行上下文不同（claude 的 CLI 执行被沙箱拦了一部分，宿主被迫更仔细啃文件），只能写"宿主间检出行为差异可见"，不能写"谁比谁强"。
3. 每个宿主都有"证据从眼前经过却没被识别"的样本：kimi 有 6 路读完截断文件照常引用其决策树；codex 有一路跑完 `wc -l`=174、打印了末行，最终报告只字未提。**L0 的最强形态不是看不见，是看见了不认为是异常。**

## 考官们的 rubric 里有没有"完整性"

skill-upper 不是孤例。静态调查了 5 个"评测/审查型"skill 与工具的 rubric，呈三层分化：

1. **规范符合性检查是标配**：frontmatter 能否解析、name/description 必填、行数/命名约束——5 个对象全有（NVIDIA SkillEvaluator 的 schema 检查、skill-creator 的 quick_validate.py、skill-grader 的硬门禁、Tessl 的 Validation、官方 skill-reviewer）。
2. **引用完整性检查是少数派**：真正查"SKILL.md 声称的附件/脚本/链接真实存在"的，只有 NVIDIA Tier 1（藏在 code-integrity 的"dead relative Markdown links"和 quality 的 paths 检查里）和 Intercom `skill-review`——后者是本次调查唯一把 **Integrity 列为 rubric 一级类别**的工具（"cross-plugin / MCP / command references resolve, paired files match, bundled scripts work"）。上游 skill-creator、skill-grader、Tessl 均无此项。
3. **即便有，定位也多是打包门禁的附属检查，而非评测维度本身**。rubric 的主战场是行为质量（触发准不准、输出好不好、with/without 有没有提升）；出现的 "completeness" 字样（如 NVIDIA 的 Documentation completeness）指的都是语义覆盖度，不是文件完整性。

最直白的佐证来自 shakacode/agent-workflows#275 在论证为何要建此类 rubric 时的自白："Everything that actually determines whether a skill works is unchecked: whether referenced files exist..."——而既有自动化检查只有 "YAML parses, name matches the folder, description is non-empty. That is it."

值得一提：我本机的 skill-creator 是上游的增强 fork，恰好在 `quick_validate.py:92-107` 补了 `validate_path_references()`（扫描 SKILL.md 的 scripts/references/assets 引用并核对存在性）——属于社区里少见的那类补丁。上游原版没有。

## 结论

1. **skill-up 对 SKILL.md 的完整性防线≈零。** CLI 只检查文件存在（`internal/cli/run.go:705` 的 `isRegularFile`），安装即拷贝，全仓库无 frontmatter 解析；`validate` 只校验 eval.yaml schema（这一层它确实兜得住：缺失 case 文件、截断 YAML 都会硬报错）。最硬的佐证来自它自己的测试套件：e2e 夹具里的 SKILL.md 全是**没有 frontmatter 的占位文件**（"This is a mock skill used for deterministic pipeline testing"）——因为没有任何代码路径会读它。
2. **skill-upper 的评测 rubric 里没有"技能完整性"维度。** 它读目标 skill 是为了提取行为生成用例，从不校验文档完整性——评的是行为，不是文档健康。
3. **唯一生效的防线是宿主警觉性，其检出率与"伤是否横在执行路径上"强相关（8/8 到 2/8 的梯度），与伤的严重程度无关。** 把完整性交给"agent 会不会刚好注意到"，等于没有防线。
4. **带伤的考官改不准带伤的卷子。** 目标残缺会沿"文档→理解→用例"链静默传导进评测结论。
5. **与 harness 矩阵的结论收敛于同一句话：内容层判不出完整性；地基只做验收，不评级。** 一个测流，一个测文件，证据形态不同，指向相同。

## 工具：skill-guard 与 skill-quake

实验沉淀为两层工具，开源在 <https://github.com/BiBoyang/skill-quake>：

- **skill-guard**：确定性完整性门禁（stdlib-only Python，单文件）。硬检查：SKILL.md 存在、frontmatter 可解析且 name/description 非空、正文引用的附件存活；软告警：悬挂代码围栏、文件止于标题/冒号等截断签名、孤儿附件。exit code 直进 CI / pre-commit。诚实的盲区：切口整齐的隐身截断（T1 型）它判不出来——防篡改需要已知良好清单的哈希比对，那是 v2 的事。**地基只做验收，不评级。**
- **skill-quake**：故障注入实验 skill。变异脚本（mutate.sh：截主文件/删引用/截附件/清空 frontmatter）、三宿主 headless 适配器（kimi/claude/codex）、L0-L3 分级 rubric、结果收集器。方法学红线写死在 SKILL.md 里：做实验的人不当宿主、只用中性 prompt、变异只动副本、单发是轶事 x/N 才算数、系列必带阳性对照。
- `docs/REPLICATION.md` 是自助复现手册：拿着原生 Claude/GPT 订阅的人照着跑就能补出宿主矩阵的另一半。

## 局限

- 单条件样本量小（N=8/3），只能区分"稳定/概率性/稳定漏检"三档，给不出精确概率；文中的 x/N 不应被读作比率估计。
- 宿主矩阵 Claude Code 列跑在 kimi 模型上，测的是宿主脚手架差异；Codex 列无效（中转额度耗尽），且事后发现其配置本就是 gpt 系中转而非 kimi——"模型统一"的口径对那一列从未成立。原生 Claude/GPT 对照列待复现（REPLICATION.md）。
- Claude Code 列部分运行的 CLI 执行被沙箱阻断（`--add-dir` 授了 skill 目录的读，未授 bin 目录的执行）——检出轴不受影响，但 validate 层的证据不完整。
- 实验任务是"设计评测 + validate"，未跑真实 `skill-up run`（无引擎凭据）；带伤执行阶段的行为未覆盖。
- skill-guard 的截断检测是启发式，切口整齐的隐身截断（T1 型）是已知盲区，防篡改需哈希清单（v2 方向）。

## 附：实验资产索引

- 单次实验全记录：EXPERIMENT-LOG.md（含每次注入的 diff、证人输出、行为证据摘录）
- 量化数据：results/A/summary-A.md（kimi 18 路）、results/summary-B.md（宿主矩阵）
- 原始报告：results/<cell>/run-N/report.md + grade.json；无效环境样本另存 results/B-invalid-env/
- 工具：bin/skill-guard、skills/skill-quake/、tests/（夹具自测套件）
