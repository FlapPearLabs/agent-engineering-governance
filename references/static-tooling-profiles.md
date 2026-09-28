# REF: Static Tooling Profiles — 跨语言推荐矩阵

> Canonical owner: references/static-analysis-and-code-intelligence.md §11。本文件**只**拥有语言/生态的**推荐档位**。
>
> **本文件是推荐，不是安装强制。** 任何仓库都不因为"本表列了某工具"而必须采用它；采用与否由 §12（GREENFIELD vs ESTABLISHED/LEGACY）与 §13（LEGACY ADOPTION RULE）判定，且通常应是一张独立工具票。
> 表内的工具名是**生态惯例候选**；实际命令**必须**来自目标仓的 `STATIC_TOOLING_DISCOVERY`（§6），不是从本表照抄。
> 档位语义（**档位名与语义的唯一声明点 = 本文件**；`references/static-analysis-and-code-intelligence.md` §11 只作指针，不重述清单）：

```text
MINIMUM_MECHANICAL_CHECK            # 最廉价的语法/编译/解析校验；无此门 = 该语言无机械底线
RECOMMENDED_LINTER                  # 生态相称的正确性 linter
RECOMMENDED_TYPE_OR_COMPILER_CHECK  # 语言/项目设计依赖类型时
OPTIONAL_DEEP_STATIC_ANALYZER       # 更深分析器；仅当重复出现真实缺陷类时值得
FORMAT_CHECK                        # 仅在仓库已标准化格式时
```

## 0. 使用约束（先读这一节）

- 本表**不**进入 B 层不变量；`RULES.md` 不包含任何语言特定策略。仓政策可显式 OVERRIDE 本表。
- 本表**不**授权"顺手安装"：向既有仓引入新工具按 §13 先测基线；基线太脏则 `STOP: STATIC_TOOLING_BASELINE_TOO_DIRTY`。
- 本表**不**声称某工具全局存在；工具必须由仓库受控版本或确定性 CI provisioning 提供（§14）。
- 门状态**不得**坍缩：`NOT_CONFIGURED != PASS`，`ENV_BLOCKED != PASS`，`FORMAT_PASS != LINT_PASS`（§8/§18）。
- 类型检查档对**无类型系统的语言/项目**合法取 `NOT_APPLICABLE`（如纯 JS 项目、未采纳静态类型的 Python 项目）。

---

## 1. JavaScript

```text
MINIMUM_MECHANICAL_CHECK            node --check <file>（逐文件语法解析）；仓有 bundler/parser 时优先仓原生路径
RECOMMENDED_LINTER                  ESLint（flat config，生态默认）；轻量快车道候选 oxlint 或 Biome
RECOMMENDED_TYPE_OR_COMPILER_CHECK  tsc --noEmit（仅当仓采纳 TypeScript 或 JSDoc 类型检查时）
OPTIONAL_DEEP_STATIC_ANALYZER       typescript-eslint 的 type-aware 规则；SonarQube/CodeQL 类
FORMAT_CHECK                        Prettier --check 或 Biome check（仅当仓已采用其中之一）
```

- ESLint 仍是**插件深度与框架规则**的安全默认（React Hooks、a11y、framework 规则）；oxlint 是**速度层**而非全量替代；Biome 是"要一个工具管 lint+format"时的选择。
- 同一规则不要在两个 linter 里重复开启；否则会得到重复诊断。

## 2. TypeScript

```text
MINIMUM_MECHANICAL_CHECK            tsc --noEmit（仓有 tsconfig 时即最小机械底线）或仓内 parser 语法校验
RECOMMENDED_LINTER                  ESLint + typescript-eslint（flat config）
RECOMMENDED_TYPE_OR_COMPILER_CHECK  tsc --noEmit（与上项同一证据即可，不重复计数）
OPTIONAL_DEEP_STATIC_ANALYZER       type-aware lint 规则（no-floating-promises 类）；更强的语义分析器按需
FORMAT_CHECK                        Prettier --check 或 Biome check（仓已采用时）
```

- `tsconfig.json` 存在本身**不是** `TYPE_GATE = PASS`；必须证明 tsc（或等价物）**被执行**（`CONFIG_FILE_EXISTS != GATE_EXECUTED`）。
- 开启严格度（`strict`）属项目设计决策，不在本表强制。

## 3. Python

```text
MINIMUM_MECHANICAL_CHECK            python -m compileall -q <paths>（或逐文件 compile）；导入期语法门
RECOMMENDED_LINTER                  Ruff（一个二进制同时替代 flake8/isort/pyupgrade 等）
RECOMMENDED_TYPE_OR_COMPILER_CHECK  Mypy 或 Pyright（**仅当**项目采纳静态类型）；未采纳 = NOT_APPLICABLE
OPTIONAL_DEEP_STATIC_ANALYZER       Bandit（安全类）、CodeQL/Semgrep 类；仅在重复出现真实缺陷类时
FORMAT_CHECK                        ruff format --check 或 Black --check（仓已标准化时）
```

- Ruff 的**默认规则集**为 `E4, E7, E9, F`（E4/E7/E9 是 pycodestyle 的一个子集 + 全部 pyflakes）；其中 `E702`（一行多语句）等属**样式**类，首次采纳时是否纳入应按 §20 的最低复杂性判断，而不是默认全开。
- `F`（pyflakes）是**正确性**家族：未定义名、未使用导入、未使用变量、重定义。
- **不要**把首次采纳做成格式化/现代化迁移（`E` 全量、`UP`、`RUF`、`I` 往往一次引入上百条样式改动）。
- 配置应钉住 `select` 以保持确定性：新 Ruff 版本会新增规则，未钉住的规则集会在升级时漂移。

## 4. Go

```text
MINIMUM_MECHANICAL_CHECK            go build ./...（或 go vet ./... 作为最小机械门）
RECOMMENDED_LINTER                  go vet（标准工具链内）
RECOMMENDED_TYPE_OR_COMPILER_CHECK  编译器自身（go build）即类型门
OPTIONAL_DEEP_STATIC_ANALYZER       Staticcheck、golangci-lint（聚合器）
FORMAT_CHECK                        gofmt -l / gofmt -d（仓已标准化时）
```

- `gofmt` 是 Go 生态事实标准；但**仍**仅在仓库已采用时才作为门。
- golangci-lint 是聚合器：启用哪些 linter 属仓政策。

## 5. Rust

```text
MINIMUM_MECHANICAL_CHECK            cargo check（工作区范围内）
RECOMMENDED_LINTER                  cargo clippy（仓已配置时）
RECOMMENDED_TYPE_OR_COMPILER_CHECK  cargo check（类型与借用检查即编译器职责）
OPTIONAL_DEEP_STATIC_ANALYZER       clippy 的 pedantic/cargo 组；Miri（UB 类）
FORMAT_CHECK                        cargo fmt --check（仓已标准化时）
```

- Cargo workspace 已配置 Clippy 时 → §9 强制：适用变更必须跑 Clippy。
- `clippy -D warnings` 属仓政策，不在本表强制。

## 6. Java

```text
MINIMUM_MECHANICAL_CHECK            编译阶段（mvn -q -DskipTests compile / gradle compileJava）
RECOMMENDED_LINTER                  Error Prone、SpotBugs（构建插件形态）
RECOMMENDED_TYPE_OR_COMPILER_CHECK  javac（编译即类型检查）
OPTIONAL_DEEP_STATIC_ANALYZER       Checkstyle、PMD、Sonar 类
FORMAT_CHECK                        google-java-format / spotless check（仓已标准化时）
```

## 7. Kotlin

```text
MINIMUM_MECHANICAL_CHECK            gradle compileKotlin 或 kotlinc 编译阶段
RECOMMENDED_LINTER                  detekt
RECOMMENDED_TYPE_OR_COMPILER_CHECK  kotlinc（编译即类型检查）
OPTIONAL_DEEP_STATIC_ANALYZER       ktlint（亦被用作格式检查）、Sonar 类
FORMAT_CHECK                        ktlint --format 的 check 形态（仓已标准化时）
```

## 8. C

```text
MINIMUM_MECHANICAL_CHECK            编译器诊断（cc/clang -fsyntax-only <file>）
RECOMMENDED_LINTER                  clang-tidy（需要 compile_commands.json）
RECOMMENDED_TYPE_OR_COMPILER_CHECK  编译器自身（-Werror 属仓政策）
OPTIONAL_DEEP_STATIC_ANALYZER       clang static analyzer、Coverity、CodeQL
FORMAT_CHECK                        clang-format --dry-run --Werror（仓已标准化时）
```

## 9. C++

```text
MINIMUM_MECHANICAL_CHECK            编译器诊断（clang++/g++ -fsyntax-only <file>）
RECOMMENDED_LINTER                  clang-tidy（compile_commands.json 驱动）
RECOMMENDED_TYPE_OR_COMPILER_CHECK  编译器自身
OPTIONAL_DEEP_STATIC_ANALYZER       clang static analyzer、cppcheck、CodeQL
FORMAT_CHECK                        clang-format --dry-run --Werror（仓已标准化时）
```

- C/C++ 的实际命令强依赖构建系统；`CMakeLists.txt` / `compile_commands.json` 是发现入口（§6）。

## 10. C#

```text
MINIMUM_MECHANICAL_CHECK            dotnet build（编译阶段）
RECOMMENDED_LINTER                  内置 Roslyn analyzer + .editorconfig 规则集
RECOMMENDED_TYPE_OR_COMPILER_CHECK  dotnet build（编译即类型检查）
OPTIONAL_DEEP_STATIC_ANALYZER       Roslyn analyzers（第三方包）、Sonar 类
FORMAT_CHECK                        dotnet format --verify-no-changes（仓已标准化时）
```

- `*.csproj` / `Directory.Build.props` 是诊断严格度的实际配置面。

## 11. Swift

```text
MINIMUM_MECHANICAL_CHECK            swiftc -parse <file>（或 swift build）
RECOMMENDED_LINTER                  SwiftLint
RECOMMENDED_TYPE_OR_COMPILER_CHECK  swiftc / swift build（编译即类型检查）
OPTIONAL_DEEP_STATIC_ANALYZER       swift-format 的 lint 模式、Xcode analyzer
FORMAT_CHECK                        swift-format lint（仓已标准化时）
```

## 12. Ruby

```text
MINIMUM_MECHANICAL_CHECK            ruby -c <file>（语法校验）
RECOMMENDED_LINTER                  RuboCop
RECOMMENDED_TYPE_OR_COMPILER_CHECK  Sorbet 或 RBS/Steep（**仅当**项目采纳静态类型）；否则 NOT_APPLICABLE
OPTIONAL_DEEP_STATIC_ANALYZER       Brakeman（Rails 安全类）
FORMAT_CHECK                        rubocop --lint 之外的格式子集 / 专用 formatter（仓已标准化时）
```

## 13. PHP

```text
MINIMUM_MECHANICAL_CHECK            php -l <file>（语法校验）
RECOMMENDED_LINTER                  PHP_CodeSniffer / PHPStan（静态分析形态）
RECOMMENDED_TYPE_OR_COMPILER_CHECK  PHPStan 或 Psalm（通常同时充当类型与静态分析门）
OPTIONAL_DEEP_STATIC_ANALYZER       Psalm/PHPStan 最高 level、Sonar 类
FORMAT_CHECK                        php-cs-fixer --dry-run / Pint（仓已标准化时）
```

## 14. Shell

```text
MINIMUM_MECHANICAL_CHECK            bash -n <file>（语法解析；按 shebang 选择解释器）
RECOMMENDED_LINTER                  ShellCheck
RECOMMENDED_TYPE_OR_COMPILER_CHECK  NOT_APPLICABLE（shell 无类型系统）
OPTIONAL_DEEP_STATIC_ANALYZER       ShellCheck 的更高严重度集合
FORMAT_CHECK                        shfmt -d（仓已标准化时）
```

- `.shellcheckrc` 是发现入口；ShellCheck 的 `--severity` 阈值属仓政策。

## 15. Terraform

```text
MINIMUM_MECHANICAL_CHECK            terraform validate（先 terraform init，或在已 init 的目录）
RECOMMENDED_LINTER                  TFLint
RECOMMENDED_TYPE_OR_COMPILER_CHECK  terraform validate 的 schema/类型校验（provider schema 驱动）
OPTIONAL_DEEP_STATIC_ANALYZER       Checkov / tfsec / Trivy 类安全扫描
FORMAT_CHECK                        terraform fmt -check（仓已标准化时）
```

- `terraform validate` **不能**替代 `plan`；静态门与状态变更验证是两件事。

## 16. JSON

```text
MINIMUM_MECHANICAL_CHECK            解析校验（python -m json.tool / jq empty / 仓内 JSON parser）
RECOMMENDED_LINTER                  JSON Schema 校验（**当且仅当**仓内有 schema）
RECOMMENDED_TYPE_OR_COMPILER_CHECK  NOT_APPLICABLE
OPTIONAL_DEEP_STATIC_ANALYZER       schema 驱动的语义约束校验
FORMAT_CHECK                        仓原生 formatter 的 check 形态（仓已标准化时）
```

- 对**有 schema 的** JSON 配置，`SCHEMA_CONFIG_GATE` 是有效门（如本仓 `schemas/*.json`）。

## 17. YAML

```text
MINIMUM_MECHANICAL_CHECK            YAML 解析校验（yq / python -c 'import yaml,...'）
RECOMMENDED_LINTER                  yamllint
RECOMMENDED_TYPE_OR_COMPILER_CHECK  JSON Schema 校验（Kubernetes/GitHub Actions schema 类）
OPTIONAL_DEEP_STATIC_ANALYZER       针对具体 dialect 的语义校验（CI schema、K8s schema）
FORMAT_CHECK                        prettier --check / yamlfmt（仓已标准化时）
```

## 18. TOML

```text
MINIMUM_MECHANICAL_CHECK            TOML 解析校验（python -c 'import tomllib,...' / taplo check）
RECOMMENDED_LINTER                  taplo（含 schema 校验能力）
RECOMMENDED_TYPE_OR_COMPILER_CHECK  NOT_APPLICABLE（除非有 schema）
OPTIONAL_DEEP_STATIC_ANALYZER       schema 驱动校验（Cargo/pyproject schema 类）
FORMAT_CHECK                        taplo format --check（仓已标准化时）
```

## 19. Dockerfile

```text
MINIMUM_MECHANICAL_CHECK            解析/构建前置校验（docker build 的 parse 阶段 / hadolint 解析）
RECOMMENDED_LINTER                  hadolint
RECOMMENDED_TYPE_OR_COMPILER_CHECK  NOT_APPLICABLE
OPTIONAL_DEEP_STATIC_ANALYZER       Trivy / Grype 类镜像层安全扫描（构建后）
FORMAT_CHECK                        NOT_APPLICABLE（生态无标准 formatter）
```

## 20. SQL

```text
MINIMUM_MECHANICAL_CHECK            方言解析校验（sqlfluff parse 或目标引擎的 dry-run/EXPLAIN 前置校验）
RECOMMENDED_LINTER                  sqlfluff
RECOMMENDED_TYPE_OR_COMPILER_CHECK  NOT_APPLICABLE（除非目标引擎提供 schema 感知的校验）
OPTIONAL_DEEP_STATIC_ANALYZER       迁移工具的前置校验（框架内建）、schema diff 工具
FORMAT_CHECK                        sqlfluff format --check（仓已标准化时）
```

- SQL 的"最小机械门"**强依赖方言与引擎**（PostgreSQL / MySQL / BigQuery / Spark 等）；不得套用单一通用命令。

---

## 21. 汇总索引

| 语言 | MINIMUM | LINTER | TYPE/COMPILER | DEEP（可选） | FORMAT |
|---|---|---|---|---|---|
| JavaScript | `node --check` | ESLint / oxlint / Biome | `tsc --noEmit`（采纳时） | type-aware 规则 | Prettier / Biome |
| TypeScript | `tsc --noEmit` | ESLint + typescript-eslint | `tsc --noEmit` | type-aware 规则 | Prettier / Biome |
| Python | `compileall` | Ruff | Mypy / Pyright（采纳时） | Bandit / CodeQL | `ruff format --check` |
| Go | `go build` | `go vet` | 编译器 | Staticcheck / golangci-lint | `gofmt -l` |
| Rust | `cargo check` | `cargo clippy` | `cargo check` | clippy pedantic / Miri | `cargo fmt --check` |
| Java | 编译阶段 | Error Prone / SpotBugs | `javac` | Checkstyle / PMD | spotless check |
| Kotlin | `compileKotlin` | detekt | `kotlinc` | ktlint / Sonar | ktlint check |
| C | `cc -fsyntax-only` | clang-tidy | 编译器 | clang analyzer / cppcheck | clang-format |
| C++ | `clang++ -fsyntax-only` | clang-tidy | 编译器 | clang analyzer / CodeQL | clang-format |
| C# | `dotnet build` | Roslyn analyzers | `dotnet build` | 第三方 analyzers | `dotnet format` |
| Swift | `swiftc -parse` | SwiftLint | `swift build` | swift-format lint | swift-format |
| Ruby | `ruby -c` | RuboCop | Sorbet / RBS（采纳时） | Brakeman | rubocop 格式子集 |
| PHP | `php -l` | PHP_CodeSniffer | PHPStan / Psalm | Psalm 最高 level | php-cs-fixer |
| Shell | `bash -n` | ShellCheck | `NOT_APPLICABLE` | 更高严重度集合 | `shfmt -d` |
| Terraform | `terraform validate` | TFLint | `terraform validate` | Checkov / tfsec | `terraform fmt -check` |
| JSON | 解析校验 | JSON Schema（有 schema 时） | `NOT_APPLICABLE` | schema 语义校验 | formatter check |
| YAML | 解析校验 | yamllint | JSON Schema（有 schema 时） | dialect 校验 | prettier / yamlfmt |
| TOML | 解析校验 | taplo | `NOT_APPLICABLE` | schema 校验 | `taplo format --check` |
| Dockerfile | parse 阶段 | hadolint | `NOT_APPLICABLE` | Trivy / Grype | `NOT_APPLICABLE` |
| SQL | 方言解析 | sqlfluff | `NOT_APPLICABLE` | 迁移/schema diff | `sqlfluff format --check` |

`NOT_APPLICABLE` 在上表是**正常且合法**的档位取值，不是缺口；只有"应存在却被跳过"才构成 `STATIC_TOOLING_GAP`。
