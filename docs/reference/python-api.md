# Python API Reference

Generated from source with `uv run python -m tools.check_docs --api-reference`.
Lists public definitions, constructors, methods, and dataclass fields. These are harness APIs; dbwarden is invoked through its installed CLI.
Abstract provider methods define the contract implemented by concrete providers. See [MCP Server](../mcp-server.md) for remote tools and limits.

## `harness/cli.py`

### `CommandResult`

```python
args: tuple[str, ...]
returncode: int
stdout: str
stderr: str
def require_success(self) -> CommandResult: ...
def require_clean(self) -> CommandResult: ...
def require_failure(self, *fragments: str) -> CommandResult: ...
def output(self) -> str: ...
def plain_output(self) -> str: ...
```

### `DbwardenCli`

Invoke the installed dbwarden CLI without importing implementation modules.

```python
def __init__(self, work_dir: Path, *, executable: str | None=None, env: dict[str, str] | None=None) -> None: ...
def run(self, *args: str, check: bool=True, timeout: float=120.0, clean: bool=False) -> CommandResult: ...
def run_raw(self, command: Sequence[str], *, check: bool=True, timeout: float=120.0) -> CommandResult: ...
```

## `harness/distribution.py`

### `DistributionReport`

```python
name: str
version: str
files: tuple[str, ...]
entry_points: tuple[tuple[str, str, str], ...] = ()
location: str = ''
```

### `inspect_distribution`

```python
def inspect_distribution(name: str='dbwarden') -> DistributionReport: ...
```

### `inspect_distributions`

```python
def inspect_distributions(names: tuple[str, ...]) -> tuple[DistributionReport, ...]: ...
```

### `assert_wheel_is_clean`

```python
def assert_wheel_is_clean(report: DistributionReport) -> None: ...
```

### `assert_console_entry_point`

```python
def assert_console_entry_point(report: DistributionReport) -> None: ...
```

## `harness/matrix.py`

### `VersionMatrix`

```python
python: tuple[str, ...] = ('3.12', '3.13')
postgres: tuple[str, ...] = ('14', '15', '16', '17')
clickhouse: tuple[str, ...] = ('24.3', '26.6')
mysql: tuple[str, ...] = ('8.0', '8.4')
mariadb: tuple[str, ...] = ('10.11', '11.4')
```

### `provider_versions`

```python
def provider_versions(matrix: VersionMatrix=DEFAULT_MATRIX) -> Iterator[tuple[str, str]]: ...
```

## `harness/plugins.py`

### `PluginInstaller`

Install plugins through dbwarden's public plugin CLI.

```python
def __init__(self, work_dir: Path) -> None: ...
def add(self, distribution: str, *, version: str | None=None) -> CommandResult: ...
def build_add_command(self, distribution: str, *, version: str | None=None) -> tuple[str, ...]: ...
def add_many(self, distributions: list[str] | tuple[str, ...]) -> list[CommandResult]: ...
def add_required(self) -> list[CommandResult]: ...
def list(self) -> CommandResult: ...
def info(self, distribution: str) -> CommandResult: ...
def remove(self, distribution: str) -> CommandResult: ...
def assert_discovered(result: CommandResult, distributions: tuple[str, ...]=REQUIRED_PLUGINS) -> None: ...
```

## `harness/provenance.py`

### `file_sha256`

```python
def file_sha256(path: Path) -> str | None: ...
```

### `collect_provenance`

```python
def collect_provenance(*, lockfile: Path | None=None, distributions: tuple[str, ...]=('dbwarden',)) -> dict[str, Any]: ...
```

### `assert_installed_distribution`

```python
def assert_installed_distribution(report: dict[str, Any], *, checkout: Path | str | None=None) -> None: ...
```

## `infrastructure/providers/base.py`

### `DatabaseProvider`

Lifecycle contract for a real database used by integration tests.

```python
def start(self) -> str: ...
def stop(self) -> None: ...
def reset(self) -> None: ...
def version(self) -> str: ...
def diagnostics(self) -> dict[str, Any]: ...
def logs(self) -> str: ...
```

## `infrastructure/providers/clickhouse.py`

### `ClickHouseProvider`

```python
def __init__(self, image: str='clickhouse/clickhouse-server:24.3', *, database: str='harness', network: Network | None=None) -> None: ...
def url(self) -> str: ...
def reset(self) -> None: ...
def wait_for_connection(self, timeout: float=60.0) -> None: ...
```

## `infrastructure/providers/clickhouse_cluster.py`

### `ClickHouseClusterProvider`

A two-node ClickHouse cluster with a shared ClickHouse Keeper.

```python
def __init__(self, image: str='clickhouse/clickhouse-server:24.3', keeper_image: str='clickhouse/clickhouse-keeper:24.3', *, database: str='harness') -> None: ...
def start(self) -> str: ...
def stop(self) -> None: ...
def reset(self) -> None: ...
def url(self, node: int=0) -> str: ...
def version(self) -> str: ...
def diagnostics(self) -> dict[str, Any]: ...
def host_port(self, node: int=0) -> tuple[str, int]: ...
```

## `infrastructure/providers/docker.py`

### `DockerDatabaseProvider`

```python
image: str
container_port: int
environment: dict[str, str] = field(default_factory=dict)
network: Network | None = field(default=None, repr=False)
def start(self) -> str: ...
def stop(self) -> None: ...
def reset(self) -> None: ...
def version(self) -> str: ...
def diagnostics(self) -> dict[str, Any]: ...
def logs(self) -> str: ...
def host_port(self) -> tuple[str, int]: ...
def url(self) -> str: ...
def wait_for_connection(self, timeout: float=60.0) -> None: ...
```

## `infrastructure/providers/factory.py`

### `provider_for`

Build a matrix provider without starting a container.

```python
def provider_for(backend: str, version: str, *, network: Network | None=None) -> DatabaseProvider: ...
```

## `infrastructure/providers/mariadb.py`

### `MariaDBProvider`

```python
def __init__(self, image: str='mariadb:11.4', *, database: str='harness', network: Network | None=None) -> None: ...
```

## `infrastructure/providers/mysql.py`

### `MySQLProvider`

```python
def __init__(self, image: str='mysql:8.4', *, database: str='harness', network: Network | None=None) -> None: ...
def url(self) -> str: ...
def reset(self) -> None: ...
```

## `infrastructure/providers/postgres.py`

### `PostgresProvider`

```python
def __init__(self, image: str='postgres:17', *, database: str='harness', network: Network | None=None) -> None: ...
def url(self) -> str: ...
def reset(self) -> None: ...
```

## `infrastructure/providers/sqlite.py`

### `SQLiteProvider`

File-backed provider for the SQLite backend.

```python
def __init__(self, path: Path | None=None) -> None: ...
def start(self) -> str: ...
def url(self) -> str: ...
def stop(self) -> None: ...
def reset(self) -> None: ...
def version(self) -> str: ...
def diagnostics(self) -> dict[str, Any]: ...
```

## `mcp_server/bundle.py`

### `assemble_proof_bundle`

Freeze workspace APIs and write a read-only evidence bundle.

```python
def assemble_proof_bundle(workspace: Workspace, base_models_source: str, mutated_models_source: str, track_a_result: TrackResult, track_b_result: TrackResult, comparison: ComparisonResult, reference_mode: str) -> TwoTrackResult: ...
```

## `mcp_server/classifier.py`

### `classify_divergence`

Deterministic 95/5 classification based on dbwarden's emitted plan.

```python
def classify_divergence(plan: dict[str, Any] | None, diff_summary: dict[str, Any]) -> str: ...
```

## `mcp_server/comparator.py`

### `compare_schemas`

```python
def compare_schemas(dump_a: str, dump_b: str, backend: str='') -> ComparisonResult: ...
```

### `normalize_schema_dump`

Canonicalize parsed DDL while preserving literals, identifiers and table options.

```python
def normalize_schema_dump(dump: str, backend: str='') -> str: ...
```

## `mcp_server/config.py`

### `HarnessMcpConfig`

Runtime configuration for the MCP server.

```python
max_workspaces: int
bug_reports_dir: Path
workspace_root: Path
warm_pool_enabled: bool
warm_pool_count: dict[str, int]
db_versions: dict[str, str]
def from_env(cls) -> HarnessMcpConfig: ...
```

## `mcp_server/dumper.py`

### `SchemaDumpError`

Raised when a native schema dump fails.

```python
```

### `dump_database_schema`

Dump the schema of a live database using backend-native tooling.

```python
def dump_database_schema(database_url: str, backend: str) -> str: ...
```

## `mcp_server/inspector.py`

### `read_workspace_file`

```python
def read_workspace_file(workspace: Workspace, relative_path: str) -> str: ...
```

### `inspect_both_schemas`

```python
def inspect_both_schemas(workspace: Workspace) -> tuple[str, str]: ...
```

### `sqlalchemy_url`

Translate ClickHouse HTTP provider URLs to the installed SQLAlchemy driver.

```python
def sqlalchemy_url(database_url: str) -> URL: ...
```

### `query_track_a`

Query Track A, guarding reads and committing explicitly enabled writes.

```python
def query_track_a(workspace: Workspace, sql: str, read_only: bool=True) -> list[dict[str, object]]: ...
```

## `mcp_server/models.py`

### `InitializeResult`

```python
workspace_id: str
backend: str
db_version: str | None
work_dir: Path
track_a_url: str
track_b_url: str
```

### `DestroyResult`

```python
workspace_id: str
removed: bool
```

### `WorkspaceInfo`

```python
workspace_id: str
backend: str
db_version: str | None
work_dir: Path
created_at: float
frozen: bool
```

### `ListWorkspacesResult`

```python
workspaces: list[WorkspaceInfo]
```

### `WriteResult`

```python
workspace_id: str
relative_path: str
bytes_written: int
```

### `MutationResult`

```python
workspace_id: str
relative_path: str
new_source: str
applied: list[dict[str, Any]]
```

### `TrackResult`

```python
success: bool
stage: str
error: str = ''
schema_dump: str = ''
schema_dump_path: Path | None = None
plan: dict[str, Any] | None = None
```

### `ComparisonSummary`

```python
missing_columns: list[dict[str, str]] = field(default_factory=list)
type_mismatches: list[dict[str, str]] = field(default_factory=list)
missing_tables: list[str] = field(default_factory=list)
extra_tables: list[str] = field(default_factory=list)
```

### `ComparisonResult`

```python
identical: bool
diff: str = ''
summary: ComparisonSummary = field(default_factory=ComparisonSummary)
```

### `TwoTrackResult`

```python
passed: bool
track_a: TrackResult
track_b: TrackResult
comparator: ComparisonResult
classification: str
proof_bundle_path: Path | None = None
ai_may_inspect: bool = True
```

## `mcp_server/mutations.py`

### `MutationError`

Raised when a mutation cannot be applied to the model source.

```python
```

### `apply_mutation`

Edit a declared model column or index; reject unsupported source shapes.

```python
def apply_mutation(source: str, mutation: dict[str, Any]) -> str: ...
```

## `mcp_server/network.py`

### `WorkspaceNetwork`

A Docker bridge network scoped to one workspace.

```python
network: Network
network_id: str
name: str
def create(cls) -> WorkspaceNetwork: ...
def connect(self, container_id: str) -> None: ...
def disconnect(self, container_id: str) -> None: ...
def remove(self) -> None: ...
```

## `mcp_server/pool.py`

### `ContainerPool`

Warm pool of pre-started database containers keyed by backend.

```python
def __init__(self) -> None: ...
def start(self) -> None: ...
def stop(self) -> None: ...
def claim(self, backend: str, version: str, workspace_network: WorkspaceNetwork) -> DatabaseProvider: ...
def release(self, backend: str, provider: DatabaseProvider, workspace_network: WorkspaceNetwork | None) -> None: ...
```

## `mcp_server/server.py`

### `initialize_workspace`

Create a new isolated workspace with a database pair for two-track testing.

```python
def initialize_workspace(backend: str, db_version: str | None=None, name_prefix: str | None=None) -> str: ...
```

### `destroy_workspace`

Destroy a workspace and release its resources.

```python
def destroy_workspace(workspace_id: str) -> str: ...
```

### `list_workspaces`

List all active workspaces.

```python
def list_workspaces() -> str: ...
```

### `write_model_file`

Write a file inside a workspace; app/models.py also updates the test model state.

```python
def write_model_file(workspace_id: str, relative_path: str, content: str) -> str: ...
```

### `apply_mutation`

Apply a structured mutation to the current app/models.py.

```python
def apply_mutation(workspace_id: str, mutation: dict[str, Any]) -> str: ...
```

### `run_two_track_test`

Run dbwarden (Track A) and a SQLAlchemy Core DDL reference (Track B), then compare schemas.

```python
def run_two_track_test(workspace_id: str, reference_mode: str='nuclear') -> str: ...
```

### `read_file`

Read a file from a workspace (read-only; works on frozen workspaces).

```python
def read_file(workspace_id: str, relative_path: str) -> str: ...
```

### `inspect_schema`

Return native schema dumps for both tracks (read-only).

```python
def inspect_schema(workspace_id: str) -> str: ...
```

### `query_database`

Run a SQL query against Track A's database. Defaults to read-only.

```python
def query_database(workspace_id: str, sql: str, read_only: bool=True) -> str: ...
```

### `run_server`

```python
def run_server() -> None: ...
```

## `mcp_server/track_a.py`

### `run_track_a`

```python
def run_track_a(workspace: Workspace, base_models_source: str, mutated_models_source: str) -> TrackResult: ...
```

## `mcp_server/track_b.py`

### `run_track_b_nuclear`

Drop and recreate the schema from the mutated model module.

```python
def run_track_b_nuclear(workspace: Workspace, mutated_models_source: str) -> TrackResult: ...
```

### `run_track_b_incremental`

Best-effort incremental reference path.

```python
def run_track_b_incremental(workspace: Workspace, base_models_source: str, mutated_models_source: str) -> TrackResult: ...
```

## `mcp_server/workspace.py`

### `Workspace`

```python
workspace_id: str
backend: str
db_version: str | None
work_dir: Path
network: WorkspaceNetwork | None
track_a_provider: DatabaseProvider
track_b_provider: DatabaseProvider
track_a_url: str
track_b_url: str
created_at: float = field(default_factory=time.time)
frozen: bool = False
mutations: list[dict[str, Any]] = field(default_factory=list)
base_models_source: str | None = None
current_models_source: str | None = None
def freeze(self) -> None: ...
def resolve_path(self, relative_path: str) -> Path: ...
```

### `WorkspaceManager`

Create, track, and destroy isolated per-test workspaces.

```python
def __init__(self) -> None: ...
def initialize(self, backend: str, db_version: str | None=None, name_prefix: str | None=None) -> InitializeResult: ...
def destroy(self, workspace_id: str) -> DestroyResult: ...
def list_workspaces(self) -> ListWorkspacesResult: ...
def get(self, workspace_id: str) -> Workspace: ...
```

## `schemas/base.py`

### `ReferenceSchema`

```python
name: str
models_py: Path
expected_tables: tuple[str, ...]
expected_indexes: tuple[str, ...]
backend: str
def source(self) -> str: ...
```

## `schemas/registry.py`

### `discover_schemas`

```python
def discover_schemas(root: Path | None=None) -> tuple[ReferenceSchema, ...]: ...
```

## `tools/artifacts.py`

### `ArtifactBundle`

```python
directory: Path
stdout: Path
stderr: Path
metadata: Path
copied_paths: tuple[Path, ...] = ()
```

### `ArtifactCollector`

Persist enough CLI context to diagnose a failed black-box test.

```python
def capture(self, result: CommandResult, *, work_dir: Path, destination: Path, extra_paths: tuple[Path, ...]=(), extra_metadata: dict[str, object] | None=None) -> ArtifactBundle: ...
def capture_provider(self, provider: object, destination: Path) -> tuple[Path, Path]: ...
```

## `tools/case_runner.py`

### `strip_ansi`

```python
def strip_ansi(text: str) -> str: ...
```

### `StepResult`

One ``make-migrations`` (+ optional ``migrate``) revision.

```python
index: int
returncode: int
stdout: str
stderr: str
new_files: tuple[str, ...] = ()
sql: str = ''
migrate_returncode: int | None = None
migrate_output: str = ''
def upgrade(self) -> str: ...
def rollback(self) -> str: ...
def generated(self) -> bool: ...
def silently_skipped(self) -> bool: ...
def reported_no_changes(self) -> bool: ...
def reported_no_tables(self) -> bool: ...
def server_error(self) -> str: ...
def verdict(self) -> str: ...
```

### `CaseResult`

```python
case_id: str
backend: str
work_dir: Path
database: str | None = None
steps: list[StepResult] = field(default_factory=list)
harness_error: str | None = None
live_schema: str = ''
schema_after_rollback: str = ''
rollback_returncode: int | None = None
rollback_output: str = ''
diff_online: str = ''
diff_offline: str = ''
def last(self) -> StepResult: ...
def verdict(self) -> str: ...
def diff_operations(self, *, offline: bool=False) -> list[dict[str, Any]]: ...
def summary(self) -> str: ...
```

### `GenerationCase`

One project taken through ``revisions`` successive model revisions.

```python
case_id: str
backend: str
revisions: Sequence[str]
flags: Sequence[Sequence[str]] | None = None
apply: bool = True
rollback: int = 0
capture_schema: bool = False
capture_diff: bool = False
config_extra: str = ''
model_paths: tuple[str, ...] = ('app',)
def flags_for(self, index: int) -> tuple[str, ...]: ...
```

### `CaseRunner`

Materialize and drive :class:`GenerationCase` projects.

```python
def __init__(self, root: Path, *, url_for: Any, clickhouse_http: str | None=None, env: dict[str, str] | None=None) -> None: ...
def clickhouse_query(self, sql: str, database: str | None=None) -> tuple[int, str]: ...
def clickhouse_schema(self, database: str) -> str: ...
def run(self, case: GenerationCase) -> CaseResult: ...
def run_all(self, cases: Iterable[GenerationCase], *, workers: int=8) -> list[CaseResult]: ...
```

### `sqlite_urls`

```python
def sqlite_urls(case_id: str, work_dir: Path) -> tuple[str, None]: ...
```

### `clickhouse_urls`

Build a ``url_for`` that gives every case its own ClickHouse database.

```python
def clickhouse_urls(base_url: str): ...
```

### `report`

One line per case — the format the generative suites put in failure text.

```python
def report(results: Sequence[CaseResult]) -> str: ...
```

### `verdict_counts`

```python
def verdict_counts(results: Sequence[CaseResult]) -> dict[str, int]: ...
```

## `tools/convergence_benchmark.py`

### `ConvergenceBenchmarkResult`

```python
migration_count: int
prepare_seconds: float
migrate_seconds: float
diff_seconds: float
total_seconds: float
def to_json(self) -> str: ...
```

### `model_source`

```python
def model_source(migration_count: int) -> str: ...
```

### `create_history`

```python
def create_history(work_dir: Path, migration_count: int) -> None: ...
```

### `run_convergence_benchmark`

```python
def run_convergence_benchmark(work_dir: Path, *, migration_count: int=500, executable: str='dbwarden') -> ConvergenceBenchmarkResult: ...
```

## `tools/drift_checker.py`

### `SchemaSnapshot`

```python
tables: tuple[str, ...]
columns: dict[str, tuple[str, ...]]
indexes: dict[str, tuple[str, ...]]
column_details: dict[str, tuple[tuple[str, str, bool, str | None], ...]] = field(default_factory=dict)
primary_keys: dict[str, tuple[str, ...]] = field(default_factory=dict)
foreign_keys: dict[str, tuple[tuple[str, str, str], ...]] = field(default_factory=dict)
unique_constraints: dict[str, tuple[str, ...]] = field(default_factory=dict)
views: tuple[str, ...] = ()
table_options: dict[str, tuple[tuple[str, str], ...]] = field(default_factory=dict)
```

### `DriftItem`

```python
kind: str
object_name: str
expected: Any
actual: Any
```

### `DriftChecker`

Capture portable structural state through SQLAlchemy inspection.

```python
def capture(self, database_url: str) -> SchemaSnapshot: ...
def diff(self, expected: SchemaSnapshot, actual: SchemaSnapshot) -> list[DriftItem]: ...
def assert_equal(self, expected: SchemaSnapshot, actual: SchemaSnapshot) -> None: ...
```

## `tools/generation_probe.py`

### `SwallowedError`

```python
location: str
exception: str
traceback: str
```

### `GenerationProbe`

Run a dbwarden command with model-discovery error swallowing disabled.

```python
def __init__(self, work_dir: Path, *, env: dict[str, str] | None=None) -> None: ...
def run(self, *args: str, timeout: float=180.0) -> tuple[int, str, str]: ...
def swallowed_errors(self, *args: str) -> tuple[SwallowedError, ...]: ...
```

### `parse_swallowed`

```python
def parse_swallowed(stderr: str) -> tuple[SwallowedError, ...]: ...
```

## `tools/migration_player.py`

### `MigrationPlayer`

Drive a disposable dbwarden project through its public CLI.

```python
def __init__(self, database_url: str, work_dir: Path) -> None: ...
def init(self) -> CommandResult: ...
def configure(self, *, database_name: str='primary', database_type: str | None=None, model_paths: tuple[str, ...]=(), dev_database_type: str | None=None, dev_database_url: str | None=None, **extra: Any) -> Path: ...
def init_and_configure(self, **kwargs: object) -> Path: ...
def write_model_source(self, source: str, *, filename: str='models.py') -> Path: ...
def make_migrations(self, message: str, *flags: str) -> CommandResult: ...
def migrate(self, *flags: str) -> CommandResult: ...
def rollback(self, count: int=1, *flags: str) -> CommandResult: ...
def status(self, *flags: str) -> CommandResult: ...
def diff(self, *flags: str) -> CommandResult: ...
def diff_operations(self) -> list[dict[str, Any]]: ...
def generate_models(self, *flags: str) -> CommandResult: ...
def export_models(self, *flags: str) -> CommandResult: ...
def check_impact(self, *flags: str) -> CommandResult: ...
def assert_converged(self, *flags: str) -> None: ...
def assert_history_integrity(self) -> None: ...
```

### `parse_diff_output`

Extract dbwarden's JSON diff payload from log-prefixed CLI output.

```python
def parse_diff_output(output: str) -> list[dict[str, Any]]: ...
```

## `tools/model_source.py`

### `module`

Assemble a model module for ``backend`` from class-definition bodies.

```python
def module(backend: str, *bodies: str, preamble: str='') -> str: ...
```

### `Column_`

One column in a generated model.

```python
name: str
type: str = 'Integer'
primary_key: bool = False
args: str = ''
def render(self) -> str: ...
```

### `ClickHouseTable`

A ClickHouse model whose Meta is assembled from named properties.

```python
name: str = 't'
class_name: str = 'T'
columns: tuple[Column_, ...] = (Column_('id', primary_key=True), Column_('a'))
engine: str = 'merge_tree()'
order_by: str | None = '["id"]'
primary_key: str | None = None
partition_by: str | None = None
sample_by: str | None = None
ttl: str | None = None
settings: str | None = None
indexes: str | None = None
projections: str | None = None
zookeeper_path: str | None = None
replica_name: str | None = None
comment: str | None = None
column_meta: dict[str, str] = field(default_factory=dict)
column_comments: dict[str, str] = field(default_factory=dict)
base: str = 'Base'
meta_base: str = 'CHTableMeta'
raw_meta: str | None = None
def render(self) -> str: ...
def with_(self, **changes: Any) -> ClickHouseTable: ...
def source(self) -> str: ...
```

### `ClickHouseView`

A ClickHouse materialized/aggregating view model.

```python
name: str = 'v'
class_name: str = 'V'
columns: tuple[Column_, ...] = (Column_('id', primary_key=True),)
spec: str = 'materialized_view(select="SELECT id FROM src", engine=merge_tree(), order_by=["id"])'
base: str = 'Base'
def render(self) -> str: ...
```

### `clickhouse_single_column`

A one-column ClickHouse table — the shape used by the type matrix.

```python
def clickhouse_single_column(column_type: str, *, column_meta: str | None=None) -> str: ...
```

## `tools/offline_integrity.py`

### `state_files`

```python
def state_files(work_dir: Path) -> tuple[Path, ...]: ...
```

### `build_state_manifest`

```python
def build_state_manifest(work_dir: Path) -> dict[str, str]: ...
```

### `write_state_manifest`

```python
def write_state_manifest(work_dir: Path, destination: Path | None=None) -> Path: ...
```

### `verify_state_manifest`

```python
def verify_state_manifest(work_dir: Path, manifest: Path | None=None) -> None: ...
```

## `tools/performance_baseline.py`

### `PerformanceBaseline`

```python
migration_count: int
prepare_seconds: float
migrate_seconds: float
diff_seconds: float
total_seconds: float
def load(cls, path: Path, migration_count: int) -> PerformanceBaseline: ...
def assert_within(self, result: ConvergenceBenchmarkResult, tolerance: float=0.2) -> None: ...
```

## `tools/report_generator.py`

### `load_junit_report`

Load pytest's portable JUnit XML through the standard library.

```python
def load_junit_report(path: Path) -> dict[str, Any]: ...
```

### `write_markdown_report`

```python
def write_markdown_report(report: dict[str, Any], destination: Path) -> None: ...
```

### `write_json_report`

```python
def write_json_report(report: dict[str, Any], destination: Path) -> None: ...
```

## `tools/round_trip_driver.py`

### `RoundTripResult`

```python
shape_id: str
work_dir: Path
database: str | None = None
make_returncode: int = 0
migrate_returncode: int = 0
generate_returncode: int = 0
generate_output: str = ''
generated_files: tuple[str, ...] = ()
generated_sources: dict[str, str] = field(default_factory=dict)
live_schema: str = ''
rediff_output: str = ''
remake_output: str = ''
remake_returncode: int = 0
remake_sql: str = ''
def diff_operations(self) -> list[dict[str, Any]]: ...
def diff_is_clean(self) -> bool: ...
def regenerated_migration(self) -> bool: ...
def bookkeeping_models(self) -> tuple[str, ...]: ...
def setup_ok(self) -> bool: ...
def converged(self) -> bool: ...
def unimportable(self) -> dict[str, str]: ...
def summary(self) -> str: ...
```

### `RoundTripDriver`

Run one model shape through the full reverse-engineering loop.

```python
def __init__(self, root: Path, *, url_for: Any, backend: str, env: dict[str, str] | None=None, prepare_database: Any=None) -> None: ...
def run(self, shape_id: str, model_source: str) -> RoundTripResult: ...
```

## `tools/schema_runner.py`

### `SchemaRunner`

Materialize a reference schema into a disposable dbwarden project.

```python
def __init__(self, schema: ReferenceSchema, player: MigrationPlayer, *, database_type: str | None=None) -> None: ...
def prepare(self) -> Path: ...
def configure(self) -> Path: ...
def initialize(self) -> Path: ...
def make_and_apply(self, message: str='reference schema') -> None: ...
def capture_schema(self) -> SchemaSnapshot: ...
def assert_expected_schema(self) -> SchemaSnapshot: ...
def reverse_engineer(self, output_dir: str='generated', *, tables: str | None=None, exclude_tables: str | None=None, clickhouse_engines: bool=False, relationships: bool=False) -> Path: ...
def round_trip(self, output_dir: str='generated', *, tables: str | None=None) -> list[dict[str, object]]: ...
```

## `tools/snapshot_manager.py`

### `SQLSnapshot`

```python
relative_path: str
content: str
sha256: str
```

### `SnapshotDiff`

```python
expected: SQLSnapshot
actual: SQLSnapshot
def changed(self) -> bool: ...
def unified_text(self) -> str: ...
```

### `SnapshotManager`

```python
def capture(self, migration_file: Path, *, root: Path | None=None) -> SQLSnapshot: ...
def compare(self, current: SQLSnapshot, baseline: SQLSnapshot) -> SnapshotDiff: ...
def approve(self, diff: SnapshotDiff, destination: Path) -> None: ...
def assert_unchanged(self, diff: SnapshotDiff) -> None: ...
def baseline_for(self, root: Path, *, version: str, backend: str, name: str) -> Path | None: ...
def build_manifest(self, root: Path) -> dict[str, str]: ...
def write_manifest(self, root: Path, destination: Path | None=None) -> Path: ...
def verify_manifest(self, root: Path, manifest: Path | None=None) -> None: ...
```

## `tools/sql_probe.py`

### `ConstraintNotEnforced`

A statement the database was expected to refuse succeeded instead.

```python
```

### `SqlProbe`

Exercise a live database with ordinary SQL to test behaviour, not shape.

```python
def __init__(self, database_url: str) -> None: ...
def close(self) -> None: ...
def execute(self, *statements: str) -> None: ...
def scalar(self, statement: str) -> Any: ...
def rows(self, statement: str) -> list[tuple[Any, ...]]: ...
def rejects(self, statement: str) -> bool: ...
def assert_rejects(self, statement: str, *, because: str) -> None: ...
```
