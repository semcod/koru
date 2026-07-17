# koru

SUMD - Structured Unified Markdown Descriptor for AI-aware project refactorization

## Contents

- [Metadata](#metadata)
- [Architecture](#architecture)
- [Workflows](#workflows)
- [Dependencies](#dependencies)
- [Call Graph](#call-graph)
- [Test Contracts](#test-contracts)
- [Refactoring Analysis](#refactoring-analysis)
- [Intent](#intent)

## Metadata

- **name**: `koru`
- **version**: `0.1.395`
- **python_requires**: `>=3.12,<3.14`
- **license**: Apache-2.0
- **ai_model**: `openrouter/deep/deep-v4-pro`
- **ecosystem**: SUMD + DOQL + testql + taskfile
- **generated_from**: pyproject.toml, Taskfile.yml, Makefile, testql(10), app.doql.less, goal.yaml, .env.example, Dockerfile, docker-compose.yml, package.json, project/(5 analysis files)

## Architecture

```
SUMD (description) → DOQL/source (code) → taskfile (automation) → testql (verification)
```

### DOQL Application Declaration (`app.doql.less`)

```less markpact:doql path=app.doql.less
// LESS format — define @variables here as needed

app {
  name: koru;
  version: 0.1.395;
}

dependencies {
  runtime: "gillm>=0.1.9, pyyaml>=6.0,<7.0, rich>=14.3.4, tillm>=0.1.35";
  watch: "websockets>=12.0,<17.0";
  vision: "mss>=9.0,<11.0";
  mesh: "websockets>=12.0,<17.0";
  observe: "mss>=9.0,<11.0, websockets>=12.0,<17.0";
  desktop: "nlp2uri[envmap]>=0.4.7, env2llm[mqtt]>=0.1.10, planfile>=0.1.100, testql>=1.2.55";
  imgl: "httpx>=0.27,<1.0";
  envmap: "nlp2uri[envmap]>=0.4.7, env2llm[mqtt]>=0.1.10";
  testql: testql>=1.2.55;
  planfile: planfile>=0.1.100;
  curllm: curllm[mcp]>=1.0.0;
  browser: "nlp2uri[envmap]>=0.4.7, env2llm[mqtt]>=0.1.10, testql>=1.2.55, curllm[mcp]>=1.0.0, playwright>=1.40,<2.0";
  vdisplay: vdisplay>=0.1.35;
  dev: "gillm>=0.1.9, pytest>=8.0,<10.0, pytest-cov>=5.0,<8.0, pytest-rerunfailures>=14.0,<17.0, pytest-timeout>=2.3,<3.0, pytest-xdist>=3.0,<4.0, ruff>=0.11,<0.16, mypy>=1.11,<3.0, pyright>=1.1.390,<2.0, hypothesis>=6.112,<7.0, pre-commit>=3.8,<5.0, types-PyYAML>=6.0,<7.0, goal>=2.1.264, costs>=0.1.53, pfix>=0.1.60, tagi>=0.49.0";
  api: "fastapi>=0.115,<1.0, uvicorn[standard]>=0.30,<1.0, httpx>=0.27,<1.0, prometheus-client>=0.21,<1.0";
  agent: "instructor>=1.6,<2.0, litellm>=1.51,<2.0, openai>=1.54,<3.0, tiktoken>=0.8,<1.0";
  fullm: fullm>=0.1.22;
  tillm: tillm>=0.1.35;
  obs: "nfo>=0.2.22,<1.0, opentelemetry-exporter-otlp>=1.28,<2.0, opentelemetry-instrumentation-fastapi>=0.49b0,<1.0, opentelemetry-instrumentation-httpx>=0.49b0,<1.0, opentelemetry-sdk>=1.28,<2.0, sentry-sdk>=2.18,<3.0, structlog>=24.4,<26.0";
  queue: "apscheduler>=3.10,<4.0, arq>=0.26,<1.0, redis>=5.1,<8.0";
  quality: "import-linter>=2.0,<3.0, mutmut>=3.2,<4.0, pyupgrade>=3.17,<4.0, refurb>=2.0,<3.0";
  all: "apscheduler>=3.10,<4.0, arq>=0.26,<1.0, fastapi>=0.115,<1.0, gillm>=0.1.9, hypothesis>=6.112,<7.0, httpx>=0.27,<1.0, import-linter>=2.0,<3.0, instructor>=1.6,<2.0, litellm>=1.51,<2.0, mss>=9.0,<11.0, mutmut>=3.2,<4.0, mypy>=1.11,<3.0, mss>=9.0,<11.0, nfo>=0.2.22,<1.0, openai>=1.54,<3.0, opentelemetry-exporter-otlp>=1.28,<2.0, opentelemetry-instrumentation-fastapi>=0.49b0,<1.0, opentelemetry-instrumentation-httpx>=0.49b0,<1.0, opentelemetry-sdk>=1.28,<2.0, pre-commit>=3.8,<5.0, prometheus-client>=0.21,<1.0, pyright>=1.1.390,<2.0, pytest>=8.0,<10.0, pytest-cov>=5.0,<8.0, pytest-rerunfailures>=14.0,<17.0, pytest-timeout>=2.3,<3.0, pytest-xdist>=3.0,<4.0, pyupgrade>=3.17,<4.0, redis>=5.1,<8.0, refurb>=2.0,<3.0, ruff>=0.11,<0.16, tillm>=0.1.35, sentry-sdk>=2.18,<3.0, structlog>=24.4,<26.0, tiktoken>=0.8,<1.0, types-PyYAML>=6.0,<7.0, uvicorn[standard]>=0.30,<1.0, websockets>=12.0,<17.0, goal>=2.1.264, costs>=0.1.53, pfix>=0.1.60, tagi>=0.49.0, curllm[mcp]>=1.0.0, env2llm[mqtt]>=0.1.10, fullm>=0.1.22, nlp2uri[envmap]>=0.4.7, planfile>=0.1.100, playwright>=1.40,<2.0, testql>=1.2.55, vdisplay>=0.1.35";
}

entity[name="TextContent"] {
  type_: Literal[!;
  text: string!;
}

entity[name="ImageURLContent"] {
  url: string!;
  detail: string!;
}

entity[name="ImageContent"] {
  type_: Literal[!;
  image_url: ImageURLContent!;
}

entity[name="FunctionObj"] {
  name: string!;
  arguments: string!;
}

entity[name="FunctionTool"] {
  description: string!;
  name: string!;
  parameters: json!;
  strict: bool!;
}

entity[name="ChatCompletionTool"] {
  type_: Literal[!;
  function: FunctionTool!;
}

entity[name="MessageToolCall"] {
  id: string!;
  type_: Literal[!;
  function: FunctionObj!;
}

entity[name="SAPMessage"] {
  role: Literal[!;
  content: string!;
}

entity[name="SAPUserMessage"] {
  role: Literal[!;
  content: Union[!;
}

entity[name="SAPAssistantMessage"] {
  role: Literal[!;
  content: string!;
  refusal: string!;
  tool_calls: list[MessageToolCall]!;
}

entity[name="SAPToolChatMessage"] {
  role: Literal[!;
  tool_call_id: string!;
  content: string!;
}

entity[name="ResponseFormat"] {
  type_: Literal[!;
}

entity[name="KeyValueListPair"] {
  key: string!;
  value: list[str]!;
}

entity[name="GroundingSearchConfig"] {
  max_chunk_count: int;
  max_document_count: int;
}

entity[name="DocumentGroundingFilter"] {
  id_: string;
  data_repository_type: Literal[!;
  search_config: GroundingSearchConfig;
  data_repositories: list[str];
  data_repository_metadata: list[KeyValueListPair];
  document_metadata: list[DocumentMetadataKeyValueListPairs];
  chunk_metadata: list[KeyValueListPair];
}

entity[name="DocumentGroundingPlaceholders"] {
  input: list[str]!;
  output: string!;
}

entity[name="DocumentGroundingConfig"] {
  filters: list[DocumentGroundingFilter];
  placeholders: DocumentGroundingPlaceholders!;
  metadata_params: list[str];
}

entity[name="GroundingModuleConfig"] {
  type_: Literal[!;
  config: DocumentGroundingConfig!;
}

entity[name="Template"] {
  template: list[ChatMessage]!;
  defaults: dict[str, str];
  response_format: Union[ResponseFormat, ResponseFormatJSONSchema];
  tools: list[ChatCompletionTool];
}

entity[name="LLMModelDetails"] {
  name: string!;
  version: string!;
  params: json;
}

entity[name="PromptTemplatingModuleConfig"] {
  prompt: Template!;
  model: LLMModelDetails!;
}

entity[name="DPIMethodConstant"] {
  method: Literal[!;
  value: string!;
}

entity[name="DPIMethodFabricatedData"] {
  method: Literal[!;
}

entity[name="DPICustomEntity"] {
  regex: Regular expression to match the entity!;
  replacement_strategy: Replacement strategy to be used for the entity!;
  regex: string!;
  replacement_strategy: DPIMethodConstant!;
}

entity[name="DPIStandardEntity"] {
  type: Standard entity type to be masked!;
  replacement_strategy: Replacement strategy to be used for the entity!;
  type_: SAPMaskingProfileEntity!;
  replacement_strategy: Optional[;
}

entity[name="MaskGroundingInput"] {
  enabled: bool!;
}

entity[name="MaskingProviderConfig"] {
  method: The method of masking to apply!;
  entities: A list of entity categories to be masked, such as names, locations, or emails!;
  allowlist: A list of strings that should not be masked!;
  mask_grounding_input: A flag indicating whether to mask input to the grounding module!;
  type_: Literal[!;
  method: Literal[!;
  entities: list[Union[DPIStandardEntity, DPICustomEntity]]!;
  allowlist: list[str];
  mask_grounding_input: MaskGroundingInput;
}

entity[name="MaskingModuleConfig"] {
  providers: list of masking service provider configurations!;
  masking_providers: list of masking provider configurations!;
  IMPORTANT: use exactly one of the parameters to set the list of masking provider configurations!;
  DEPRECATED: parameter!;
  providers: list[MaskingProviderConfig];
  masking_providers: list[MaskingProviderConfig];
}

entity[name="AzureContentFilter"] {
  hate: Threshold for hate speech content!;
  sexual: Threshold for sexual content!;
  violence: Threshold for violent content!;
  self_harm: Threshold for self!;
  hate: Union[AzureThreshold, Literal[0, 2, 4, 6]];
  sexual: Union[AzureThreshold, Literal[0, 2, 4, 6]];
  violence: Union[AzureThreshold, Literal[0, 2, 4, 6]];
  self_harm: Union[AzureThreshold, Literal[0, 2, 4, 6]];
}

entity[name="LlamaGuard38bFilter"] {
  violent_crimes: Responses that enable, encourage, or endorse the commission of violent crimes!;
  non_violent_crimes: Responses that enable, encourage, or endorse the commission of non!;
  sex_crimes: Responses that enable, encourage, or endorse the commission of sex!;
  child_exploitation: Responses that contain, describe, enable or endorse the sexual abuse of children!;
  defamation: Responses that are both verifiably false and likely to injure a living person!;
  specialized_advice: Responses that contain specialized financial, medical or legal advice!;
  privacy: Responses that contain sensitive or nonpublic personal information!;
  intellectual_property: Responses that may violate the intellectual property rights of any third party!;
  indiscriminate_weapons: Responses that enable, encourage, or endorse the creation of indiscriminate weapons!;
  hate: Responses that demean or dehumanize people on the basis of their sensitive, personal characteristics!;
  self_harm: Responses that enable, encourage, or endorse acts of intentional self!;
  sexual_content: Responses that contain erotica!;
  elections: Responses that contain factually incorrect information about electoral systems and processes!;
  code_interpreter_abuse: Responses that seek to abuse code interpreters!;
  violent_crimes: bool!;
  non_violent_crimes: bool!;
  sex_crimes: bool!;
  child_exploitation: bool!;
  defamation: bool!;
  specialized_advice: bool!;
  privacy: bool!;
  intellectual_property: bool!;
  indiscriminate_weapons: bool!;
  hate: bool!;
  self_harm: bool!;
  sexual_content: bool!;
  elections: bool!;
  code_interpreter_abuse: bool!;
}

entity[name="LlamaGuard38bFilterConfig"] {
  type_: Literal[!;
  config: LlamaGuard38bFilter!;
}

entity[name="AzureContentSafetyInputFilterConfig"] {
  type_: Literal[!;
  config: AzureContentSafetyInput;
}

entity[name="AzureContentSafetyOutputFilterConfig"] {
  type_: Literal[!;
  config: AzureContentSafetyOutput;
}

entity[name="FilteringStreamOptions"] {
  overlap: Number of characters that should be additionally sent to content filtering services!;
  overlap: int;
}

entity[name="InputFiltering"] {
  filters: List of ContentFilter objects to be applied to input content!;
  filters: list[!;
}

entity[name="OutputFiltering"] {
  filters: List of ContentFilter objects to be applied to output content!;
  stream_options: Module!;
  filters: list[!;
  stream_options: FilteringStreamOptions;
}

entity[name="FilteringModuleConfig"] {
  input: Module for filtering and validating input content before processing!;
  output: Module for filtering and validating output content after generation!;
  input: InputFiltering;
  output: OutputFiltering;
}

entity[name="SAPDocumentTranslationApplyToSelector"] {
  category: Literal[!;
  items: list[str]!;
  source_language: string!;
}

entity[name="InputTranslationConfig"] {
  source_language: Language of the text to be translated!;
  target_language: Language to which the text should be translated!;
  apply_to: List of selectors that define the scope of translation!;
  source_language: string;
  target_language: string!;
  apply_to: list[SAPDocumentTranslationApplyToSelector];
}

entity[name="OutputTranslationConfig"] {
  source_language: string;
  target_language: Union[str, SAPDocumentTranslationApplyToSelector]!;
}

entity[name="SAPDocumentTranslationInput"] {
  type: The type of translation module!;
  translate_messages_history: If true, the messages history will be translated as well!;
  config: Configuration object for the translation module!;
  type_: Literal[!;
  translate_messages_history: bool;
  config: InputTranslationConfig!;
}

entity[name="SAPDocumentTranslationOutput"] {
  type: The type of translation module!;
  config: Configuration object for the translation module!;
  type_: Literal[!;
  config: OutputTranslationConfig!;
}

entity[name="TranslationModuleConfig"] {
  input: Configuration for input translation!;
  output: Configuration for output translation!;
  input: SAPDocumentTranslationInput;
  output: SAPDocumentTranslationOutput;
}

entity[name="ModuleConfig"] {
  prompt_templating: PromptTemplatingModuleConfig!;
  filtering: FilteringModuleConfig;
  masking: MaskingModuleConfig;
  grounding: GroundingModuleConfig;
  translation: TranslationModuleConfig;
}

entity[name="GlobalStreamOptions"] {
  enabled: bool!;
  chunk_size: int;
  delimiters: list[str];
}

entity[name="OrchestrationConfig"] {
  modules: Union[ModuleConfig, list[ModuleConfig]]!;
  stream: GlobalStreamOptions;
}

entity[name="DomainModel"] {
  created_at: datetime;
  updated_at: datetime;
}

entity[name="CredentialBase"] {
  credential_name: string!;
  credential_info: json!;
}

interface[type="api"] {
  type: rest;
  framework: fastapi;
}

interface[type="cli"] {
  framework: argparse;
}
interface[type="cli"] page[name="coru"] {
  entry: coru.cli:main;
}
interface[type="cli"] page[name="koru"] {
  entry: koru.cli:main;
}
interface[type="cli"] page[name="koru-wup-testql"] {
  entry: koru.wup_testql_compat:main;
}
interface[type="cli"] page[name="koru-dsl"] {
  entry: korudsl.cli:main;
}
interface[type="cli"] page[name="koru-api"] {
  entry: koruapi.cli:main;
}

interface[type="web"] {
  type: spa;
  framework: static;
}

integration[name="nlp"] {
  type: api;
}

integration[name="github"] {
  type: scm;
}

workflow[name="test"] {
  trigger: manual;
  step-1: run cmd=$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --verbose $(PYTEST_ARGS);
}

workflow[name="test-fast"] {
  trigger: manual;
  step-1: run cmd=$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --critical --quick $(PYTEST_ARGS);
}

workflow[name="test-parallel"] {
  trigger: manual;
  step-1: run cmd=$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --critical --fast --maxfail=1 $(PYTEST_ARGS);
}

workflow[name="test-parallel-fast"] {
  trigger: manual;
  step-1: run cmd=$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --changed --critical --quick $(PYTEST_ARGS);
}

workflow[name="test-python-parallel"] {
  trigger: manual;
  step-1: depend target=test-parallel;
}

workflow[name="test-api-parallel"] {
  trigger: manual;
  step-1: run cmd=$(KORU_PYTEST_ENV) scripts/koru-pytest.sh --fast --maxfail=1 \;
  step-2: run cmd=tests/test_koruapi.py \;
  step-3: run cmd=tests/test_koruapi_transports.py \;
  step-4: run cmd=tests/test_dashboard_projects_by_ide.py \;
  step-5: run cmd=tests/test_dashboard_topology_post.py \;
  step-6: run cmd=tests/test_mcp_server.py \;
  step-7: run cmd=$(PYTEST_ARGS);
}

workflow[name="install-imgl-bridge"] {
  trigger: manual;
  step-1: depend target=$(VENV)/.imgl-bridge-installed;
}

workflow[name="test-imgl"] {
  trigger: manual;
  step-1: run cmd=$(PY) -m pytest tests/test_imgl_integration.py packages/dsl2coru/tests/test_dsl2coru_ui.py -q;
}

workflow[name="imgl-capture"] {
  trigger: manual;
  step-1: run cmd=test -x "$(IMGL_ROOT)/.venv/bin/imgl" || (echo "Brak $(IMGL_ROOT)/.venv — cd $(IMGL_ROOT) && make install-dev" && exit 1);
  step-2: run cmd=$(IMGL_ROOT)/.venv/bin/imgl capture --smart -o "$(IMGL_IMAGE)";
  step-3: run cmd=echo "export KORU_IMGL_IMAGE=$(IMGL_IMAGE)";
}

workflow[name="imgl-capture-interactive"] {
  trigger: manual;
  step-1: run cmd=test -x "$(IMGL_ROOT)/.venv/bin/imgl" || (echo "Brak $(IMGL_ROOT)/.venv — cd $(IMGL_ROOT) && make install-dev" && exit 1);
  step-2: run cmd=rm -f "$(IMGL_IMAGE:.png=.vql.imgl.json)" "$(IMGL_IMAGE:.png=.vql.json)" "$(IMGL_IMAGE:.png=.captured_at)" "$(IMGL_IMAGE)";
  step-3: run cmd=$(IMGL_ROOT)/.venv/bin/imgl capture -o "$(IMGL_IMAGE)" --verify;
  step-4: run cmd=rm -f "$(IMGL_IMAGE:.png=.vql.imgl.json)" "$(IMGL_IMAGE:.png=.vql.json)";
  step-5: run cmd=echo "export KORU_IMGL_IMAGE=$(IMGL_IMAGE)";
}

workflow[name="imgl-key"] {
  trigger: manual;
  step-1: run cmd=IMGL_ROOT="$(IMGL_ROOT)" KORU_IMGL_IMAGE=$(IMGL_IMAGE) $(VENV)/bin/dsl2coru exec 'UI_KEY ctrl+Return';
}

workflow[name="imgl-type"] {
  trigger: manual;
  step-1: run cmd=IMGL_ROOT="$(IMGL_ROOT)" KORU_IMGL_IMAGE=$(IMGL_IMAGE) $(VENV)/bin/dsl2coru exec 'UI_TYPE "test" IN "Chat input" WINDOW $(IMGL_WINDOW)';
}

workflow[name="imgl-chat"] {
  trigger: manual;
  step-1: run cmd=IMGL_ROOT="$(IMGL_ROOT)" KORU_IMGL_IMAGE=$(IMGL_IMAGE) $(VENV)/bin/dsl2coru exec 'UI_TYPE "demo" IN "Chat input" WINDOW $(IMGL_WINDOW)';
  step-2: run cmd=IMGL_ROOT="$(IMGL_ROOT)" KORU_IMGL_IMAGE=$(IMGL_IMAGE) $(VENV)/bin/dsl2coru exec 'UI_KEY ctrl+Return';
}

workflow[name="imgl-execute"] {
  trigger: manual;
  step-1: run cmd=test -f "$(IMGL_IMAGE)" || (echo "Brak zrzutu — najpierw: make imgl-capture-interactive" && exit 1);
  step-2: run cmd=test -n "$(PROMPT)" || (echo "Użycie: make imgl-execute PROMPT='wpisz test w Chat input'" && exit 1);
  step-3: run cmd=IMGL_ROOT="$(IMGL_ROOT)" KORU_IMGL_IMAGE=$(IMGL_IMAGE) $(VENV)/bin/koru imgl execute "$(PROMPT)" --image $(IMGL_IMAGE) --window $(IMGL_WINDOW) --execute --format $(or $(FORMAT),markdown);
}

workflow[name="imgl-execute-dry"] {
  trigger: manual;
  step-1: run cmd=test -f "$(IMGL_IMAGE)" || (echo "Brak zrzutu — najpierw: make imgl-capture-interactive" && exit 1);
  step-2: run cmd=test -n "$(PROMPT)" || (echo "Użycie: make imgl-execute-dry PROMPT='wpisz test w Chat input'" && exit 1);
  step-3: run cmd=IMGL_ROOT="$(IMGL_ROOT)" KORU_IMGL_IMAGE=$(IMGL_IMAGE) $(VENV)/bin/koru imgl execute "$(PROMPT)" --image $(IMGL_IMAGE) --window $(IMGL_WINDOW) --dry-run --format $(or $(FORMAT),markdown);
}

workflow[name="imgl-shot"] {
  trigger: manual;
  step-1: depend target=imgl-capture-interactive;
  step-2: depend target=imgl-execute;
}

workflow[name="imgl-doctor"] {
  trigger: manual;
  step-1: run cmd=IMGL_ROOT="$(IMGL_ROOT)" KORU_IMGL_IMAGE=$(IMGL_IMAGE) $(VENV)/bin/koru imgl doctor --image $(IMGL_IMAGE) --format $(or $(FORMAT),auto);
}

workflow[name="imgl-serve-rest"] {
  trigger: manual;
  step-1: run cmd=test -x "$(IMGL_ROOT)/.venv/bin/rest2imgl" || (cd "$(IMGL_ROOT)" && make install-control);
  step-2: run cmd=$(IMGL_ROOT)/.venv/bin/rest2imgl serve --port 8219;
}

workflow[name="sync-plugin-version"] {
  trigger: manual;
  step-1: run cmd=python3 scripts/sync-plugin-version.py --ide vscode;
  step-2: run cmd=python3 scripts/sync-plugin-version.py --ide cursor;
}

workflow[name="sync-plugin-shared"] {
  trigger: manual;
  step-1: run cmd=python3 scripts/sync-plugin-shared.py;
}

workflow[name="clean-dist"] {
  trigger: manual;
  step-1: run cmd=rm -f dist/koru-*;
}

workflow[name="build"] {
  trigger: manual;
  step-1: run cmd=rm -rf build/ *.egg-info src/*.egg-info;
  step-2: run cmd=$(PYTHON) -m pip install -q build;
  step-3: run cmd=$(PYTHON) -m build;
  step-4: run cmd=echo "✓ Built dist/koru-$(VERSION)*";
}

workflow[name="check-dist"] {
  trigger: manual;
  step-1: run cmd=test -n "$(VERSION)" || (echo "Could not read version from pyproject.toml" && exit 1);
  step-2: run cmd=test -n "$$(ls dist/koru-$(VERSION)* 2>/dev/null)" || (echo "No artifacts for $(VERSION) in dist/ — run make build" && exit 1);
  step-3: run cmd=$(PYTHON) -m pip install -q twine;
  step-4: run cmd=$(PYTHON) -m twine check dist/koru-$(VERSION)*;
}

workflow[name="bump-patch"] {
  trigger: manual;
  step-1: run cmd=echo "🔢 Bumping patch version...";
  step-2: run cmd=$(PYTHON) scripts/bump_version.py patch;
}

workflow[name="bump-minor"] {
  trigger: manual;
  step-1: run cmd=echo "🔢 Bumping minor version...";
  step-2: run cmd=$(PYTHON) scripts/bump_version.py minor;
}

workflow[name="bump-major"] {
  trigger: manual;
  step-1: run cmd=echo "🔢 Bumping major version...";
  step-2: run cmd=$(PYTHON) scripts/bump_version.py major;
}

workflow[name="publish-test"] {
  trigger: manual;
  step-1: run cmd=echo "🚀 Publishing to TestPyPI...";
  step-2: run cmd=bash -c '\;
  step-3: run cmd=if [ -n "$${PYPI_API_TOKEN}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \;
  step-4: run cmd=export TWINE_USERNAME=__token__ TWINE_PASSWORD="$${PYPI_API_TOKEN}"; \;
  step-5: run cmd=fi; \;
  step-6: run cmd=if [ -z "$${TWINE_USERNAME}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \;
  step-7: run cmd=echo "⚠️  No PyPI credentials. Set TWINE_USERNAME/TWINE_PASSWORD or PYPI_API_TOKEN"; \;
  step-8: run cmd=echo "   Skipping upload (dist/koru-$(VERSION)* built and twine-checked)."; \;
  step-9: run cmd=else \;
  step-10: run cmd=$(PYTHON) -m pip install -q twine && \;
  step-11: run cmd=$(PYTHON) -m twine upload --repository testpypi dist/koru-$(VERSION)* && \;
  step-12: run cmd=echo "✓ Published koru $(VERSION) to TestPyPI"; \;
  step-13: run cmd=fi';
}

workflow[name="publish"] {
  trigger: manual;
  step-1: run cmd=echo "🚀 Publishing to PyPI...";
  step-2: run cmd=bash -c '\;
  step-3: run cmd=if [ -z "$${PYPI_API_TOKEN}" ] && [ -z "$${TWINE_USERNAME}" ] && [ -z "$${TWINE_PASSWORD}" ] && [ ! -f "$${HOME}/.pypirc" ]; then \;
  step-4: run cmd=echo "⚠️  No PyPI credentials. Set PYPI_API_TOKEN or TWINE_USERNAME/TWINE_PASSWORD (no version bump performed)."; \;
  step-5: run cmd=echo "   Example: PYPI_API_TOKEN=pypi-xxx make publish"; \;
  step-6: run cmd=exit 1; \;
  step-7: run cmd=fi';
  step-8: run cmd=$(MAKE) bump-patch;
  step-9: run cmd=$(MAKE) build;
  step-10: run cmd=$(MAKE) check-dist;
  step-11: run cmd=bash -c 'set -euo pipefail; \;
  step-12: run cmd=if [ -n "$${PYPI_API_TOKEN:-}" ] && [ -z "$${TWINE_PASSWORD:-}" ]; then \;
  step-13: run cmd=export TWINE_USERNAME=__token__ TWINE_PASSWORD="$${PYPI_API_TOKEN}"; \;
  step-14: run cmd=fi; \;
  step-15: run cmd=FILES="$$(ls dist/koru-*.whl dist/koru-*.tar.gz 2>/dev/null)"; \;
  step-16: run cmd=test -n "$${FILES}" || { echo "No built artifacts in dist/ — run make build"; exit 1; }; \;
  step-17: run cmd=echo "📦 Uploading to PyPI:"; echo "$${FILES}" | sed "s/^/   /"; \;
  step-18: run cmd=$(PYTHON) -m pip install -q twine; \;
  step-19: run cmd=$(PYTHON) -m twine upload $${FILES}; \;
  step-20: run cmd=echo "✓ Published koru to PyPI"';
}

workflow[name="packages-build"] {
  trigger: manual;
  step-1: run cmd=set -euo pipefail; \;
  step-2: run cmd=if [ -z "$(PACKAGE_DIRS)" ]; then \;
  step-3: run cmd=echo "No package directories found under packages/"; \;
  step-4: run cmd=exit 1; \;
  step-5: run cmd=fi; \;
  step-6: run cmd=$(PYTHON) -m pip install -q build; \;
  step-7: run cmd=for pkg in $(PACKAGE_DIRS); do \;
  step-8: run cmd=if [ ! -f "$$pkg/pyproject.toml" ]; then \;
  step-9: run cmd=echo "- skipping $$pkg (no pyproject.toml)"; \;
  step-10: run cmd=continue; \;
  step-11: run cmd=fi; \;
  step-12: run cmd=echo "📦 building $$pkg"; \;
  step-13: run cmd=rm -rf "$$pkg/dist" "$$pkg/build" "$$pkg"/*.egg-info "$$pkg/src"/*.egg-info; \;
  step-14: run cmd=$(PYTHON) -m build "$$pkg"; \;
  step-15: run cmd=done;
}

workflow[name="packages-check"] {
  trigger: manual;
  step-1: run cmd=set -euo pipefail; \;
  step-2: run cmd=$(PYTHON) -m pip install -q twine; \;
  step-3: run cmd=for pkg in $(PACKAGE_DIRS); do \;
  step-4: run cmd=if [ ! -f "$$pkg/pyproject.toml" ]; then \;
  step-5: run cmd=continue; \;
  step-6: run cmd=fi; \;
  step-7: run cmd=if ls "$$pkg"/dist/* >/dev/null 2>&1; then \;
  step-8: run cmd=echo "🔎 twine check $$pkg/dist/*"; \;
  step-9: run cmd=$(PYTHON) -m twine check "$$pkg"/dist/*; \;
  step-10: run cmd=else \;
  step-11: run cmd=echo "No artifacts in $$pkg/dist (run: make packages-build)"; \;
  step-12: run cmd=exit 1; \;
  step-13: run cmd=fi; \;
  step-14: run cmd=done;
}

workflow[name="packages-publish-test"] {
  trigger: manual;
  step-1: run cmd=echo "🚀 Publishing packages/* to TestPyPI...";
  step-2: run cmd=bash -c '\;
  step-3: run cmd=if [ -n "$${PYPI_API_TOKEN}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \;
  step-4: run cmd=export TWINE_USERNAME=__token__ TWINE_PASSWORD="$${PYPI_API_TOKEN}"; \;
  step-5: run cmd=fi; \;
  step-6: run cmd=if [ -z "$${TWINE_USERNAME}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \;
  step-7: run cmd=echo "⚠️  No PyPI credentials. Set TWINE_USERNAME/TWINE_PASSWORD or PYPI_API_TOKEN"; \;
  step-8: run cmd=echo "   Skipping upload (artifacts are built and twine-checked)."; \;
  step-9: run cmd=exit 0; \;
  step-10: run cmd=fi; \;
  step-11: run cmd=for pkg in $(PACKAGE_DIRS); do \;
  step-12: run cmd=if [ ! -f "$$pkg/pyproject.toml" ]; then \;
  step-13: run cmd=continue; \;
  step-14: run cmd=fi; \;
  step-15: run cmd=echo "⬆️  testpypi upload $$pkg/dist/*"; \;
  step-16: run cmd=$(PYTHON) -m twine upload --repository testpypi "$$pkg"/dist/*; \;
  step-17: run cmd=done; \;
  step-18: run cmd=echo "✓ Published all packages/* to TestPyPI"';
}

workflow[name="packages-publish"] {
  trigger: manual;
  step-1: run cmd=echo "🚀 Publishing packages/* to PyPI...";
  step-2: run cmd=bash -c '\;
  step-3: run cmd=if [ -n "$${PYPI_API_TOKEN}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \;
  step-4: run cmd=export TWINE_USERNAME=__token__ TWINE_PASSWORD="$${PYPI_API_TOKEN}"; \;
  step-5: run cmd=fi; \;
  step-6: run cmd=if [ -z "$${TWINE_USERNAME}" ] && [ -z "$${TWINE_PASSWORD}" ]; then \;
  step-7: run cmd=echo "⚠️  No PyPI credentials. Set TWINE_USERNAME/TWINE_PASSWORD or PYPI_API_TOKEN"; \;
  step-8: run cmd=exit 1; \;
  step-9: run cmd=fi; \;
  step-10: run cmd=for pkg in $(PACKAGE_DIRS); do \;
  step-11: run cmd=if [ ! -f "$$pkg/pyproject.toml" ]; then \;
  step-12: run cmd=continue; \;
  step-13: run cmd=fi; \;
  step-14: run cmd=echo "⬆️  pypi upload $$pkg/dist/*"; \;
  step-15: run cmd=$(PYTHON) -m twine upload "$$pkg"/dist/*; \;
  step-16: run cmd=done; \;
  step-17: run cmd=echo "✓ Published all packages/* to PyPI"';
}

workflow[name="default"] {
  trigger: manual;
  step-1: run cmd=task --list-all;
}

workflow[name="version"] {
  trigger: manual;
  step-1: run cmd=echo "koru v{{.KORU_VERSION}}";
}

workflow[name="install"] {
  trigger: manual;
  step-1: run cmd=pip install -e .;
}

workflow[name="install:dev"] {
  trigger: manual;
  step-1: run cmd=pip install -e ".[dev]" || pip install -e .;
}

workflow[name="install:tools"] {
  trigger: manual;
  step-1: run cmd=pip install planfile wup testql regix "redup>=0.4.28" vallm prefact pfix sumd sumr code2llm redsl llx doql redeploy goal costs op3 toonic protogate rebuild mdflow metrun;
  step-2: run cmd=echo "✓ semcod toolchain installed. Optional interactive agent: pip install aider-chat";
}

workflow[name="test:all"] {
  trigger: manual;
  step-1: run cmd=scripts/koru-pytest.sh --serial --all --verbose {{.CLI_ARGS}};
}

workflow[name="test:docker"] {
  trigger: manual;
  step-1: run cmd=scripts/koru-pytest.sh --serial tests/test_docker_e2e.py -v -m "" {{.CLI_ARGS}};
}

workflow[name="test:docker:ide-matrix"] {
  trigger: manual;
  step-1: run cmd=KORU_DOCKER_SYSTEMS="{{.SYSTEMS}}" KORU_DOCKER_IDES="{{.IDES}}" bash scripts/docker-ide-matrix.sh;
}

workflow[name="test:fast"] {
  trigger: manual;
  step-1: run cmd=scripts/koru-pytest.sh --critical --fast {{.CLI_ARGS}};
}

workflow[name="test:quick"] {
  trigger: manual;
  step-1: run cmd=scripts/koru-pytest.sh --critical --quick {{.CLI_ARGS}};
}

workflow[name="test:parallel"] {
  trigger: manual;
  step-1: run cmd=scripts/koru-pytest.sh --critical --fast --maxfail=1 {{.CLI_ARGS}};
}

workflow[name="test:changed"] {
  trigger: manual;
  step-1: run cmd=scripts/koru-pytest.sh --changed --critical --quick {{.CLI_ARGS}};
}

workflow[name="test:profile"] {
  trigger: manual;
  step-1: run cmd=scripts/koru-pytest.sh --fast --profile {{.CLI_ARGS}};
}

workflow[name="lint"] {
  trigger: manual;
  step-1: run cmd=python3 -m ruff check src tests;
}

workflow[name="lint:fix"] {
  trigger: manual;
  step-1: run cmd=python3 -m ruff check src tests --fix;
}

workflow[name="loop"] {
  trigger: manual;
  step-1: run cmd=koru --workspace "{{.WORKSPACE}}" --include "{{.INCLUDE}}" --command "{{.COMMAND}}";
}

workflow[name="queue:run"] {
  trigger: manual;
  step-1: run cmd=koru --queue --project "{{.PROJECT}}" --actor "{{.ACTOR}}" {{if eq .DRY_RUN "true"}}--dry-run{{end}};
}

workflow[name="queue:watch"] {
  trigger: manual;
  step-1: run cmd=koru --watch --ws-url "{{.WS_URL}}" {{if .MAX_EVENTS}}--max-events "{{.MAX_EVENTS}}"{{end}};
}

workflow[name="queue:autoloop"] {
  trigger: manual;
  step-1: run cmd=PROJECT="{{.PROJECT}}" \
ACTOR="{{.ACTOR}}" \
QUEUE_NAME="{{.QUEUE_NAME}}" \
USE_ALL_QUEUES="{{.USE_ALL_QUEUES}}" \
MAX_ITERATIONS="{{.MAX_ITERATIONS}}" \
MAX_CYCLES="{{.MAX_CYCLES}}" \
SLEEP_SECONDS="{{.SLEEP_SECONDS}}" \
INITIAL_DELAY_SECONDS="{{.INITIAL_DELAY_SECONDS}}" \
ENABLE_SCAN="{{.ENABLE_SCAN}}" \
TICKET_SOURCES="{{.TICKET_SOURCES}}" \
ENABLE_INTERACTIVE="{{.ENABLE_INTERACTIVE}}" \
ENABLE_AUTOPILOT_DRIVE="{{.ENABLE_AUTOPILOT_DRIVE}}" \
AUTOPILOT_ACTION="{{.AUTOPILOT_ACTION}}" \
AUTOPILOT_IDE="{{.AUTOPILOT_IDE}}" \
AUTOPILOT_SUBMIT="{{.AUTOPILOT_SUBMIT}}" \
AUTOPILOT_ON_IDLE_ONLY="{{.AUTOPILOT_ON_IDLE_ONLY}}" \
AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL="{{.AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL}}" \
DRIVE_PROMPT="{{.DRIVE_PROMPT}}" \
ENABLE_IDLE_DIAGNOSTICS="{{.ENABLE_IDLE_DIAGNOSTICS}}" \
IDLE_DIAGNOSTICS_PROFILE="{{.IDLE_DIAGNOSTICS_PROFILE}}" \
STRICT_DIAGNOSTICS="{{.STRICT_DIAGNOSTICS}}" \
ENABLE_DIAGNOSTIC_TICKETS="{{.ENABLE_DIAGNOSTIC_TICKETS}}" \
DIAGNOSTIC_TICKET_QUEUE="{{.DIAGNOSTIC_TICKET_QUEUE}}" \
DIAGNOSTIC_TICKET_PRIORITY="{{.DIAGNOSTIC_TICKET_PRIORITY}}" \
DIAG_STATE_DIR="{{.DIAG_STATE_DIR}}" \
AUTOPILOT_SKIP_STATUSES="{{.AUTOPILOT_SKIP_STATUSES}}" \
BACKOFF_ON_STAGNATION="{{.BACKOFF_ON_STAGNATION}}" \
MAX_SLEEP_SECONDS="{{.MAX_SLEEP_SECONDS}}" \
SCAN_SKIP_IF_CLEAN="{{.SCAN_SKIP_IF_CLEAN}}" \
SCAN_SKIP_AFTER="{{.SCAN_SKIP_AFTER}}" \
KORU_CMD="{{.KORU_CMD}}" \
KORU_PLANFILE_CMD="{{.KORU_PLANFILE_CMD}}" \
KORU_PYTHONPATH="{{.KORU_PYTHONPATH}}" \
bash scripts/koru-autoloop.sh;
}

workflow[name="queue:autoloop:reset-diag-markers"] {
  trigger: manual;
  step-1: run cmd=MARKER_DIR="{{.MARKER_DIR}}" \
CHECK="{{.CHECK}}" \
CLOSE_TICKETS="{{.CLOSE_TICKETS}}" \
CLOSE_STATUS="{{.CLOSE_STATUS}}" \
KORU_PLANFILE_CMD="{{.KORU_PLANFILE_CMD}}" \
KORU_PYTHONPATH="{{.KORU_PYTHONPATH}}" \
bash scripts/koru-autoloop-reset-diag-markers.sh;
}

workflow[name="koru:server"] {
  trigger: manual;
  step-1: run cmd={{.PYTHON}} -m koru.cli serve --project . --host "{{.HOST}}" --port "{{.PORT}}" --auto-port --no-open;
}

workflow[name="koru:mcp:bootstrap"] {
  trigger: manual;
  step-1: run cmd={{.PYTHON}} -m koru.cli init-ide --project . --ide all;
}

workflow[name="koru:operator:plugin-probe"] {
  trigger: manual;
  step-1: run cmd={{.PYTHON}} -m koru.cli autopilot manage --ide "{{.IDE}}";
}

workflow[name="koru:operator:setup-host"] {
  trigger: manual;
  step-1: run cmd={{.PYTHON}} -m koru.cli autopilot setup-host;
}

workflow[name="koru:ide-os:calibrate"] {
  trigger: manual;
  step-1: run cmd={{.PYTHON}} -m koru.cli autopilot calibrate --ide "{{.IDE}}";
}

workflow[name="quality:regix"] {
  trigger: manual;
  step-1: run cmd=set -euo pipefail
if python3 -m koru.cli topology --project . --is-enabled gate:regix >/dev/null 2>&1; then
  regix gates
else
  rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "quality:regix skipped (gate:regix disabled in topology)"
    exit 0
  fi
  regix gates
fi;
}

workflow[name="quality:regix:local"] {
  trigger: manual;
  step-1: run cmd=regix compare HEAD --local;
}

workflow[name="quality:wup"] {
  trigger: manual;
  step-1: run cmd=set -euo pipefail
if python3 -m koru.cli topology --project . --is-enabled gate:wup >/dev/null 2>&1; then
  wup status
else
  rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "quality:wup skipped (gate:wup disabled in topology)"
    exit 0
  fi
  wup status
fi;
}

workflow[name="quality:redup"] {
  trigger: manual;
  step-1: run cmd=set -euo pipefail
if python3 -m koru.cli topology --project . --is-enabled gate:redup >/dev/null 2>&1; then
  python3 -m redup scan . --min-lines 10
else
  rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "quality:redup skipped (gate:redup disabled in topology)"
    exit 0
  fi
  python3 -m redup scan . --min-lines 10
fi;
}

workflow[name="quality:redup:changed"] {
  trigger: manual;
  step-1: run cmd=bash -lc 'set -euo pipefail; BASE_REF="${BASE_REF:-{{.BASE_REF | default "HEAD"}}}"; OUT="${OUT:-{{.OUT | default ".redup/wup-changed.json"}}}"; if python3 -m koru.cli topology --project . --is-enabled gate:redup >/dev/null 2>&1; then python3 -m koru.redup_integration changed-scan --base-ref "$BASE_REF" --output "$OUT" --min-lines 10; else rc=$?; if [ "$rc" -eq 1 ]; then echo "quality:redup:changed skipped (gate:redup disabled in topology)"; exit 0; fi; python3 -m koru.redup_integration changed-scan --base-ref "$BASE_REF" --output "$OUT" --min-lines 10; fi';
}

workflow[name="quality:redup:check"] {
  trigger: manual;
  step-1: run cmd=set -euo pipefail
if python3 -m koru.cli topology --project . --is-enabled gate:redup >/dev/null 2>&1; then
  bash scripts/redup-check.sh "{{.PATH | default "."}}"
else
  rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "quality:redup:check skipped (gate:redup disabled in topology)"
    exit 0
  fi
  bash scripts/redup-check.sh "{{.PATH | default "."}}"
fi;
}

workflow[name="quality:vallm"] {
  trigger: manual;
  step-1: run cmd=vallm validate -f "{{.FILE}}";
}

workflow[name="quality:vallm:semantic"] {
  trigger: manual;
  step-1: run cmd=vallm validate -f "{{.FILE}}" --semantic -v;
}

workflow[name="quality:sumr:status"] {
  trigger: manual;
  step-1: run cmd=set -euo pipefail
if python3 -m koru.cli topology --project . --is-enabled gate:sumr >/dev/null 2>&1; then
  scripts/sumr-refresh.sh --status
else
  rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "quality:sumr:status skipped (gate:sumr disabled in topology)"
    exit 0
  fi
  scripts/sumr-refresh.sh --status
fi;
}

workflow[name="quality:sumr:auto"] {
  trigger: manual;
  step-1: run cmd=set -euo pipefail
if python3 -m koru.cli topology --project . --is-enabled gate:sumr >/dev/null 2>&1; then
  scripts/sumr-refresh.sh
else
  rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "quality:sumr:auto skipped (gate:sumr disabled in topology)"
    exit 0
  fi
  scripts/sumr-refresh.sh
fi;
}

workflow[name="quality:sumr:refresh"] {
  trigger: manual;
  step-1: run cmd=set -euo pipefail
if python3 -m koru.cli topology --project . --is-enabled gate:sumr >/dev/null 2>&1; then
  scripts/sumr-refresh.sh --force
else
  rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "quality:sumr:refresh skipped (gate:sumr disabled in topology)"
    exit 0
  fi
  scripts/sumr-refresh.sh --force
fi;
}

workflow[name="quality:sumr:install-hook"] {
  trigger: manual;
  step-1: run cmd=bash scripts/git-hooks/install.sh {{.HOOK | default "post-merge"}};
}

workflow[name="quality:sumr:uninstall-hook"] {
  trigger: manual;
  step-1: run cmd=bash scripts/git-hooks/install.sh --uninstall;
}

workflow[name="quality:semcod:planfile"] {
  trigger: manual;
  step-1: run cmd=bash scripts/koru-semcod-gates.sh;
}

workflow[name="tickets:next"] {
  trigger: manual;
  step-1: run cmd=planfile ticket next;
}

workflow[name="tickets:list"] {
  trigger: manual;
  step-1: run cmd=planfile ticket list --status open --format yaml;
}

workflow[name="tickets:show"] {
  trigger: manual;
  step-1: run cmd=planfile ticket show "{{.TID}}";
}

workflow[name="tickets:done"] {
  trigger: manual;
  step-1: run cmd=planfile ticket update "{{.TID}}" --status done;
}

workflow[name="tickets:export"] {
  trigger: manual;
  step-1: run cmd=bash scripts/planfile-export-prompt.sh "{{.TID}}";
}

workflow[name="template:list"] {
  trigger: manual;
  step-1: run cmd=ls templates/;
}

workflow[name="template:install"] {
  trigger: manual;
  step-1: run cmd=cp templates/pyqual.yaml.template ./pyqual.yaml;
  step-2: run cmd=cp templates/redup.toml.template ./redup.toml;
  step-3: run cmd=cp templates/redsl.yaml.template ./redsl.yaml;
  step-4: run cmd=cp templates/regix.yaml.template ./regix.yaml;
  step-5: run cmd=cp templates/llx.toml.template ./llx.toml;
  step-6: run cmd=cp templates/llx.yaml.template ./llx.yaml;
  step-7: run cmd=cp templates/prefact.yaml.template ./prefact.yaml;
  step-8: run cmd=echo "✓ All templates copied. Review and edit before committing.";
}

workflow[name="template:install:single"] {
  trigger: manual;
  step-1: run cmd=cp templates/{{.TPL}}.template ./{{.TPL}} && echo "✓ {{.TPL}} copied";
}

workflow[name="template:install:compose"] {
  trigger: manual;
  step-1: run cmd=cp templates/docker-compose.quality.yml.template ./docker-compose.quality.yml;
  step-2: run cmd=echo "✓ docker-compose.quality.yml copied. Review service definitions.";
}

workflow[name="template:install:sumr"] {
  trigger: manual;
  step-1: run cmd=mkdir -p scripts scripts/git-hooks .github/workflows;
  step-2: run cmd=cp templates/sumr-refresh.sh.template scripts/sumr-refresh.sh;
  step-3: run cmd=cp templates/git-hooks/post-merge.template scripts/git-hooks/post-merge;
  step-4: run cmd=cp templates/git-hooks/post-commit.template scripts/git-hooks/post-commit;
  step-5: run cmd=cp templates/git-hooks/install.sh.template scripts/git-hooks/install.sh;
  step-6: run cmd=cp templates/sumr-weekly.yml.template .github/workflows/sumr-weekly.yml;
  step-7: run cmd=chmod +x scripts/sumr-refresh.sh scripts/git-hooks/post-merge scripts/git-hooks/post-commit scripts/git-hooks/install.sh;
  step-8: run cmd=grep -q '^\.sumr/$' .gitignore 2>/dev/null || echo '.sumr/' >> .gitignore;
  step-9: run cmd=echo "✓ SUMR stack installed. Next: task quality:sumr:install-hook (see workflows/sumr-refresh-loop.md)";
}

workflow[name="template:install:redeploy"] {
  trigger: manual;
  step-1: run cmd=mkdir -p redeploy/local redeploy/device;
  step-2: run cmd=cp templates/redeploy/local/deployment.md.template     redeploy/local/deployment.md;
  step-3: run cmd=cp templates/redeploy/device/manifest.yaml.template    redeploy/device/manifest.yaml;
  step-4: run cmd=cp templates/redeploy/device/migration.md.template     redeploy/device/migration.md;
  step-5: run cmd=cp templates/redeploy/device/diagnose.md.template      redeploy/device/diagnose.md;
  step-6: run cmd=echo "✓ redeploy templates installed at redeploy/";
  step-7: run cmd=echo "  Next: substitute placeholders (see workflows/redeploy-multi-device.md Krok 3)";
  step-8: run cmd=echo "        rename redeploy/device/ → redeploy/<your-device>/";
  step-9: run cmd=echo "        sed -i 's/<APP_NAME>/myapp/g' redeploy/local/*.md redeploy/device/*";
}

workflow[name="template:install:observability"] {
  trigger: manual;
  step-1: run cmd=mkdir -p monitoring/prometheus/rules monitoring/alertmanager monitoring/grafana/provisioning;
  step-2: run cmd=cp templates/observability/docker-compose.observability.yml.template      docker-compose.observability.yml;
  step-3: run cmd=cp templates/observability/prometheus/prometheus.yml.template             monitoring/prometheus/prometheus.yml;
  step-4: run cmd=cp templates/observability/prometheus/rules/app-alerts.yml.template       monitoring/prometheus/rules/app-alerts.yml;
  step-5: run cmd=cp templates/observability/alertmanager/alertmanager.yml.template         monitoring/alertmanager/alertmanager.yml;
  step-6: run cmd=echo "✓ Observability stack installed.";
  step-7: run cmd=echo "  Next: substitute <APP_NAME>/<APP_PORT> placeholders, then task monitor:up";
  step-8: run cmd=echo "  See: workflows/observability-bootstrap.md";
}

workflow[name="template:install:windsurf"] {
  trigger: manual;
  step-1: run cmd=mkdir -p .windsurf;
  step-2: run cmd=cp templates/.windsurf/rules.md.template               .windsurf/rules.md;
  step-3: run cmd=cp templates/.windsurf/mcp_config.example.json.template .windsurf/mcp_config.example.json;
  step-4: run cmd=echo "✓ .windsurf/ installed.";
  step-5: run cmd=echo "  Next: substitute <APP_NAME>/<REPO_PATH>, then merge mcp_config into ~/.codeium/windsurf/mcp_config.json";
}

workflow[name="template:install:ci"] {
  trigger: manual;
  step-1: run cmd=mkdir -p .github/workflows;
  step-2: run cmd=cp templates/github-workflows/version-drift.yml.template   .github/workflows/version-drift.yml;
  step-3: run cmd=cp templates/github-workflows/code-quality.yml.template    .github/workflows/code-quality.yml;
  step-4: run cmd=mkdir -p scripts;
  step-5: run cmd=cp templates/scripts/check-version-drift.sh.template       scripts/check-version-drift.sh;
  step-6: run cmd=chmod +x scripts/check-version-drift.sh;
  step-7: run cmd=echo "✓ CI templates installed.";
  step-8: run cmd=echo "  Next: ensure VERSION file at repo root + commit + push";
}

workflow[name="template:install:precommit"] {
  trigger: manual;
  step-1: run cmd=cp templates/.pre-commit-config.yaml.template .pre-commit-config.yaml;
  step-2: run cmd=echo "✓ .pre-commit-config.yaml installed.";
  step-3: run cmd=echo "  Next: substitute <APP_NAME>, then: pip install pre-commit && pre-commit install";
}

workflow[name="template:install:wup"] {
  trigger: manual;
  step-1: run cmd=cp templates/wup.yaml.template ./wup.yaml;
  step-2: run cmd=if [ -n "${PROJECT:-}" ]; then
  sed -i "s/__PROJECT__/${PROJECT}/g" ./wup.yaml
  echo "✓ wup.yaml installed (project=${PROJECT})"
else
  echo "✓ wup.yaml installed (no PROJECT set; placeholder __PROJECT__ left in file)"
fi;
  step-3: run cmd=echo "  Next: 1) review wup.yaml services/paths";
  step-4: run cmd=echo "        2) wup map-deps         (build dependency map)";
  step-5: run cmd=echo "        3) wup testql-endpoints (verify scenarios reachable)";
  step-6: run cmd=echo "        4) wup watch            (start daemon, foreground)";
  step-7: run cmd=echo "  See: workflows/on-change-gates.md for the full triad cycle";
}

workflow[name="template:install:on-change-gates"] {
  trigger: manual;
  step-1: run cmd=test -f regix.yaml || cp templates/regix.yaml.template ./regix.yaml;
  step-2: run cmd=echo "✓ on-change gate triad installed (wup.yaml + regix.yaml)";
  step-3: run cmd=echo "  testql scenarios are project-specific — re-use existing testql-testing/scenarios/ or write new TOON YAML by hand";
  step-4: run cmd=echo "  Workflow guide: see koru workflows/on-change-gates.md";
  step-5: run cmd=echo "  Slash command:  /koru-gate (invokes all three on demand)";
}

workflow[name="scripts:list"] {
  trigger: manual;
  step-1: run cmd=ls scripts/;
}

workflow[name="scripts:redup:check"] {
  trigger: manual;
  step-1: run cmd=bash scripts/redup-check.sh "{{.PATH | default \".\"}}";
}

workflow[name="scripts:redup:precommit"] {
  trigger: manual;
  step-1: run cmd=bash scripts/redup-precommit.sh;
}

workflow[name="scripts:regix:precommit"] {
  trigger: manual;
  step-1: run cmd=bash scripts/regix-precommit.sh;
}

workflow[name="scripts:redsl:precommit"] {
  trigger: manual;
  step-1: run cmd=bash scripts/redsl-gate-precommit.sh;
}

workflow[name="scripts:planfile:sync-todo"] {
  trigger: manual;
  step-1: run cmd=python3 scripts/planfile-sync-todo.py;
}

workflow[name="scripts:soak:start"] {
  trigger: manual;
  step-1: run cmd=bash scripts/koru-soak-start.sh;
}

workflow[name="scripts:soak:status"] {
  trigger: manual;
  step-1: run cmd=bash scripts/koru-soak-status.sh;
}

workflow[name="scripts:soak:monitor"] {
  trigger: manual;
  step-1: run cmd=mkdir -p .planfile/.koru
if ! pgrep -f "autonomous up.*--max-cycles 0" >/dev/null 2>&1; then
  echo "! no running soak process found; start with: task scripts:soak:start"
  exit 1
fi
pkill -f koru-soak-monitor.sh || true
nohup env PROJECT="$PWD" TICKET_ID="{{.TID | default "STARTER-009"}}" \
  POLL_SECONDS="{{.POLL_SECONDS | default "60"}}" \
  bash scripts/koru-soak-monitor.sh > .planfile/.koru/soak-monitor.log 2>&1 &
echo "✓ soak monitor started for {{.TID | default "STARTER-009"}}";
}

workflow[name="scripts:soak:report"] {
  trigger: manual;
  step-1: run cmd=test -f .planfile/.koru/soak-interim-report.md && cat .planfile/.koru/soak-interim-report.md || true
test -f .planfile/.koru/soak-final-report.md && cat .planfile/.koru/soak-final-report.md || true
test -f .planfile/.koru/soak-stop-report.md && cat .planfile/.koru/soak-stop-report.md || true;
}

workflow[name="scripts:soak:stop"] {
  trigger: manual;
  step-1: run cmd=bash scripts/koru-soak-stop.sh;
}

workflow[name="deploy:plan"] {
  trigger: manual;
  step-1: run cmd=redeploy run "redeploy/{{.DEVICE | default \"local\"}}/{{.SPEC | default \"deployment.md\"}}" --plan-only;
}

workflow[name="deploy:dry"] {
  trigger: manual;
  step-1: run cmd=redeploy run "redeploy/{{.DEVICE | default \"local\"}}/{{.SPEC | default \"deployment.md\"}}" --dry-run;
}

workflow[name="deploy:local"] {
  trigger: manual;
  step-1: run cmd=redeploy run redeploy/local/deployment.md;
}

workflow[name="deploy:device"] {
  trigger: manual;
  step-1: run cmd=redeploy run "redeploy/{{.DEVICE}}/migration.md";
}

workflow[name="deploy:diagnose"] {
  trigger: manual;
  step-1: run cmd=redeploy run "redeploy/{{.DEVICE | default \"local\"}}/diagnose.md";
}

workflow[name="deploy:resume"] {
  trigger: manual;
  step-1: run cmd=redeploy run "redeploy/{{.DEVICE}}/migration.md" --from-step {{.STEP}};
}

workflow[name="deploy:drift"] {
  trigger: manual;
  step-1: run cmd=doql adopt --from-device "{{.DEVICE_HOST}}" -o app.doql.less;
  step-2: run cmd=echo "✓ Intended state captured. Commit app.doql.less to lock baseline.";
}

workflow[name="monitor:net"] {
  trigger: manual;
  step-1: run cmd=NET="${MONITOR_NET:-koru-quality-net}"
docker network inspect "$NET" >/dev/null 2>&1 || docker network create "$NET"
echo "✓ network $NET ready";
}

workflow[name="monitor:up"] {
  trigger: manual;
  step-1: run cmd=docker compose -f docker-compose.observability.yml up -d --build;
  step-2: run cmd=echo "";
  step-3: run cmd=echo "Grafana       → http://localhost:$${GRAFANA_PORT:-3000} (anonymous viewer)";
  step-4: run cmd=echo "Prometheus    → http://localhost:$${PROMETHEUS_PORT:-9090}";
  step-5: run cmd=echo "Alertmanager  → http://localhost:$${ALERTMANAGER_PORT:-9093}";
  step-6: run cmd=echo "Loki          → http://localhost:$${LOKI_PORT:-3100}";
  step-7: run cmd=echo "Uptime Kuma   → http://localhost:$${UPTIME_KUMA_PORT:-3001}";
  step-8: run cmd=echo "Healing hook  → http://localhost:$${HEALING_WEBHOOK_PORT:-8810}/health";
}

workflow[name="monitor:up:lite"] {
  trigger: manual;
  step-1: run cmd=docker compose -f docker-compose.observability.yml up -d --build prometheus alertmanager grafana blackbox-exporter node-exporter cadvisor uptime-kuma healing-webhook;
}

workflow[name="monitor:down"] {
  trigger: manual;
  step-1: run cmd=docker compose -f docker-compose.observability.yml down;
}

workflow[name="monitor:status"] {
  trigger: manual;
  step-1: run cmd=docker compose -f docker-compose.observability.yml ps;
}

workflow[name="monitor:logs"] {
  trigger: manual;
  step-1: run cmd=docker compose -f docker-compose.observability.yml logs -f --tail=50 {{.SVC | default "healing-webhook"}};
}

workflow[name="monitor:probe"] {
  trigger: manual;
  step-1: run cmd=for url in \
  "http://localhost:$${PROMETHEUS_PORT:-9090}/-/healthy" \
  "http://localhost:$${ALERTMANAGER_PORT:-9093}/-/healthy" \
  "http://localhost:$${GRAFANA_PORT:-3000}/api/health" \
  "http://localhost:$${LOKI_PORT:-3100}/ready" \
  "http://localhost:$${HEALING_WEBHOOK_PORT:-8810}/health"; do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$url" || echo 000)
  printf '  %-3s  %s\n' "$CODE" "$url"
done;
}

workflow[name="monitor:reload-prometheus"] {
  trigger: manual;
  step-1: run cmd=curl -X POST http://localhost:$${PROMETHEUS_PORT:-9090}/-/reload && echo "✓ reloaded";
}

workflow[name="webhook:run"] {
  trigger: manual;
  step-1: run cmd=cd services/healing-webhook && python3 app.py;
}

workflow[name="webhook:docker:build"] {
  trigger: manual;
  step-1: run cmd=docker build -t koru-healing-webhook:latest services/healing-webhook/;
}

workflow[name="webhook:docker:run"] {
  trigger: manual;
  step-1: run cmd=docker run --rm -p 8810:8810 koru-healing-webhook:latest;
}

workflow[name="webhook:test"] {
  trigger: manual;
  step-1: run cmd=curl -X POST http://localhost:8810/alert -H "Content-Type: application/json" -d '{"alerts":[{"status":"firing","labels":{"alertname":"TestAlert","severity":"warning"},"annotations":{"summary":"Smoke test"}}]}';
}

workflow[name="docs"] {
  trigger: manual;
  step-1: run cmd=echo "Documentation: docs/README.md";
  step-2: run cmd=echo "Agent guide:   docs/agent-guide.md";
  step-3: run cmd=echo "Tool catalog:  docs/llm-tools/README.md";
  step-4: run cmd=echo "CLI examples:  docs/cli-examples.md";
}

workflow[name="docs:serve"] {
  trigger: manual;
  step-1: run cmd=cd docs && python3 -m http.server 8000;
}

workflow[name="workflow:list"] {
  trigger: manual;
  step-1: run cmd=ls workflows/;
}

workflow[name="workflow:show"] {
  trigger: manual;
  step-1: run cmd=cat workflows/{{.NAME}}.md;
}

tests {
  import: .planfile/.koru/**/*.testql.toon.yaml;
  import: examples/nlp2uri-testql-browser/**/*.testql.toon.yaml;
  import: testql-scenarios/**/*.testql.toon.yaml;
  import: testql-scenarios/conversations/**/*.testql.toon.yaml;
  import: testql-testing/scenarios/**/*.testql.toon.yaml;
}

env_vars {
  keys: OPENROUTER_API_KEY, LLM_MODEL, KORU_LLM_NEEDS_INPUT_HEURISTIC, PFIX_AUTO_APPLY, PFIX_AUTO_INSTALL_DEPS, PFIX_AUTO_RESTART, PFIX_MAX_RETRIES, PFIX_DRY_RUN, PFIX_ENABLED, PFIX_GIT_COMMIT, PFIX_GIT_PREFIX, PFIX_CREATE_BACKUPS, OLLAMA_API_URL, OLLAMA_LLM_MODEL, KORU_FORCE_OLLAMA, KORU_VISION_INTERVAL, KORU_VISION_INTERVAL_MIN, KORU_VISION_PROVIDER, KORU_OBS_URL, KORU_OBS_PASSWORD, KORU_OBS_SOURCE, KORU_OBS_IMAGE_WIDTH, KORU_VISION_SCALE, KORU_VISION_PREFER_PORTAL, KORU_PORTAL_PYTHON, KORU_OBSERVE_PYTHON, KORU_MESH_FRAME_STORE, KORU_AGENT_LANE, KORU_PLANFILE_CMD, KORU_VDISPLAY_CONTROL_FALLBACK, KORU_VDISPLAY_SOURCE, KORU_VDISPLAY_LLM_VISION_DECISION, VDISPLAY_VISION_CHAT_DETECT, VDISPLAY_VISION_LLM_ENABLED, VDISPLAY_VISION_LLM_MODE, KORU_NXDO_MAX_TICKETS, KORU_NXDO_COOLDOWN_SECONDS, KORU_NXDO_MODEL, WAYLAND_DISPLAY, DISPLAY, XDG_SESSION_TYPE, ENV2LLM_PROJECT_DIR, KORU_PROJECT_ROOT, ENV2LLM_DESKTOP_PROBE, KORU_SERVE_NO_REPLACE, KORU_SERVE_WORKSPACE, NLP2CMD_INTEGRATION, KORU_PORTAL_CAPTURE, NLP2URI_CAPTURE_DIR, KORU_IMGL_STALE_BLOCK, KORU_IMGL_DIAG_BLOCK, XDG_RUNTIME_DIR, KORU_STRICT_PLUGIN_ACK, KORU_STRICT_PLUGIN_VERSION, KORU_PLUGIN_VERSION_POLICY, KORU_LLM_PICKER, KORU_AUTOPILOT_DRIVE_TIMEOUT_SECONDS, PYTEST_CURRENT_TEST, CURSOR_AGENT, CURSOR_CLI, TERM_PROGRAM_VERSION, WINDSURF_CASCADE_TERMINAL, GIO_LAUNCHED_DESKTOP_FILE, TERMINAL_EMULATOR, IDEA_INITIAL_DIRECTORY, PYCHARM_HOSTED, JETBRAINS_IDE, VSCODE_PID, WINDSURF_VERSION, WINDSURF_CSRF_TOKEN, CHROME_DESKTOP, TERM_PROGRAM, KORU_AUTOPILOT_IDE, XDG_CONFIG_HOME, KORU_COMMAND_CATALOG, KORU_COMMAND_PICKER, KORU_AUTOPILOT_INSTANCE, KORU_AUTOPILOT_SOCKET, LOCALAPPDATA, TEMP, XDG_STATE_HOME, KORU_AUTOPILOT_VSIX, KORU_AUTOPILOT_REASSERT_INSTALL, KORU_AUTOPILOT_FORCE_REASSERT_INSTALL, KORU_AUTOPILOT_BUILD_LOCAL_VSIX, PATH, KORU_OPERATOR_AUTOSTART_MCP, KORU_PLUGIN_DEBUG_LOG, KORU_AUTO_SKIP_WIZARD, VDISPLAY_AGENT_URL, KORU_OBSERVABILITY_TERMINAL, KORU_OBSERVABILITY_DSL_LOG, KORU_TILLM_CLIENT, KORU_DOCTOR_PYTEST_TIMEOUT, VIRTUAL_ENV, KORU_IDE_BACKEND, KORU_TOOL_REGISTRY, CI, GITHUB_ACTIONS, KORU_LOCAL_SERVICE_HOST, KORU_FLEET_WORKSPACE, KORU_EVENTS_URL, KORU_PLANFILE_API_URL, NO_COLOR, CLICOLOR_FORCE, KORU_TILLM_PATH, XDG_CURRENT_DESKTOP, KORU_SCAN_PATHS, KORU_SCAN_SEMCOD_ARTIFACTS, KORU_INCLUDE_FIXTURES, KORU_LOCAL_MANAGER_URL, KORU_LOCAL_SERVICE_URL, KORU_LOCAL_MANAGER_ENABLED, KORU_LOCAL_SERVICE_PORT, KORU_IDE_CONSOLE_LOG_DIR, KORU_ACTIVITY_LOG, KORU_NFO_LOG_PATH, KORU_NFO_LOG, KORU_DEBUG, KORU_FORCE_COLOR, KORU_COLOR, KORU_DOCTOR_CONSOLE_LOG_LINES, USER, ANTIGRAVITY_AGENT, KORU_LLM_REFLECT, KORU_INTEGRATION_LEDGER_PATH, KORU_STDIO_FORMAT, KORU_TILLM_DRY_RUN, KORU_OS_INJECTOR_PROFILE, KORU_OS_INJECTOR_CONFIG, KORU_NLP2URI_DRY_RUN, KORU_IMGL_DRY_RUN, KORU_VDISPLAY_DRY_RUN, KORU_AUTO_INSTALL_DEPS, KORU_PLANNING_LLM, KORU_PLANNING_LLM_MODEL, KORU_PLANNING_LLM_TIMEOUT, KORU_PLANFILE_HEALTH_URL, KORU_OPERATOR_AUTOSTART_SERVER, KORU_SELF_CONTROL_AUTOREPAIR, KORU_TEST_REAL_SELF_CONTROL, KORU_INPROGRESS_STALE_MINUTES, KORU_SHELL_DRIVE_AUTODONE, TICKET_SOURCES, IDLE_DIAGNOSTICS_PROFILE, WUP_MODE, KORU_AUTOPILOT_ALLOW_KEYBOARD_FALLBACK, KORU_AUTOPILOT_GILLM_FALLBACK, KORU_AUTOPILOT_KEYBOARD_IF_NO_PLUGIN, KORU_AUTOPILOT_ALLOW_CROSS_IDE, KORU_LLM_ENDPOINT, OPENAI_API_KEY, KORU_LLM_HTTP_REFERER, KORU_LLM_X_TITLE, KORU_QUEUE_RUNNER_LOCK, KORU_TICKET_LEASE_SECONDS, KORU_SRC, IMGL_SRC, VDISPLAY_ROOT, VDISPLAY_SRC, KORU_VDISPLAY_AGENT_URL, VDISPLAY_SESSION_ID, KORU_VDISPLAY_PHOTO_VQL_CODE_EDIT, KORU_VDISPLAY_PREFER_PHOTO_VQL, KORU_VDISPLAY_CAPTURE_MATCHES_IDE, KORU_DRIVE_IDE, KORU_VDISPLAY_ABORT_ON_PROBE_FAIL, VDISPLAY_METADATA_DIR, KORU_VDISPLAY_VQL_PATH, KORU_VDISPLAY_PHOTO_PATH, KORU_VDISPLAY_AUTO_IDE_CONTROL, KORU_VDISPLAY_AUTO_OPEN_IDE, VDISPLAY_CLI, VDISPLAY_OBSERVE_PYTHON, KORU_VDISPLAY_RAISE_ALT_TAB, KORU_VDISPLAY_FOCUS_RECOVERY_ATTEMPTS, KORU_VDISPLAY_POST_FOCUS_CAPTURE_DELAY_S, KORU_VDISPLAY_RAISE_ALT_TAB_CYCLES, KORU_VDISPLAY_PHOTO_VQL_REFRESH, KORU_VDISPLAY_DEBUG_CAPTURE, KORU_VDISPLAY_IDE_CONTROL_RETRIES, KORU_VDISPLAY_IDE_CONTROL_RETRY_DELAY_S, KORU_IDE_CONTROL_PASTE_ONLY, KORU_IDE_CONTROL_FORCE_SUBMIT, KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS, VDISPLAY_ALLOW_YDOTOOL_TYPING, KORU_VDISPLAY_PHOTO_VQL_MAP_FALLBACK, KORU_VDISPLAY_ALLOW_SURFACE_ONLY_ACTUATION, KORU_VDISPLAY_SURFACE_ONLY_FALLBACK, KORU_VDISPLAY_ALLOW_MAP_SOURCE_MISMATCH, KORU_VDISPLAY_VERIFY_AFTER_PASTE, KORU_VDISPLAY_SUBMIT_DELAY_S, KORU_IMGL_REST_URL, KORU_IMGL_FALLBACK, KORU_IMGL_DESKTOP, KORU_IMGL_IMAGE, KORU_IMGL_WINDOW, KORU_IMGL_CAPTURE_INTERACTIVE, KORU_VDISPLAY_ALLOW_IDE_MISMATCH, KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH, KORU_VDISPLAY_ALLOW_SURFACE_ON_CAPTURE_ERROR, KORU_VDISPLAY_LLM_CHAT_DETECT_TIMEOUT_S, KORU_VDISPLAY_LLM_CHAT_DETECT_MIN_CONFIDENCE, KORU_VDISPLAY_VQL_MAX_AGE_S, KORU_AUTONOMY_SESSION_DIR, KORU_VDISPLAY_SIDECAR_WRITE_GRACE_S, VDISPLAY_AGENT_PORT, KORU_AUTOPILOT_RESTART_IDE_ON_PLUGIN_BUILD_MISMATCH, KORU_AUTOPILOT_ALLOW_PLUGIN_VERSION_MISMATCH, KORU_AUTOPILOT_ALLOW_PLUGIN_BUILD_MISMATCH, KORU_AUTOPILOT_DRIVE_AUTO_DIRECT, KORU_DRIVE_VERIFY, KORU_AUTOPILOT_AUTO_RELOAD_IDE, KORU_AUTOPILOT_REUSE_WINDOW_RELOAD, KORU_AUTOPILOT_COMMAND_PALETTE_RELOAD, KORU_AUTOPILOT_NEW_WINDOW_RELOAD, KORU_AUTOPILOT_DETACHED_RELOAD, KORU_AUTOPILOT_RELOAD_VERIFY_PLUGIN, KORU_OS_INJECTOR_DRY_RUN, KORU_VDISPLAY_PORTAL_INPUT, KORU_VDISPLAY_PORTAL_TOKEN, KORU_VDISPLAY_ADAPTIVE_POINTER, KORU_VDISPLAY_ABS_POINTER, KORU_VDISPLAY_ABS_RECALIBRATE, KORU_AUTOPILOT_AUTO_LLM_READY, KORU_AUTOPILOT_NO_RESPONSE_REDRIVE_LIMIT, KORU_AUTO_SHELL_CLIENT, KORU_NLP2URI_DESKTOP_FALLBACK, KORU_AUTONOMOUS_SCAN_WHILE_WAITING, KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS, KORU_AUTOPILOT_OS_INJECTOR_COOLDOWN_SECONDS, KORU_AUTOPILOT_ESCALATION_COOLDOWN_SECONDS, KORU_LLM_REFLECTION_SUMMARY_MAX_AGE_SECONDS, KORU_LLM_NEEDS_INPUT_TICKET, KORU_LLM_NEEDS_INPUT_TICKET_QUEUE, KORU_LLM_NEEDS_INPUT_TICKET_PRIORITY, KORU_AUTOPILOT_CHAT_INTAKE_TICKET, KORU_AUTOPILOT_DRIVE_MAX_RETRIES, KORU_AUTOPILOT_ALLOW_WORKSPACE_MISMATCH, KORU_TILLM_TIMEOUT_SECONDS, KORU_TILLM_MODEL, KORU_TILLM_EXECUTE_PROFILE, KORU_ERROR_STAGNATION_DIAG_THRESHOLD, KORU_AUTOPILOT_RELOAD_RETRY_WAIT_SECONDS, WUP_PLANFILE_COMMAND, KORU_WUP_COMPOSE_HEALTH_TIMEOUT, KORU_WUP_COMPOSE_PROFILES, KORU_OPERATOR_AUTOSTART_ENVMAP, KORU_QUEUE_UNBLOCK, KORU_ONBOARDING_MAX_QUESTIONS, KORU_AUTONOMOUS_REEXECED, KORU_CLI_REEXECED, KORU_CLI_SYNC_DONE, KORU_READINESS_STRICT, KORU_AUTONOMOUS_START_LOCK, KORU_SUBMIT_UNVERIFIED_ALT_ATTEMPTS, KORU_SCAN_CREATE_FAILED_COOLDOWN_SECONDS, KORU_SCAN_DUPLICATE_COOLDOWN_SECONDS, KORU_AUTO_PIPELINE, KORU_ALLOW_BLIND_KEYBOARD_FALLBACK, KORU_PLUGIN_REJECTION_LOG_INTERVAL_SECONDS, KORU_VISION_BACKEND, DBUS_SESSION_BUS_ADDRESS, KORU_VISION_BROWSER_INTERVAL, KORU_SCREENCAST_SESSION, KORU_LLM_PROVIDER, KORU_LLM_BACKEND, CODEX_HOME, OLLAMA_MODEL, OPENAI_MODEL, ANTHROPIC_MODEL;
}

deploy {
  target: docker-compose;
  compose_file: docker-compose.yml;
}

environment[name="local"] {
  runtime: docker-compose;
  env_file: .env;
  template_file: .env.example;
  python_version: >=3.12,<3.14;
  vars: KORU_AGENT_LANE, KORU_FORCE_OLLAMA, KORU_LLM_NEEDS_INPUT_HEURISTIC, KORU_MESH_FRAME_STORE, KORU_NXDO_COOLDOWN_SECONDS, KORU_NXDO_MAX_TICKETS, KORU_NXDO_MODEL, KORU_OBSERVE_PYTHON, KORU_OBS_IMAGE_WIDTH, KORU_OBS_PASSWORD, KORU_OBS_SOURCE, KORU_OBS_URL, KORU_PLANFILE_CMD, KORU_PORTAL_PYTHON, KORU_VDISPLAY_CONTROL_FALLBACK, KORU_VDISPLAY_LLM_VISION_DECISION, KORU_VDISPLAY_SOURCE, KORU_VISION_INTERVAL, KORU_VISION_INTERVAL_MIN, KORU_VISION_PREFER_PORTAL, KORU_VISION_PROVIDER, KORU_VISION_SCALE, LLM_MODEL, OLLAMA_API_URL, OLLAMA_LLM_MODEL, OPENROUTER_API_KEY, PFIX_AUTO_APPLY, PFIX_AUTO_INSTALL_DEPS, PFIX_AUTO_RESTART, PFIX_CREATE_BACKUPS, PFIX_DRY_RUN, PFIX_ENABLED, PFIX_GIT_COMMIT, PFIX_GIT_PREFIX, PFIX_MAX_RETRIES, VDISPLAY_VISION_CHAT_DETECT, VDISPLAY_VISION_LLM_ENABLED, VDISPLAY_VISION_LLM_MODE;
  runtime_llm: OPENROUTER_API_KEY;
  runtime_ollama: OLLAMA_API_URL, OLLAMA_LLM_MODEL, OLLAMA_MODEL;
  runtime_pfix: PFIX_AUTO_APPLY, PFIX_AUTO_INSTALL_DEPS, PFIX_AUTO_RESTART, PFIX_CREATE_BACKUPS, PFIX_DRY_RUN, PFIX_ENABLED, PFIX_GIT_COMMIT, PFIX_GIT_PREFIX, PFIX_MAX_RETRIES;
}
```

## Workflows

### Taskfile Tasks (`Taskfile.yml`)

```yaml markpact:taskfile path=Taskfile.yml
version: '3'

# Taskfile for koru — closed-loop refactor automation.
#
# Usage:
#   task                      # show all tasks
#   task install              # install koru in editable mode
#   task loop -- WORKSPACE=/repos COMMAND='pytest -q'
#   task tickets:next
#   task quality:regix
#   task template:install     # copy all template configs to current dir
#
# See docs/cli-examples.md for full examples.

vars:
  KORU_VERSION:
    sh: cat VERSION 2>/dev/null || echo "0.1.1"
  PYTHON:
    sh: if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi

tasks:
  default:
    desc: Show all available tasks
    cmds:
      - task --list-all
    silent: true

  version:
    desc: Show koru version
    cmds:
      - 'echo "koru v{{.KORU_VERSION}}"'
    silent: true

  # =====================================================================
  # Install / setup
  # =====================================================================

  install:
    desc: Install koru in editable mode
    cmds:
      - pip install -e .
    sources:
      - pyproject.toml
      - src/**/*.py

  install:dev:
    desc: Install koru with dev dependencies (pytest etc.)
    cmds:
      - pip install -e ".[dev]" || pip install -e .

  install:tools:
    desc: Install semcod toolchain used by koru (planfile, wup, testql, regix, redup, sumr/sumd, doql, redeploy, ...)
    cmds:
      - pip install planfile wup testql regix "redup>=0.4.28" vallm prefact pfix sumd sumr code2llm redsl llx doql redeploy goal costs op3 toonic protogate rebuild mdflow metrun
      - 'echo "✓ semcod toolchain installed. Optional interactive agent: pip install aider-chat"'

  # =====================================================================
  # Tests
  # =====================================================================

  test:
    desc: Run default koru tests in parallel when pytest-xdist is installed (slow Docker/integration tests are deselected by pytest addopts)
    cmds:
      - scripts/koru-pytest.sh --verbose {{.CLI_ARGS}}

  test:all:
    desc: Run every koru test, including slow Docker/integration tests, serially
    cmds:
      - scripts/koru-pytest.sh --serial --all --verbose {{.CLI_ARGS}}

  test:docker:
    desc: Run Docker E2E tests only (slow; deselected by default addopts)
    cmds:
      - scripts/koru-pytest.sh --serial tests/test_docker_e2e.py -v -m "" {{.CLI_ARGS}}

  test:docker:ide-matrix:
    desc: 'Run Docker OS x IDE smoke matrix. Vars: SYSTEMS, IDES (defaults cover Debian/Ubuntu/Fedora/Alpine and VS Code/VSCodium/Cursor/Windsurf/JetBrains/Zed)'
    cmds:
      - KORU_DOCKER_SYSTEMS="{{.SYSTEMS}}" KORU_DOCKER_IDES="{{.IDES}}" bash scripts/docker-ide-matrix.sh
    vars:
      SYSTEMS: '{{.SYSTEMS | default ""}}'
      IDES: '{{.IDES | default ""}}'

  test:fast:
    desc: Run critical tests quietly in parallel when pytest-xdist is installed
    cmds:
      - scripts/koru-pytest.sh --critical --fast {{.CLI_ARGS}}

  test:quick:
    desc: Fastest feedback loop (parallel, fail fast, failed tests first)
    cmds:
      - scripts/koru-pytest.sh --critical --quick {{.CLI_ARGS}}

  test:parallel:
    desc: Run critical tests in parallel with configurable workers (KORU_PYTEST_WORKERS=4)
    cmds:
      - scripts/koru-pytest.sh --critical --fast --maxfail=1 {{.CLI_ARGS}}

  test:changed:
    desc: Run changed pytest files under tests/; falls back to default tests when none changed
    cmds:
      - scripts/koru-pytest.sh --changed --critical --quick {{.CLI_ARGS}}

  test:profile:
    desc: Run default tests and show the slowest test durations
    cmds:
      - scripts/koru-pytest.sh --fast --profile {{.CLI_ARGS}}

  lint:
    desc: Run ruff on koru sources and tests
    cmds:
      - python3 -m ruff check src tests

  lint:fix:
    desc: Run ruff with autofix
    cmds:
      - python3 -m ruff check src tests --fix

  ci:
    desc: Local CI equivalent (lint + tests)
    cmds:
      - task: lint
      - task: test:fast

  # =====================================================================
  # Closed-loop automation (the core koru CLI)
  # =====================================================================

  loop:
    desc: 'Run closed-loop across workspace. Vars: WORKSPACE, INCLUDE, COMMAND'
    cmds:
      - koru --workspace "{{.WORKSPACE}}" --include "{{.INCLUDE}}" --command "{{.COMMAND}}"
    vars:
      WORKSPACE: '{{.WORKSPACE | default "."}}'
      INCLUDE: '{{.INCLUDE | default "**"}}'
      COMMAND: '{{.COMMAND | default "pytest -q"}}'
    interactive: true

  loop:test:
    desc: Run pytest in closed-loop mode
    cmds:
      - task: loop
        vars: {COMMAND: 'pytest -q'}

  loop:lint:
    desc: Run ruff in closed-loop mode
    cmds:
      - task: loop
        vars: {COMMAND: 'ruff check .'}

  queue:run:
    desc: 'Run one task from planfile queue. Vars: PROJECT, ACTOR, DRY_RUN'
    cmds:
      - koru --queue --project "{{.PROJECT}}" --actor "{{.ACTOR}}" {{if eq .DRY_RUN "true"}}--dry-run{{end}}
    vars:
      PROJECT: '{{.PROJECT | default "."}}'
      ACTOR: '{{.ACTOR | default "koru-shell"}}'
      DRY_RUN: '{{.DRY_RUN | default "false"}}'
    interactive: true

  queue:dry-run:
    desc: Preview one runnable planfile queue task without executing it
    cmds:
      - task: queue:run
        vars: {DRY_RUN: "true"}

  queue:watch:
    desc: 'Watch planfile WebSocket events. Vars: WS_URL, MAX_EVENTS'
    cmds:
      - koru --watch --ws-url "{{.WS_URL}}" {{if .MAX_EVENTS}}--max-events "{{.MAX_EVENTS}}"{{end}}
    vars:
      WS_URL: '{{.WS_URL | default "ws://localhost:8000/ws"}}'
      MAX_EVENTS: '{{.MAX_EVENTS | default ""}}'
    interactive: true

  queue:autoloop:
    desc: 'Continuous intake+execution loop (scan + queue --loop + idle diagnostics + autopilot drive). See scripts/koru-autoloop.sh header for all env vars.'
    cmds:
      - |
        PROJECT="{{.PROJECT}}" \
        ACTOR="{{.ACTOR}}" \
        QUEUE_NAME="{{.QUEUE_NAME}}" \
        USE_ALL_QUEUES="{{.USE_ALL_QUEUES}}" \
        MAX_ITERATIONS="{{.MAX_ITERATIONS}}" \
        MAX_CYCLES="{{.MAX_CYCLES}}" \
        SLEEP_SECONDS="{{.SLEEP_SECONDS}}" \
        INITIAL_DELAY_SECONDS="{{.INITIAL_DELAY_SECONDS}}" \
        ENABLE_SCAN="{{.ENABLE_SCAN}}" \
        TICKET_SOURCES="{{.TICKET_SOURCES}}" \
        ENABLE_INTERACTIVE="{{.ENABLE_INTERACTIVE}}" \
        ENABLE_AUTOPILOT_DRIVE="{{.ENABLE_AUTOPILOT_DRIVE}}" \
        AUTOPILOT_ACTION="{{.AUTOPILOT_ACTION}}" \
        AUTOPILOT_IDE="{{.AUTOPILOT_IDE}}" \
        AUTOPILOT_SUBMIT="{{.AUTOPILOT_SUBMIT}}" \
        AUTOPILOT_ON_IDLE_ONLY="{{.AUTOPILOT_ON_IDLE_ONLY}}" \
        AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL="{{.AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL}}" \
        DRIVE_PROMPT="{{.DRIVE_PROMPT}}" \
        ENABLE_IDLE_DIAGNOSTICS="{{.ENABLE_IDLE_DIAGNOSTICS}}" \
        IDLE_DIAGNOSTICS_PROFILE="{{.IDLE_DIAGNOSTICS_PROFILE}}" \
        STRICT_DIAGNOSTICS="{{.STRICT_DIAGNOSTICS}}" \
        ENABLE_DIAGNOSTIC_TICKETS="{{.ENABLE_DIAGNOSTIC_TICKETS}}" \
        DIAGNOSTIC_TICKET_QUEUE="{{.DIAGNOSTIC_TICKET_QUEUE}}" \
        DIAGNOSTIC_TICKET_PRIORITY="{{.DIAGNOSTIC_TICKET_PRIORITY}}" \
        DIAG_STATE_DIR="{{.DIAG_STATE_DIR}}" \
        AUTOPILOT_SKIP_STATUSES="{{.AUTOPILOT_SKIP_STATUSES}}" \
        BACKOFF_ON_STAGNATION="{{.BACKOFF_ON_STAGNATION}}" \
        MAX_SLEEP_SECONDS="{{.MAX_SLEEP_SECONDS}}" \
        SCAN_SKIP_IF_CLEAN="{{.SCAN_SKIP_IF_CLEAN}}" \
        SCAN_SKIP_AFTER="{{.SCAN_SKIP_AFTER}}" \
        KORU_CMD="{{.KORU_CMD}}" \
        KORU_PLANFILE_CMD="{{.KORU_PLANFILE_CMD}}" \
        KORU_PYTHONPATH="{{.KORU_PYTHONPATH}}" \
        bash scripts/koru-autoloop.sh
    vars:
      PROJECT: '{{.PROJECT | default "."}}'
      ACTOR: '{{.ACTOR | default "koru-shell"}}'
      QUEUE_NAME: '{{.QUEUE_NAME | default ""}}'
      USE_ALL_QUEUES: '{{.USE_ALL_QUEUES | default "false"}}'
      MAX_ITERATIONS: '{{.MAX_ITERATIONS | default "50"}}'
      MAX_CYCLES: '{{.MAX_CYCLES | default "0"}}'
      SLEEP_SECONDS: '{{.SLEEP_SECONDS | default "120"}}'
      INITIAL_DELAY_SECONDS: '{{.INITIAL_DELAY_SECONDS | default "0"}}'
      ENABLE_SCAN: '{{.ENABLE_SCAN | default "true"}}'
      TICKET_SOURCES: '{{.TICKET_SOURCES | default "queue"}}'
      ENABLE_INTERACTIVE: '{{.ENABLE_INTERACTIVE | default "false"}}'
      ENABLE_AUTOPILOT_DRIVE: '{{.ENABLE_AUTOPILOT_DRIVE | default "true"}}'
      AUTOPILOT_ACTION: '{{.AUTOPILOT_ACTION | default "drive"}}'
      AUTOPILOT_IDE: '{{.AUTOPILOT_IDE | default "auto"}}'
      AUTOPILOT_SUBMIT: '{{.AUTOPILOT_SUBMIT | default "true"}}'
      AUTOPILOT_ON_IDLE_ONLY: '{{.AUTOPILOT_ON_IDLE_ONLY | default "false"}}'
      AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL: '{{.AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL | default "true"}}'
      DRIVE_PROMPT: '{{.DRIVE_PROMPT | default "continue with the next ticket"}}'
      ENABLE_IDLE_DIAGNOSTICS: '{{.ENABLE_IDLE_DIAGNOSTICS | default "false"}}'
      IDLE_DIAGNOSTICS_PROFILE: '{{.IDLE_DIAGNOSTICS_PROFILE | default "quick"}}'
      STRICT_DIAGNOSTICS: '{{.STRICT_DIAGNOSTICS | default "false"}}'
      ENABLE_DIAGNOSTIC_TICKETS: '{{.ENABLE_DIAGNOSTIC_TICKETS | default "false"}}'
      DIAGNOSTIC_TICKET_QUEUE: '{{.DIAGNOSTIC_TICKET_QUEUE | default "default"}}'
      DIAGNOSTIC_TICKET_PRIORITY: '{{.DIAGNOSTIC_TICKET_PRIORITY | default "high"}}'
      DIAG_STATE_DIR: '{{.DIAG_STATE_DIR | default ".planfile/.koru/autoloop-diag"}}'
      AUTOPILOT_SKIP_STATUSES: '{{.AUTOPILOT_SKIP_STATUSES | default "waiting_input"}}'
      BACKOFF_ON_STAGNATION: '{{.BACKOFF_ON_STAGNATION | default "true"}}'
      MAX_SLEEP_SECONDS: '{{.MAX_SLEEP_SECONDS | default "900"}}'
      SCAN_SKIP_IF_CLEAN: '{{.SCAN_SKIP_IF_CLEAN | default "false"}}'
      SCAN_SKIP_AFTER: '{{.SCAN_SKIP_AFTER | default "1"}}'
      KORU_CMD: '{{.KORU_CMD | default "koru"}}'
      KORU_PLANFILE_CMD: '{{.KORU_PLANFILE_CMD | default "planfile"}}'
      KORU_PYTHONPATH: '{{.KORU_PYTHONPATH | default ""}}'
    interactive: true

  queue:autoloop:reset-diag-markers:
    desc: 'Clear autoloop diagnostic dedup markers; optionally close [AUTO-DIAG] tickets. Usage: task queue:autoloop:reset-diag-markers CLOSE_TICKETS=true CHECK=regix'
    cmds:
      - |
        MARKER_DIR="{{.MARKER_DIR}}" \
        CHECK="{{.CHECK}}" \
        CLOSE_TICKETS="{{.CLOSE_TICKETS}}" \
        CLOSE_STATUS="{{.CLOSE_STATUS}}" \
        KORU_PLANFILE_CMD="{{.KORU_PLANFILE_CMD}}" \
        KORU_PYTHONPATH="{{.KORU_PYTHONPATH}}" \
        bash scripts/koru-autoloop-reset-diag-markers.sh
    vars:
      MARKER_DIR: '{{.MARKER_DIR | default ".planfile/.koru/autoloop-diag"}}'
      CHECK: '{{.CHECK | default "all"}}'
      CLOSE_TICKETS: '{{.CLOSE_TICKETS | default "false"}}'
      CLOSE_STATUS: '{{.CLOSE_STATUS | default "done"}}'
      KORU_PLANFILE_CMD: '{{.KORU_PLANFILE_CMD | default "planfile"}}'
      KORU_PYTHONPATH: '{{.KORU_PYTHONPATH | default ""}}'

  # =====================================================================
  # Koru operator helpers
  # =====================================================================

  koru:server:
    desc: Start the local koru dashboard/API for operator checks
    cmds:
      - '{{.PYTHON}} -m koru.cli serve --project . --host "{{.HOST}}" --port "{{.PORT}}" --auto-port --no-open'
    vars:
      HOST: '{{.HOST | default "127.0.0.1"}}'
      PORT: '{{.PORT | default "8765"}}'
    interactive: true

  koru:mcp:bootstrap:
    desc: Provision koru MCP config for Cursor, VS Code, and Windsurf
    cmds:
      - '{{.PYTHON}} -m koru.cli init-ide --project . --ide all'

  koru:operator:plugin-probe:
    desc: Check autopilot daemon/plugin install, live version, and socket status
    cmds:
      - '{{.PYTHON}} -m koru.cli autopilot manage --ide "{{.IDE}}"'
    vars:
      IDE: '{{.IDE | default "auto"}}'

  koru:operator:setup-host:
    desc: Probe host injector dependencies for autopilot
    cmds:
      - '{{.PYTHON}} -m koru.cli autopilot setup-host'

  koru:ide-os:calibrate:
    desc: Calibrate OS injector chat coordinates for an IDE (IDE=vscode|vscodium|cursor|windsurf|jetbrains|zed)
    cmds:
      - '{{.PYTHON}} -m koru.cli autopilot calibrate --ide "{{.IDE}}"'
    vars:
      IDE: '{{.IDE | default "auto"}}'
    interactive: true

  # =====================================================================
  # Quality gates (LLM-free, proxies to underlying tools)
  # =====================================================================

  quality:regix:
    desc: Run regix gates locally (LLM-free regression metrics)
    cmds:
      - |
        set -euo pipefail
        if python3 -m koru.cli topology --project . --is-enabled gate:regix >/dev/null 2>&1; then
          regix gates
        else
          rc=$?
          if [ "$rc" -eq 1 ]; then
            echo "quality:regix skipped (gate:regix disabled in topology)"
            exit 0
          fi
          regix gates
        fi
    preconditions:
      - sh: which regix
        msg: "regix not installed. Run: task install:tools"

  quality:regix:local:
    desc: Compare working tree against HEAD with regix
    cmds:
      - regix compare HEAD --local
    preconditions:
      - sh: which regix
        msg: "regix not installed. Run: task install:tools"

  quality:wup:
    desc: Check WUP on-change watcher configuration
    cmds:
      - |
        set -euo pipefail
        if python3 -m koru.cli topology --project . --is-enabled gate:wup >/dev/null 2>&1; then
          wup status
        else
          rc=$?
          if [ "$rc" -eq 1 ]; then
            echo "quality:wup skipped (gate:wup disabled in topology)"
            exit 0
          fi
          wup status
        fi
    preconditions:
      - sh: which wup
        msg: "wup not installed. Run: task install:tools"
      - sh: test -f wup.yaml
        msg: "wup.yaml missing. Run: task template:install:wup"

  quality:redup:
    desc: 'Run redup duplicate detection (default: current dir)'
    cmds:
      - |
        set -euo pipefail
        if python3 -m koru.cli topology --project . --is-enabled gate:redup >/dev/null 2>&1; then
          python3 -m redup scan . --min-lines 10
        else
          rc=$?
          if [ "$rc" -eq 1 ]; then
            echo "quality:redup skipped (gate:redup disabled in topology)"
            exit 0
          fi
          python3 -m redup scan . --min-lines 10
        fi
    preconditions:
      - sh: python3 -m redup --help >/dev/null
        msg: "redup Python module not installed. Run: task install:tools"

  quality:redup:changed:
    desc: 'Run incremental redup scan over files changed since BASE_REF (default: HEAD)'
    cmds:
      - bash -lc 'set -euo pipefail; BASE_REF="${BASE_REF:-{{.BASE_REF | default "HEAD"}}}"; OUT="${OUT:-{{.OUT | default ".redup/wup-changed.json"}}}"; if python3 -m koru.cli topology --project . --is-enabled gate:redup >/dev/null 2>&1; then python3 -m koru.redup_integration changed-scan --base-ref "$BASE_REF" --output "$OUT" --min-lines 10; else rc=$?; if [ "$rc" -eq 1 ]; then echo "quality:redup:changed skipped (gate:redup disabled in topology)"; exit 0; fi; python3 -m koru.redup_integration changed-scan --base-ref "$BASE_REF" --output "$OUT" --min-lines 10; fi'
    preconditions:
      - sh: python3 -m redup --help >/dev/null
        msg: "redup Python module not installed. Run: task install:tools"

  quality:redup:check:
    desc: Run redup with budget check (uses scripts/redup-check.sh)
    cmds:
      - |
        set -euo pipefail
        if python3 -m koru.cli topology --project . --is-enabled gate:redup >/dev/null 2>&1; then
          bash scripts/redup-check.sh "{{.PATH | default "."}}"
        else
          rc=$?
          if [ "$rc" -eq 1 ]; then
            echo "quality:redup:check skipped (gate:redup disabled in topology)"
            exit 0
          fi
          bash scripts/redup-check.sh "{{.PATH | default "."}}"
        fi

  quality:vallm:
    desc: 'Validate file with vallm (FILE=path/to/file.py)'
    cmds:
      - vallm validate -f "{{.FILE}}"
    requires:
      vars: [FILE]

  quality:vallm:semantic:
    desc: 'Validate with LLM-as-judge (requires OPENROUTER_API_KEY, FILE=...)'
    cmds:
      - vallm validate -f "{{.FILE}}" --semantic -v
    requires:
      vars: [FILE]
    preconditions:
      - sh: '[ -n "$OPENROUTER_API_KEY" ]'
        msg: "OPENROUTER_API_KEY not set"

  # ── SUMR — debounced refactor snapshot (requires `task template:install:sumr`) ─

  quality:sumr:status:
    desc: Show SUMR.md staleness vs HEAD (LLM-free; exit 1 if stale)
    cmds:
      - |
        set -euo pipefail
        if python3 -m koru.cli topology --project . --is-enabled gate:sumr >/dev/null 2>&1; then
          scripts/sumr-refresh.sh --status
        else
          rc=$?
          if [ "$rc" -eq 1 ]; then
            echo "quality:sumr:status skipped (gate:sumr disabled in topology)"
            exit 0
          fi
          scripts/sumr-refresh.sh --status
        fi
    preconditions:
      - sh: test -x scripts/sumr-refresh.sh
        msg: "scripts/sumr-refresh.sh missing. Run: task template:install:sumr"

  quality:sumr:auto:
    desc: Refresh SUMR.md only if stale (debounced; safe for hooks/cron)
    cmds:
      - |
        set -euo pipefail
        if python3 -m koru.cli topology --project . --is-enabled gate:sumr >/dev/null 2>&1; then
          scripts/sumr-refresh.sh
        else
          rc=$?
          if [ "$rc" -eq 1 ]; then
            echo "quality:sumr:auto skipped (gate:sumr disabled in topology)"
            exit 0
          fi
          scripts/sumr-refresh.sh
        fi

  quality:sumr:refresh:
    desc: Force-refresh SUMR.md (bumps sumd/code2llm/redup/doql + regenerates)
    cmds:
      - |
        set -euo pipefail
        if python3 -m koru.cli topology --project . --is-enabled gate:sumr >/dev/null 2>&1; then
          scripts/sumr-refresh.sh --force
        else
          rc=$?
          if [ "$rc" -eq 1 ]; then
            echo "quality:sumr:refresh skipped (gate:sumr disabled in topology)"
            exit 0
          fi
          scripts/sumr-refresh.sh --force
        fi

  quality:sumr:install-hook:
    desc: 'Install git post-merge hook (HOOK=post-commit|both for alt)'
    cmds:
      - bash scripts/git-hooks/install.sh {{.HOOK | default "post-merge"}}

  quality:sumr:uninstall-hook:
    desc: Remove sumr-refresh git hooks (leaves foreign hooks intact)
    cmds:
      - bash scripts/git-hooks/install.sh --uninstall

  quality:semcod:planfile:
    desc: Run configured semcod/* gates and create/update deduplicated planfile tickets on failures
    cmds:
      - bash scripts/koru-semcod-gates.sh

  # =====================================================================
  # Tickets (planfile)
  # =====================================================================

  tickets:next:
    desc: Show highest-priority open ticket
    cmds:
      - planfile ticket next
    preconditions:
      - sh: which planfile
        msg: "planfile not installed. Run: pip install planfile"

  tickets:list:
    desc: List open tickets
    cmds:
      - planfile ticket list --status open --format yaml

  tickets:show:
    desc: 'Show ticket details (TID=PLF-XXX)'
    cmds:
      - planfile ticket show "{{.TID}}"
    requires:
      vars: [TID]

  tickets:done:
    desc: 'Mark ticket as done (TID=PLF-XXX)'
    cmds:
      - planfile ticket update "{{.TID}}" --status done
    requires:
      vars: [TID]

  tickets:export:
    desc: 'Export ticket as LLM-ready prompt (TID=PLF-XXX)'
    cmds:
      - bash scripts/planfile-export-prompt.sh "{{.TID}}"
    requires:
      vars: [TID]

  # =====================================================================
  # Templates (copy reference configs to current directory)
  # =====================================================================

  template:list:
    desc: List available templates
    cmds:
      - ls templates/

  template:install:
    desc: Copy all template configs to current directory
    cmds:
      - cp templates/pyqual.yaml.template ./pyqual.yaml
      - cp templates/redup.toml.template ./redup.toml
      - cp templates/redsl.yaml.template ./redsl.yaml
      - cp templates/regix.yaml.template ./regix.yaml
      - cp templates/llx.toml.template ./llx.toml
      - cp templates/llx.yaml.template ./llx.yaml
      - cp templates/prefact.yaml.template ./prefact.yaml
      - 'echo "✓ All templates copied. Review and edit before committing."'

  template:install:single:
    desc: 'Copy single template (TPL=pyqual.yaml|redup.toml|redsl.yaml|...)'
    cmds:
      - 'cp templates/{{.TPL}}.template ./{{.TPL}} && echo "✓ {{.TPL}} copied"'
    requires:
      vars: [TPL]

  template:install:compose:
    desc: Copy docker-compose.quality.yml template
    cmds:
      - cp templates/docker-compose.quality.yml.template ./docker-compose.quality.yml
      - 'echo "✓ docker-compose.quality.yml copied. Review service definitions."'

  template:install:sumr:
    desc: 'Copy SUMR-refresh stack (script + git hooks + weekly workflow)'
    cmds:
      - mkdir -p scripts scripts/git-hooks .github/workflows
      - cp templates/sumr-refresh.sh.template scripts/sumr-refresh.sh
      - cp templates/git-hooks/post-merge.template scripts/git-hooks/post-merge
      - cp templates/git-hooks/post-commit.template scripts/git-hooks/post-commit
      - cp templates/git-hooks/install.sh.template scripts/git-hooks/install.sh
      - cp templates/sumr-weekly.yml.template .github/workflows/sumr-weekly.yml
      - chmod +x scripts/sumr-refresh.sh scripts/git-hooks/post-merge scripts/git-hooks/post-commit scripts/git-hooks/install.sh
      - |
        grep -q '^\.sumr/$' .gitignore 2>/dev/null || echo '.sumr/' >> .gitignore
      - 'echo "✓ SUMR stack installed. Next: task quality:sumr:install-hook (see workflows/sumr-refresh-loop.md)"'

  template:install:redeploy:
    desc: 'Copy redeploy templates (local + device baseline) to redeploy/'
    cmds:
      - mkdir -p redeploy/local redeploy/device
      - cp templates/redeploy/local/deployment.md.template     redeploy/local/deployment.md
      - cp templates/redeploy/device/manifest.yaml.template    redeploy/device/manifest.yaml
      - cp templates/redeploy/device/migration.md.template     redeploy/device/migration.md
      - cp templates/redeploy/device/diagnose.md.template      redeploy/device/diagnose.md
      - 'echo "✓ redeploy templates installed at redeploy/"'
      - 'echo "  Next: substitute placeholders (see workflows/redeploy-multi-device.md Krok 3)"'
      - 'echo "        rename redeploy/device/ → redeploy/<your-device>/"'
      - 'echo "        sed -i ''s/<APP_NAME>/myapp/g'' redeploy/local/*.md redeploy/device/*"'

  template:install:observability:
    desc: 'Copy observability stack (Prometheus + Grafana + Loki + Alertmanager + healing-webhook)'
    cmds:
      - mkdir -p monitoring/prometheus/rules monitoring/alertmanager monitoring/grafana/provisioning
      - cp templates/observability/docker-compose.observability.yml.template      docker-compose.observability.yml
      - cp templates/observability/prometheus/prometheus.yml.template             monitoring/prometheus/prometheus.yml
      - cp templates/observability/prometheus/rules/app-alerts.yml.template       monitoring/prometheus/rules/app-alerts.yml
      - cp templates/observability/alertmanager/alertmanager.yml.template         monitoring/alertmanager/alertmanager.yml
      - 'echo "✓ Observability stack installed."'
      - 'echo "  Next: substitute <APP_NAME>/<APP_PORT> placeholders, then task monitor:up"'
      - 'echo "  See: workflows/observability-bootstrap.md"'

  template:install:windsurf:
    desc: 'Copy .windsurf/ bootstrap (rules.md + mcp_config.example.json)'
    cmds:
      - mkdir -p .windsurf
      - cp templates/.windsurf/rules.md.template               .windsurf/rules.md
      - cp templates/.windsurf/mcp_config.example.json.template .windsurf/mcp_config.example.json
      - 'echo "✓ .windsurf/ installed."'
      - 'echo "  Next: substitute <APP_NAME>/<REPO_PATH>, then merge mcp_config into ~/.codeium/windsurf/mcp_config.json"'

  template:install:ci:
    desc: 'Copy GH Actions templates (version-drift + code-quality) to .github/workflows/'
    cmds:
      - mkdir -p .github/workflows
      - cp templates/github-workflows/version-drift.yml.template   .github/workflows/version-drift.yml
      - cp templates/github-workflows/code-quality.yml.template    .github/workflows/code-quality.yml
      - mkdir -p scripts
      - cp templates/scripts/check-version-drift.sh.template       scripts/check-version-drift.sh
      - chmod +x scripts/check-version-drift.sh
      - 'echo "✓ CI templates installed."'
      - 'echo "  Next: ensure VERSION file at repo root + commit + push"'

  template:install:precommit:
    desc: 'Copy .pre-commit-config.yaml template'
    cmds:
      - cp templates/.pre-commit-config.yaml.template .pre-commit-config.yaml
      - 'echo "✓ .pre-commit-config.yaml installed."'
      - 'echo "  Next: substitute <APP_NAME>, then: pip install pre-commit && pre-commit install"'

  template:install:wup:
    desc: 'Copy wup.yaml template (on-change file watcher feeding testql gates)'
    cmds:
      - cp templates/wup.yaml.template ./wup.yaml
      - |
        if [ -n "${PROJECT:-}" ]; then
          sed -i "s/__PROJECT__/${PROJECT}/g" ./wup.yaml
          echo "✓ wup.yaml installed (project=${PROJECT})"
        else
          echo "✓ wup.yaml installed (no PROJECT set; placeholder __PROJECT__ left in file)"
        fi
      - 'echo "  Next: 1) review wup.yaml services/paths"'
      - 'echo "        2) wup map-deps         (build dependency map)"'
      - 'echo "        3) wup testql-endpoints (verify scenarios reachable)"'
      - 'echo "        4) wup watch            (start daemon, foreground)"'
      - 'echo "  See: workflows/on-change-gates.md for the full triad cycle"'

  template:install:on-change-gates:
    desc: 'Bootstrap on-change gate triad configs (wup.yaml + regix.yaml)'
    cmds:
      - task: template:install:wup
        vars: {PROJECT: '{{.PROJECT}}'}
      - test -f regix.yaml || cp templates/regix.yaml.template ./regix.yaml
      - 'echo "✓ on-change gate triad installed (wup.yaml + regix.yaml)"'
      - 'echo "  testql scenarios are project-specific — re-use existing testql-testing/scenarios/ or write new TOON YAML by hand"'
      - 'echo "  Workflow guide: see koru workflows/on-change-gates.md"'
      - 'echo "  Slash command:  /koru-gate (invokes all three on demand)"'

  # =====================================================================
  # Scripts wrappers
  # =====================================================================

  scripts:list:
    desc: List available scripts
    cmds:
      - ls scripts/

  scripts:redup:check:
    desc: 'Run redup-check.sh (PATH=. by default)'
    cmds:
      - bash scripts/redup-check.sh "{{.PATH | default \".\"}}"

  scripts:redup:precommit:
    desc: Run redup precommit hook
    cmds:
      - bash scripts/redup-precommit.sh

  scripts:regix:precommit:
    desc: Run regix precommit hook
    cmds:
      - bash scripts/regix-precommit.sh

  scripts:redsl:precommit:
    desc: Run redsl gate precommit hook
    cmds:
      - bash scripts/redsl-gate-precommit.sh

  scripts:planfile:sync-todo:
    desc: Sync planfile tickets with TODO.md
    cmds:
      - python3 scripts/planfile-sync-todo.py

  scripts:soak:start:
    desc: Start background koru autonomous soak (--max-cycles 0, logs to .planfile/.koru/soak.log)
    cmds:
      - bash scripts/koru-soak-start.sh

  scripts:soak:status:
    desc: Show current long-run autonomy soak status (PID, uptime, cycle, ticket, report)
    cmds:
      - bash scripts/koru-soak-status.sh

  scripts:soak:monitor:
    desc: Start or restart the background soak completion monitor for STARTER-009
    cmds:
      - |
        mkdir -p .planfile/.koru
        if ! pgrep -f "autonomous up.*--max-cycles 0" >/dev/null 2>&1; then
          echo "! no running soak process found; start with: task scripts:soak:start"
          exit 1
        fi
        pkill -f koru-soak-monitor.sh || true
        nohup env PROJECT="$PWD" TICKET_ID="{{.TID | default "STARTER-009"}}" \
          POLL_SECONDS="{{.POLL_SECONDS | default "60"}}" \
          bash scripts/koru-soak-monitor.sh > .planfile/.koru/soak-monitor.log 2>&1 &
        echo "✓ soak monitor started for {{.TID | default "STARTER-009"}}"

  scripts:soak:report:
    desc: Show interim/final soak reports when present
    cmds:
      - |
        test -f .planfile/.koru/soak-interim-report.md && cat .planfile/.koru/soak-interim-report.md || true
        test -f .planfile/.koru/soak-final-report.md && cat .planfile/.koru/soak-final-report.md || true
        test -f .planfile/.koru/soak-stop-report.md && cat .planfile/.koru/soak-stop-report.md || true

  scripts:soak:stop:
    desc: Stop the background soak run and monitor, write a stop report, optionally mark ticket done
    cmds:
      - |
        bash scripts/koru-soak-stop.sh
    vars:
      TID: '{{.TID | default "STARTER-009"}}'
      MARK_DONE: '{{.MARK_DONE | default "false"}}'
    env:
      TICKET_ID: '{{.TID | default "STARTER-009"}}'
      MARK_DONE: '{{.MARK_DONE | default "false"}}'

  # =====================================================================
  # Deploy (redeploy + markpact specs — local + multi-device)
  # =====================================================================
  # Templates: templates/redeploy/   |   Workflow: workflows/redeploy-multi-device.md
  # Bootstrap: task template:install:redeploy

  deploy:plan:
    desc: 'Plan deploy without changes — DEVICE=<name> SPEC=<file> (defaults: local + deployment.md)'
    cmds:
      - redeploy run "redeploy/{{.DEVICE | default \"local\"}}/{{.SPEC | default \"deployment.md\"}}" --plan-only
    preconditions:
      - sh: which redeploy
        msg: "redeploy not installed. Run: task install:tools (or pip install --user redeploy)"

  deploy:dry:
    desc: 'Dry run deploy (preview commands) — DEVICE=<name>'
    cmds:
      - redeploy run "redeploy/{{.DEVICE | default \"local\"}}/{{.SPEC | default \"deployment.md\"}}" --dry-run

  deploy:local:
    desc: Deploy locally via Docker Compose
    cmds:
      - redeploy run redeploy/local/deployment.md
    preconditions:
      - sh: test -f redeploy/local/deployment.md
        msg: "redeploy/local/deployment.md missing. Run: task template:install:redeploy"

  deploy:device:
    desc: 'Deploy to remote device — DEVICE=<name> (e.g. pi109, edge01)'
    cmds:
      - redeploy run "redeploy/{{.DEVICE}}/migration.md"
    requires:
      vars: [DEVICE]
    preconditions:
      - sh: test -f "redeploy/{{.DEVICE}}/migration.md"
        msg: "redeploy/{{.DEVICE}}/migration.md missing. Copy from templates/redeploy/device/ and customize."

  deploy:diagnose:
    desc: 'Read-only diagnose — DEVICE=<name> (default: local)'
    cmds:
      - redeploy run "redeploy/{{.DEVICE | default \"local\"}}/diagnose.md"

  deploy:resume:
    desc: 'Resume failed deploy — DEVICE=<name> STEP=<step_id>'
    cmds:
      - redeploy run "redeploy/{{.DEVICE}}/migration.md" --from-step {{.STEP}}
    requires:
      vars: [DEVICE, STEP]

  deploy:drift:
    desc: 'Snapshot device state into app.doql.less (drift baseline) — DEVICE_HOST=<user@host>'
    cmds:
      - doql adopt --from-device "{{.DEVICE_HOST}}" -o app.doql.less
      - 'echo "✓ Intended state captured. Commit app.doql.less to lock baseline."'
    requires:
      vars: [DEVICE_HOST]
    preconditions:
      - sh: which doql
        msg: "doql not installed. Run: pip install --user doql"

  # =====================================================================
  # Observability stack (Prometheus + Grafana + Loki + Alertmanager + healing-webhook)
  # =====================================================================
  # Templates: templates/observability/  |  Workflow: workflows/observability-bootstrap.md
  # Bootstrap: task template:install:observability

  monitor:net:
    desc: Ensure the shared quality-net docker network exists
    cmds:
      - |
        NET="${MONITOR_NET:-koru-quality-net}"
        docker network inspect "$NET" >/dev/null 2>&1 || docker network create "$NET"
        echo "✓ network $NET ready"

  monitor:up:
    desc: Bring up the full observability + self-healing stack (10 services)
    deps: [monitor:net]
    cmds:
      - docker compose -f docker-compose.observability.yml up -d --build
      - echo ""
      - 'echo "Grafana       → http://localhost:$${GRAFANA_PORT:-3000} (anonymous viewer)"'
      - 'echo "Prometheus    → http://localhost:$${PROMETHEUS_PORT:-9090}"'
      - 'echo "Alertmanager  → http://localhost:$${ALERTMANAGER_PORT:-9093}"'
      - 'echo "Loki          → http://localhost:$${LOKI_PORT:-3100}"'
      - 'echo "Uptime Kuma   → http://localhost:$${UPTIME_KUMA_PORT:-3001}"'
      - 'echo "Healing hook  → http://localhost:$${HEALING_WEBHOOK_PORT:-8810}/health"'
    preconditions:
      - sh: test -f docker-compose.observability.yml
        msg: "docker-compose.observability.yml missing. Run: task template:install:observability"

  monitor:up:lite:
    desc: Bring up observability without Loki/Promtail (skip if disk is tight)
    deps: [monitor:net]
    cmds:
      - docker compose -f docker-compose.observability.yml up -d --build
          prometheus alertmanager grafana blackbox-exporter
          node-exporter cadvisor uptime-kuma healing-webhook

  monitor:down:
    desc: Stop the observability stack
    cmds:
      - docker compose -f docker-compose.observability.yml down

  monitor:status:
    desc: Show status of observability containers
    cmds:
      - docker compose -f docker-compose.observability.yml ps

  monitor:logs:
    desc: 'Tail logs of one observability service — SVC=<name> (default: healing-webhook)'
    cmds:
      - docker compose -f docker-compose.observability.yml logs -f --tail=50 {{.SVC | default "healing-webhook"}}

  monitor:probe:
    desc: 'Sanity check — curl health endpoints of all observability services'
    cmds:
      - |
        for url in \
          "http://localhost:$${PROMETHEUS_PORT:-9090}/-/healthy" \
          "http://localhost:$${ALERTMANAGER_PORT:-9093}/-/healthy" \
          "http://localhost:$${GRAFANA_PORT:-3000}/api/health" \
          "http://localhost:$${LOKI_PORT:-3100}/ready" \
          "http://localhost:$${HEALING_WEBHOOK_PORT:-8810}/health"; do
          CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$url" || echo 000)
          printf '  %-3s  %s\n' "$CODE" "$url"
        done

  monitor:reload-prometheus:
    desc: Hot-reload Prometheus rules (no restart)
    cmds:
      - 'curl -X POST http://localhost:$${PROMETHEUS_PORT:-9090}/-/reload && echo "✓ reloaded"'

  # =====================================================================
  # Healing-webhook (generic alert → ticket service)
  # =====================================================================

  webhook:run:
    desc: 'Run healing-webhook locally on port 8810'
    cmds:
      - cd services/healing-webhook && python3 app.py
    interactive: true

  webhook:docker:build:
    desc: Build healing-webhook Docker image
    cmds:
      - docker build -t koru-healing-webhook:latest services/healing-webhook/

  webhook:docker:run:
    desc: Run healing-webhook in Docker (port 8810)
    cmds:
      - docker run --rm -p 8810:8810 koru-healing-webhook:latest

  webhook:test:
    desc: Send test alertmanager payload to local webhook
    cmds:
      - 'curl -X POST http://localhost:8810/alert -H "Content-Type: application/json" -d ''{"alerts":[{"status":"firing","labels":{"alertname":"TestAlert","severity":"warning"},"annotations":{"summary":"Smoke test"}}]}'''

  # =====================================================================
  # Documentation
  # =====================================================================

  docs:
    desc: Open documentation index
    cmds:
      - 'echo "Documentation: docs/README.md"'
      - 'echo "Agent guide:   docs/agent-guide.md"'
      - 'echo "Tool catalog:  docs/llm-tools/README.md"'
      - 'echo "CLI examples:  docs/cli-examples.md"'
    silent: true

  docs:serve:
    desc: 'Serve docs over HTTP (port 8000)'
    cmds:
      - cd docs && python3 -m http.server 8000

  # =====================================================================
  # Workflows (slash-commands ported from .windsurf/workflows/)
  # =====================================================================

  workflow:list:
    desc: List available workflows (markdown instructions for agents)
    cmds:
      - ls workflows/

  workflow:show:
    desc: 'Show workflow content (NAME=testql-autoloop|aider-docker-autoloop|...)'
    cmds:
      - 'cat workflows/{{.NAME}}.md'
    requires:
      vars: [NAME]
```

## Dependencies

### Runtime

```text markpact:deps python
gillm>=0.1.9
pyyaml>=6.0,<7.0
rich>=14.3.4
tillm>=0.1.35
```

### Development

```text markpact:deps python scope=dev
gillm>=0.1.9
pytest>=8.0,<10.0
pytest-cov>=5.0,<8.0
pytest-rerunfailures>=14.0,<17.0
pytest-timeout>=2.3,<3.0
pytest-xdist>=3.0,<4.0
ruff>=0.11,<0.16
mypy>=1.11,<3.0
pyright>=1.1.390,<2.0
hypothesis>=6.112,<7.0
pre-commit>=3.8,<5.0
types-PyYAML>=6.0,<7.0
goal>=2.1.264
costs>=0.1.53
pfix>=0.1.60
tagi>=0.49.0
```

## Call Graph

*374 nodes · 500 edges · 69 modules · CC̄=3.7*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `print` *(in project)* | 0 | 1042 | 0 | **1042** |
| `list` *(in src.koru.wizard.gui.static.wizard)* | 5 | 221 | 9 | **230** |
| `dispatch` *(in packages.dsl2koru.src.dsl2koru.bus)* | 11 ⚠ | 27 | 25 | **52** |
| `_flag` *(in packages.dsl2coru.src.dsl2coru.parser)* | 7 | 33 | 8 | **41** |
| `_maybe_reexec_into_project_python` *(in packages.coru.src.coru.cli)* | 16 ⚠ | 1 | 33 | **34** |
| `append_command` *(in packages.dsl2koru.src.dsl2koru.events.EventStore)* | 3 | 0 | 33 | **33** |
| `load_registry` *(in packages.coru.src.coru.supervisor.registry)* | 5 | 21 | 11 | **32** |
| `_run_lane_repair` *(in packages.coru.src.coru.cli)* | 7 | 7 | 24 | **31** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/koru
# generated in 0.89s
# nodes: 374 | edges: 500 | modules: 69
# CC̄=3.7

HUBS[20]:
  project.print
    CC=0  in:1042  out:0  total:1042
  src.koru.wizard.gui.static.wizard.list
    CC=5  in:221  out:9  total:230
  packages.dsl2koru.src.dsl2koru.bus.dispatch
    CC=11  in:27  out:25  total:52
  packages.dsl2coru.src.dsl2coru.parser._flag
    CC=7  in:33  out:8  total:41
  packages.coru.src.coru.cli._maybe_reexec_into_project_python
    CC=16  in:1  out:33  total:34
  packages.dsl2koru.src.dsl2koru.events.EventStore.append_command
    CC=3  in:0  out:33  total:33
  packages.coru.src.coru.supervisor.registry.load_registry
    CC=5  in:21  out:11  total:32
  packages.coru.src.coru.cli._run_lane_repair
    CC=7  in:7  out:24  total:31
  src.koruide.ide.detect_running_ides
    CC=4  in:25  out:4  total:29
  packages.nlp2coru.src.nlp2coru.cli._emit
    CC=4  in:24  out:4  total:28
  packages.coru.src.coru.cli_checks._trace
    CC=3  in:23  out:5  total:28
  packages.uri2coru.src.uri2coru.nlp2uri.nlp2uri
    CC=14  in:4  out:23  total:27
  packages.coru.src.coru.cli._repo_root
    CC=4  in:23  out:4  total:27
  packages.dsl2coru.src.dsl2coru.events.EventStore._append_jsonl
    CC=3  in:0  out:26  total:26
  packages.dsl2coru.src.dsl2coru.events.EventStore._append_pb
    CC=3  in:0  out:26  total:26
  packages.dsl2koru.src.dsl2koru.cli._main_subcommand
    CC=1  in:1  out:24  total:25
  packages.coru.src.coru.cli_calibration._materialize_calibration_desktop_oql
    CC=7  in:2  out:22  total:24
  packages.uri2koru.src.uri2koru.nlp2uri.nlp2uri
    CC=13  in:1  out:23  total:24
  packages.dsl2koru.src.dsl2koru.codegen.render_models_module
    CC=12  in:1  out:22  total:23
  packages.uri2coru.src.uri2coru.decode.uri_to_dsl
    CC=7  in:4  out:18  total:22

MODULES:
  packages.cli2coru.src.cli2coru.cli  [4 funcs]
    _handle_exec  CC=2  out:2
    _handle_run  CC=3  out:4
    _handle_shell  CC=1  out:1
    _print_result  CC=4  out:6
  packages.cli2coru.src.cli2coru.shell  [1 funcs]
    run_shell  CC=9  out:12
  packages.cli2koru.src.cli2koru.cli  [4 funcs]
    _handle_exec  CC=2  out:2
    _handle_run  CC=3  out:4
    _handle_shell  CC=1  out:1
    _print_result  CC=4  out:6
  packages.cli2koru.src.cli2koru.shell  [1 funcs]
    run_shell  CC=9  out:12
  packages.coru.src.coru.cli  [91 funcs]
    _active_project_root  CC=3  out:2
    _agent_lane_from_auto_args  CC=7  out:7
    _alive_daemon_ide  CC=8  out:6
    _alive_daemon_instance  CC=13  out:16
    _auto_default_instance  CC=4  out:3
    _autonomous_startup_chain  CC=2  out:8
    _binary_path  CC=6  out:8
    _chain_project_from_plans  CC=3  out:1
    _choose_option  CC=9  out:11
    _cmd_exists  CC=1  out:1
  packages.coru.src.coru.cli_calibration  [25 funcs]
    _append_desktop_focus_lines  CC=2  out:2
    _calibration_desktop_focus_titles  CC=4  out:7
    _calibration_desktop_template_path  CC=3  out:1
    _calibration_preflight_reports  CC=3  out:4
    _calibration_probe_drive  CC=6  out:8
    _calibration_socket_fix  CC=4  out:5
    _desktop_capture_enabled  CC=1  out:3
    _format_calibration_bridge_report  CC=7  out:13
    _format_calibration_desktop_report  CC=6  out:14
    _format_calibration_probe_report  CC=9  out:11
  packages.coru.src.coru.cli_checks  [2 funcs]
    _coru_normalize_project  CC=7  out:6
    _trace  CC=3  out:5
  packages.coru.src.coru.cli_parser  [1 funcs]
    _add_lane_identifiers  CC=1  out:2
  packages.coru.src.coru.ecosystem  [5 funcs]
    _default_runner  CC=1  out:2
    _detect_running_plugin_ides  CC=4  out:2
    _local_package_paths  CC=5  out:7
    sync_ecosystem  CC=14  out:13
    sync_python_packages  CC=6  out:5
  packages.coru.src.coru.repair.runtime  [1 funcs]
    run_lane_repair  CC=1  out:1
  packages.coru.src.coru.supervisor.paths  [1 funcs]
    registry_path  CC=1  out:1
  packages.coru.src.coru.supervisor.registry  [2 funcs]
    active_lane_pair  CC=2  out:2
    load_registry  CC=5  out:11
  packages.dsl2coru.src.dsl2coru.bus  [7 funcs]
    _dispatch_koru  CC=6  out:7
    _normalize_command  CC=5  out:10
    _route_payload  CC=5  out:8
    dispatch  CC=9  out:10
    dispatch_text  CC=2  out:2
    execute_dsl  CC=5  out:6
    execute_dsl_line  CC=1  out:1
  packages.dsl2coru.src.dsl2coru.cli  [13 funcs]
    _build_subcommand_parser  CC=3  out:4
    _cmd_decode  CC=2  out:6
    _cmd_encode  CC=4  out:6
    _cmd_exec  CC=2  out:2
    _cmd_replay  CC=6  out:8
    _cmd_roundtrip  CC=2  out:2
    _cmd_run  CC=4  out:7
    _cmd_validate_schema  CC=3  out:3
    _handle_subcommand  CC=2  out:2
    _main_legacy  CC=5  out:17
  packages.dsl2coru.src.dsl2coru.codec  [7 funcs]
    envelope_from_bytes  CC=1  out:2
    envelope_from_json  CC=2  out:5
    envelope_to_bytes  CC=1  out:2
    envelope_to_json  CC=1  out:3
    parse_text  CC=2  out:2
    roundtrip_text  CC=2  out:4
    validate_payload  CC=2  out:6
  packages.dsl2coru.src.dsl2coru.codegen  [5 funcs]
    _python_type  CC=9  out:4
    build_model_registry  CC=3  out:10
    main  CC=9  out:19
    render_models_module  CC=7  out:19
    validate_payload  CC=2  out:7
  packages.dsl2coru.src.dsl2coru.events  [2 funcs]
    _append_jsonl  CC=3  out:26
    _append_pb  CC=3  out:26
  packages.dsl2coru.src.dsl2coru.handlers.argv  [1 funcs]
    to_cli_args  CC=4  out:7
  packages.dsl2coru.src.dsl2coru.handlers.command  [1 funcs]
    run_command  CC=6  out:9
  packages.dsl2coru.src.dsl2coru.handlers.query  [1 funcs]
    run_query  CC=6  out:9
  packages.dsl2coru.src.dsl2coru.handlers.runner  [2 funcs]
    _run_subprocess  CC=4  out:1
    default_runner  CC=5  out:6
  packages.dsl2coru.src.dsl2coru.handlers.ui  [4 funcs]
    _build_ui_result  CC=2  out:7
    _ensure_imgl_available  CC=3  out:2
    _ui_prompt_for_verb  CC=12  out:11
    run_ui_command  CC=3  out:13
  packages.dsl2coru.src.dsl2coru.parser  [20 funcs]
    _flag  CC=7  out:8
    _parse_auto  CC=6  out:4
    _parse_calibration  CC=6  out:4
    _parse_chat  CC=5  out:4
    _parse_doctor  CC=5  out:4
    _parse_ensure  CC=2  out:1
    _parse_env  CC=3  out:1
    _parse_lane  CC=4  out:3
    _parse_repair_run  CC=4  out:3
    _parse_status  CC=2  out:1
  packages.dsl2coru.src.dsl2coru.pb_codec  [10 funcs]
    _extract_auto  CC=4  out:1
    _set_body  CC=3  out:7
    decode_protobuf  CC=1  out:3
    decode_protobuf_to_text  CC=1  out:2
    dict_to_envelope  CC=1  out:5
    encode_protobuf  CC=1  out:2
    encode_result_protobuf  CC=1  out:2
    encode_text_to_protobuf  CC=3  out:3
    envelope_to_dict  CC=4  out:6
    result_to_pb  CC=3  out:3
  packages.dsl2coru.src.dsl2coru.schema_registry  [5 funcs]
    _load_schemas  CC=4  out:11
    all_verbs  CC=1  out:3
    normalize_verb  CC=1  out:6
    schema_for_verb  CC=2  out:4
    validate_schemas  CC=3  out:6
  packages.dsl2coru.src.dsl2coru.serializer  [9 funcs]
    _append_flag  CC=5  out:6
    _serialize_auto  CC=2  out:5
    _serialize_calibration  CC=3  out:4
    _serialize_chat  CC=3  out:5
    _serialize_doctor  CC=3  out:5
    _serialize_lane  CC=1  out:3
    _serialize_repair_run  CC=2  out:4
    _serialize_text  CC=4  out:8
    to_text  CC=4  out:12
  packages.dsl2koru.src.dsl2koru.bus  [3 funcs]
    dispatch  CC=11  out:25
    execute_dsl  CC=4  out:6
    execute_dsl_line  CC=1  out:1
  packages.dsl2koru.src.dsl2koru.cli  [10 funcs]
    _cmd_decode  CC=2  out:6
    _cmd_encode  CC=3  out:6
    _cmd_replay  CC=4  out:8
    _cmd_roundtrip  CC=1  out:2
    _cmd_run  CC=3  out:7
    _cmd_validate_schema  CC=3  out:3
    _main_legacy  CC=4  out:17
    _main_subcommand  CC=1  out:24
    _run_results  CC=6  out:6
    main  CC=4  out:2
  packages.dsl2koru.src.dsl2koru.codec  [7 funcs]
    envelope_from_bytes  CC=1  out:2
    envelope_from_json  CC=2  out:5
    envelope_to_bytes  CC=1  out:2
    envelope_to_json  CC=1  out:3
    parse_text  CC=2  out:2
    roundtrip_text  CC=1  out:4
    validate_payload  CC=2  out:6
  packages.dsl2koru.src.dsl2koru.codegen  [5 funcs]
    _python_type  CC=11  out:5
    build_model_registry  CC=3  out:10
    main  CC=6  out:18
    render_models_module  CC=12  out:22
    validate_payload  CC=2  out:7
  packages.dsl2koru.src.dsl2koru.events  [1 funcs]
    append_command  CC=3  out:33
  packages.dsl2koru.src.dsl2koru.grammar  [8 funcs]
    _flag  CC=3  out:3
    _parse_query_lane_status  CC=4  out:2
    _parse_query_repair_history  CC=5  out:4
    _parse_repair_run  CC=7  out:4
    _parse_resolve  CC=5  out:5
    _parse_validate_lane  CC=4  out:2
    parse_line  CC=5  out:7
    to_text  CC=2  out:6
  packages.dsl2koru.src.dsl2koru.handlers  [7 funcs]
    _query_lane_status  CC=1  out:11
    _query_repair_history  CC=2  out:14
    _repair_run  CC=6  out:9
    _resolve  CC=3  out:8
    _validate_lane  CC=1  out:7
    run_command  CC=2  out:4
    run_query  CC=5  out:7
  packages.dsl2koru.src.dsl2koru.pb_codec  [8 funcs]
    _set_body  CC=3  out:7
    decode_protobuf  CC=1  out:3
    decode_protobuf_to_text  CC=1  out:2
    encode_protobuf  CC=1  out:6
    encode_result_protobuf  CC=1  out:2
    encode_text_to_protobuf  CC=3  out:3
    envelope_to_dict  CC=4  out:6
    result_to_pb  CC=3  out:3
  packages.dsl2koru.src.dsl2koru.schema_registry  [4 funcs]
    _load_schemas  CC=4  out:11
    all_verbs  CC=1  out:3
    schema_for_verb  CC=2  out:4
    validate_schemas  CC=3  out:6
  packages.koruenv.src.koruenv.cli  [6 funcs]
    _emit_log  CC=5  out:7
    _iso_ts  CC=1  out:4
    _normalize_log_format  CC=3  out:2
    _run_with_overlay  CC=4  out:11
    _strip_double_dash  CC=3  out:1
    main  CC=5  out:18
  packages.koruenv.src.koruenv.lane  [6 funcs]
    _fallback_temp_dir  CC=5  out:5
    build_lane_environ  CC=2  out:5
    resolve_lane_socket  CC=1  out:1
    resolve_lane_socket_for_os  CC=5  out:10
    validate_ide  CC=3  out:6
    validate_instance  CC=3  out:4
  packages.mcp2coru.src.mcp2coru.cli  [1 funcs]
    main  CC=4  out:9
  packages.mcp2coru.src.mcp2coru.server  [4 funcs]
    __post_init__  CC=1  out:3
    _require_fastmcp  CC=2  out:1
    create_server  CC=1  out:1
    run_server  CC=1  out:2
  packages.mcp2coru.src.mcp2coru.tools  [4 funcs]
    coru_run_command  CC=1  out:2
    coru_run_command_pb  CC=1  out:2
    coru_run_dsl  CC=2  out:2
    coru_to_dsl  CC=1  out:1
  packages.mcp2koru.src.mcp2koru.cli  [1 funcs]
    main  CC=4  out:9
  packages.mcp2koru.src.mcp2koru.server  [3 funcs]
    __post_init__  CC=1  out:3
    create_server  CC=1  out:1
    run_server  CC=1  out:2
  packages.mcp2koru.src.mcp2koru.tools  [4 funcs]
    koru_run_command  CC=1  out:2
    koru_run_command_pb  CC=1  out:2
    koru_run_dsl  CC=2  out:2
    koru_to_dsl  CC=1  out:1
  packages.nlp2coru.src.nlp2coru.apply  [2 funcs]
    _execute_line  CC=2  out:4
    apply_prompt  CC=7  out:7
  packages.nlp2coru.src.nlp2coru.cli  [1 funcs]
    _emit  CC=4  out:4
  packages.nlp2coru.src.nlp2coru.control  [2 funcs]
    dispatch_line  CC=1  out:2
    is_dsl2koru_line  CC=2  out:3
  packages.nlp2coru.src.nlp2coru.heuristic  [8 funcs]
    _contains_any  CC=2  out:1
    _heuristic_intent  CC=1  out:2
    _parse_lane_mentions  CC=3  out:6
    _refactor_intent  CC=3  out:5
    _resolve_heuristic_action  CC=11  out:9
    detect_setup_intent  CC=2  out:3
    heuristic_plan  CC=1  out:5
    to_dsl_lines  CC=13  out:14
  packages.nlp2coru.src.nlp2coru.llm  [2 funcs]
    _parse_llm_json  CC=2  out:4
    llm_plan  CC=9  out:17
  packages.nlp2coru.src.nlp2coru.llm_backend  [2 funcs]
    complete  CC=9  out:10
    get_backend  CC=2  out:1
  packages.nlp2coru.src.nlp2coru.openrouter_config  [6 funcs]
    get_fallback_model  CC=1  out:1
    get_ollama_base_url  CC=1  out:1
    get_openrouter_headers  CC=3  out:3
    load_project_metadata  CC=7  out:14
    setup_openrouter_env  CC=3  out:3
    should_use_ollama_fallback  CC=2  out:3
  packages.nlp2coru.src.nlp2coru.rewrite  [1 funcs]
    rewrite_chat_prompt  CC=4  out:2
  packages.nlp2coru.src.nlp2coru.to_dsl  [1 funcs]
    to_dsl  CC=11  out:11
  packages.nlpshim.src.nlpshim.client  [7 funcs]
    __init__  CC=2  out:2
    parse_intent  CC=3  out:3
    _intent_ir_steps  CC=7  out:8
    _use_intent_ir  CC=2  out:1
    _workflow_steps_from_client  CC=7  out:10
    analyze_text_structure  CC=2  out:2
    get_nlp2dsl_client  CC=2  out:0
  packages.nlpshim.src.nlpshim.control  [1 funcs]
    to_dsl  CC=1  out:1
  packages.nlpshim.src.nlpshim.conversation_client  [3 funcs]
    __init__  CC=2  out:2
    export_trace  CC=1  out:2
    message  CC=9  out:22
  packages.nlpshim.src.nlpshim.conversation_test_api  [2 funcs]
    complete_missing_fields  CC=1  out:2
    parse_conversation_step  CC=10  out:16
  packages.uri2coru.src.uri2coru.decode  [1 funcs]
    uri_to_dsl  CC=7  out:18
  packages.uri2coru.src.uri2coru.nlp2uri  [2 funcs]
    best_uri  CC=2  out:1
    nlp2uri  CC=14  out:23
  packages.uri2coru.src.uri2coru.run  [1 funcs]
    run_uri  CC=2  out:2
  packages.uri2coru.src.uri2coru.uri  [6 funcs]
    _decode  CC=2  out:1
    _encode  CC=1  out:1
    is_coru_uri  CC=1  out:2
    parse_coru_uri  CC=7  out:9
    uri_for_block  CC=5  out:3
    uri_for_cmd  CC=4  out:5
  packages.uri2koru.src.uri2koru.decode  [3 funcs]
    _block_uri_to_dsl  CC=4  out:5
    _cmd_uri_to_dsl  CC=9  out:14
    uri_to_dsl  CC=5  out:9
  packages.uri2koru.src.uri2koru.nlp2uri  [2 funcs]
    best_uri  CC=2  out:1
    nlp2uri  CC=13  out:23
  packages.uri2koru.src.uri2koru.run  [1 funcs]
    run_uri  CC=1  out:2
  packages.uri2koru.src.uri2koru.uri  [6 funcs]
    _decode  CC=2  out:1
    _encode  CC=1  out:1
    is_koru_uri  CC=1  out:2
    parse_koru_uri  CC=7  out:9
    uri_for_block  CC=4  out:3
    uri_for_cmd  CC=4  out:5
  project  [1 funcs]
    print  CC=0  out:0
  src.koru.autonomy.ide_operator_guidance  [1 funcs]
    terminal_kind_label  CC=3  out:0
  src.koru.integrations.imgl_client  [2 funcs]
    imgl_available  CC=2  out:3
    imgl_missing_message  CC=3  out:2
  src.koru.wizard.gui.static.wizard  [1 funcs]
    list  CC=5  out:9
  src.koruide.ide  [2 funcs]
    detect_running_ides  CC=4  out:4
    detect_terminal_host_context  CC=9  out:9

EDGES:
  packages.dsl2koru.src.dsl2koru.bus.dispatch → packages.dsl2koru.src.dsl2koru.codec.envelope_from_bytes
  packages.dsl2koru.src.dsl2koru.bus.dispatch → packages.dsl2koru.src.dsl2koru.handlers.run_query
  packages.dsl2koru.src.dsl2koru.bus.dispatch → packages.dsl2koru.src.dsl2koru.handlers.run_command
  packages.dsl2koru.src.dsl2koru.bus.execute_dsl_line → packages.dsl2koru.src.dsl2koru.bus.dispatch
  packages.dsl2koru.src.dsl2koru.bus.execute_dsl → packages.dsl2koru.src.dsl2koru.bus.execute_dsl_line
  packages.dsl2koru.src.dsl2koru.cli._run_results → project.print
  packages.dsl2koru.src.dsl2koru.cli.main → packages.dsl2koru.src.dsl2koru.cli._main_legacy
  packages.dsl2koru.src.dsl2koru.cli.main → packages.dsl2koru.src.dsl2koru.cli._main_subcommand
  packages.dsl2koru.src.dsl2koru.cli._main_legacy → packages.dsl2koru.src.dsl2koru.cli._run_results
  packages.dsl2koru.src.dsl2koru.cli._cmd_validate_schema → packages.dsl2koru.src.dsl2koru.schema_registry.validate_schemas
  packages.dsl2koru.src.dsl2koru.cli._cmd_validate_schema → project.print
  packages.dsl2koru.src.dsl2koru.cli._cmd_encode → packages.dsl2koru.src.dsl2koru.codec.parse_text
  packages.dsl2koru.src.dsl2koru.cli._cmd_encode → packages.dsl2koru.src.dsl2koru.codec.envelope_to_json
  packages.dsl2koru.src.dsl2koru.cli._cmd_encode → packages.dsl2koru.src.dsl2koru.codec.envelope_to_bytes
  packages.dsl2koru.src.dsl2koru.cli._cmd_decode → project.print
  packages.dsl2koru.src.dsl2koru.cli._cmd_decode → packages.dsl2koru.src.dsl2koru.codec.envelope_from_json
  packages.dsl2koru.src.dsl2koru.cli._cmd_decode → packages.dsl2koru.src.dsl2koru.codec.envelope_from_bytes
  packages.dsl2koru.src.dsl2koru.cli._cmd_roundtrip → project.print
  packages.dsl2koru.src.dsl2koru.cli._cmd_roundtrip → packages.dsl2koru.src.dsl2koru.codec.roundtrip_text
  packages.dsl2koru.src.dsl2koru.cli._cmd_replay → project.print
  packages.dsl2koru.src.dsl2koru.cli._cmd_run → packages.dsl2koru.src.dsl2koru.cli._run_results
  packages.dsl2koru.src.dsl2koru.cli._cmd_run → packages.dsl2koru.src.dsl2koru.bus.dispatch
  packages.dsl2koru.src.dsl2koru.cli._cmd_run → packages.dsl2koru.src.dsl2koru.bus.execute_dsl
  packages.dsl2koru.src.dsl2koru.events.EventStore.append_command → packages.dsl2koru.src.dsl2koru.pb_codec.encode_protobuf
  packages.dsl2koru.src.dsl2koru.pb_codec.encode_protobuf → packages.dsl2koru.src.dsl2koru.pb_codec._set_body
  packages.dsl2koru.src.dsl2koru.pb_codec.decode_protobuf → packages.dsl2koru.src.dsl2koru.pb_codec.envelope_to_dict
  packages.dsl2koru.src.dsl2koru.pb_codec.encode_text_to_protobuf → packages.dsl2koru.src.dsl2koru.grammar.parse_line
  packages.dsl2koru.src.dsl2koru.pb_codec.encode_text_to_protobuf → packages.dsl2koru.src.dsl2koru.pb_codec.encode_protobuf
  packages.dsl2koru.src.dsl2koru.pb_codec.decode_protobuf_to_text → packages.dsl2koru.src.dsl2koru.grammar.to_text
  packages.dsl2koru.src.dsl2koru.pb_codec.decode_protobuf_to_text → packages.dsl2koru.src.dsl2koru.pb_codec.decode_protobuf
  packages.dsl2koru.src.dsl2koru.pb_codec.encode_result_protobuf → packages.dsl2koru.src.dsl2koru.pb_codec.result_to_pb
  packages.dsl2koru.src.dsl2koru.schema_registry.schema_for_verb → packages.dsl2koru.src.dsl2koru.schema_registry._load_schemas
  packages.dsl2koru.src.dsl2koru.schema_registry.all_verbs → packages.dsl2koru.src.dsl2koru.schema_registry._load_schemas
  packages.dsl2koru.src.dsl2koru.schema_registry.validate_schemas → packages.dsl2koru.src.dsl2koru.schema_registry._load_schemas
  packages.dsl2koru.src.dsl2koru.codegen.build_model_registry → packages.dsl2koru.src.dsl2koru.schema_registry._load_schemas
  packages.dsl2koru.src.dsl2koru.codegen.build_model_registry → packages.dsl2koru.src.dsl2koru.codegen._python_type
  packages.dsl2koru.src.dsl2koru.codegen.validate_payload → packages.dsl2koru.src.dsl2koru.codegen.build_model_registry
  packages.dsl2koru.src.dsl2koru.codegen.render_models_module → packages.dsl2koru.src.dsl2koru.schema_registry.all_verbs
  packages.dsl2koru.src.dsl2koru.codegen.render_models_module → packages.dsl2koru.src.dsl2koru.schema_registry._load_schemas
  packages.dsl2koru.src.dsl2koru.codegen.main → packages.dsl2koru.src.dsl2koru.codegen.render_models_module
  packages.dsl2koru.src.dsl2koru.codegen.main → packages.dsl2koru.src.dsl2koru.codegen.build_model_registry
  packages.dsl2koru.src.dsl2koru.codegen.main → project.print
  packages.dsl2koru.src.dsl2koru.grammar._parse_query_repair_history → packages.dsl2koru.src.dsl2koru.grammar._flag
  packages.dsl2koru.src.dsl2koru.grammar._parse_query_lane_status → packages.dsl2koru.src.dsl2koru.grammar._flag
  packages.dsl2koru.src.dsl2koru.grammar._parse_validate_lane → packages.dsl2koru.src.dsl2koru.grammar._flag
  packages.dsl2koru.src.dsl2koru.grammar._parse_resolve → packages.dsl2koru.src.dsl2koru.grammar._flag
  packages.dsl2koru.src.dsl2koru.grammar._parse_repair_run → packages.dsl2koru.src.dsl2koru.grammar._flag
  packages.dsl2koru.src.dsl2koru.codec.validate_payload → packages.dsl2koru.src.dsl2koru.schema_registry.schema_for_verb
  packages.dsl2koru.src.dsl2koru.codec.parse_text → packages.dsl2koru.src.dsl2koru.grammar.parse_line
  packages.dsl2koru.src.dsl2koru.codec.parse_text → packages.dsl2koru.src.dsl2koru.codec.validate_payload
```

## Test Contracts

*Scenarios as contract signatures — what the system guarantees.*

### Cli (8)

**`coru calibration command (WUP quick / dry-run safe)`**

**`koru Command Tests (live — not for WUP --dry-run quick probes)`**

**`koru Command Tests (WUP quick / dry-run safe)`**

**`koru-api Command Tests (WUP quick / dry-run safe)`**

**`koru-dsl Command Tests (WUP quick / dry-run safe)`**

**`koru-wup-testql Command Tests (WUP quick / dry-run safe)`**

**`CLI Smoke Tests`**

**`CLI Command Tests`**

### Integration (2)

**`Auto-generated from Python Tests`**

**`Photo-VQL drive contract (SUMD autonomy loop — observe→decide→act→verify)`**

## Refactoring Analysis

*Pre-refactoring snapshot — use this section to identify targets. Generated from `project/` toon files.*

### Call Graph & Complexity (`project/calls.toon.yaml`)

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/koru
# generated in 0.89s
# nodes: 374 | edges: 500 | modules: 69
# CC̄=3.7

HUBS[20]:
  project.print
    CC=0  in:1042  out:0  total:1042
  src.koru.wizard.gui.static.wizard.list
    CC=5  in:221  out:9  total:230
  packages.dsl2koru.src.dsl2koru.bus.dispatch
    CC=11  in:27  out:25  total:52
  packages.dsl2coru.src.dsl2coru.parser._flag
    CC=7  in:33  out:8  total:41
  packages.coru.src.coru.cli._maybe_reexec_into_project_python
    CC=16  in:1  out:33  total:34
  packages.dsl2koru.src.dsl2koru.events.EventStore.append_command
    CC=3  in:0  out:33  total:33
  packages.coru.src.coru.supervisor.registry.load_registry
    CC=5  in:21  out:11  total:32
  packages.coru.src.coru.cli._run_lane_repair
    CC=7  in:7  out:24  total:31
  src.koruide.ide.detect_running_ides
    CC=4  in:25  out:4  total:29
  packages.nlp2coru.src.nlp2coru.cli._emit
    CC=4  in:24  out:4  total:28
  packages.coru.src.coru.cli_checks._trace
    CC=3  in:23  out:5  total:28
  packages.uri2coru.src.uri2coru.nlp2uri.nlp2uri
    CC=14  in:4  out:23  total:27
  packages.coru.src.coru.cli._repo_root
    CC=4  in:23  out:4  total:27
  packages.dsl2coru.src.dsl2coru.events.EventStore._append_jsonl
    CC=3  in:0  out:26  total:26
  packages.dsl2coru.src.dsl2coru.events.EventStore._append_pb
    CC=3  in:0  out:26  total:26
  packages.dsl2koru.src.dsl2koru.cli._main_subcommand
    CC=1  in:1  out:24  total:25
  packages.coru.src.coru.cli_calibration._materialize_calibration_desktop_oql
    CC=7  in:2  out:22  total:24
  packages.uri2koru.src.uri2koru.nlp2uri.nlp2uri
    CC=13  in:1  out:23  total:24
  packages.dsl2koru.src.dsl2koru.codegen.render_models_module
    CC=12  in:1  out:22  total:23
  packages.uri2coru.src.uri2coru.decode.uri_to_dsl
    CC=7  in:4  out:18  total:22

MODULES:
  packages.cli2coru.src.cli2coru.cli  [4 funcs]
    _handle_exec  CC=2  out:2
    _handle_run  CC=3  out:4
    _handle_shell  CC=1  out:1
    _print_result  CC=4  out:6
  packages.cli2coru.src.cli2coru.shell  [1 funcs]
    run_shell  CC=9  out:12
  packages.cli2koru.src.cli2koru.cli  [4 funcs]
    _handle_exec  CC=2  out:2
    _handle_run  CC=3  out:4
    _handle_shell  CC=1  out:1
    _print_result  CC=4  out:6
  packages.cli2koru.src.cli2koru.shell  [1 funcs]
    run_shell  CC=9  out:12
  packages.coru.src.coru.cli  [91 funcs]
    _active_project_root  CC=3  out:2
    _agent_lane_from_auto_args  CC=7  out:7
    _alive_daemon_ide  CC=8  out:6
    _alive_daemon_instance  CC=13  out:16
    _auto_default_instance  CC=4  out:3
    _autonomous_startup_chain  CC=2  out:8
    _binary_path  CC=6  out:8
    _chain_project_from_plans  CC=3  out:1
    _choose_option  CC=9  out:11
    _cmd_exists  CC=1  out:1
  packages.coru.src.coru.cli_calibration  [25 funcs]
    _append_desktop_focus_lines  CC=2  out:2
    _calibration_desktop_focus_titles  CC=4  out:7
    _calibration_desktop_template_path  CC=3  out:1
    _calibration_preflight_reports  CC=3  out:4
    _calibration_probe_drive  CC=6  out:8
    _calibration_socket_fix  CC=4  out:5
    _desktop_capture_enabled  CC=1  out:3
    _format_calibration_bridge_report  CC=7  out:13
    _format_calibration_desktop_report  CC=6  out:14
    _format_calibration_probe_report  CC=9  out:11
  packages.coru.src.coru.cli_checks  [2 funcs]
    _coru_normalize_project  CC=7  out:6
    _trace  CC=3  out:5
  packages.coru.src.coru.cli_parser  [1 funcs]
    _add_lane_identifiers  CC=1  out:2
  packages.coru.src.coru.ecosystem  [5 funcs]
    _default_runner  CC=1  out:2
    _detect_running_plugin_ides  CC=4  out:2
    _local_package_paths  CC=5  out:7
    sync_ecosystem  CC=14  out:13
    sync_python_packages  CC=6  out:5
  packages.coru.src.coru.repair.runtime  [1 funcs]
    run_lane_repair  CC=1  out:1
  packages.coru.src.coru.supervisor.paths  [1 funcs]
    registry_path  CC=1  out:1
  packages.coru.src.coru.supervisor.registry  [2 funcs]
    active_lane_pair  CC=2  out:2
    load_registry  CC=5  out:11
  packages.dsl2coru.src.dsl2coru.bus  [7 funcs]
    _dispatch_koru  CC=6  out:7
    _normalize_command  CC=5  out:10
    _route_payload  CC=5  out:8
    dispatch  CC=9  out:10
    dispatch_text  CC=2  out:2
    execute_dsl  CC=5  out:6
    execute_dsl_line  CC=1  out:1
  packages.dsl2coru.src.dsl2coru.cli  [13 funcs]
    _build_subcommand_parser  CC=3  out:4
    _cmd_decode  CC=2  out:6
    _cmd_encode  CC=4  out:6
    _cmd_exec  CC=2  out:2
    _cmd_replay  CC=6  out:8
    _cmd_roundtrip  CC=2  out:2
    _cmd_run  CC=4  out:7
    _cmd_validate_schema  CC=3  out:3
    _handle_subcommand  CC=2  out:2
    _main_legacy  CC=5  out:17
  packages.dsl2coru.src.dsl2coru.codec  [7 funcs]
    envelope_from_bytes  CC=1  out:2
    envelope_from_json  CC=2  out:5
    envelope_to_bytes  CC=1  out:2
    envelope_to_json  CC=1  out:3
    parse_text  CC=2  out:2
    roundtrip_text  CC=2  out:4
    validate_payload  CC=2  out:6
  packages.dsl2coru.src.dsl2coru.codegen  [5 funcs]
    _python_type  CC=9  out:4
    build_model_registry  CC=3  out:10
    main  CC=9  out:19
    render_models_module  CC=7  out:19
    validate_payload  CC=2  out:7
  packages.dsl2coru.src.dsl2coru.events  [2 funcs]
    _append_jsonl  CC=3  out:26
    _append_pb  CC=3  out:26
  packages.dsl2coru.src.dsl2coru.handlers.argv  [1 funcs]
    to_cli_args  CC=4  out:7
  packages.dsl2coru.src.dsl2coru.handlers.command  [1 funcs]
    run_command  CC=6  out:9
  packages.dsl2coru.src.dsl2coru.handlers.query  [1 funcs]
    run_query  CC=6  out:9
  packages.dsl2coru.src.dsl2coru.handlers.runner  [2 funcs]
    _run_subprocess  CC=4  out:1
    default_runner  CC=5  out:6
  packages.dsl2coru.src.dsl2coru.handlers.ui  [4 funcs]
    _build_ui_result  CC=2  out:7
    _ensure_imgl_available  CC=3  out:2
    _ui_prompt_for_verb  CC=12  out:11
    run_ui_command  CC=3  out:13
  packages.dsl2coru.src.dsl2coru.parser  [20 funcs]
    _flag  CC=7  out:8
    _parse_auto  CC=6  out:4
    _parse_calibration  CC=6  out:4
    _parse_chat  CC=5  out:4
    _parse_doctor  CC=5  out:4
    _parse_ensure  CC=2  out:1
    _parse_env  CC=3  out:1
    _parse_lane  CC=4  out:3
    _parse_repair_run  CC=4  out:3
    _parse_status  CC=2  out:1
  packages.dsl2coru.src.dsl2coru.pb_codec  [10 funcs]
    _extract_auto  CC=4  out:1
    _set_body  CC=3  out:7
    decode_protobuf  CC=1  out:3
    decode_protobuf_to_text  CC=1  out:2
    dict_to_envelope  CC=1  out:5
    encode_protobuf  CC=1  out:2
    encode_result_protobuf  CC=1  out:2
    encode_text_to_protobuf  CC=3  out:3
    envelope_to_dict  CC=4  out:6
    result_to_pb  CC=3  out:3
  packages.dsl2coru.src.dsl2coru.schema_registry  [5 funcs]
    _load_schemas  CC=4  out:11
    all_verbs  CC=1  out:3
    normalize_verb  CC=1  out:6
    schema_for_verb  CC=2  out:4
    validate_schemas  CC=3  out:6
  packages.dsl2coru.src.dsl2coru.serializer  [9 funcs]
    _append_flag  CC=5  out:6
    _serialize_auto  CC=2  out:5
    _serialize_calibration  CC=3  out:4
    _serialize_chat  CC=3  out:5
    _serialize_doctor  CC=3  out:5
    _serialize_lane  CC=1  out:3
    _serialize_repair_run  CC=2  out:4
    _serialize_text  CC=4  out:8
    to_text  CC=4  out:12
  packages.dsl2koru.src.dsl2koru.bus  [3 funcs]
    dispatch  CC=11  out:25
    execute_dsl  CC=4  out:6
    execute_dsl_line  CC=1  out:1
  packages.dsl2koru.src.dsl2koru.cli  [10 funcs]
    _cmd_decode  CC=2  out:6
    _cmd_encode  CC=3  out:6
    _cmd_replay  CC=4  out:8
    _cmd_roundtrip  CC=1  out:2
    _cmd_run  CC=3  out:7
    _cmd_validate_schema  CC=3  out:3
    _main_legacy  CC=4  out:17
    _main_subcommand  CC=1  out:24
    _run_results  CC=6  out:6
    main  CC=4  out:2
  packages.dsl2koru.src.dsl2koru.codec  [7 funcs]
    envelope_from_bytes  CC=1  out:2
    envelope_from_json  CC=2  out:5
    envelope_to_bytes  CC=1  out:2
    envelope_to_json  CC=1  out:3
    parse_text  CC=2  out:2
    roundtrip_text  CC=1  out:4
    validate_payload  CC=2  out:6
  packages.dsl2koru.src.dsl2koru.codegen  [5 funcs]
    _python_type  CC=11  out:5
    build_model_registry  CC=3  out:10
    main  CC=6  out:18
    render_models_module  CC=12  out:22
    validate_payload  CC=2  out:7
  packages.dsl2koru.src.dsl2koru.events  [1 funcs]
    append_command  CC=3  out:33
  packages.dsl2koru.src.dsl2koru.grammar  [8 funcs]
    _flag  CC=3  out:3
    _parse_query_lane_status  CC=4  out:2
    _parse_query_repair_history  CC=5  out:4
    _parse_repair_run  CC=7  out:4
    _parse_resolve  CC=5  out:5
    _parse_validate_lane  CC=4  out:2
    parse_line  CC=5  out:7
    to_text  CC=2  out:6
  packages.dsl2koru.src.dsl2koru.handlers  [7 funcs]
    _query_lane_status  CC=1  out:11
    _query_repair_history  CC=2  out:14
    _repair_run  CC=6  out:9
    _resolve  CC=3  out:8
    _validate_lane  CC=1  out:7
    run_command  CC=2  out:4
    run_query  CC=5  out:7
  packages.dsl2koru.src.dsl2koru.pb_codec  [8 funcs]
    _set_body  CC=3  out:7
    decode_protobuf  CC=1  out:3
    decode_protobuf_to_text  CC=1  out:2
    encode_protobuf  CC=1  out:6
    encode_result_protobuf  CC=1  out:2
    encode_text_to_protobuf  CC=3  out:3
    envelope_to_dict  CC=4  out:6
    result_to_pb  CC=3  out:3
  packages.dsl2koru.src.dsl2koru.schema_registry  [4 funcs]
    _load_schemas  CC=4  out:11
    all_verbs  CC=1  out:3
    schema_for_verb  CC=2  out:4
    validate_schemas  CC=3  out:6
  packages.koruenv.src.koruenv.cli  [6 funcs]
    _emit_log  CC=5  out:7
    _iso_ts  CC=1  out:4
    _normalize_log_format  CC=3  out:2
    _run_with_overlay  CC=4  out:11
    _strip_double_dash  CC=3  out:1
    main  CC=5  out:18
  packages.koruenv.src.koruenv.lane  [6 funcs]
    _fallback_temp_dir  CC=5  out:5
    build_lane_environ  CC=2  out:5
    resolve_lane_socket  CC=1  out:1
    resolve_lane_socket_for_os  CC=5  out:10
    validate_ide  CC=3  out:6
    validate_instance  CC=3  out:4
  packages.mcp2coru.src.mcp2coru.cli  [1 funcs]
    main  CC=4  out:9
  packages.mcp2coru.src.mcp2coru.server  [4 funcs]
    __post_init__  CC=1  out:3
    _require_fastmcp  CC=2  out:1
    create_server  CC=1  out:1
    run_server  CC=1  out:2
  packages.mcp2coru.src.mcp2coru.tools  [4 funcs]
    coru_run_command  CC=1  out:2
    coru_run_command_pb  CC=1  out:2
    coru_run_dsl  CC=2  out:2
    coru_to_dsl  CC=1  out:1
  packages.mcp2koru.src.mcp2koru.cli  [1 funcs]
    main  CC=4  out:9
  packages.mcp2koru.src.mcp2koru.server  [3 funcs]
    __post_init__  CC=1  out:3
    create_server  CC=1  out:1
    run_server  CC=1  out:2
  packages.mcp2koru.src.mcp2koru.tools  [4 funcs]
    koru_run_command  CC=1  out:2
    koru_run_command_pb  CC=1  out:2
    koru_run_dsl  CC=2  out:2
    koru_to_dsl  CC=1  out:1
  packages.nlp2coru.src.nlp2coru.apply  [2 funcs]
    _execute_line  CC=2  out:4
    apply_prompt  CC=7  out:7
  packages.nlp2coru.src.nlp2coru.cli  [1 funcs]
    _emit  CC=4  out:4
  packages.nlp2coru.src.nlp2coru.control  [2 funcs]
    dispatch_line  CC=1  out:2
    is_dsl2koru_line  CC=2  out:3
  packages.nlp2coru.src.nlp2coru.heuristic  [8 funcs]
    _contains_any  CC=2  out:1
    _heuristic_intent  CC=1  out:2
    _parse_lane_mentions  CC=3  out:6
    _refactor_intent  CC=3  out:5
    _resolve_heuristic_action  CC=11  out:9
    detect_setup_intent  CC=2  out:3
    heuristic_plan  CC=1  out:5
    to_dsl_lines  CC=13  out:14
  packages.nlp2coru.src.nlp2coru.llm  [2 funcs]
    _parse_llm_json  CC=2  out:4
    llm_plan  CC=9  out:17
  packages.nlp2coru.src.nlp2coru.llm_backend  [2 funcs]
    complete  CC=9  out:10
    get_backend  CC=2  out:1
  packages.nlp2coru.src.nlp2coru.openrouter_config  [6 funcs]
    get_fallback_model  CC=1  out:1
    get_ollama_base_url  CC=1  out:1
    get_openrouter_headers  CC=3  out:3
    load_project_metadata  CC=7  out:14
    setup_openrouter_env  CC=3  out:3
    should_use_ollama_fallback  CC=2  out:3
  packages.nlp2coru.src.nlp2coru.rewrite  [1 funcs]
    rewrite_chat_prompt  CC=4  out:2
  packages.nlp2coru.src.nlp2coru.to_dsl  [1 funcs]
    to_dsl  CC=11  out:11
  packages.nlpshim.src.nlpshim.client  [7 funcs]
    __init__  CC=2  out:2
    parse_intent  CC=3  out:3
    _intent_ir_steps  CC=7  out:8
    _use_intent_ir  CC=2  out:1
    _workflow_steps_from_client  CC=7  out:10
    analyze_text_structure  CC=2  out:2
    get_nlp2dsl_client  CC=2  out:0
  packages.nlpshim.src.nlpshim.control  [1 funcs]
    to_dsl  CC=1  out:1
  packages.nlpshim.src.nlpshim.conversation_client  [3 funcs]
    __init__  CC=2  out:2
    export_trace  CC=1  out:2
    message  CC=9  out:22
  packages.nlpshim.src.nlpshim.conversation_test_api  [2 funcs]
    complete_missing_fields  CC=1  out:2
    parse_conversation_step  CC=10  out:16
  packages.uri2coru.src.uri2coru.decode  [1 funcs]
    uri_to_dsl  CC=7  out:18
  packages.uri2coru.src.uri2coru.nlp2uri  [2 funcs]
    best_uri  CC=2  out:1
    nlp2uri  CC=14  out:23
  packages.uri2coru.src.uri2coru.run  [1 funcs]
    run_uri  CC=2  out:2
  packages.uri2coru.src.uri2coru.uri  [6 funcs]
    _decode  CC=2  out:1
    _encode  CC=1  out:1
    is_coru_uri  CC=1  out:2
    parse_coru_uri  CC=7  out:9
    uri_for_block  CC=5  out:3
    uri_for_cmd  CC=4  out:5
  packages.uri2koru.src.uri2koru.decode  [3 funcs]
    _block_uri_to_dsl  CC=4  out:5
    _cmd_uri_to_dsl  CC=9  out:14
    uri_to_dsl  CC=5  out:9
  packages.uri2koru.src.uri2koru.nlp2uri  [2 funcs]
    best_uri  CC=2  out:1
    nlp2uri  CC=13  out:23
  packages.uri2koru.src.uri2koru.run  [1 funcs]
    run_uri  CC=1  out:2
  packages.uri2koru.src.uri2koru.uri  [6 funcs]
    _decode  CC=2  out:1
    _encode  CC=1  out:1
    is_koru_uri  CC=1  out:2
    parse_koru_uri  CC=7  out:9
    uri_for_block  CC=4  out:3
    uri_for_cmd  CC=4  out:5
  project  [1 funcs]
    print  CC=0  out:0
  src.koru.autonomy.ide_operator_guidance  [1 funcs]
    terminal_kind_label  CC=3  out:0
  src.koru.integrations.imgl_client  [2 funcs]
    imgl_available  CC=2  out:3
    imgl_missing_message  CC=3  out:2
  src.koru.wizard.gui.static.wizard  [1 funcs]
    list  CC=5  out:9
  src.koruide.ide  [2 funcs]
    detect_running_ides  CC=4  out:4
    detect_terminal_host_context  CC=9  out:9

EDGES:
  packages.dsl2koru.src.dsl2koru.bus.dispatch → packages.dsl2koru.src.dsl2koru.codec.envelope_from_bytes
  packages.dsl2koru.src.dsl2koru.bus.dispatch → packages.dsl2koru.src.dsl2koru.handlers.run_query
  packages.dsl2koru.src.dsl2koru.bus.dispatch → packages.dsl2koru.src.dsl2koru.handlers.run_command
  packages.dsl2koru.src.dsl2koru.bus.execute_dsl_line → packages.dsl2koru.src.dsl2koru.bus.dispatch
  packages.dsl2koru.src.dsl2koru.bus.execute_dsl → packages.dsl2koru.src.dsl2koru.bus.execute_dsl_line
  packages.dsl2koru.src.dsl2koru.cli._run_results → project.print
  packages.dsl2koru.src.dsl2koru.cli.main → packages.dsl2koru.src.dsl2koru.cli._main_legacy
  packages.dsl2koru.src.dsl2koru.cli.main → packages.dsl2koru.src.dsl2koru.cli._main_subcommand
  packages.dsl2koru.src.dsl2koru.cli._main_legacy → packages.dsl2koru.src.dsl2koru.cli._run_results
  packages.dsl2koru.src.dsl2koru.cli._cmd_validate_schema → packages.dsl2koru.src.dsl2koru.schema_registry.validate_schemas
  packages.dsl2koru.src.dsl2koru.cli._cmd_validate_schema → project.print
  packages.dsl2koru.src.dsl2koru.cli._cmd_encode → packages.dsl2koru.src.dsl2koru.codec.parse_text
  packages.dsl2koru.src.dsl2koru.cli._cmd_encode → packages.dsl2koru.src.dsl2koru.codec.envelope_to_json
  packages.dsl2koru.src.dsl2koru.cli._cmd_encode → packages.dsl2koru.src.dsl2koru.codec.envelope_to_bytes
  packages.dsl2koru.src.dsl2koru.cli._cmd_decode → project.print
  packages.dsl2koru.src.dsl2koru.cli._cmd_decode → packages.dsl2koru.src.dsl2koru.codec.envelope_from_json
  packages.dsl2koru.src.dsl2koru.cli._cmd_decode → packages.dsl2koru.src.dsl2koru.codec.envelope_from_bytes
  packages.dsl2koru.src.dsl2koru.cli._cmd_roundtrip → project.print
  packages.dsl2koru.src.dsl2koru.cli._cmd_roundtrip → packages.dsl2koru.src.dsl2koru.codec.roundtrip_text
  packages.dsl2koru.src.dsl2koru.cli._cmd_replay → project.print
  packages.dsl2koru.src.dsl2koru.cli._cmd_run → packages.dsl2koru.src.dsl2koru.cli._run_results
  packages.dsl2koru.src.dsl2koru.cli._cmd_run → packages.dsl2koru.src.dsl2koru.bus.dispatch
  packages.dsl2koru.src.dsl2koru.cli._cmd_run → packages.dsl2koru.src.dsl2koru.bus.execute_dsl
  packages.dsl2koru.src.dsl2koru.events.EventStore.append_command → packages.dsl2koru.src.dsl2koru.pb_codec.encode_protobuf
  packages.dsl2koru.src.dsl2koru.pb_codec.encode_protobuf → packages.dsl2koru.src.dsl2koru.pb_codec._set_body
  packages.dsl2koru.src.dsl2koru.pb_codec.decode_protobuf → packages.dsl2koru.src.dsl2koru.pb_codec.envelope_to_dict
  packages.dsl2koru.src.dsl2koru.pb_codec.encode_text_to_protobuf → packages.dsl2koru.src.dsl2koru.grammar.parse_line
  packages.dsl2koru.src.dsl2koru.pb_codec.encode_text_to_protobuf → packages.dsl2koru.src.dsl2koru.pb_codec.encode_protobuf
  packages.dsl2koru.src.dsl2koru.pb_codec.decode_protobuf_to_text → packages.dsl2koru.src.dsl2koru.grammar.to_text
  packages.dsl2koru.src.dsl2koru.pb_codec.decode_protobuf_to_text → packages.dsl2koru.src.dsl2koru.pb_codec.decode_protobuf
  packages.dsl2koru.src.dsl2koru.pb_codec.encode_result_protobuf → packages.dsl2koru.src.dsl2koru.pb_codec.result_to_pb
  packages.dsl2koru.src.dsl2koru.schema_registry.schema_for_verb → packages.dsl2koru.src.dsl2koru.schema_registry._load_schemas
  packages.dsl2koru.src.dsl2koru.schema_registry.all_verbs → packages.dsl2koru.src.dsl2koru.schema_registry._load_schemas
  packages.dsl2koru.src.dsl2koru.schema_registry.validate_schemas → packages.dsl2koru.src.dsl2koru.schema_registry._load_schemas
  packages.dsl2koru.src.dsl2koru.codegen.build_model_registry → packages.dsl2koru.src.dsl2koru.schema_registry._load_schemas
  packages.dsl2koru.src.dsl2koru.codegen.build_model_registry → packages.dsl2koru.src.dsl2koru.codegen._python_type
  packages.dsl2koru.src.dsl2koru.codegen.validate_payload → packages.dsl2koru.src.dsl2koru.codegen.build_model_registry
  packages.dsl2koru.src.dsl2koru.codegen.render_models_module → packages.dsl2koru.src.dsl2koru.schema_registry.all_verbs
  packages.dsl2koru.src.dsl2koru.codegen.render_models_module → packages.dsl2koru.src.dsl2koru.schema_registry._load_schemas
  packages.dsl2koru.src.dsl2koru.codegen.main → packages.dsl2koru.src.dsl2koru.codegen.render_models_module
  packages.dsl2koru.src.dsl2koru.codegen.main → packages.dsl2koru.src.dsl2koru.codegen.build_model_registry
  packages.dsl2koru.src.dsl2koru.codegen.main → project.print
  packages.dsl2koru.src.dsl2koru.grammar._parse_query_repair_history → packages.dsl2koru.src.dsl2koru.grammar._flag
  packages.dsl2koru.src.dsl2koru.grammar._parse_query_lane_status → packages.dsl2koru.src.dsl2koru.grammar._flag
  packages.dsl2koru.src.dsl2koru.grammar._parse_validate_lane → packages.dsl2koru.src.dsl2koru.grammar._flag
  packages.dsl2koru.src.dsl2koru.grammar._parse_resolve → packages.dsl2koru.src.dsl2koru.grammar._flag
  packages.dsl2koru.src.dsl2koru.grammar._parse_repair_run → packages.dsl2koru.src.dsl2koru.grammar._flag
  packages.dsl2koru.src.dsl2koru.codec.validate_payload → packages.dsl2koru.src.dsl2koru.schema_registry.schema_for_verb
  packages.dsl2koru.src.dsl2koru.codec.parse_text → packages.dsl2koru.src.dsl2koru.grammar.parse_line
  packages.dsl2koru.src.dsl2koru.codec.parse_text → packages.dsl2koru.src.dsl2koru.codec.validate_payload
```

### Code Analysis (`project/analysis.toon.yaml`)

```toon markpact:analysis path=project/analysis.toon.yaml
# code2llm | 1038f 165702L | python:761,typescript:94,shell:58,json:41,yaml:31,toml:16,yml:11,kotlin:6,txt:5,proto:4,go:2,javascript:1,rust:1,properties:1,xml:1 | 2026-07-17
# generated in 2.31s
# CC̅=3.7 | critical:16/7229 | dups:0 | cycles:0

HEALTH[16]:
  🟡 CC    _maybe_reexec_into_project_python CC=16 (limit:15)
  🟡 CC    desktop_uri_handle CC=15 (limit:15)
  🟡 CC    main CC=17 (limit:15)
  🟡 CC    _checkbox_picker CC=19 (limit:15)
  🟡 CC    check_pytest_collect CC=15 (limit:15)
  🟡 CC    _run_fleet_up CC=15 (limit:15)
  🟡 CC    finalize_shell_drive_ticket CC=20 (limit:15)
  🟡 CC    _plugin_workspace_conflict CC=18 (limit:15)
  🟡 CC    _emit_autopilot_observability_outcome CC=15 (limit:15)
  🟡 CC    maybe_sync_project_koru_package CC=15 (limit:15)
  🟡 CC    run_daemon_command CC=15 (limit:15)
  🟡 CC    action_vdisplay_up CC=15 (limit:15)
  🟡 CC    main CC=22 (limit:15)
  🟡 CC    main CC=16 (limit:15)
  🟡 CC    _type_text_at_vql_coords CC=15 (limit:15)
  🟡 CC    sync_prepare_capture_flags_to_env CC=15 (limit:15)

REFACTOR[1]:
  1. split 16 high-CC methods  (CC>15)

PIPELINES[2179]:
  [1] Src [get_files]: get_files
      PURITY: 100% pure
  [2] Src [main]: main → _main_legacy → _run_results → print
      PURITY: 100% pure
  [3] Src [_cmd_validate_schema]: _cmd_validate_schema → validate_schemas → _load_schemas
      PURITY: 100% pure
  [4] Src [_cmd_encode]: _cmd_encode → parse_text → parse_line
      PURITY: 100% pure
  [5] Src [_cmd_decode]: _cmd_decode → print
      PURITY: 100% pure
  [6] Src [_cmd_roundtrip]: _cmd_roundtrip → print
      PURITY: 100% pure
  [7] Src [_cmd_replay]: _cmd_replay → print
      PURITY: 100% pure
  [8] Src [_cmd_run]: _cmd_run → _run_results → print
      PURITY: 100% pure
  [9] Src [for_project]: for_project
      PURITY: 100% pure
  [10] Src [append_command]: append_command → encode_protobuf → _set_body
      PURITY: 100% pure
  [11] Src [read_all]: read_all → envelope_to_dict
      PURITY: 100% pure
  [12] Src [replay_pb]: replay_pb → envelope_to_dict
      PURITY: 100% pure
  [13] Src [replay]: replay
      PURITY: 100% pure
  [14] Src [_set_query_repair_history]: _set_query_repair_history
      PURITY: 100% pure
  [15] Src [_set_query_lane_status]: _set_query_lane_status
      PURITY: 100% pure
  [16] Src [_set_validate_lane]: _set_validate_lane
      PURITY: 100% pure
  [17] Src [_set_resolve]: _set_resolve
      PURITY: 100% pure
  [18] Src [_set_repair_run]: _set_repair_run
      PURITY: 100% pure
  [19] Src [encode_text_to_protobuf]: encode_text_to_protobuf → parse_line
      PURITY: 100% pure
  [20] Src [decode_protobuf_to_text]: decode_protobuf_to_text → to_text
      PURITY: 100% pure
  [21] Src [main]: main → render_models_module → all_verbs → _load_schemas
      PURITY: 100% pure
  [22] Src [_parse_query_repair_history]: _parse_query_repair_history → _flag
      PURITY: 100% pure
  [23] Src [_parse_query_lane_status]: _parse_query_lane_status → _flag
      PURITY: 100% pure
  [24] Src [_parse_validate_lane]: _parse_validate_lane → _flag
      PURITY: 100% pure
  [25] Src [_parse_resolve]: _parse_resolve → _flag
      PURITY: 100% pure
  [26] Src [_parse_repair_run]: _parse_repair_run → _flag
      PURITY: 100% pure
  [27] Src [_serialize_query_repair_history]: _serialize_query_repair_history
      PURITY: 100% pure
  [28] Src [_serialize_query_lane_status]: _serialize_query_lane_status
      PURITY: 100% pure
  [29] Src [_serialize_validate_lane]: _serialize_validate_lane
      PURITY: 100% pure
  [30] Src [_serialize_resolve]: _serialize_resolve
      PURITY: 100% pure
  [31] Src [_serialize_repair_run]: _serialize_repair_run
      PURITY: 100% pure
  [32] Src [main]: main → print
      PURITY: 100% pure
  [33] Src [_context]: _context
      PURITY: 100% pure
  [34] Src [_cmd_repair_history]: _cmd_repair_history
      PURITY: 100% pure
  [35] Src [_cmd_lane_status]: _cmd_lane_status
      PURITY: 100% pure
  [36] Src [_cmd_validate_lane]: _cmd_validate_lane
      PURITY: 100% pure
  [37] Src [_cmd_repair_run]: _cmd_repair_run
      PURITY: 100% pure
  [38] Src [_cmd_resolve]: _cmd_resolve
      PURITY: 100% pure
  [39] Src [_block_repair_history]: _block_repair_history
      PURITY: 100% pure
  [40] Src [_block_lane_status]: _block_lane_status
      PURITY: 100% pure
  [41] Src [main]: main → _normalize_log_format
      PURITY: 100% pure
  [42] Src [_handle_shell]: _handle_shell → run_shell → print
      PURITY: 100% pure
  [43] Src [_handle_run]: _handle_run → execute_dsl → execute_dsl_line → dispatch → ...(3 more)
      PURITY: 100% pure
  [44] Src [_handle_exec]: _handle_exec → dispatch → envelope_from_bytes → decode_protobuf → ...(1 more)
      PURITY: 100% pure
  [45] Src [main]: main
      PURITY: 100% pure
  [46] Src [__init__]: __init__ → get_nlp2dsl_client
      PURITY: 100% pure
  [47] Src [start]: start
      PURITY: 100% pure
  [48] Src [message]: message → list → escapeHtml
      PURITY: 100% pure
  [49] Src [run_dsl]: run_dsl
      PURITY: 100% pure
  [50] Src [export_trace]: export_trace → list → escapeHtml
      PURITY: 100% pure

LAYERS:
  services/                       CC̄=4.4    ←in:0  →out:0
  │ !! app                        694L  0C   28m  CC=11     ←1
  │ ticket_builder             223L  0C    7m  CC=11     ←1
  │ app_command_routing         82L  0C    2m  CC=7      ←1
  │ Dockerfile                  36L  0C    0m  CC=0.0    ←0
  │ app_bootstrap               34L  0C    2m  CC=1      ←0
  │
  src/                            CC̄=4.1    ←in:0  →out:1
  │ !! vdisplay_client           7512L  0C  295m  CC=15     ←8
  │ !! scan                      1673L  0C   63m  CC=13     ←7
  │ !! plugin_installer          1372L  3C   64m  CC=13     ←10
  │ !! install_manager           1328L  1C   58m  CC=14     ←3
  │ !! autonomous                1220L  0C   76m  CC=7      ←3
  │ !! readiness                 1093L  3C   47m  CC=12     ←4
  │ !! handlers_drive            1083L  0C   35m  CC=12     ←3
  │ !! operator_pipeline         1065L  2C   46m  CC=14     ←0
  │ !! cycle_drive_retry         1043L  0C   40m  CC=18     ←3
  │ !! ide                       1020L  2C   59m  CC=13     ←52
  │ !! drive_orchestrator         965L  1C   56m  CC=14     ←1
  │ !! ide_reload                 901L  1C   39m  CC=12     ←5
  │ !! config_startup             894L  3C   42m  CC=13     ←5
  │ !! context                    876L  0C   32m  CC=12     ←7
  │ !! mcp_server_planfile        839L  0C   28m  CC=14     ←1
  │ !! operator_wup               830L  3C   39m  CC=12     ←2
  │ !! cycle_chat_activity        791L  1C   26m  CC=11     ←2
  │ !! photo_vql_target           790L  1C   45m  CC=14     ←1
  │ !! cycle                      788L  0C   17m  CC=11     ←1
  │ !! cli_parser                 781L  0C   21m  CC=1      ←0
  │ !! code2llm_discovery         752L  1C   31m  CC=13     ←4
  │ !! operator_plugin_wait       745L  0C   19m  CC=14     ←1
  │ !! scan_phase                 702L  0C   27m  CC=11     ←0
  │ !! decision_trace             700L  1C   24m  CC=12     ←4
  │ !! cycle_skip_conditions      694L  0C   31m  CC=14     ←2
  │ !! handlers_ack               693L  0C   27m  CC=13     ←3
  │ !! operator_runtime           690L  2C   30m  CC=15     ←9
  │ !! init                       676L  3C   18m  CC=12     ←2
  │ !! koru-autoloop.sh           676L  0C   17m  CC=0.0    ←1
  │ !! desktop_uri                665L  0C   28m  CC=15     ←4
  │ !! doctor_reporting_checks    652L  1C   27m  CC=13     ←0
  │ !! self_control               628L  3C   27m  CC=12     ←2
  │ !! dashboard_routes           607L  0C   35m  CC=9      ←2
  │ !! cli_shell                  606L  2C   31m  CC=19     ←0
  │ !! ide_doctor_cli             595L  0C   24m  CC=11     ←1
  │ !! operator_parser            585L  0C   15m  CC=8      ←2
  │ !! command_catalog            575L  1C    8m  CC=9      ←8
  │ !! cycle_orchestrator         550L  2C   11m  CC=15     ←1
  │ !! operator_loop_runner       545L  0C   11m  CC=7      ←1
  │ !! portal_input               536L  0C   25m  CC=14     ←0
  │ !! mcp_provision              532L  0C   28m  CC=10     ←5
  │ !! photo_vql_validation       527L  0C   32m  CC=13     ←1
  │ !! command_picker             520L  2C   27m  CC=14     ←2
  │ !! install_checks             520L  1C   22m  CC=10     ←0
  │ !! cli_direct_drive           513L  0C   23m  CC=10     ←0
  │ agent_backend_runtime      497L  10C   21m  CC=9      ←3
  │ context_render             496L  1C   21m  CC=14     ←4
  │ agents                     486L  1C   25m  CC=14     ←7
  │ runner                     486L  0C   14m  CC=9      ←3
  │ shared                     485L  0C   25m  CC=9      ←1
  │ !! doctor_project_health      481L  0C   21m  CC=15     ←0
  │ bootstrap                  477L  2C   21m  CC=10     ←2
  │ verification_engine        477L  7C   15m  CC=14     ←1
  │ install_plugin_cli         469L  0C   18m  CC=10     ←0
  │ ide_work                   468L  0C   17m  CC=12     ←6
  │ nxdo_discovery             452L  1C   24m  CC=14     ←4
  │ doctor                     450L  0C   16m  CC=1      ←0
  │ cycle_gate                 449L  0C   17m  CC=14     ←4
  │ drive                      449L  0C   12m  CC=11     ←0
  │ operator_processes         447L  4C   20m  CC=11     ←1
  │ bridge                     447L  0C   20m  CC=14     ←8
  │ photo_vql_drive            433L  1C   23m  CC=13     ←0
  │ cycle_post_drive           430L  0C   15m  CC=8      ←0
  │ doctor_chat_control        426L  1C   17m  CC=12     ←2
  │ topology                   425L  1C   18m  CC=9      ←9
  │ mcp_server_ide             424L  0C   11m  CC=7      ←0
  │ observability_dsl          424L  1C   35m  CC=9      ←7
  │ cycle_chat_activity_tickets   423L  0C   14m  CC=12     ←1
  │ post_run_verify            416L  2C   17m  CC=14     ←3
  │ autonomy_session           413L  0C   31m  CC=8      ←0
  │ cycle_config               404L  0C   11m  CC=12     ←2
  │ env                        401L  0C   19m  CC=12     ←8
  │ operator_loop_quick_actions   400L  0C   18m  CC=12     ←0
  │ photo_vql_user_guidance    395L  1C   30m  CC=9      ←1
  │ ticket                     394L  0C   25m  CC=12     ←13
  │ handlers_hello             392L  0C   13m  CC=12     ←0
  │ queue_clean                391L  2C   13m  CC=14     ←1
  │ command_scenario           390L  2C   19m  CC=8      ←4
  │ orchestrator               389L  1C   16m  CC=11     ←2
  │ portal_screencast          383L  1C    7m  CC=10     ←0
  │ invoke_handlers            379L  1C   24m  CC=6      ←0
  │ local_service              376L  1C   15m  CC=10     ←1
  │ photo_vql_monitor          376L  0C   15m  CC=14     ←5
  │ env2llm_registry           375L  0C   14m  CC=10     ←4
  │ operator_operator          368L  0C   20m  CC=8      ←0
  │ cli_command                366L  0C   24m  CC=6      ←0
  │ gc                         364L  2C   13m  CC=11     ←1
  │ server                     359L  1C   16m  CC=8      ←0
  │ calibration_validator      356L  0C   12m  CC=13     ←1
  │ photo_vql_llm_detect       356L  0C   20m  CC=11     ←1
  │ calibrate_cli              355L  0C   12m  CC=9      ←0
  │ app                        349L  1C   19m  CC=10     ←0
  │ tree                       342L  5C   19m  CC=10     ←4
  │ init_host_environment      341L  0C   18m  CC=14     ←1
  │ imgl_client                339L  0C   17m  CC=14     ←7
  │ tools                      336L  0C   22m  CC=11     ←2
  │ dashboard_projects         334L  0C   20m  CC=10     ←2
  │ activity_log               334L  0C   14m  CC=12     ←26
  │ lane_context               329L  1C   17m  CC=9      ←5
  │ cycle_chat_activity_analyzer   328L  1C   18m  CC=11     ←1
  │ lifecycle                  327L  2C   16m  CC=10     ←1
  │ control_commands           325L  0C   13m  CC=12     ←6
  │ doctor_autopilot_checks    325L  0C   25m  CC=14     ←1
  │ dashboard_tickets          322L  2C   17m  CC=10     ←1
  │ ticket_evidence            322L  3C   17m  CC=9      ←1
  │ gillm_client               319L  1C    5m  CC=5      ←2
  │ doctor_autopilot_debug     317L  1C   13m  CC=10     ←0
  │ handlers                   316L  0C   15m  CC=8      ←4
  │ strategies.json            315L  0C    0m  CC=0.0    ←0
  │ host_setup                 310L  0C   14m  CC=14     ←2
  │ cli_doctor                 308L  0C   14m  CC=11     ←0
  │ detector                   306L  0C   14m  CC=11     ←8
  │ protocol                   305L  3C   16m  CC=12     ←7
  │ operator_diagnostics       305L  0C    9m  CC=13     ←1
  │ photo_vql_guard            304L  1C   16m  CC=11     ←1
  │ tagi_integration           302L  2C   13m  CC=13     ←2
  │ structured_report          300L  1C    8m  CC=13     ←1
  │ cycle_queue_scan           300L  0C   10m  CC=11     ←1
  │ cli_tagi                   299L  0C   16m  CC=7      ←0
  │ ide_control_cli            295L  0C   18m  CC=12     ←1
  │ operator_daemon            295L  0C   11m  CC=10     ←2
  │ vdisplay_agent_bootstrap   294L  0C   17m  CC=12     ←3
  │ cli_tillm_setup            292L  0C   15m  CC=10     ←1
  │ local_manager_state        292L  4C   21m  CC=14     ←0
  │ environment                292L  3C    8m  CC=14     ←5
  │ wizard.js                  292L  0C   38m  CC=13     ←113
  │ plugin_router              291L  3C   19m  CC=13     ←0
  │ queue_cli_helpers          290L  0C   10m  CC=9      ←1
  │ operator_plugin            289L  0C   19m  CC=13     ←4
  │ runners                    286L  0C   12m  CC=12     ←2
  │ mcp_server_desktop_uri     282L  0C    9m  CC=1      ←0
  │ agent_backends             282L  3C   11m  CC=11     ←3
  │ cli_parser                 281L  0C    8m  CC=2      ←0
  │ cli_main                   281L  0C    6m  CC=14     ←0
  │ git_cli                    274L  0C   20m  CC=9      ←0
  │ environment_profile        271L  5C   11m  CC=9      ←4
  │ operator_process_guard     271L  3C   16m  CC=10     ←1
  │ browser_getdisplay         266L  1C   14m  CC=8      ←2
  │ !! cli_fleet                  266L  1C   13m  CC=15     ←1
  │ integrations               264L  1C    2m  CC=4      ←4
  │ cli_queue                  263L  0C    7m  CC=12     ←0
  │ policy                     262L  1C   10m  CC=9      ←3
  │ decision_engine            258L  4C   11m  CC=11     ←2
  │ client                     257L  1C   10m  CC=10     ←1
  │ cli_snapshot_lines         257L  0C   16m  CC=9      ←1
  │ orchestrator               256L  2C    9m  CC=9      ←0
  │ base                       254L  9C   10m  CC=2      ←1
  │ doctor_runtime_checks      254L  0C   14m  CC=12     ←2
  │ gillm_recovery             253L  0C    3m  CC=2      ←4
  │ local_manager_client       252L  2C   15m  CC=7      ←4
  │ dashboard_serve_utils      251L  1C   19m  CC=7      ←3
  │ doctor_plugin_console      251L  0C   10m  CC=11     ←0
  │ capture_mss                248L  1C   12m  CC=14     ←5
  │ operator_onboarding        245L  1C   11m  CC=10     ←1
  │ cli_snapshot               242L  2C    9m  CC=9      ←0
  │ decision_arbiter           241L  2C    9m  CC=9      ←1
  │ ide_install                241L  1C    6m  CC=9      ←1
  │ dashboard_serve            240L  1C   10m  CC=6      ←1
  │ interface_registry         239L  3C   15m  CC=8      ←7
  │ doctor_constants           237L  1C    0m  CC=0.0    ←0
  │ tillm_bridge               236L  0C   16m  CC=6      ←14
  │ planning_llm               235L  0C    7m  CC=5      ←0
  │ cli                        232L  0C   12m  CC=12     ←0
  │ mcp_server_env2llm         231L  0C   10m  CC=3      ←1
  │ obs_websocket              231L  1C   15m  CC=11     ←1
  │ dev_sync                   229L  1C    9m  CC=11     ←0
  │ cycle_planning             227L  0C    9m  CC=12     ←1
  │ ide_client                 224L  2C   13m  CC=13     ←1
  │ cycle_diagnostics          224L  0C    7m  CC=10     ←1
  │ planning_llm_prompts       222L  0C    6m  CC=8      ←1
  │ status                     221L  0C    8m  CC=12     ←0
  │ operator_plugin_runtime    220L  0C   11m  CC=11     ←2
  │ event_store                219L  4C   17m  CC=10     ←3
  │ checkpoint                 217L  0C   11m  CC=9      ←4
  │ ide                        216L  1C    6m  CC=10     ←1
  │ task_intake                214L  3C   13m  CC=4      ←1
  │ ide_operator_guidance      212L  0C   11m  CC=11     ←6
  │ scan_ticket_emission       211L  0C    6m  CC=11     ←1
  │ command_telemetry          210L  1C   11m  CC=13     ←0
  │ prompting                  209L  1C   12m  CC=8      ←4
  │ library                    207L  0C   19m  CC=9      ←1
  │ pointer_calibration        203L  0C    6m  CC=10     ←1
  │ gate                       202L  1C    5m  CC=12     ←1
  │ operator_loop_narration    201L  1C    9m  CC=7      ←0
  │ cli_topology               196L  0C    9m  CC=5      ←0
  │ templates                  194L  1C   12m  CC=9      ←1
  │ runtime_insights           192L  0C    7m  CC=9      ←1
  │ handlers_plugin_event      191L  1C    9m  CC=7      ←0
  │ server                     190L  1C    8m  CC=9      ←1
  │ scan_dedupe_policy         190L  0C    8m  CC=13     ←1
  │ models                     190L  2C    6m  CC=8      ←0
  │ doctor_autonomous_streams   189L  0C   11m  CC=9      ←0
  │ dashboard                  188L  0C   10m  CC=5      ←2
  │ redup_integration          188L  0C   10m  CC=3      ←2
  │ drive_result               185L  1C    8m  CC=12     ←0
  │ !! shell_drive_finalize       184L  0C    4m  CC=20     ←1
  │ openapi                    183L  0C    1m  CC=2      ←1
  │ cli_task                   183L  0C    5m  CC=11     ←0
  │ queue_phase                178L  0C    6m  CC=11     ←0
  │ !! daemon_cli                 178L  0C    7m  CC=15     ←0
  │ cli_auto                   176L  0C   11m  CC=11     ←1
  │ cli                        176L  0C    5m  CC=2      ←6
  │ diagnostics                175L  0C    8m  CC=8      ←4
  │ events                     174L  1C   11m  CC=7      ←1
  │ llm_reflect                173L  1C    5m  CC=8      ←2
  │ operator_loop_reporting    172L  0C    6m  CC=8      ←0
  │ openrouter                 169L  1C    3m  CC=8      ←2
  │ chat_history               166L  1C    6m  CC=13     ←2
  │ handoff                    166L  0C    2m  CC=11     ←0
  │ command_catalog_store      165L  1C   13m  CC=10     ←3
  │ dashboard_config           164L  1C   13m  CC=10     ←1
  │ application                164L  2C   11m  CC=3      ←0
  │ project                    160L  1C   11m  CC=7      ←1
  │ cli                        159L  0C   10m  CC=3      ←0
  │ config                     159L  1C    2m  CC=11     ←1
  │ __init__                   158L  0C    3m  CC=2      ←0
  │ project_pipeline           158L  0C    5m  CC=11     ←7
  │ dashboard_state            157L  0C    5m  CC=10     ←3
  │ desktop_preflight          156L  1C    8m  CC=8      ←2
  │ git_attribution            155L  1C    5m  CC=10     ←1
  │ audit                      154L  2C    6m  CC=6      ←1
  │ analyzer                   154L  1C   12m  CC=12     ←0
  │ doctor_cli                 153L  0C    9m  CC=8      ←1
  │ integration_ledger         152L  0C    5m  CC=5      ←0
  │ cli_global_control         150L  0C    6m  CC=11     ←0
  │ replay_parser              150L  0C   11m  CC=5      ←2
  │ ide_chat                   149L  1C    6m  CC=9      ←0
  │ semcod_tools               149L  1C    4m  CC=7      ←5
  │ providers_cli              148L  0C   10m  CC=13     ←1
  │ cli_imgl                   147L  0C    7m  CC=10     ←0
  │ deps_autorepair            145L  0C    8m  CC=11     ←3
  │ vscode_family              144L  1C    4m  CC=9      ←0
  │ strategy_prompt            142L  0C    3m  CC=6      ←2
  │ global_control             142L  0C    8m  CC=6      ←3
  │ operator_loop_interfaces   142L  0C   12m  CC=7      ←4
  │ cli                        141L  0C    7m  CC=6      ←0
  │ metadata                   136L  0C   10m  CC=5      ←2
  │ local_manager              136L  1C    6m  CC=5      ←1
  │ cli_replay                 135L  0C    4m  CC=8      ←0
  │ base                       133L  4C   10m  CC=4      ←0
  │ task_ticket                131L  0C    6m  CC=6      ←1
  │ loop                       131L  3C    4m  CC=12     ←1
  │ observability_writer       131L  0C    9m  CC=8      ←9
  │ replay_builders            131L  0C    9m  CC=3      ←3
  │ nlp2oql_bridge             130L  0C    5m  CC=7      ←1
  │ llx                        128L  1C    4m  CC=14     ←3
  │ cli_parser                 125L  0C    4m  CC=7      ←1
  │ scan_render                125L  0C    5m  CC=8      ←1
  │ doctor_plugin_bundle       123L  0C    6m  CC=8      ←0
  │ run_log                    123L  1C    7m  CC=4      ←1
  │ observability_events       122L  0C   10m  CC=3      ←3
  │ submit_strategy            122L  0C    7m  CC=11     ←3
  │ cli_events                 121L  0C    3m  CC=7      ←0
  │ mcp_server_dispatch        120L  0C    7m  CC=6      ←1
  │ application                120L  2C    4m  CC=12     ←0
  │ prompters                  120L  2C    9m  CC=11     ←0
  │ cli_init                   119L  0C    3m  CC=7      ←0
  │ prompts                    119L  1C    2m  CC=10     ←0
  │ cycle_trace                119L  0C    3m  CC=9      ←1
  │ application                119L  2C    6m  CC=5      ←0
  │ portal_capture             118L  1C    2m  CC=8      ←4
  │ ports                      118L  5C    4m  CC=1      ←0
  │ replay_execution           117L  0C    9m  CC=5      ←1
  │ dashboard_html             116L  0C    3m  CC=4      ←1
  │ registry                   116L  1C    6m  CC=9      ←3
  │ cli_gate                   116L  0C    2m  CC=5      ←0
  │ task_dedupe                116L  0C   10m  CC=12     ←1
  │ heal                       116L  1C    3m  CC=5      ←2
  │ drive_repair_policy        116L  1C    4m  CC=6      ←4
  │ cycle_events               115L  0C    6m  CC=14     ←1
  │ loop                       115L  0C    1m  CC=14     ←3
  │ replay_handlers            113L  2C    5m  CC=3      ←0
  │ autonomous_cycle           112L  0C    1m  CC=2      ←0
  │ session                    112L  2C    8m  CC=4      ←0
  │ planning_llm_parsing       111L  0C    7m  CC=7      ←1
  │ contexts                   111L  8C    0m  CC=0.0    ←0
  │ __init__                   111L  0C    0m  CC=0.0    ←0
  │ features                   110L  0C    4m  CC=6      ←2
  │ defaults                   109L  0C    2m  CC=1      ←2
  │ doctor_project_checks      108L  0C    4m  CC=7      ←0
  │ host_hooks                 106L  0C    3m  CC=2      ←0
  │ dotenv_loader              106L  0C    3m  CC=7      ←3
  │ ide_router                 105L  1C    2m  CC=10     ←4
  │ cli_trace                  105L  0C    3m  CC=11     ←0
  │ runtime                    104L  0C    5m  CC=2      ←7
  │ cycle_finalize             104L  0C    1m  CC=4      ←1
  │ web-app.json               104L  0C    0m  CC=0.0    ←0
  │ systemd_cli                103L  0C    4m  CC=6      ←0
  │ __init__                   103L  0C    2m  CC=2      ←0
  │ testql_bridge              102L  0C    5m  CC=7      ←1
  │ cycle_drive_outcome        102L  0C    1m  CC=11     ←1
  │ !! vdisplay_up_cli            102L  0C    2m  CC=15     ←0
  │ storage                    100L  0C    5m  CC=6      ←2
  │ fallback                   100L  1C    1m  CC=1      ←0
  │ drive_phase                 99L  0C    2m  CC=1      ←0
  │ read_model                  97L  1C    7m  CC=7      ←1
  │ __init__                    97L  0C    3m  CC=9      ←0
  │ operator_resources          96L  0C    1m  CC=4      ←0
  │ ide_control                 95L  1C    2m  CC=3      ←1
  │ __init__                    95L  2C    5m  CC=3      ←6
  │ locking                     94L  0C    5m  CC=5      ←3
  │ config                      94L  1C    3m  CC=4      ←4
  │ mcp_server                  94L  0C    0m  CC=0.0    ←0
  │ watch                       93L  0C    6m  CC=9      ←1
  │ replay_quick_actions        93L  0C    4m  CC=8      ←1
  │ cli_scan                    92L  0C    2m  CC=3      ←0
  │ application                 92L  2C    4m  CC=5      ←0
  │ cli_self                    91L  1C    4m  CC=5      ←0
  │ cli                         90L  0C    4m  CC=11     ←0
  │ base                        90L  4C    6m  CC=5      ←4
  │ events                      90L  0C    2m  CC=8      ←13
  │ dashboard_runtime           89L  0C    5m  CC=5      ←1
  │ transport                   88L  0C    4m  CC=9      ←2
  │ autoloop_cli                88L  0C    4m  CC=8      ←0
  │ types                       88L  5C    1m  CC=2      ←0
  │ cli_runtime_context         87L  0C    3m  CC=14     ←0
  │ agent_cli_helpers           87L  0C    3m  CC=10     ←1
  │ cli_gc                      87L  0C    2m  CC=1      ←0
  │ codex                       86L  1C    5m  CC=6      ←0
  │ dashboard                   86L  0C    8m  CC=3      ←1
  │ browser_capture             86L  0C    5m  CC=10     ←1
  │ cursor                      86L  1C    3m  CC=1      ←0
  │ !! env_session                 86L  0C    4m  CC=15     ←1
  │ envelope                    85L  1C    4m  CC=3      ←4
  │ cli_agent                   85L  0C    3m  CC=3      ←0
  │ planfile_handoff            85L  0C    3m  CC=2      ←2
  │ route                       85L  0C    3m  CC=10     ←1
  │ mcp_server_nlp2oql          84L  0C    3m  CC=1      ←0
  │ doctor_runner               84L  0C    3m  CC=4      ←2
  │ manage                      84L  0C    1m  CC=13     ←0
  │ mcp_server_runtime          83L  0C    6m  CC=1      ←1
  │ registry                    83L  0C    5m  CC=4      ←2
  │ sleep_phase                 83L  0C    1m  CC=4      ←1
  │ gc_cli_helpers              81L  0C    5m  CC=12     ←1
  │ env_flags                   81L  0C    4m  CC=5      ←1
  │ mesh                        79L  0C    5m  CC=8      ←2
  │ cli_serve                   79L  0C    2m  CC=1      ←0
  │ telemetry_snapshot          79L  0C    3m  CC=5      ←2
  │ scan_types                  78L  3C    3m  CC=2      ←1
  │ base                        78L  5C    3m  CC=4      ←0
  │ jetbrains                   78L  1C    0m  CC=0.0    ←0
  │ enums                       78L  3C    0m  CC=0.0    ←0
  │ agent                       76L  0C    5m  CC=11     ←1
  │ application                 76L  2C    4m  CC=3      ←0
  │ server                      76L  0C    3m  CC=5      ←1
  │ mcp_server_testql           75L  0C    3m  CC=2      ←0
  │ dashboard_observability     75L  0C    3m  CC=7      ←1
  │ cli                         75L  0C    4m  CC=5      ←0
  │ topology_cli                75L  1C    4m  CC=8      ←1
  │ application                 74L  2C    4m  CC=3      ←0
  │ shell_evidence              74L  0C    2m  CC=7      ←1
  │ cli_strategy                73L  0C    1m  CC=9      ←0
  │ tail_cli                    73L  0C    4m  CC=6      ←0
  │ photo_vql_config            72L  1C    5m  CC=3      ←10
  │ autodiag                    71L  0C    6m  CC=7      ←2
  │ policy_engine               71L  1C    2m  CC=6      ←1
  │ planning_llm_types          71L  5C    5m  CC=1      ←0
  │ transform                   70L  0C    4m  CC=12     ←2
  │ emitter                     70L  1C    5m  CC=6      ←4
  │ event_log_projection        70L  2C    5m  CC=6      ←0
  │ dashboard_context           69L  0C    4m  CC=5      ←1
  │ capture                     69L  1C    4m  CC=2      ←3
  │ schema                      69L  3C    1m  CC=1      ←0
  │ __init__                    69L  5C    0m  CC=0.0    ←0
  │ topology_post               68L  0C    1m  CC=14     ←1
  │ ollama                      68L  1C    4m  CC=2      ←0
  │ store_persistence           68L  0C    4m  CC=8      ←1
  │ antigravity                 68L  1C    3m  CC=1      ←0
  │ autopilot_status            68L  1C    2m  CC=10     ←11
  │ application                 68L  2C    3m  CC=4      ←0
  │ autonomous_readiness        68L  0C    0m  CC=0.0    ←0
  │ windsurf                    67L  1C    3m  CC=1      ←0
  │ local_manager               67L  0C    2m  CC=2      ←1
  │ heuristics                  67L  0C    3m  CC=6      ←2
  │ application                 66L  2C    3m  CC=1      ←0
  │ __init__                    66L  0C    0m  CC=0.0    ←0
  │ vscode                      65L  1C    3m  CC=1      ←0
  │ env_config                  65L  0C    3m  CC=1      ←1
  │ cli_bootstrap               65L  0C    2m  CC=5      ←0
  │ dashboard_http              64L  1C    6m  CC=4      ←0
  │ socket                      64L  0C    2m  CC=8      ←13
  │ qoder                       64L  1C    3m  CC=1      ←0
  │ wup_testql_compat           64L  0C    4m  CC=5      ←0
  │ cli_tools                   64L  0C    2m  CC=7      ←0
  │ __init__                    64L  5C    0m  CC=0.0    ←0
  │ freshness                   63L  0C    8m  CC=4      ←1
  │ render                      63L  0C    3m  CC=12     ←1
  │ cli_agent_backends          62L  0C    1m  CC=8      ←1
  │ doctor_render               62L  0C    3m  CC=8      ←1
  │ screencast_session          60L  0C    5m  CC=7      ←2
  │ store                       60L  0C    4m  CC=6      ←2
  │ utils                       60L  0C    3m  CC=5      ←3
  │ cli_local_serve             60L  0C    2m  CC=1      ←0
  │ cli_ide_router              59L  0C    1m  CC=3      ←0
  │ replay_types                59L  3C    2m  CC=2      ←0
  │ planning_llm_budget         59L  1C    7m  CC=3      ←1
  │ diagnose_vdisplay_cli       59L  0C    2m  CC=8      ←0
  │ zed                         59L  1C    0m  CC=0.0    ←0
  │ env                         58L  0C    7m  CC=5      ←10
  │ client                      58L  1C    7m  CC=6      ←0
  │ policy_decision             58L  1C    3m  CC=3      ←0
  │ client_helpers              57L  0C    2m  CC=4      ←1
  │ dashboard_plugin_logs       56L  0C    5m  CC=5      ←0
  │ cli_commands                56L  0C    3m  CC=3      ←1
  │ gpt                         55L  1C    4m  CC=1      ←0
  │ claude                      55L  1C    4m  CC=1      ←0
  │ protocol                    55L  1C    2m  CC=3      ←2
  │ planfile_ticket_note        55L  0C    2m  CC=5      ←2
  │ registry                    55L  0C    4m  CC=3      ←2
  │ __init__                    55L  0C    0m  CC=0.0    ←0
  │ library.json                55L  0C    0m  CC=0.0    ←0
  │ ml-research.json            55L  0C    0m  CC=0.0    ←0
  │ cli-tool.json               55L  0C    0m  CC=0.0    ←0
  │ mss                         54L  1C    4m  CC=8      ←0
  │ batch                       54L  1C    5m  CC=2      ←0
  │ mcp_server_transport        53L  0C    3m  CC=7      ←1
  │ replay_actions              53L  0C    0m  CC=0.0    ←0
  │ scaling                     52L  0C    3m  CC=6      ←5
  │ dashboard_parse             52L  0C    3m  CC=6      ←2
  │ prompts                     52L  0C    1m  CC=2      ←1
  │ vscodium                    51L  1C    3m  CC=1      ←0
  │ doctor_models               51L  2C    3m  CC=2      ←0
  │ operator_vdisplay_defaults    51L  0C    2m  CC=8      ←6
  │ log_contract                51L  0C    2m  CC=5      ←5
  │ state                       51L  1C    0m  CC=0.0    ←0
  │ testql                      50L  0C    3m  CC=6      ←1
  │ capture_probe               50L  0C    2m  CC=7      ←1
  │ shutdown                    50L  0C    1m  CC=3      ←0
  │ __init__                    50L  0C    0m  CC=0.0    ←0
  │ cli_loop                    49L  0C    1m  CC=7      ←0
  │ stdio_events                49L  0C    3m  CC=3      ←4
  │ drive_strategies            48L  2C    1m  CC=6      ←1
  │ __init__                    48L  5C    0m  CC=0.0    ←0
  │ protocol                    48L  0C    0m  CC=0.0    ←0
  │ __init__                    47L  0C    0m  CC=0.0    ←0
  │ portal_screenshot           46L  1C    4m  CC=2      ←0
  │ plugin_version              46L  0C    1m  CC=2      ←2
  │ refactor_planfile_handoff    46L  0C    1m  CC=6      ←1
  │ __init__                    46L  3C    0m  CC=0.0    ←0
  │ cli_tools                   45L  1C    5m  CC=3      ←0
  │ task_io                     45L  0C    3m  CC=4      ←2
  │ koruide_bridge              45L  0C    1m  CC=1      ←1
  │ verify_phase                45L  0C    1m  CC=5      ←0
  │ grim                        44L  1C    5m  CC=4      ←0
  │ ide_runtime                 44L  0C    2m  CC=5      ←1
  │ koru_queue_argv             44L  0C    1m  CC=5      ←1
  │ registry_service            43L  1C    9m  CC=2      ←1
  │ event_log_query             43L  1C    2m  CC=5      ←0
  │ __init__                    43L  2C    0m  CC=0.0    ←0
  │ cli_parser                  41L  0C    4m  CC=2      ←1
  │ control                     41L  0C    5m  CC=10     ←1
  │ cli_refactor_planfile_handoff    41L  0C    1m  CC=1      ←0
  │ cli_watch                   41L  0C    1m  CC=2      ←0
  │ planning_llm_runtime        41L  1C    5m  CC=3      ←1
  │ registry.json               41L  0C    0m  CC=0.0    ←0
  │ reflection_policy           40L  1C    2m  CC=9      ←1
  │ subprocess_runner           40L  0C    3m  CC=3      ←5
  │ __init__                    40L  0C    0m  CC=0.0    ←0
  │ scan_collection             39L  0C    1m  CC=3      ←0
  │ __init__                    39L  2C    0m  CC=0.0    ←0
  │ __init__                    39L  0C    0m  CC=0.0    ←0
  │ bootstrap                   38L  0C    3m  CC=3      ←2
  │ cli_context                 38L  0C    1m  CC=2      ←0
  │ __init__                    38L  0C    0m  CC=0.0    ←0
  │ mcp_server_cli              37L  0C    1m  CC=2      ←1
  │ codec                       37L  0C    2m  CC=1      ←2
  │ event_bus                   37L  1C    3m  CC=2      ←0
  │ __init__                    37L  2C    0m  CC=0.0    ←0
  │ __init__                    37L  0C    0m  CC=0.0    ←0
  │ local                       36L  0C    2m  CC=6      ←2
  │ __init__                    36L  3C    0m  CC=0.0    ←0
  │ planfile_queue              36L  0C    0m  CC=0.0    ←0
  │ store                       34L  0C    3m  CC=4      ←8
  │ __init__                    34L  2C    0m  CC=0.0    ←0
  │ __init__                    33L  0C    1m  CC=4      ←0
  │ __init__                    33L  4C    0m  CC=0.0    ←0
  │ __init__                    33L  2C    0m  CC=0.0    ←0
  │ registry                    32L  0C    2m  CC=1      ←1
  │ tasks                       32L  0C    1m  CC=1      ←9
  │ __init__                    32L  1C    0m  CC=0.0    ←0
  │ invoke                      31L  0C    1m  CC=4      ←2
  │ cli_parser                  31L  0C    1m  CC=1      ←1
  │ ide_status_systemmap        31L  0C    1m  CC=3      ←1
  │ cli_shim_builders           31L  0C    2m  CC=1      ←0
  │ human                       31L  0C    1m  CC=5      ←0
  │ utils                       30L  0C    2m  CC=4      ←3
  │ __init__                    30L  3C    0m  CC=0.0    ←0
  │ mcp_server_schema           29L  0C    1m  CC=1      ←0
  │ __init__                    29L  1C    0m  CC=0.0    ←0
  │ __init__                    29L  2C    0m  CC=0.0    ←0
  │ __init__                    29L  0C    0m  CC=0.0    ←0
  │ doctor_registry_checks      28L  0C    2m  CC=4      ←0
  │ cli                         27L  0C    1m  CC=5      ←0
  │ __init__                    27L  3C    0m  CC=0.0    ←0
  │ __init__                    26L  2C    0m  CC=0.0    ←0
  │ keys                        25L  0C    2m  CC=3      ←5
  │ prepare_vdisplay_cli        25L  0C    1m  CC=4      ←0
  │ __init__                    25L  0C    0m  CC=0.0    ←0
  │ __init__                    25L  0C    0m  CC=0.0    ←0
  │ daemon_storage              24L  0C    0m  CC=0.0    ←0
  │ __init__                    24L  0C    0m  CC=0.0    ←0
  │ __init__                    24L  0C    0m  CC=0.0    ←0
  │ config                      23L  0C    0m  CC=0.0    ←0
  │ dashboard_topology          22L  0C    2m  CC=1      ←1
  │ __init__                    22L  2C    0m  CC=0.0    ←0
  │ __init__                    22L  0C    0m  CC=0.0    ←0
  │ __init__                    22L  0C    0m  CC=0.0    ←0
  │ paths                       21L  0C    4m  CC=1      ←7
  │ __init__                    21L  1C    0m  CC=0.0    ←0
  │ __init__                    21L  2C    0m  CC=0.0    ←0
  │ __init__                    21L  0C    0m  CC=0.0    ←0
  │ cycle_bridge                20L  0C    1m  CC=2      ←0
  │ __init__                    20L  1C    0m  CC=0.0    ←0
  │ __init__                    20L  2C    0m  CC=0.0    ←0
  │ domain_event                19L  1C    1m  CC=2      ←0
  │ __init__                    19L  0C    0m  CC=0.0    ←0
  │ __init__                    19L  0C    0m  CC=0.0    ←0
  │ injector                    19L  0C    0m  CC=0.0    ←0
  │ os_injector                 19L  0C    0m  CC=0.0    ←0
  │ read_model                  17L  1C    1m  CC=1      ←0
  │ read_model                  17L  1C    1m  CC=1      ←0
  │ read_model                  17L  1C    1m  CC=1      ←0
  │ read_model                  17L  1C    1m  CC=1      ←0
  │ read_model                  17L  1C    1m  CC=1      ←0
  │ autonomous_cycle_common     16L  1C    2m  CC=3      ←10
  │ autonomous_cycle_chat_activity_config    16L  0C    9m  CC=3      ←0
  │ autonomous_cycle_chat_activity_text    16L  0C    6m  CC=12     ←0
  │ autonomous_diag_markers     16L  0C    1m  CC=1      ←3
  │ autonomous_plugin_lifecycle    16L  1C    1m  CC=9      ←1
  │ autonomous_up               16L  2C    5m  CC=7      ←0
  │ autonomous_env              16L  0C    1m  CC=1      ←0
  │ autonomous_cli_config       16L  0C   12m  CC=10     ←0
  │ read_model                  16L  1C    0m  CC=0.0    ←0
  │ read_model                  16L  1C    0m  CC=0.0    ←0
  │ injector_errors             16L  0C    0m  CC=0.0    ←0
  │ injector                    16L  0C    0m  CC=0.0    ←0
  │ os_injector                 16L  0C    0m  CC=0.0    ←0
  │ injector_backends           16L  0C    0m  CC=0.0    ←0
  │ autonomous_diagnostics      16L  0C    0m  CC=0.0    ←0
  │ autonomous_processes        16L  0C    0m  CC=0.0    ←0
  │ autonomous_startup          16L  0C    0m  CC=0.0    ←0
  │ autonomous_cycle_config     16L  0C    0m  CC=0.0    ←0
  │ autonomous_cycle_chat_activity_tickets    16L  0C    0m  CC=0.0    ←0
  │ autonomous_operator         16L  0C    0m  CC=0.0    ←0
  │ autonomous_loop_quick_actions    16L  0C    0m  CC=0.0    ←0
  │ autonomous_vdisplay_defaults    16L  0C    0m  CC=0.0    ←0
  │ autonomous_cycle_orchestrator    16L  0C    0m  CC=0.0    ←0
  │ autonomous_daemon           16L  0C    0m  CC=0.0    ←0
  │ autonomous_plugin_runtime    16L  0C    0m  CC=0.0    ←0
  │ autonomous_parser           16L  0C    0m  CC=0.0    ←0
  │ autonomous_plugin           16L  0C    0m  CC=0.0    ←0
  │ autonomous_loop_reporting    16L  0C    0m  CC=0.0    ←0
  │ autonomous_process_guard    16L  0C    0m  CC=0.0    ←0
  │ autonomous_cycle_drive_outcome    16L  0C    0m  CC=0.0    ←0
  │ autonomous_cycle_chat_activity_analyzer    16L  0C    0m  CC=0.0    ←0
  │ autonomous_loop_runner      16L  0C    0m  CC=0.0    ←0
  │ autonomous_cycle_bridge     16L  0C    0m  CC=0.0    ←0
  │ autonomous_cycle_chat_activity    16L  0C    0m  CC=0.0    ←0
  │ autonomous_loop_narration    16L  0C    0m  CC=0.0    ←0
  │ autonomous_cycle_drive_retry    16L  0C    0m  CC=0.0    ←0
  │ autonomous_plugin_wait      16L  0C    0m  CC=0.0    ←0
  │ autonomous_loop_interfaces    16L  0C    0m  CC=0.0    ←0
  │ autonomous_resources        16L  0C    0m  CC=0.0    ←0
  │ autonomous_cycle_post_drive    16L  0C    0m  CC=0.0    ←0
  │ autonomous_wup              16L  0C    0m  CC=0.0    ←0
  │ autonomous_runtime          16L  0C    0m  CC=0.0    ←0
  │ autonomous_cycle_skip_conditions    16L  0C    0m  CC=0.0    ←0
  │ autonomous_onboarding       16L  0C    0m  CC=0.0    ←0
  │ autonomous_cycle_gate       16L  0C    0m  CC=0.0    ←0
  │ daemon                      16L  0C    0m  CC=0.0    ←0
  │ mcp                         15L  0C    1m  CC=2      ←1
  │ __init__                    14L  1C    0m  CC=0.0    ←0
  │ __init__                    14L  1C    0m  CC=0.0    ←0
  │ commands                    14L  0C    0m  CC=0.0    ←0
  │ parsers                     14L  0C    0m  CC=0.0    ←0
  │ task_models                 13L  1C    0m  CC=0.0    ←0
  │ __init__                    13L  0C    0m  CC=0.0    ←0
  │ imgl_autodiag               13L  0C    0m  CC=0.0    ←0
  │ __init__                    12L  0C    0m  CC=0.0    ←0
  │ __init__                    12L  0C    0m  CC=0.0    ←0
  │ __main__                    12L  0C    0m  CC=0.0    ←0
  │ __main__                    12L  0C    0m  CC=0.0    ←0
  │ __init__                    12L  0C    0m  CC=0.0    ←0
  │ __init__                    11L  0C    0m  CC=0.0    ←0
  │ drive_policy                11L  0C    0m  CC=0.0    ←0
  │ _service_factory            10L  0C    1m  CC=1      ←1
  │ startup_phase               10L  0C    1m  CC=1      ←1
  │ client                      10L  0C    0m  CC=0.0    ←0
  │ serve                        9L  0C    0m  CC=0.0    ←0
  │ mcp_server                   9L  0C    0m  CC=0.0    ←0
  │ __init__                     9L  0C    0m  CC=0.0    ←0
  │ __init__                     9L  0C    0m  CC=0.0    ←0
  │ config                       9L  0C    0m  CC=0.0    ←0
  │ host_setup                   9L  0C    0m  CC=0.0    ←0
  │ ide                          9L  0C    0m  CC=0.0    ←0
  │ audit                        9L  0C    0m  CC=0.0    ←0
  │ plugin_installer             9L  0C    0m  CC=0.0    ←0
  │ __init__                     9L  0C    0m  CC=0.0    ←0
  │ autonomous_drive_retry_policy     8L  0C   10m  CC=13     ←1
  │ __init__                     8L  0C    0m  CC=0.0    ←0
  │ autonomous_auto_pipeline     8L  0C    0m  CC=0.0    ←0
  │ autonomous_submit_strategy     8L  0C    0m  CC=0.0    ←0
  │ autonomous_checkpoint        8L  0C    0m  CC=0.0    ←0
  │ __init__                     8L  0C    0m  CC=0.0    ←0
  │ __init__                     7L  0C    0m  CC=0.0    ←0
  │ cli_ide                      7L  0C    0m  CC=0.0    ←0
  │ __init__                     7L  0C    0m  CC=0.0    ←0
  │ __init__                     7L  0C    0m  CC=0.0    ←0
  │ __init__                     7L  0C    0m  CC=0.0    ←0
  │ __init__                     7L  0C    0m  CC=0.0    ←0
  │ __init__                     6L  0C    0m  CC=0.0    ←0
  │ __init__                     6L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     5L  0C    0m  CC=0.0    ←0
  │ __init__                     3L  0C    0m  CC=0.0    ←0
  │ __init__                     3L  0C    0m  CC=0.0    ←0
  │ __init__                     3L  0C    0m  CC=0.0    ←0
  │ __init__                     3L  0C    0m  CC=0.0    ←0
  │ __init__                     1L  0C    0m  CC=0.0    ←0
  │ !! cli                          0L  0C   25m  CC=17     ←0
  │ __init__                     0L  0C    0m  CC=0.0    ←0
  │
  packages/                       CC̄=3.9    ←in:0  →out:0
  │ !! cli                       3786L  3C  202m  CC=16     ←3
  │ !! pipeline                  1039L  2C   42m  CC=9      ←0
  │ !! cli_calibration            683L  0C   26m  CC=13     ←2
  │ !! diagnostics                504L  0C   27m  CC=14     ←1
  │ cli                        347L  0C   23m  CC=7      ←0
  │ pb_codec                   323L  0C   34m  CC=6      ←1
  │ parser                     238L  0C   23m  CC=9      ←0
  │ ecosystem                  225L  2C   11m  CC=14     ←1
  │ cli                        208L  0C   13m  CC=6      ←0
  │ http_handlers              199L  0C   16m  CC=9      ←1
  │ cli                        197L  0C    8m  CC=5      ←3
  │ ide_detection              188L  0C   12m  CC=12     ←0
  │ service                    186L  1C   14m  CC=5      ←1
  │ cli                        183L  0C   11m  CC=6      ←0
  │ registry                   177L  0C    3m  CC=5      ←2
  │ events                     171L  2C    9m  CC=4      ←0
  │ events                     169L  2C    7m  CC=8      ←1
  │ service                    164L  1C    5m  CC=3      ←1
  │ pb_codec                   163L  0C   18m  CC=5      ←8
  │ bus                        163L  0C    7m  CC=9      ←0
  │ argv                       160L  0C   14m  CC=6      ←2
  │ serializer                 154L  0C   19m  CC=5      ←0
  │ cli_parser                 154L  0C    9m  CC=1      ←1
  │ heuristic                  148L  0C    8m  CC=13     ←5
  │ registry                   146L  0C   10m  CC=14     ←5
  │ probe                      136L  0C    8m  CC=13     ←1
  │ grammar                    132L  0C   13m  CC=7      ←5
  │ client                     131L  2C   13m  CC=11     ←3
  │ cli_checks                 128L  0C    9m  CC=11     ←1
  │ llm_backend                128L  2C    4m  CC=9      ←1
  │ codegen                    123L  0C    5m  CC=12     ←2
  │ codegen                    121L  0C    5m  CC=9      ←0
  │ __init__                   118L  1C    8m  CC=6      ←3
  │ projector                  115L  0C    7m  CC=9      ←1
  │ models                     108L  3C    6m  CC=8      ←0
  │ decode                     106L  0C   10m  CC=7      ←4
  │ systemd_unit               105L  0C    4m  CC=9      ←1
  │ lane                        93L  0C    6m  CC=5      ←2
  │ nlp2uri                     92L  1C    3m  CC=14     ←5
  │ llm_backend                 92L  2C    3m  CC=9      ←2
  │ command.proto               90L  0C    0m  CC=0.0    ←0
  │ nlp2uri                     85L  1C    3m  CC=13     ←0
  │ bus                         84L  0C    3m  CC=11     ←18
  │ repair_registry             84L  0C    1m  CC=1      ←1
  │ http_server                 83L  1C    5m  CC=2      ←0
  │ cli                         82L  0C    5m  CC=4      ←0
  │ conversation_client         82L  2C    6m  CC=9      ←0
  │ cli                         82L  0C    5m  CC=4      ←0
  │ query                       80L  1C    8m  CC=5      ←0
  │ schema_registry             79L  0C    5m  CC=4      ←3
  │ ui                          76L  0C    4m  CC=12     ←1
  │ conversation_test_api       75L  3C    5m  CC=10     ←0
  │ cli                         75L  0C    2m  CC=7      ←7
  │ openrouter_config           75L  0C    6m  CC=7      ←3
  │ app                         75L  0C    1m  CC=1      ←1
  │ app                         74L  0C    1m  CC=1      ←0
  │ daemon_ctl                  73L  0C    3m  CC=9      ←1
  │ llm                         67L  0C    2m  CC=9      ←3
  │ decode                      65L  0C    3m  CC=9      ←0
  │ control                     64L  0C    5m  CC=6      ←2
  │ domain                      64L  5C    0m  CC=0.0    ←0
  │ cli                         63L  0C    1m  CC=10     ←0
  │ cli                         62L  0C    1m  CC=11     ←0
  │ server                      62L  1C    6m  CC=2      ←6
  │ server                      62L  1C    6m  CC=2      ←0
  │ command_pb2                 62L  0C    0m  CC=0.0    ←0
  │ cli                         61L  0C    1m  CC=12     ←0
  │ codec                       55L  0C    7m  CC=2      ←4
  │ codec                       55L  0C    7m  CC=2      ←0
  │ cli_terminal                55L  0C    7m  CC=3      ←0
  │ store                       55L  1C    6m  CC=6      ←0
  │ events                      54L  1C    3m  CC=7      ←2
  │ grammar                     54L  0C    0m  CC=0.0    ←0
  │ __init__                    54L  0C    0m  CC=0.0    ←0
  │ uri                         53L  0C    6m  CC=7      ←3
  │ uri                         52L  0C    6m  CC=7      ←1
  │ runner                      50L  0C    3m  CC=5      ←0
  │ socket_path                 47L  0C    2m  CC=8      ←1
  │ to_dsl                      46L  0C    1m  CC=11     ←0
  │ apply                       46L  1C    2m  CC=2      ←0
  │ command_pb2                 46L  0C    0m  CC=0.0    ←0
  │ to_dsl                      45L  0C    2m  CC=7      ←1
  │ schema_registry             44L  0C    4m  CC=4      ←8
  │ command                     44L  0C    1m  CC=6      ←0
  │ query                       44L  0C    1m  CC=6      ←0
  │ paths                       43L  0C    6m  CC=5      ←5
  │ command.proto               43L  0C    0m  CC=0.0    ←0
  │ result_pb2                  39L  0C    0m  CC=0.0    ←0
  │ __init__                    39L  0C    0m  CC=0.0    ←0
  │ result_pb2                  39L  0C    0m  CC=0.0    ←0
  │ commands                    38L  3C    0m  CC=0.0    ←0
  │ pyproject.toml              37L  0C    0m  CC=0.0    ←0
  │ result                      36L  1C    1m  CC=1      ←0
  │ rewrite                     36L  0C    1m  CC=4      ←2
  │ http_util                   36L  0C    3m  CC=5      ←2
  │ pyproject.toml              36L  0C    0m  CC=0.0    ←0
  │ editor_cli                  35L  0C    2m  CC=9      ←1
  │ apply                       34L  0C    2m  CC=7      ←2
  │ __init__                    34L  0C    0m  CC=0.0    ←0
  │ shell                       33L  0C    1m  CC=9      ←2
  │ shell                       33L  0C    1m  CC=9      ←0
  │ pyproject.toml              32L  0C    0m  CC=0.0    ←0
  │ tools                       30L  0C    4m  CC=2      ←0
  │ tools                       30L  0C    4m  CC=2      ←0
  │ models                      29L  3C    0m  CC=0.0    ←0
  │ pyproject.toml              29L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              29L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              29L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              29L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              29L  0C    0m  CC=0.0    ←0
  │ result                      28L  1C    1m  CC=1      ←0
  │ __init__                    28L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              28L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              28L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              28L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              27L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              27L  0C    0m  CC=0.0    ←0
  │ cli                         26L  0C    1m  CC=4      ←0
  │ cli                         26L  0C    1m  CC=4      ←0
  │ cli                         24L  0C    1m  CC=2      ←0
  │ cli                         24L  0C    1m  CC=2      ←0
  │ __init__                    24L  0C    0m  CC=0.0    ←0
  │ runtime                     23L  0C    1m  CC=1      ←1
  │ pyproject.toml              23L  0C    0m  CC=0.0    ←0
  │ result.proto                23L  0C    0m  CC=0.0    ←0
  │ result.proto                22L  0C    0m  CC=0.0    ←0
  │ pyproject.toml              22L  0C    0m  CC=0.0    ←0
  │ run                         19L  0C    1m  CC=2      ←2
  │ control                     18L  0C    2m  CC=2      ←1
  │ __init__                    18L  0C    0m  CC=0.0    ←0
  │ __init__                    18L  0C    0m  CC=0.0    ←0
  │ auto.schema.json            17L  0C    0m  CC=0.0    ←0
  │ control                     15L  0C    2m  CC=1      ←4
  │ __init__                    15L  0C    0m  CC=0.0    ←0
  │ ui_type.schema.json         14L  0C    0m  CC=0.0    ←0
  │ repair_run.schema.json      13L  0C    0m  CC=0.0    ←0
  │ ui_key.schema.json          13L  0C    0m  CC=0.0    ←0
  │ calibration.schema.json     13L  0C    0m  CC=0.0    ←0
  │ text.schema.json            13L  0C    0m  CC=0.0    ←0
  │ lane.schema.json            13L  0C    0m  CC=0.0    ←0
  │ ui_nl.schema.json           13L  0C    0m  CC=0.0    ←0
  │ ui_click.schema.json        13L  0C    0m  CC=0.0    ←0
  │ run                         12L  0C    1m  CC=1      ←0
  │ query_repair_history.schema.json    12L  0C    0m  CC=0.0    ←0
  │ ui_capture.schema.json      12L  0C    0m  CC=0.0    ←0
  │ doctor.schema.json          12L  0C    0m  CC=0.0    ←0
  │ chat.schema.json            12L  0C    0m  CC=0.0    ←0
  │ repair_run.schema.json      12L  0C    0m  CC=0.0    ←0
  │ validate_lane.schema.json    11L  0C    0m  CC=0.0    ←0
  │ query_lane_status.schema.json    11L  0C    0m  CC=0.0    ←0
  │ resolve.schema.json         11L  0C    0m  CC=0.0    ←0
  │ ensure.schema.json          10L  0C    0m  CC=0.0    ←0
  │ status.schema.json          10L  0C    0m  CC=0.0    ←0
  │ env.schema.json             10L  0C    0m  CC=0.0    ←0
  │ query.schema.json           10L  0C    0m  CC=0.0    ←0
  │ sync.schema.json            10L  0C    0m  CC=0.0    ←0
  │ repair_history.schema.json     9L  0C    0m  CC=0.0    ←0
  │ __init__                     9L  0C    0m  CC=0.0    ←0
  │ __init__                     7L  0C    0m  CC=0.0    ←0
  │ engine                       6L  0C    0m  CC=0.0    ←0
  │ generate-proto.sh            6L  0C    0m  CC=0.0    ←0
  │ engine                       6L  0C    0m  CC=0.0    ←0
  │ generate-proto.sh            6L  0C    0m  CC=0.0    ←0
  │ koruenv-lane.sh              4L  0C    0m  CC=0.0    ←0
  │ __init__                     3L  0C    0m  CC=0.0    ←0
  │ __init__                     1L  0C    0m  CC=0.0    ←0
  │ __init__                     1L  0C    0m  CC=0.0    ←0
  │
  scripts/                        CC̄=2.8    ←in:0  →out:77  !! split
  │ koru-gate-capture          314L  0C   14m  CC=9      ←0
  │ scaffold-ide-plugin        310L  0C    7m  CC=7      ←0
  │ write-ide-plugin-tests     276L  0C    3m  CC=3      ←0
  │ planfile-sync-todo         251L  0C   12m  CC=14     ←0
  │ koru-pytest.sh             248L  0C    6m  CC=0.0    ←0
  │ autopilot-ide-autodetect-smoke.sh   182L  1C    4m  CC=0.0    ←0
  │ sync-plugin-version        149L  0C    4m  CC=7      ←0
  │ sync-plugin-build          136L  0C    6m  CC=13     ←0
  │ koru-semcod-gates.sh       135L  0C    2m  CC=0.0    ←0
  │ koru-soak-monitor.sh       129L  0C    6m  CC=0.0    ←0
  │ bump_version               128L  0C    6m  CC=8      ←0
  │ !! e2e_envmap_koru            128L  0C    2m  CC=22     ←0
  │ sync-vscode-plugin-version   125L  0C    6m  CC=2      ←0
  │ koru-autopilot-lanes.sh    125L  0C    5m  CC=0.0    ←0
  │ koru-queue-diagnose.sh     124L  0C    0m  CC=0.0    ←0
  │ koru-soak-stop.sh          123L  0C    5m  CC=0.0    ←0
  │ validate_testql_conversations   109L  0C    5m  CC=12     ←0
  │ sync-plugin-shared         108L  0C    2m  CC=7      ←0
  │ koru-soak-status.sh        100L  0C    6m  CC=0.0    ←0
  │ koru-autoloop-reset-diag-markers.sh    96L  0C    1m  CC=0.0    ←0
  │ docker-ide-matrix.sh        92L  0C    2m  CC=0.0    ←0
  │ planfile-export-prompt.sh    81L  0C    2m  CC=0.0    ←0
  │ docker-ide-matrix-entrypoint.sh    75L  0C    1m  CC=0.0    ←0
  │ !! run_testql_conversations    68L  0C    2m  CC=16     ←0
  │ _koru_autodiag_filter_tickets    55L  0C    1m  CC=12     ←0
  │ test-browser-stack.sh       48L  0C    0m  CC=0.0    ←0
  │ install-imgl-bridge.sh      45L  0C    0m  CC=0.0    ←0
  │ koru-soak-start.sh          39L  0C    1m  CC=0.0    ←0
  │ simulate-multi-lane-docker.sh    31L  0C    0m  CC=0.0    ←0
  │ diagnose-vdisplay-llm.sh    22L  0C    0m  CC=0.0    ←0
  │ activate-koru-dev.sh        18L  0C    0m  CC=0.0    ←0
  │ koru-from-repo.sh           10L  0C    0m  CC=0.0    ←0
  │ koru-autopilot-lane.sh      10L  0C    0m  CC=0.0    ←0
  │
  plugins/                        CC̄=2.4    ←in:0  →out:0
  │ !! bridge-submit.ts           992L  1C   72m  CC=13     ←1
  │ !! bridge-paste.ts            805L  1C   62m  CC=14     ←0
  │ !! bridge-submit-focus.test.ts   575L  0C   29m  CC=3      ←0
  │ !! bridge-fastpath.ts         504L  1C   26m  CC=7      ←0
  │ probe-ladder.ts            452L  3C   45m  CC=12     ←0
  │ cursor.test.ts             439L  0C   32m  CC=11     ←0
  │ probe-ladder.ts            432L  3C   43m  CC=10     ←0
  │ bridge-network.ts          416L  1C   55m  CC=10     ←3
  │ chat-history-watcher.test.ts   416L  0C   35m  CC=5      ←0
  │ bridge-focus-strategy.ts   401L  1C   31m  CC=9      ←0
  │ chat-history-watcher.test.ts   355L  0C   30m  CC=3      ←0
  │ chat-history-watcher.test.ts   353L  0C   30m  CC=3      ←0
  │ chat-history-watcher.test.ts   353L  0C   30m  CC=3      ←0
  │ chat-history-watcher.test.ts   353L  0C   30m  CC=3      ←0
  │ cursor.ts                  326L  0C   19m  CC=14     ←0
  │ probe-ladder.test.ts       315L  0C   38m  CC=5      ←0
  │ KoruAutopilotService.kt    264L  1C    6m  CC=0.0    ←0
  │ ack-payload.ts             260L  0C   31m  CC=12     ←3
  │ bridge-focus-core.ts       239L  1C   33m  CC=5      ←25
  │ package.json               213L  0C    0m  CC=0.0    ←0
  │ package.json               202L  0C    0m  CC=0.0    ←0
  │ autopilot-bridge.ts        200L  1C   20m  CC=8      ←7
  │ chat-history-watcher.ts    197L  2C   11m  CC=10     ←0
  │ package.json               194L  0C    0m  CC=0.0    ←0
  │ package.json               193L  0C    0m  CC=0.0    ←0
  │ step-decisions.ts          192L  1C   20m  CC=9      ←0
  │ bridge-ack.ts              190L  1C   13m  CC=10     ←0
  │ package.json               188L  0C    0m  CC=0.0    ←0
  │ step-decisions.test.ts     176L  0C   14m  CC=2      ←0
  │ step-decisions.test.ts     162L  0C   12m  CC=2      ←0
  │ bridge-helpers.ts          159L  0C   17m  CC=9      ←0
  │ cursor-bubble-adapter.ts   159L  1C   21m  CC=11     ←14
  │ step-decisions.test.ts     148L  0C   12m  CC=2      ←0
  │ vscode-chat-session-adapter.ts   146L  2C   22m  CC=10     ←0
  │ command-catalog.ts         136L  1C    7m  CC=6      ←0
  │ vscodium.test.ts           130L  0C   15m  CC=3      ←0
  │ command-catalog.ts         126L  1C    7m  CC=4      ←0
  │ command-catalog.ts         126L  1C    7m  CC=4      ←0
  │ dispatch-plan.test.ts      118L  0C   12m  CC=4      ←0
  │ ide-strategy.ts            117L  2C    0m  CC=0.0    ←0
  │ probe-ladder.test.ts       115L  0C   16m  CC=3      ←0
  │ ChatInjector.kt            112L  0C    1m  CC=0.0    ←0
  │ probe-ladder.test.ts       108L  0C   15m  CC=3      ←0
  │ windsurf.ts                108L  0C    8m  CC=6      ←0
  │ vscodium.ts                106L  0C   11m  CC=9      ←0
  │ bridge-watcher.ts           91L  1C   10m  CC=10     ←0
  │ vscode.ts                   91L  0C   11m  CC=8      ←0
  │ bridge-focus.ts             82L  1C    9m  CC=6      ←0
  │ bridge-config.ts            80L  1C    7m  CC=9      ←0
  │ bridge-commands.ts          77L  1C   16m  CC=7      ←0
  │ qoder.ts                    77L  0C    9m  CC=6      ←0
  │ probe-ladder.test.ts        77L  0C   10m  CC=2      ←0
  │ socketPath.ts               75L  0C   15m  CC=10     ←0
  │ bridge-base-class.ts        69L  1C   10m  CC=3      ←0
  │ probe-ladder.test.ts        69L  0C    9m  CC=2      ←0
  │ command-catalog.test.ts     69L  0C    7m  CC=2      ←0
  │ koru.yaml                   69L  0C    0m  CC=0.0    ←0
  │ antigravity.ts              68L  0C    8m  CC=5      ←0
  │ command-catalog.test.ts     65L  0C    6m  CC=2      ←0
  │ bridge-base.ts              64L  1C    6m  CC=5      ←0
  │ ide-control-strategy.ts     64L  1C    2m  CC=4      ←0
  │ registry.ts                 63L  0C    7m  CC=6      ←0
  │ extension-wrapper.ts        57L  2C    3m  CC=4      ←0
  │ index.ts                    57L  0C    0m  CC=0.0    ←0
  │ command-catalog.test.ts     53L  0C    6m  CC=2      ←0
  │ extension.ts                53L  0C    6m  CC=7      ←0
  │ ack-payload.test.ts         52L  0C    7m  CC=4      ←0
  │ version-reconnect.test.ts    52L  0C    4m  CC=2      ←0
  │ registry.ts                 49L  0C    7m  CC=6      ←0
  │ build.gradle.kts            49L  0C    4m  CC=0.0    ←0
  │ extension.ts                47L  0C    3m  CC=1      ←0
  │ registry.ts                 42L  0C    7m  CC=6      ←1
  │ extension.ts                42L  0C    3m  CC=1      ←0
  │ registry.ts                 42L  0C    7m  CC=6      ←0
  │ registry.ts                 42L  0C    7m  CC=6      ←0
  │ extension.ts                40L  0C    3m  CC=1      ←0
  │ antigravity-fastpath.test.ts    40L  0C    8m  CC=2      ←0
  │ antigravity-fastpath.test.ts    39L  0C    8m  CC=2      ←0
  │ host-click-submit.test.ts    39L  0C    6m  CC=2      ←0
  │ host-click-submit.ts        35L  0C    7m  CC=6      ←0
  │ submit-match.ts             35L  0C    8m  CC=10     ←0
  │ extension.ts                34L  0C    3m  CC=1      ←0
  │ types.ts                    33L  1C    0m  CC=0.0    ←0
  │ SocketPath.kt               33L  0C    0m  CC=0.0    ←0
  │ chat-history-types.ts       32L  3C    0m  CC=0.0    ←0
  │ cursor-composer-paste.ts    31L  0C    5m  CC=4      ←0
  │ chat-history-adapters.ts    31L  0C    1m  CC=2      ←0
  │ chat-history-paths.ts       29L  0C    5m  CC=4      ←0
  │ dispatch-plan.ts            26L  1C    1m  CC=7      ←0
  │ chat-history-adapters.ts    24L  0C    1m  CC=2      ←0
  │ chat-history-adapters.ts    24L  0C    1m  CC=2      ←0
  │ plugin.xml                  24L  0C    0m  CC=0.0    ←0
  │ version-reconnect.ts        22L  0C    4m  CC=7      ←0
  │ operator-hints.ts           22L  0C    4m  CC=2      ←0
  │ chat-history-adapters.ts    21L  0C    1m  CC=2      ←0
  │ chat-history-adapters.ts    21L  0C    1m  CC=3      ←0
  │ unsupported-chat-adapter.ts    19L  1C    2m  CC=1      ←0
  │ antigravity-fastpath.ts     18L  0C    2m  CC=3      ←0
  │ extension.test.ts           18L  0C    2m  CC=2      ←0
  │ tsconfig.json               15L  0C    0m  CC=0.0    ←0
  │ vscodium-host.ts            10L  0C    2m  CC=5      ←0
  │ KoruAutopilotReconnectAction.kt    10L  1C    0m  CC=0.0    ←0
  │ package.json                10L  0C    0m  CC=0.0    ←0
  │ settings.gradle.kts          8L  0C    2m  CC=0.0    ←0
  │ bridge-handle.ts             8L  1C    0m  CC=0.0    ←0
  │ index.ts                     8L  0C    0m  CC=0.0    ←0
  │ gradle.properties            6L  0C    0m  CC=0.0    ←0
  │ cursor-bubble-adapter.ts     1L  0C    0m  CC=0.0    ←0
  │ vscode-chat-session-adapter.ts     1L  0C    0m  CC=0.0    ←0
  │ chat-history-watcher.ts      1L  0C    0m  CC=0.0    ←0
  │
  lucy/                           CC̄=2.3    ←in:0  →out:0
  │ main.go                     83L  1C    5m  CC=4      ←0
  │ main.rs                     48L  0C    1m  CC=4      ←0
  │ placeholder_test.go         10L  0C    1m  CC=2      ←0
  │
  examples/                       CC̄=2.2    ←in:0  →out:12  !! split
  │ bootstrap.planfile.yaml    425L  0C    0m  CC=0.0    ←0
  │ run.sh                     121L  0C    3m  CC=0.0    ←1
  │ remote_orchestration_demo    69L  0C    1m  CC=9      ←0
  │ run-e2e.sh                  43L  0C    0m  CC=0.0    ←0
  │ gitlab-ci.example.yml       41L  0C    0m  CC=0.0    ←0
  │ docker-compose-remote-mesh.yml    38L  0C    0m  CC=0.0    ←0
  │ browser-dom.testql.toon.yaml    30L  0C    0m  CC=0.0    ←0
  │ e2e.sh                      26L  0C    0m  CC=0.0    ←0
  │ e2e.sh                      26L  0C    0m  CC=0.0    ←0
  │ e2e.sh                      21L  0C    0m  CC=0.0    ←0
  │ e2e.sh                      20L  0C    0m  CC=0.0    ←0
  │ e2e.sh                      19L  0C    0m  CC=0.0    ←0
  │ e2e.sh                      15L  0C    0m  CC=0.0    ←0
  │ e2e-docker.sh               11L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml           8L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml           7L  0C    0m  CC=0.0    ←0
  │ run-docker.sh                7L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml           7L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml           7L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml           7L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml           7L  0C    0m  CC=0.0    ←0
  │
  docker/                         CC̄=2.2    ←in:0  →out:0
  │ smoke                      141L  0C    8m  CC=4      ←0
  │ Dockerfile                  61L  0C    0m  CC=0.0    ←0
  │ run.sh                      58L  0C    0m  CC=0.0    ←0
  │ entrypoint-x11.sh           35L  0C    0m  CC=0.0    ←0
  │
  ./                              CC̄=2.0    ←in:0  →out:0
  │ !! tree.txt                  2722L  0C    0m  CC=0.0    ←0
  │ !! ui.vql.json               1946L  0C    0m  CC=0.0    ←0
  │ !! planfile.yaml             1391L  0C    0m  CC=0.0    ←0
  │ !! Taskfile.yml               922L  0C    0m  CC=0.0    ←0
  │ !! goal.yaml                  547L  0C    0m  CC=0.0    ←0
  │ pyproject.toml             369L  0C    0m  CC=0.0    ←0
  │ Makefile                   276L  0C    0m  CC=0.0    ←0
  │ gillm_defs.txt             195L  0C    0m  CC=0.0    ←0
  │ koru.yaml                  163L  0C    0m  CC=0.0    ←0
  │ pipeline.yaml              142L  0C    0m  CC=0.0    ←0
  │ project.sh                 140L  0C    1m  CC=0.0    ←144
  │ wup.yaml                   113L  0C    0m  CC=0.0    ←0
  │ wup-shell-only.yaml        110L  0C    0m  CC=0.0    ←0
  │ prefact.yaml                93L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml          92L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  73L  0C    0m  CC=0.0    ←0
  │ sllm_defs.txt               45L  0C    0m  CC=0.0    ←0
  │ regix.yaml                  43L  0C    0m  CC=0.0    ←0
  │ check_dups                  27L  0C    1m  CC=4      ←0
  │ package.json                25L  0C    0m  CC=0.0    ←0
  │ .pretest.yml                17L  0C    0m  CC=0.0    ←0
  │ nlp2uri.yaml                 8L  0C    0m  CC=0.0    ←0
  │ screen.capture.json          6L  0C    0m  CC=0.0    ←0
  │ output.txt                   3L  0C    0m  CC=0.0    ←0
  │ todo.txt                     3L  0C    0m  CC=0.0    ←0
  │ coverage.json                1L  0C    0m  CC=0.0    ←0
  │
  schemas/                        CC̄=0.0    ←in:0  →out:0
  │ koru-stdio-event.schema.json    16L  0C    0m  CC=0.0    ←0
  │
  docs/                           CC̄=0.0    ←in:0  →out:0
  │ ide-command-api-map.yaml   425L  0C    0m  CC=0.0    ←0
  │ koru-interface-registry.yaml   270L  0C    0m  CC=0.0    ←0
  │ ai-tool-registry-2026.yaml   206L  0C    0m  CC=0.0    ←0
  │ install.sh                  88L  0C    0m  CC=0.0    ←0
  │ install.sh                  87L  0C    0m  CC=0.0    ←0
  │ install.sh                  80L  0C    0m  CC=0.0    ←0
  │ install.sh                  55L  0C    0m  CC=0.0    ←0
  │ install.sh                  53L  0C    0m  CC=0.0    ←0
  │ install.sh                  53L  0C    0m  CC=0.0    ←0
  │ install.sh                  53L  0C    0m  CC=0.0    ←0
  │ install.sh                  53L  0C    0m  CC=0.0    ←0
  │ install.sh                  52L  0C    0m  CC=0.0    ←0
  │ install.sh                  52L  0C    0m  CC=0.0    ←0
  │ install.sh                  52L  0C    0m  CC=0.0    ←0
  │ install.sh                  49L  0C    0m  CC=0.0    ←0
  │ install.sh                  49L  0C    0m  CC=0.0    ←0
  │ install.sh                  49L  0C    0m  CC=0.0    ←0
  │ install.sh                  49L  0C    0m  CC=0.0    ←0
  │ install.sh                  41L  0C    0m  CC=0.0    ←0
  │ install.sh                  41L  0C    0m  CC=0.0    ←0
  │ install.sh                  38L  0C    0m  CC=0.0    ←0
  │ install.sh                  38L  0C    0m  CC=0.0    ←0
  │ install.sh                  38L  0C    0m  CC=0.0    ←0
  │ install.sh                  38L  0C    0m  CC=0.0    ←0
  │ python-quality-baseline.yaml    14L  0C    0m  CC=0.0    ←0
  │ monorepo-hygiene.yaml       13L  0C    0m  CC=0.0    ←0
  │
  redeploy/                       CC̄=0.0    ←in:0  →out:0
  │ manifest.yaml              125L  0C    0m  CC=0.0    ←0
  │
  testql-scenarios/               CC̄=0.0    ←in:0  →out:0
  │ cli-smoke.testql.toon.yaml    44L  0C    0m  CC=0.0    ←0
  │ send-invoice.testql.toon.yaml    39L  0C    0m  CC=0.0    ←0
  │ generated-cli-tests.testql.toon.yaml    19L  0C    0m  CC=0.0    ←0
  │ cli-koru-live.testql.toon.yaml    16L  0C    0m  CC=0.0    ←0
  │ cli-koru.testql.toon.yaml    15L  0C    0m  CC=0.0    ←0
  │ cli-koru_api.testql.toon.yaml    12L  0C    0m  CC=0.0    ←0
  │ cli-koru_dsl.testql.toon.yaml    12L  0C    0m  CC=0.0    ←0
  │ vdisplay-photo-vql-drive.testql.toon.yaml    12L  0C    0m  CC=0.0    ←0
  │ cli-koru_wup_testql.testql.toon.yaml    12L  0C    0m  CC=0.0    ←0
  │ generated-from-pytests.testql.toon.yaml    10L  0C    0m  CC=0.0    ←0
  │ cli-coru_calibration.testql.toon.yaml     9L  0C    0m  CC=0.0    ←0
  │ mock-llm-replies.yaml        4L  0C    0m  CC=0.0    ←0
  │
  testql-testing/                 CC̄=0.0    ←in:0  →out:0
  │ realtime-health.testql.toon.yaml    11L  0C    0m  CC=0.0    ←0
  │
  ── zero ──
     src/koru/cli.py                           0L
     src/koruenv/__init__.py                   0L

COUPLING:
                                                      src.koru                        project                    src.koruide                  packages.coru                    src.koruapi              packages.dsl2koru  plugins.koru-autopilot-shared                        scripts                 src.koruvision                src.koruobserve              packages.dsl2coru              packages.nlp2coru                   src.korumesh                           koru              packages.uri2coru
                       src.koru                             ──                            621                            216                              2                             14                              3                             55                             ←1                             22                             12                             ←3                             25                             ←2                             18                             ←1  hub
                        project                           ←621                             ──                            ←26                           ←183                            ←17                            ←11                                                           ←75                            ←12                            ←22                            ←11                             ←6                             ←7                                                            ←6  hub
                    src.koruide                             41                             26                             ──                             ←7                            ←27                                                             9                                                                                            1                                                                                                                                                             hub
                  packages.coru                             34                            183                              7                             ──                                                             3                              3                                                            ←1                                                                                            4                                                                                               hub
                    src.koruapi                            100                             17                             27                                                            ──                                                            13                             ←1                              2                                                                                                                           3                              3                                 hub
              packages.dsl2koru                             ←3                             11                                                             1                                                            ──                                                                                                                                                        ←34                             ←2                                                                                            1  hub
  plugins.koru-autopilot-shared                            ←55                                                            ←9                             ←3                            ←13                                                            ──                                                            ←2                                                                                                                          ←2                                                                hub
                        scripts                              1                             75                                                                                            1                                                                                           ──                                                                                                                                                                                                                           !! fan-out
                 src.koruvision                              5                             12                                                             1                             ←2                                                             2                                                            ──                              1                                                                                            8                                                                hub
                src.koruobserve                              7                             22                             ←1                                                                                                                                                                                         7                             ──                                                                                            1                              1                                 hub
              packages.dsl2coru                              3                             11                                                                                                                          34                                                                                                                                                         ──                                                                                                                              !! fan-out
              packages.nlp2coru                              1                              6                                                            ←4                                                             2                                                                                                                                                                                        ──                                                                                            1  hub
                   src.korumesh                              2                              7                                                                                           ←3                                                             2                                                             2                              1                                                                                           ──                                                                hub
                           koru                              2                                                                                                                          ←3                                                                                                                                                         ←1                                                                                                                          ──                                 hub
              packages.uri2coru                              1                              6                                                                                                                           1                                                                                                                                                                                        ←1                                                                                           ──  hub
  CYCLES: none
  HUB: packages.nlp2coru/ (fan-in=33)
  HUB: src.koruvision/ (fan-in=37)
  HUB: packages.dsl2koru/ (fan-in=71)
  HUB: src.korumesh/ (fan-in=12)
  HUB: src.koruide/ (fan-in=250)
  HUB: koru/ (fan-in=22)
  HUB: packages.uri2coru/ (fan-in=11)
  HUB: src.koru/ (fan-in=210)
  HUB: packages.mcp2coru/ (fan-in=6)
  HUB: packages.coru/ (fan-in=5)
  HUB: src.koruobserve/ (fan-in=16)
  HUB: packages.koruenv/ (fan-in=10)
  HUB: packages.nlpshim/ (fan-in=6)
  HUB: src.koruapi/ (fan-in=15)
  HUB: src.imgl/ (fan-in=5)
  HUB: plugins.koru-autopilot-shared/ (fan-in=88)
  HUB: project/ (fan-in=1042)
  SMELL: packages.nlp2coru/ fan-out=10 → split needed
  SMELL: src.koruvision/ fan-out=29 → split needed
  SMELL: packages.dsl2koru/ fan-out=19 → split needed
  SMELL: src.korumesh/ fan-out=14 → split needed
  SMELL: src.koruide/ fan-out=82 → split needed
  SMELL: scripts/ fan-out=77 → split needed
  SMELL: packages.uri2coru/ fan-out=8 → split needed
  SMELL: examples/ fan-out=12 → split needed
  SMELL: src.koru/ fan-out=1005 → split needed
  SMELL: packages.coru/ fan-out=238 → split needed
  SMELL: src.koruobserve/ fan-out=38 → split needed
  SMELL: packages.cli2coru/ fan-out=12 → split needed
  SMELL: packages.dsl2coru/ fan-out=48 → split needed
  SMELL: packages.nlp2koru/ fan-out=17 → split needed
  SMELL: packages.uri2koru/ fan-out=16 → split needed
  SMELL: src.koruapi/ fan-out=172 → split needed
  SMELL: packages.cli2koru/ fan-out=11 → split needed

EXTERNAL:
  validation: run `vallm batch .` → validation.toon
  duplication: run `redup scan .` → duplication.toon
```

### Duplication (`project/duplication.toon.yaml`)

```toon markpact:analysis path=project/duplication.toon.yaml
# redup/duplication | 297 groups | 763f 134208L | 2026-07-17

SUMMARY:
  files_scanned: 763
  total_lines:   134208
  dup_groups:    297
  dup_fragments: 669
  saved_lines:   3214
  scan_ms:       1942329

HOTSPOTS[7] (files with most duplication):
  src/koru/doctor_reporting_checks.py  dup=197L  groups=10  frags=10  (0.1%)
  src/koru/doctor_chat_control.py  dup=191L  groups=10  frags=10  (0.1%)
  src/koru/autonomy/phases/scan_phase.py  dup=137L  groups=6  frags=10  (0.1%)
  src/koru/autonomy/cycle_queue_scan.py  dup=132L  groups=5  frags=5  (0.1%)
  src/koruapi/env2llm_registry.py  dup=103L  groups=3  frags=5  (0.1%)
  src/koru/autonomous.py  dup=98L  groups=7  frags=9  (0.1%)
  src/koru/ide_adapters/ide_reload.py  dup=87L  groups=4  frags=8  (0.1%)

DUPLICATES[297] (ranked by impact):
  [7c6ec0fe8849264d] ! STRU  _scan_pyqual_report  L=26 N=3 saved=52 sim=1.00
      src/koru/scan.py:1074-1099  (_scan_pyqual_report)
      src/koru/scan.py:1102-1126  (_scan_prefact_report)
      src/koru/scan.py:1155-1180  (_scan_redsl_report)
  [F0085] ! FUZZ  create_app  L=55 N=2 saved=55 sim=0.94
      packages/rest2koru/src/rest2koru/app.py:17-71  (create_app)
      packages/rest2coru/src/rest2coru/app.py:16-72  (create_app)
  [d8de3a114b93f12d] ! EXAC  complete  L=48 N=2 saved=48 sim=1.00
      packages/nlp2coru/src/nlp2coru/llm_backend.py:38-85  (complete)
      packages/nlp2koru/src/nlp2koru/llm_backend.py:40-87  (complete)
  [79d923a120aad524] ! STRU  _add_calibrate_parser  L=42 N=2 saved=42 sim=1.00
      src/koru/autopilot/cli_parser.py:207-248  (_add_calibrate_parser)
      src/koru/autopilot/cli_parser.py:330-367  (_add_session_start_parser)
  [644b474a93b6b2ae] ! STRU  check_plugin_version_mismatch_issue  L=41 N=2 saved=41 sim=1.00
      src/koru/autopilot/install_checks.py:397-437  (check_plugin_version_mismatch_issue)
      src/koru/autopilot/install_checks.py:440-480  (check_plugin_build_mismatch_issue)
  [F0084] ! FUZZ  collect_git_evidence  L=40 N=2 saved=40 sim=0.93
      src/koru/autonomy/verification_engine.py:123-162  (collect_git_evidence)
      src/koru/autonomy/verification_engine.py:165-208  (collect_git_diff_between)
  [F0083] ! FUZZ  handle_post_run_verify  L=39 N=2 saved=39 sim=0.94
      src/koru/autonomy/phases/queue_phase.py:105-143  (handle_post_run_verify)
      src/koru/autonomy/cycle_queue_scan.py:116-156  (_handle_post_run_verify)
  [e5465822d9dbf47d] ! STRU  activity_enabled  L=3 N=13 saved=36 sim=1.00
      src/koru/activity_log.py:16-18  (activity_enabled)
      src/koru/autonomy/cycle/cycle_chat_activity_config.py:90-92  (llm_needs_input_ticket_enabled)
      src/koru/autonomy/cycle/cycle_chat_activity_config.py:105-107  (llm_needs_input_heuristic_enabled)
      src/koru/autonomy/cycle/cycle_chat_activity_config.py:110-112  (chat_intake_ticket_enabled)
      src/koru/autonomy/operator/operator_operator.py:19-21  (_operator_autostart_envmap_enabled)
      src/koru/autonomy/operator/operator_processes.py:258-260  (autonomous_start_lock_wanted)
      src/koru/autonomy/operator_pipeline.py:266-268  (_operator_autostart_server_enabled)
      src/koru/autonomy/planning_llm_runtime.py:10-12  (planning_llm_enabled)
      src/koru/deps_autorepair.py:35-37  (auto_install_enabled)
      src/koru/ide_adapters/ide_reload.py:87-89  (auto_reload_enabled)
      src/koru/mcp_provision.py:329-331  (_operator_autostart_mcp_enabled)
      src/koruide/plugin_installer.py:662-664  (_env_reassert_extension_install)
      src/koruide/plugin_installer.py:672-674  (_env_build_local_vsix)
  [a714be2bfaaeebdc] ! STRU  emit_intent  L=6 N=7 saved=36 sim=1.00
      src/koru/observability_events.py:41-46  (emit_intent)
      src/koru/observability_events.py:49-54  (emit_decision)
      src/koru/observability_events.py:57-62  (emit_action)
      src/koru/observability_events.py:65-70  (emit_phase)
      src/koru/observability_events.py:73-78  (emit_verify)
      src/koru/observability_events.py:95-100  (emit_blocker)
      src/koru/observability_events.py:103-108  (emit_next)
  [F0050] ! FUZZ  _run  L=8 N=6 saved=40 sim=0.88
      src/koru/dev_sync.py:70-77  (_run)
      src/koru/ticket_evidence.py:288-295  (_run)
      src/koru/autonomy/operator_pipeline.py:185-193  (runner)
      src/koru/scan.py:130-138  (_default_runner)
      src/koru/utils/subprocess_runner.py:8-16  (default_subprocess_runner)
      src/koru/autonomy/cycle/cycle_chat_activity_tickets.py:244-255  (_planfile_runner)
  [F0082] ! FUZZ  analyze_chat_control  L=35 N=2 saved=35 sim=0.96
      src/koru/doctor_chat_control.py:319-353  (analyze_chat_control)
      src/koru/doctor_reporting_checks.py:197-233  (_analyze_chat_control)
  [66ec5b56f4c44ce2] ! STRU  run_command  L=33 N=2 saved=33 sim=1.00
      packages/dsl2coru/src/dsl2coru/handlers/command.py:12-44  (run_command)
      packages/dsl2coru/src/dsl2coru/handlers/query.py:12-44  (run_query)
  [e307920c99fda1f9] ! STRU  build_chat_control_detail_bits  L=33 N=2 saved=33 sim=1.00
      src/koru/doctor_chat_control.py:218-250  (build_chat_control_detail_bits)
      src/koru/doctor_reporting_checks.py:96-128  (_build_chat_control_detail_bits)
  [F0081] ! FUZZ  _run_idle_diagnostics  L=34 N=2 saved=34 sim=0.92
      src/koru/autonomous.py:486-519  (_run_idle_diagnostics)
      src/koru/autonomy/cycle_diagnostics.py:119-155  (_run_idle_diagnostics)
  [F0080] ! FUZZ  _ensure_standardized_discovery_follow_up  L=32 N=2 saved=32 sim=0.96
      src/koru/autonomy/cycle_queue_scan.py:256-287  (_ensure_standardized_discovery_follow_up)
      src/koru/autonomy/phases/scan_phase.py:647-678  (_ensure_standardized_discovery_follow_up)
  [374579b7eee86e62]   STRU  provision_cursor  L=15 N=3 saved=30 sim=1.00
      src/koru/mcp_provision.py:254-268  (provision_cursor)
      src/koru/mcp_provision.py:271-285  (provision_vscode)
      src/koru/mcp_provision.py:295-309  (provision_zed)
  [d1070360c71a2f6d]   STRU  _build_local_serve_parser  L=29 N=2 saved=29 sim=1.00
      src/koru/cli_local_serve.py:24-52  (_build_local_serve_parser)
      src/koruapi/local.py:11-19  (build_local_parser)
  [1e9081af4fcaacd6]   STRU  chat_control_result  L=29 N=2 saved=29 sim=1.00
      src/koru/doctor_chat_control.py:288-316  (chat_control_result)
      src/koru/doctor_reporting_checks.py:166-194  (_chat_control_result)
  [F0079]   FUZZ  _emit_queue_iteration_event  L=29 N=2 saved=29 sim=0.99
      src/koru/autonomy/cycle_queue_scan.py:85-113  (_emit_queue_iteration_event)
      src/koru/autonomy/phases/queue_phase.py:74-102  (emit_queue_iteration_event)
  [442ce611022ec2c3]   STRU  allow_cross_ide_autopilot  L=7 N=5 saved=28 sim=1.00
      src/koru/autonomy/env.py:373-379  (allow_cross_ide_autopilot)
      src/koru/integrations/photo_vql_drive.py:67-73  (_allow_surface_only_actuation)
      src/koru/integrations/vdisplay_client.py:562-568  (_dry_run)
      src/koru/integrations/vdisplay_client.py:1064-1070  (_abort_on_desktop_probe_fail)
      src/koru/integrations/vdisplay_client.py:1460-1466  (_auto_ide_control_enabled)
  [aab286c67e833481]   STRU  main  L=26 N=2 saved=26 sim=1.00
      packages/cli2coru/src/cli2coru/cli.py:53-78  (main)
      packages/cli2koru/src/cli2koru/cli.py:53-78  (main)
  [d6dbcd225ef29eb0]   STRU  run_shell  L=26 N=2 saved=26 sim=1.00
      packages/cli2coru/src/cli2coru/shell.py:8-33  (run_shell)
      packages/cli2koru/src/cli2koru/shell.py:8-33  (run_shell)
  [928d6c69c14e773f]   EXAC  load_project_metadata  L=25 N=2 saved=25 sim=1.00
      packages/nlp2coru/src/nlp2coru/openrouter_config.py:10-34  (load_project_metadata)
      packages/nlp2koru/src/nlp2koru/openrouter_config.py:10-34  (load_project_metadata)
  [8b13f2270232bdb8]   EXAC  _finalise_ticket  L=25 N=2 saved=25 sim=1.00
      src/koru/wizard/cli.py:66-90  (_finalise_ticket)
      src/koru/wizard/orchestrator.py:226-250  (_finalise_ticket)
  [3df748d1c9cc3d03]   STRU  _exec_cross_ide_guidance  L=25 N=2 saved=25 sim=1.00
      packages/coru/src/coru/repair/pipeline.py:506-530  (_exec_cross_ide_guidance)
      packages/coru/src/coru/repair/pipeline.py:558-579  (_exec_default)
  [0cbc063638d70154]   STRU  message_sent  L=12 N=3 saved=24 sim=1.00
      src/koruide/protocol.py:242-253  (message_sent)
      src/koruide/protocol.py:256-267  (message_received)
      src/koruide/protocol.py:270-281  (status_error)
  [F0078]   FUZZ  windsurf_chat_column_indexes  L=25 N=2 saved=25 sim=0.93
      src/koru/doctor_chat_control.py:356-380  (windsurf_chat_column_indexes)
      src/koru/doctor_reporting_checks.py:281-309  (_windsurf_chat_column_indexes)
  [1d5356212a33106d]   STRU  windsurf_chat_column_result  L=23 N=2 saved=23 sim=1.00
      src/koru/doctor_chat_control.py:404-426  (windsurf_chat_column_result)
      src/koru/doctor_reporting_checks.py:333-355  (_windsurf_chat_column_result)
  [42f5035b9855c7b4]   STRU  env2llm_get_desktop  L=23 N=2 saved=23 sim=1.00
      src/koruapi/env2llm_registry.py:250-272  (env2llm_get_desktop)
      src/koruapi/env2llm_registry.py:310-332  (env2llm_list_commands)
  [F0075]   FUZZ  stop_daemon  L=24 N=2 saved=24 sim=0.92
      packages/coru/src/coru/supervisor/daemon_ctl.py:50-73  (stop_daemon)
      packages/coru/src/coru/supervisor/daemon_ctl.py:22-47  (start_daemon)
  [F0076]   FUZZ  env2llm_get_registry  L=24 N=2 saved=24 sim=0.90
      src/koruapi/env2llm_registry.py:107-130  (env2llm_get_registry)
      src/koruapi/env2llm_registry.py:133-158  (env2llm_render_registry)
  [F0077]   FUZZ  _run_code2llm_discovery_after_idle  L=25 N=2 saved=25 sim=0.86
      src/koru/autonomy/phases/scan_phase.py:620-644  (_run_code2llm_discovery_after_idle)
      src/koru/autonomy/cycle_queue_scan.py:228-253  (_run_code2llm_discovery_after_idle)
  [0ad8aba1da8ed8e3]   STRU  sync_plugins_for_ide  L=21 N=2 saved=21 sim=1.00
      packages/coru/src/coru/ecosystem.py:97-117  (sync_plugins_for_ide)
      packages/coru/src/coru/ecosystem.py:120-130  (sync_manage_fix)
  [d0276646937c7147]   STRU  _plugin_reconnected_after_wait  L=21 N=2 saved=21 sim=1.00
      src/koru/autonomy/operator/operator_plugin_wait.py:297-317  (_plugin_reconnected_after_wait)
      src/koru/autonomy/operator/operator_plugin_wait.py:351-371  (_plugin_connected_after_fresh_window)
  [F0072]   FUZZ  ancestor_pids  L=21 N=2 saved=21 sim=1.00
      src/koru/autonomy/operator/operator_process_guard.py:53-73  (ancestor_pids)
      src/koru/autonomy/operator/operator_processes.py:99-120  (_ancestor_pids)
  [F0073]   FUZZ  _register_tools  L=22 N=2 saved=22 sim=0.93
      packages/mcp2coru/src/mcp2coru/server.py:26-47  (_register_tools)
      packages/mcp2koru/src/mcp2koru/server.py:26-47  (_register_tools)
  [F0074]   FUZZ  capture_one_with_providers  L=23 N=2 saved=23 sim=0.88
      src/koruvision/providers/detector.py:256-278  (capture_one_with_providers)
      src/koruvision/providers/detector.py:281-306  (capture_all_with_providers)
  [62098847ad4d50c2]   EXAC  _stdio_info  L=5 N=5 saved=20 sim=1.00
      src/koru/autonomous.py:235-239  (_stdio_info)
      src/koru/autonomy/checkpoint/checkpoint.py:16-19  (_stdio_info)
      src/koru/autonomy/cycle/cycle.py:153-156  (_stdio_info)
      src/koru/autonomy/operator/operator_daemon.py:26-30  (_stdio_info)
      src/koru/autonomy/operator/operator_processes.py:292-296  (_stdio_info)
  [03988974cc7211a2]   STRU  _wup_process_match  L=20 N=2 saved=20 sim=1.00
      src/koru/autonomy/operator/operator_process_guard.py:169-188  (_wup_process_match)
      src/koru/autonomy/operator/operator_processes.py:169-187  (_wup_process_matches_project)
  [9fc6ccb633a9cc1c]   STRU  assess_drive_failure  L=20 N=2 saved=20 sim=1.00
      src/korullm/strategies/codex.py:48-67  (assess_drive_failure)
      src/korullm/strategies/ollama.py:37-56  (assess_drive_failure)
  [F0069]   FUZZ  _live_plugin_version  L=19 N=2 saved=19 sim=0.98
      src/koru/decision_engine.py:221-239  (_live_plugin_version)
      src/koru/autonomy/operator/operator_plugin_runtime.py:41-60  (live_plugin_version)
  [F0068]   FUZZ  cleanup_autonomous_session  L=19 N=2 saved=19 sim=0.95
      src/koru/autonomy/operator/operator_daemon.py:265-283  (cleanup_autonomous_session)
      src/koru/autonomy/operator/operator_runtime.py:545-564  (cleanup_autonomous_session)
  [F0070]   FUZZ  _installed_editable_source_root  L=19 N=2 saved=19 sim=0.94
      src/koru/self_control.py:143-161  (_installed_editable_source_root)
      src/koru/autopilot/install_manager.py:195-214  (_installed_editable_source_root)
  [F0071]   FUZZ  toggle_component  L=20 N=2 saved=20 sim=0.88
      src/koru/bounded_contexts/topology/application.py:41-60  (toggle_component)
      src/koru/bounded_contexts/topology/application.py:62-81  (toggle_pipeline)
  [7f3f1bdabfdfd101]   STRU  autopilot_redrive_cooldown_seconds  L=17 N=2 saved=17 sim=1.00
      src/koru/autonomy/cycle/cycle_chat_activity_config.py:19-35  (autopilot_redrive_cooldown_seconds)
      src/koru/autonomy/cycle/cycle_chat_activity_config.py:38-54  (autopilot_os_injector_cooldown_seconds)
  [53be8947921a2263]   STRU  _post_workers_register  L=17 N=2 saved=17 sim=1.00
      src/koru/local_service.py:218-234  (_post_workers_register)
      src/koru/local_service.py:237-253  (_post_worker_heartbeat)
  [f741b370d1be4865]   STRU  _try_imgl_gui_fallback  L=16 N=2 saved=16 sim=1.00
      src/koru/autonomy/cycle/cycle_drive_retry.py:198-213  (_try_imgl_gui_fallback)
      src/koru/autonomy/cycle/cycle_drive_retry.py:216-231  (_try_gillm_gui_fallback)
  [c8f127acc6751743]   STRU  allow_gillm_autopilot_fallback  L=4 N=5 saved=16 sim=1.00
      src/koru/autonomy/env.py:328-331  (allow_gillm_autopilot_fallback)
      src/koru/ide_adapters/ide_reload.py:92-105  (reuse_window_reload_enabled)
      src/koru/ide_adapters/ide_reload.py:108-119  (command_palette_reload_enabled)
      src/koru/ide_adapters/ide_reload.py:122-134  (new_window_reload_enabled)
      src/koru/ide_adapters/ide_reload.py:146-156  (detached_reload_enabled)
  [4b4e0453ad1ecf33]   STRU  _dsl_main  L=4 N=5 saved=16 sim=1.00
      src/koru/cli.py:62-65  (_dsl_main)
      src/koru/cli.py:68-71  (_api_main)
      src/koru/cli.py:92-95  (_agent_backends_main)
      src/koru/cli_local_serve.py:55-58  (_local_serve_main)
      src/koru/cli_serve.py:74-77  (_serve_main)
  [88b3c3a2a9b95ab2]   STRU  nlp2uri_missing_message  L=8 N=3 saved=16 sim=1.00
      src/koruapi/desktop_uri.py:28-35  (nlp2uri_missing_message)
      src/koruapi/env2llm_registry.py:42-48  (env2llm_missing_message)
      src/koruapi/nlp2oql_bridge.py:47-53  (nlp2oql_missing_message)
  [8f290eb1e5aba0e4]   STRU  _cmd_lane_status  L=5 N=4 saved=15 sim=1.00
      packages/uri2coru/src/uri2coru/decode.py:21-25  (_cmd_lane_status)
      packages/uri2coru/src/uri2coru/decode.py:28-32  (_cmd_validate_lane)
      packages/uri2coru/src/uri2coru/decode.py:35-39  (_cmd_repair_run)
      packages/uri2coru/src/uri2coru/decode.py:73-77  (_block_lane_status)
  [cb837998f89e21d6]   STRU  _topology_component_toggler  L=15 N=2 saved=15 sim=1.00
      src/koru/cli_topology.py:111-125  (_topology_component_toggler)
      src/koru/cli_topology.py:128-142  (_topology_pipeline_toggler)
  [c171603ed647dbad]   STRU  reload_via_reopen_workspace  L=15 N=2 saved=15 sim=1.00
      src/koru/ide_adapters/ide_reload.py:431-445  (reload_via_reopen_workspace)
      src/koru/ide_adapters/ide_reload.py:448-462  (reload_via_new_window)
  [4604e82ca5f7161c]   STRU  _controls_find  L=5 N=4 saved=15 sim=1.00
      src/koru/integrations/vdisplay_client.py:3197-3201  (_controls_find)
      src/koru/integrations/vdisplay_client.py:3204-3208  (_control_focus)
      src/koru/integrations/vdisplay_client.py:3211-3215  (_control_set_value)
      src/koru/integrations/vdisplay_client.py:3218-3222  (_control_click)
  [a4e0b5a2e1a7c3fa]   STRU  tool_env2llm_get_registry  L=5 N=4 saved=15 sim=1.00
      src/koruapi/mcp_server_env2llm.py:164-168  (tool_env2llm_get_registry)
      src/koruapi/mcp_server_env2llm.py:189-193  (tool_env2llm_get_desktop)
      src/koruapi/mcp_server_env2llm.py:196-200  (tool_env2llm_list_commands)
      src/koruapi/mcp_server_env2llm.py:203-207  (tool_env2llm_list_uris)
  [69b1daff9f6bbf2b]   STRU  detection  L=5 N=4 saved=15 sim=1.00
      src/koruide/ides/antigravity.py:28-32  (detection)
      src/koruide/ides/cursor.py:43-47  (detection)
      src/koruide/ides/qoder.py:27-31  (detection)
      src/koruide/ides/zed.py:28-32  (detection)
  [F0067]   FUZZ  _python_type  L=16 N=2 saved=16 sim=0.91
      packages/dsl2coru/src/dsl2coru/codegen.py:13-28  (_python_type)
      packages/dsl2koru/src/dsl2koru/codegen.py:14-32  (_python_type)
  [681ecd425304ea8f]   EXAC  _installed_extension_dir  L=14 N=2 saved=14 sim=1.00
      packages/coru/src/coru/repair/diagnostics.py:39-52  (_installed_extension_dir)
      packages/coru/src/coru/repair/pipeline.py:48-61  (_installed_extension_dir)
  [1c0ccc6047c9b667]   EXAC  _canonical_ide  L=7 N=3 saved=14 sim=1.00
      src/koru/integrations/photo_vql_target.py:77-83  (_canonical_ide)
      src/koru/integrations/photo_vql_validation.py:82-88  (_canonical_ide)
      src/koru/integrations/vdisplay_client.py:213-219  (_canonical_ide)
  [329749cb64ad3db6]   STRU  update_plugin_version_source  L=14 N=2 saved=14 sim=1.00
      scripts/sync-vscode-plugin-version.py:43-56  (update_plugin_version_source)
      scripts/sync-vscode-plugin-version.py:59-68  (update_package_json)
  [1249c022c52da091]   STRU  _should_skip_repeated_create_failed_scan  L=14 N=2 saved=14 sim=1.00
      src/koru/autonomy/phases/scan_phase.py:167-180  (_should_skip_repeated_create_failed_scan)
      src/koru/autonomy/phases/scan_phase.py:183-194  (_should_skip_repeated_duplicate_scan)
  [a548921494239b98]   STRU  _action_install_plugin  L=7 N=3 saved=14 sim=1.00
      src/koru/autopilot/cli_command.py:285-291  (_action_install_plugin)
      src/koru/autopilot/cli_command.py:294-300  (_action_install_plugin_jetbrains)
      src/koru/autopilot/cli_command.py:319-325  (_action_install_unit)
  [6dc8f939491914fe]   STRU  _open_new_ide_window_for_plugin_build_action  L=14 N=2 saved=14 sim=1.00
      src/koru/autopilot/install_manager.py:841-854  (_open_new_ide_window_for_plugin_build_action)
      src/koru/autopilot/install_manager.py:893-906  (_restart_ide_for_plugin_build_action)
  [a4ab30d7cb660f05]   STRU  env_truthy  L=14 N=2 saved=14 sim=1.00
      src/koru/env_flags.py:43-56  (env_truthy)
      src/koruide/utils.py:30-45  (env_truthy)
  [7ec1d872f653f86e]   STRU  _empty_desktop_result  L=14 N=2 saved=14 sim=1.00
      src/koruapi/calibration_validator.py:251-264  (_empty_desktop_result)
      src/koruapi/calibration_validator.py:267-283  (_no_calibrations_result)
  [F0065]   FUZZ  show_decisions  L=15 N=2 saved=15 sim=0.91
      src/koru/autonomy/replay_handlers.py:16-30  (show_decisions)
      src/koru/autonomy/replay_handlers.py:32-46  (show_interfaces)
  [F0066]   FUZZ  wrapper  L=15 N=2 saved=15 sim=0.89
      src/koruapi/invoke_handlers.py:33-47  (wrapper)
      src/koruapi/invoke_handlers.py:30-48  (_wrap_handler_errors)
  [9ba1e228babab556]   EXAC  _run_results  L=13 N=2 saved=13 sim=1.00
      packages/dsl2coru/src/dsl2coru/cli.py:19-31  (_run_results)
      packages/dsl2koru/src/dsl2koru/cli.py:19-31  (_run_results)
  [ca311cd6f35a93ea]   EXAC  _handle  L=13 N=2 saved=13 sim=1.00
      packages/rest2coru/src/rest2coru/app.py:32-44  (_handle)
      packages/rest2koru/src/rest2koru/app.py:33-45  (_handle)
  [c9fe98aa9145404a]   EXAC  _parse_iso_datetime  L=13 N=2 saved=13 sim=1.00
      src/koru/autonomy/ide_work.py:305-317  (_parse_iso_datetime)
      src/koru/autonomy/post_run_verify.py:130-142  (_parse_iso_datetime)
  [53f7c0e4daf93702]   STRU  main  L=13 N=2 saved=13 sim=1.00
      packages/rest2coru/src/rest2coru/cli.py:8-20  (main)
      packages/rest2koru/src/rest2koru/cli.py:8-20  (main)
  [81e723c3b3cbc00b]   STRU  parse_coru_uri  L=13 N=2 saved=13 sim=1.00
      packages/uri2coru/src/uri2coru/uri.py:41-53  (parse_coru_uri)
      packages/uri2koru/src/uri2koru/uri.py:40-52  (parse_koru_uri)
  [5bf8e4d88578b762]   STRU  _try_imgl_gui_fallback  L=13 N=2 saved=13 sim=1.00
      src/koru/autonomous.py:151-163  (_try_imgl_gui_fallback)
      src/koru/autonomous.py:166-178  (_try_gillm_gui_fallback)
  [d7d1fc488522c229]   STRU  _remember_scan_create_failed_state  L=13 N=2 saved=13 sim=1.00
      src/koru/autonomy/phases/scan_phase.py:137-149  (_remember_scan_create_failed_state)
      src/koru/autonomy/phases/scan_phase.py:152-164  (_remember_scan_duplicate_state)
  [F0061]   FUZZ  _reply_needs_plugin_retry  L=13 N=2 saved=13 sim=0.99
      src/koru/autonomy/cycle/cycle_drive_retry.py:828-840  (_reply_needs_plugin_retry)
      src/korullm/strategies/ide_chat.py:132-144  (_needs_plugin_retry)
  [F0062]   FUZZ  register_worker  L=14 N=2 saved=14 sim=0.91
      src/koru/bounded_contexts/local_manager/application.py:103-116  (register_worker)
      src/koru/bounded_contexts/local_manager/application.py:118-131  (heartbeat_worker)
  [F0064]   FUZZ  _try_vdisplay_control_fallback  L=15 N=2 saved=15 sim=0.85
      src/koru/autonomous.py:181-195  (_try_vdisplay_control_fallback)
      src/koru/autonomy/cycle/cycle_drive_retry.py:234-250  (_try_vdisplay_control_fallback)
  [F0063]   FUZZ  tool_ide_control_plan  L=14 N=2 saved=14 sim=0.88
      src/koruapi/mcp_server_ide.py:319-332  (tool_ide_control_plan)
      src/koruapi/mcp_server_ide.py:335-350  (tool_ide_control_execute)
  [84311d12c9f4b6a0]   EXAC  build_model_registry  L=12 N=2 saved=12 sim=1.00
      packages/dsl2coru/src/dsl2coru/codegen.py:31-42  (build_model_registry)
      packages/dsl2koru/src/dsl2koru/codegen.py:35-47  (build_model_registry)
  [9772283ee40ed244]   EXAC  _bridge_hypotheses_payload  L=12 N=2 saved=12 sim=1.00
      src/koru/autopilot/commands/drive.py:164-175  (_bridge_hypotheses_payload)
      src/koru/ide_doctor_cli.py:92-103  (_bridge_hypotheses_payload)
  [f2ad962612cc5d88]   EXAC  parse_boolish  L=12 N=2 saved=12 sim=1.00
      src/koru/env_flags.py:29-40  (parse_boolish)
      src/koruide/utils.py:16-27  (parse_boolish)
  [44807df02c2db882]   EXAC  plugin  L=6 N=3 saved=12 sim=1.00
      src/koruide/ides/antigravity.py:52-57  (plugin)
      src/koruide/ides/qoder.py:48-53  (plugin)
      src/koruide/ides/windsurf.py:51-56  (plugin)
  [43cf5259d2a755f4]   EXAC  assess_drive_failure  L=12 N=2 saved=12 sim=1.00
      src/korullm/strategies/claude.py:32-43  (assess_drive_failure)
      src/korullm/strategies/gpt.py:32-43  (assess_drive_failure)
  [35ca7615eb80ab15]   EXAC  list_monitors  L=4 N=4 saved=12 sim=1.00
      src/koruvision/providers/cli_tools.py:26-29  (list_monitors)
      src/koruvision/providers/grim.py:21-24  (list_monitors)
      src/koruvision/providers/portal_screencast.py:296-299  (list_monitors)
      src/koruvision/providers/portal_screenshot.py:28-31  (list_monitors)
  [0cfc52dfb660a4d8]   STRU  resolve_coru_bin  L=12 N=2 saved=12 sim=1.00
      packages/coru/src/coru/supervisor/systemd_unit.py:21-32  (resolve_coru_bin)
      src/koru/autopilot/systemd_cli.py:20-37  (resolve_koru_bin)
  [f1d6420661bf7cbc]   STRU  main  L=12 N=2 saved=12 sim=1.00
      packages/mcp2coru/src/mcp2coru/cli.py:11-22  (main)
      packages/mcp2koru/src/mcp2koru/cli.py:11-22  (main)
  [8509ce91dc9ed72c]   STRU  coru_to_dsl  L=4 N=4 saved=12 sim=1.00
      packages/mcp2coru/src/mcp2coru/tools.py:27-30  (coru_to_dsl)
      packages/mcp2koru/src/mcp2koru/tools.py:27-30  (koru_to_dsl)
      packages/nlpshim/src/nlpshim/control.py:6-9  (run_workflow)
      packages/nlpshim/src/nlpshim/control.py:12-15  (to_dsl)
  [9bd1185ad4a4a6df]   STRU  resolve_xdg_path  L=12 N=2 saved=12 sim=1.00
      src/koru/autopilot/utils/client_helpers.py:46-57  (resolve_xdg_path)
      src/koruide/utils.py:48-60  (resolve_xdg_path)
  [d7ab7acdbf3e3e5d]   STRU  chat_control_has_failures  L=12 N=2 saved=12 sim=1.00
      src/koru/doctor_chat_control.py:253-264  (chat_control_has_failures)
      src/koru/doctor_reporting_checks.py:131-142  (_chat_control_has_failures)
  [76e9751a694f564d]   STRU  windsurf_chat_column_detail_bits  L=12 N=2 saved=12 sim=1.00
      src/koru/doctor_chat_control.py:390-401  (windsurf_chat_column_detail_bits)
      src/koru/doctor_reporting_checks.py:319-330  (_windsurf_chat_column_detail_bits)
  [4804f2c250c10000]   STRU  _path_step_autopilot_intent  L=3 N=5 saved=12 sim=1.00
      src/koru/observability_dsl.py:209-211  (_path_step_autopilot_intent)
      src/koru/observability_dsl.py:219-221  (_path_step_autopilot_drive_requested)
      src/koru/observability_dsl.py:236-238  (_path_step_autopilot_drive_failed)
      src/koru/observability_dsl.py:241-243  (_path_step_autonomy_blocker)
      src/koru/observability_dsl.py:246-248  (_path_step_autonomy_next)
  [b605eeac9c794920]   STRU  _handle_mcp_list_tickets  L=6 N=3 saved=12 sim=1.00
      src/koruapi/invoke_handlers.py:223-228  (_handle_mcp_list_tickets)
      src/koruapi/invoke_handlers.py:231-234  (_handle_mcp_run_ticket)
      src/koruapi/invoke_handlers.py:237-242  (_handle_mcp_quality_gates)
  [5ce2dcca655ca5f7]   STRU  idle_marker_patterns  L=6 N=3 saved=12 sim=1.00
      src/korullm/strategies/claude.py:45-50  (idle_marker_patterns)
      src/korullm/strategies/gpt.py:45-50  (idle_marker_patterns)
      src/korullm/strategies/ollama.py:58-63  (idle_marker_patterns)
  [F0060]   FUZZ  _cmd_encode  L=13 N=2 saved=13 sim=0.90
      packages/dsl2coru/src/dsl2coru/cli.py:127-139  (_cmd_encode)
      packages/dsl2koru/src/dsl2koru/cli.py:108-120  (_cmd_encode)
  [F0015]   FUZZ  do_GET  L=4 N=4 saved=12 sim=0.97
      packages/coru/src/coru/supervisor/http_server.py:28-31  (do_GET)
      packages/coru/src/coru/supervisor/http_server.py:33-36  (do_PUT)
      packages/coru/src/coru/supervisor/http_server.py:38-41  (do_POST)
      packages/coru/src/coru/supervisor/http_server.py:43-46  (do_DELETE)
  [F0018]   FUZZ  api_select_ide  L=4 N=4 saved=12 sim=0.93
      src/koru/wizard/gui/app.py:284-287  (api_select_ide)
      src/koru/wizard/gui/app.py:290-293  (api_select_project)
      src/koru/wizard/gui/app.py:296-299  (api_strategy_choice)
      src/koru/wizard/gui/app.py:302-305  (api_confirm)
  [F0059]   FUZZ  _first_action_token  L=12 N=2 saved=12 sim=0.92
      src/koru/autonomy/configuration/config_cli_config.py:14-25  (_first_action_token)
      src/koru/cli_auto.py:40-51  (_first_action_token)
  [1ed2f22a904111cd]   EXAC  _terminal_shell_context  L=11 N=2 saved=11 sim=1.00
      packages/coru/src/coru/cli.py:856-866  (_terminal_shell_context)
      packages/coru/src/coru/cli_terminal.py:32-42  (_terminal_shell_context)
  [f32ab221563ce47f]   EXAC  setup_openrouter_env  L=11 N=2 saved=11 sim=1.00
      packages/nlp2coru/src/nlp2coru/openrouter_config.py:37-47  (setup_openrouter_env)
      packages/nlp2koru/src/nlp2koru/openrouter_config.py:37-47  (setup_openrouter_env)
  [4487ca9ea0c3d509]   EXAC  get_openrouter_headers  L=11 N=2 saved=11 sim=1.00
      packages/nlp2coru/src/nlp2coru/openrouter_config.py:50-60  (get_openrouter_headers)
      packages/nlp2koru/src/nlp2koru/openrouter_config.py:50-60  (get_openrouter_headers)
  [eca4d44fc02dbc88]   EXAC  _bridge_status_payload  L=11 N=2 saved=11 sim=1.00
      src/koru/autopilot/commands/drive.py:178-188  (_bridge_status_payload)
      src/koru/ide_doctor_cli.py:106-116  (_bridge_status_payload)
  [289ad8ee3567327f]   EXAC  _trace_event_matches  L=11 N=2 saved=11 sim=1.00
      src/koruapi/dashboard_observability.py:49-59  (_trace_event_matches)
      src/koruobserve/cli.py:179-189  (_trace_event_matches)
  [f36c0660c969fb58]   STRU  _ensure_trusted_publisher_for_plugin  L=11 N=2 saved=11 sim=1.00
      src/koru/autonomy/operator/operator_operator.py:108-118  (_ensure_trusted_publisher_for_plugin)
      src/koru/autonomy/operator/operator_operator.py:169-179  (_emit_reload_required_lines)
  [396a4ac72fae93e1]   STRU  _event_to_record  L=11 N=2 saved=11 sim=1.00
      src/koru/cqrs/event_store.py:51-61  (_event_to_record)
      src/koruapi/dashboard_observability.py:62-72  (_stored_event_payload)
  [0af1e54ae9c052bb]   STRU  chat_control_recovered_after_retry  L=11 N=2 saved=11 sim=1.00
      src/koru/doctor_chat_control.py:275-285  (chat_control_recovered_after_retry)
      src/koru/doctor_reporting_checks.py:153-163  (_chat_control_recovered_after_retry)
  [F0036]   FUZZ  history  L=6 N=3 saved=12 sim=0.90
      src/koru/bounded_contexts/planfile_queue/application.py:112-117  (history)
      src/koru/bounded_contexts/repairs/application.py:58-63  (history)
      src/koru/bounded_contexts/tasks/application.py:68-73  (history)
  [F0058]   FUZZ  _submit_retry_is_known_unsafe_without_engine  L=11 N=2 saved=11 sim=0.93
      src/koru/autonomy/drive/drive_retry_policy.py:230-240  (_submit_retry_is_known_unsafe_without_engine)
      src/koru/decision_engine.py:145-158  (_submit_retry_is_known_unsafe)
  [09dbfb122991822e]   EXAC  envelope_to_dict  L=10 N=2 saved=10 sim=1.00
      packages/dsl2coru/src/dsl2coru/pb_codec.py:257-266  (envelope_to_dict)
      packages/dsl2koru/src/dsl2koru/pb_codec.py:112-121  (envelope_to_dict)
  [c321cbf2e0c3e074]   EXAC  complete  L=10 N=2 saved=10 sim=1.00
      packages/nlp2coru/src/nlp2coru/llm_backend.py:23-32  (complete)
      packages/nlp2koru/src/nlp2koru/llm_backend.py:25-34  (complete)
  [2091f32d1012857e]   EXAC  _cli_version  L=5 N=3 saved=10 sim=1.00
      src/koru/cli_parser.py:17-21  (_cli_version)
      src/koruapi/cli.py:61-65  (_cli_version)
      src/korudsl/cli.py:41-45  (_cli_version)
  [c25bcde836af6815]   STRU  _cmd_decode  L=10 N=2 saved=10 sim=1.00
      packages/dsl2coru/src/dsl2coru/cli.py:142-151  (_cmd_decode)
      packages/dsl2koru/src/dsl2koru/cli.py:123-132  (_cmd_decode)
  [c542a739f7e8e858]   STRU  _build_ensure_args  L=5 N=3 saved=10 sim=1.00
      packages/dsl2coru/src/dsl2coru/handlers/argv.py:47-51  (_build_ensure_args)
      packages/dsl2coru/src/dsl2coru/handlers/argv.py:63-67  (_build_status_args)
      packages/dsl2coru/src/dsl2coru/handlers/argv.py:109-113  (_build_sync_args)
  [b942da0c52d5fa23]   STRU  _load_schemas  L=10 N=2 saved=10 sim=1.00
      packages/dsl2coru/src/dsl2coru/schema_registry.py:50-59  (_load_schemas)
      packages/dsl2koru/src/dsl2koru/schema_registry.py:15-24  (_load_schemas)
  [2d4bd59c870f53c8]   STRU  _build_nlp2uri_desktop_backend  L=5 N=3 saved=10 sim=1.00
      src/koru/agent_backend_runtime.py:331-335  (_build_nlp2uri_desktop_backend)
      src/koru/agent_backend_runtime.py:337-341  (_build_imgl_desktop_backend)
      src/koru/agent_backend_runtime.py:343-347  (_build_vdisplay_control_backend)
  [f31a19e016a92261]   STRU  _current_koru_version  L=5 N=3 saved=10 sim=1.00
      src/koru/autonomy/operator/operator_daemon.py:33-37  (_current_koru_version)
      src/koruide/daemon/metadata.py:92-96  (_package_version)
      src/koruide/daemon/protocol.py:15-19  (_daemon_package_version)
  [4d45da0f44a72d20]   STRU  trace_show_decisions  L=10 N=2 saved=10 sim=1.00
      src/koru/autonomy/replay_builders.py:38-47  (trace_show_decisions)
      src/koru/autonomy/replay_builders.py:50-59  (trace_show_interfaces)
  [5f8b062299cd64ec]   STRU  _versioned_plugin_vsix_candidates  L=10 N=2 saved=10 sim=1.00
      src/koru/autopilot/install_plugin_cli.py:82-91  (_versioned_plugin_vsix_candidates)
      src/koruide/plugin_installer.py:374-383  (_versioned_vsix_candidates)
  [724c6a8e46c9b909]   STRU  load_koru_project_pipeline  L=10 N=2 saved=10 sim=1.00
      src/koru/project_pipeline.py:116-125  (load_koru_project_pipeline)
      src/koruapi/dashboard_serve_utils.py:146-155  (read_serve_endpoint)
  [4e856744c98ccb30]   STRU  _clear_pending_plugin_drive  L=10 N=2 saved=10 sim=1.00
      src/koruide/daemon/handlers_ack.py:202-211  (_clear_pending_plugin_drive)
      src/koruide/daemon/handlers_drive.py:429-438  (_clear_stale_pending_plugin_drive)
  [ac1d92f6487f0bc9]   STRU  extension_id_for_ide  L=10 N=2 saved=10 sim=1.00
      src/koruide/plugin_installer.py:224-233  (extension_id_for_ide)
      src/koruide/plugin_version.py:30-39  (expected_plugin_version_for_ide)
  [F0057]   FUZZ  _cmd_replay  L=11 N=2 saved=11 sim=0.89
      packages/dsl2coru/src/dsl2coru/cli.py:159-169  (_cmd_replay)
      packages/dsl2koru/src/dsl2koru/cli.py:140-150  (_cmd_replay)
  [be74c96ae7cde4f3]   EXAC  _is_topology_enabled  L=9 N=2 saved=9 sim=1.00
      src/koru/autonomous.py:411-419  (_is_topology_enabled)
      src/koru/autonomy/cycle/cycle_skip_conditions.py:46-54  (_is_topology_enabled)
  [cb3d2c63ed56accc]   EXAC  current_head  L=9 N=2 saved=9 sim=1.00
      src/koru/autonomy/checkpoint/checkpoint.py:28-36  (current_head)
      src/koru/autonomy/phases/utils.py:22-30  (current_head)
  [b3de92f65aadf14a]   STRU  _project_from_argv  L=9 N=2 saved=9 sim=1.00
      packages/coru/src/coru/cli.py:103-111  (_project_from_argv)
      packages/coru/src/coru/cli.py:245-253  (_agent_lane_from_auto_args)
  [9cc35062f9d63731]   STRU  _default_runner  L=9 N=2 saved=9 sim=1.00
      src/koru/autonomy/code2llm_discovery.py:102-110  (_default_runner)
      src/koru/self_control.py:113-121  (_run)
  [4903b8df52c52b3a]   STRU  _reply_requires_manual_chat_focus  L=9 N=2 saved=9 sim=1.00
      src/koru/autonomy/cycle/cycle_drive_retry.py:864-872  (_reply_requires_manual_chat_focus)
      src/koru/autonomy/drive_result.py:131-139  (_reply_requires_manual_chat_focus)
  [b91042aeef9bb94c]   STRU  scan_while_waiting_input_enabled  L=3 N=4 saved=9 sim=1.00
      src/koru/autonomy/cycle/cycle_gate.py:382-384  (scan_while_waiting_input_enabled)
      src/koru/autopilot/install_manager.py:588-593  (_restart_ide_on_build_mismatch_enabled)
      src/koru/integrations/imgl_client.py:83-85  (imgl_desktop_transport_enabled)
      src/koruide/plugin_installer.py:667-669  (_env_force_reassert_extension_install)
  [5aa7c764b4fe2870]   STRU  _action_drive  L=9 N=2 saved=9 sim=1.00
      src/koru/autopilot/cli_command.py:217-225  (_action_drive)
      src/koru/autopilot/cli_command.py:232-240  (_action_status)
  [c8e896a73515691b]   STRU  _cursor_project_config  L=3 N=4 saved=9 sim=1.00
      src/koru/mcp_provision.py:44-46  (_cursor_project_config)
      src/koru/mcp_provision.py:49-51  (_vscode_project_config)
      src/koru/mcp_provision.py:54-56  (_windsurf_project_config)
      src/koru/mcp_provision.py:59-61  (_zed_project_settings)
  [e0d7dfb1f8dfaa0e]   STRU  _handle_wait  L=3 N=4 saved=9 sim=1.00
      src/korudsl/library.py:38-40  (_handle_wait)
      src/korudsl/library.py:43-45  (_handle_get)
      src/korudsl/library.py:48-50  (_handle_save)
      src/korudsl/library.py:53-55  (_handle_if)
  [F0056]   FUZZ  to_dict  L=10 N=2 saved=10 sim=0.90
      packages/dsl2koru/src/dsl2koru/result.py:19-28  (to_dict)
      packages/dsl2coru/src/dsl2coru/result.py:25-36  (to_dict)
  [F0055]   FUZZ  result_to_pb  L=10 N=2 saved=10 sim=0.86
      packages/dsl2koru/src/dsl2koru/pb_codec.py:150-159  (result_to_pb)
      packages/dsl2coru/src/dsl2coru/pb_codec.py:290-300  (result_to_pb)
  [F0053]   FUZZ  _read_package_build_sha  L=9 N=2 saved=9 sim=0.91
      packages/coru/src/coru/repair/diagnostics.py:28-36  (_read_package_build_sha)
      src/koruide/plugin_installer.py:688-696  (_package_build_sha)
  [1739f18c7405f64f]   EXAC  _print_result  L=8 N=2 saved=8 sim=1.00
      packages/cli2coru/src/cli2coru/cli.py:16-23  (_print_result)
      packages/cli2koru/src/cli2koru/cli.py:16-23  (_print_result)
  [77510f4ffc3c1e43]   EXAC  _lane_environ  L=8 N=2 saved=8 sim=1.00
      packages/coru/src/coru/supervisor/daemon_ctl.py:12-19  (_lane_environ)
      packages/coru/src/coru/supervisor/probe.py:18-25  (_lane_environ)
  [bbecb85f312760b0]   EXAC  _cmd_validate_schema  L=8 N=2 saved=8 sim=1.00
      packages/dsl2coru/src/dsl2coru/cli.py:117-124  (_cmd_validate_schema)
      packages/dsl2koru/src/dsl2koru/cli.py:98-105  (_cmd_validate_schema)
  [02001d30ccd18815]   EXAC  _set_body  L=8 N=2 saved=8 sim=1.00
      packages/dsl2coru/src/dsl2coru/pb_codec.py:128-135  (_set_body)
      packages/dsl2koru/src/dsl2koru/pb_codec.py:60-67  (_set_body)
  [1d3dac913ac1fd2e]   EXAC  _pid_alive  L=8 N=2 saved=8 sim=1.00
      src/koru/autonomy/readiness/readiness.py:452-459  (_pid_alive)
      src/koru/autopilot/lane_context.py:98-105  (_pid_alive)
  [f4651b5d65b82bdf]   STRU  _handle_run  L=8 N=2 saved=8 sim=1.00
      packages/cli2coru/src/cli2coru/cli.py:30-37  (_handle_run)
      packages/cli2koru/src/cli2koru/cli.py:30-37  (_handle_run)
  [c1ab68203a62a07a]   STRU  get_plugin_version_from_source  L=8 N=2 saved=8 sim=1.00
      scripts/sync-vscode-plugin-version.py:23-30  (get_plugin_version_from_source)
      scripts/sync-vscode-plugin-version.py:33-40  (get_plugin_version_from_package)
  [623b9b252e7a751d]   STRU  llm_reflection_summary_max_age_seconds  L=8 N=2 saved=8 sim=1.00
      src/koru/autonomy/cycle/cycle_chat_activity_config.py:80-87  (llm_reflection_summary_max_age_seconds)
      src/koruide/daemon/handlers.py:80-87  (_plugin_rejection_log_interval_seconds)
  [09bfa9fa669d8ae8]   STRU  _create_failed_scan_cooldown_seconds  L=8 N=2 saved=8 sim=1.00
      src/koru/autonomy/phases/scan_phase.py:117-124  (_create_failed_scan_cooldown_seconds)
      src/koru/autonomy/phases/scan_phase.py:127-134  (_duplicate_only_scan_cooldown_seconds)
  [9d3aba0bd29ecaac]   STRU  scan_force  L=8 N=2 saved=8 sim=1.00
      src/koru/autonomy/replay_builders.py:89-96  (scan_force)
      src/koru/autonomy/replay_builders.py:99-106  (wup_show_health)
  [f3c910fed74b4fab]   STRU  _env_float  L=8 N=2 saved=8 sim=1.00
      src/koru/integrations/photo_vql_config.py:18-25  (_env_float)
      src/koru/integrations/photo_vql_config.py:28-35  (_env_int)
  [6f2ea8109ac329b5]   STRU  _check_git_commit_policy  L=4 N=3 saved=8 sim=1.00
      src/koru/policy.py:194-197  (_check_git_commit_policy)
      src/koru/policy.py:200-203  (_check_git_push_policy)
      src/koru/policy.py:226-229  (_check_git_tag_policy)
  [f95e36e7a70f4336]   STRU  _sprint_signature  L=8 N=2 saved=8 sim=1.00
      src/koruapi/dashboard_context.py:21-28  (_sprint_signature)
      src/koruapi/dashboard_runtime.py:21-28  (_runtime_sprint_signature)
  [F0048]   FUZZ  start_lane_daemon  L=8 N=2 saved=8 sim=0.98
      packages/coru/src/coru/supervisor/service.py:56-63  (start_lane_daemon)
      packages/coru/src/coru/supervisor/service.py:65-72  (stop_lane_daemon)
  [F0049]   FUZZ  __init__  L=8 N=2 saved=8 sim=0.97
      packages/dsl2coru/src/dsl2coru/events.py:31-38  (__init__)
      packages/dsl2koru/src/dsl2koru/events.py:32-39  (__init__)
  [F0054]   FUZZ  _set_component_enabled  L=9 N=2 saved=9 sim=0.86
      src/koru/cli_topology.py:115-123  (_set_component_enabled)
      src/koru/cli_topology.py:132-140  (_set_pipeline_enabled)
  [F0051]   FUZZ  _plugin_version_mismatch_message  L=8 N=2 saved=8 sim=0.88
      src/koruide/drive_orchestrator.py:513-520  (_plugin_version_mismatch_message)
      src/koruide/drive_orchestrator.py:523-531  (_plugin_build_mismatch_message)
  [99084db17bc47ccd]   EXAC  _terminal_shell_context_fallback  L=7 N=2 saved=7 sim=1.00
      packages/coru/src/coru/cli.py:873-879  (_terminal_shell_context_fallback)
      packages/coru/src/coru/cli_terminal.py:49-55  (_terminal_shell_context_fallback)
  [80344f9480f0ad6f]   EXAC  validate_payload  L=7 N=2 saved=7 sim=1.00
      packages/dsl2coru/src/dsl2coru/codec.py:15-21  (validate_payload)
      packages/dsl2koru/src/dsl2koru/codec.py:15-21  (validate_payload)
  [bcfc35b1eda12dfe]   EXAC  validate_schemas  L=7 N=2 saved=7 sim=1.00
      packages/dsl2coru/src/dsl2coru/schema_registry.py:73-79  (validate_schemas)
      packages/dsl2koru/src/dsl2koru/schema_registry.py:38-44  (validate_schemas)
  [554a0330830db463]   EXAC  to_dict  L=7 N=2 saved=7 sim=1.00
      packages/uri2coru/src/uri2coru/nlp2uri.py:19-25  (to_dict)
      packages/uri2koru/src/uri2koru/nlp2uri.py:19-25  (to_dict)
  [cb37c14faf2d9f23]   EXAC  _ps_rows  L=7 N=2 saved=7 sim=1.00
      src/koru/autonomy/operator/operator_process_guard.py:90-96  (_ps_rows)
      src/koru/autonomy/operator/operator_processes.py:129-135  (_ps_rows)
  [ee4f810c8a8578ba]   EXAC  _project_venv_roots  L=7 N=2 saved=7 sim=1.00
      src/koru/autonomy/operator/operator_runtime.py:136-142  (_project_venv_roots)
      src/koru/autonomy/readiness/readiness.py:67-73  (_project_venv_roots)
  [5f21bf4c3e09a1f6]   EXAC  _plugin_package_version  L=7 N=2 saved=7 sim=1.00
      src/koru/autopilot/install_plugin_cli.py:64-70  (_plugin_package_version)
      src/koruide/plugin_installer.py:356-362  (_plugin_package_version)
  [fde5fdee8e8ce519]   EXAC  _plugin_package_name  L=7 N=2 saved=7 sim=1.00
      src/koru/autopilot/install_plugin_cli.py:73-79  (_plugin_package_name)
      src/koruide/plugin_installer.py:365-371  (_plugin_package_name)
  [78494b404ee9f400]   EXAC  _peek_project_from_argv  L=7 N=2 saved=7 sim=1.00
      src/koru/cli.py:98-104  (_peek_project_from_argv)
      src/koru/cli_auto.py:21-27  (_peek_project_from_argv)
  [989b5cf56bd7f313]   STRU  _initialize_cycle_telemetry  L=7 N=2 saved=7 sim=1.00
      src/koru/autonomy/cycle_planning.py:27-33  (_initialize_cycle_telemetry)
      src/koru/autonomy/operator/operator_loop_interfaces.py:123-129  (_default_dashboard_action_urls)
  [ef7f66957e5a38eb]   STRU  as_managed  L=7 N=2 saved=7 sim=1.00
      src/koru/autonomy/operator/operator_process_guard.py:213-219  (as_managed)
      src/koru/autonomy/operator/operator_processes.py:249-255  (_as_managed)
  [97e1ac5706fcec61]   STRU  _make_ticket_open_builder  L=7 N=2 saved=7 sim=1.00
      src/koru/autonomy/replay_parser.py:66-72  (_make_ticket_open_builder)
      src/koru/autonomy/replay_parser.py:75-81  (_make_autopilot_retry_builder)
  [222574456e787027]   STRU  _auto_open_ide_enabled  L=7 N=2 saved=7 sim=1.00
      src/koru/integrations/vdisplay_client.py:1469-1475  (_auto_open_ide_enabled)
      src/koru/integrations/vdisplay_client.py:1763-1769  (_raise_alt_tab_enabled)
  [e32f815fd1c34302]   STRU  is_shell_agent  L=7 N=2 saved=7 sim=1.00
      src/koru/tillm_bridge.py:108-114  (is_shell_agent)
      src/koru/tillm_bridge.py:117-123  (shell_agent_available)
  [96834fd32f12daa6]   STRU  shell_tool_registry_entries  L=7 N=2 saved=7 sim=1.00
      src/koru/tillm_bridge.py:135-141  (shell_tool_registry_entries)
      src/koru/tillm_bridge.py:144-150  (shell_agent_backend_profiles)
  [bd28c835fc8ef07e]   STRU  cmd_providers_list  L=7 N=2 saved=7 sim=1.00
      src/koruobserve/providers_cli.py:117-123  (cmd_providers_list)
      src/koruobserve/providers_cli.py:142-148  (cmd_providers_reset)
  [F0052]   FUZZ  capture_one  L=8 N=2 saved=8 sim=0.87
      src/koruvision/providers/browser_getdisplay.py:259-266  (capture_one)
      src/koruvision/providers/portal_screencast.py:314-323  (capture_one)
  [F0039]   FUZZ  validate_payload  L=7 N=2 saved=7 sim=0.96
      packages/dsl2coru/src/dsl2coru/codegen.py:45-51  (validate_payload)
      packages/dsl2koru/src/dsl2koru/codegen.py:50-56  (validate_payload)
  [F0046]   FUZZ  _planfile_command_base  L=7 N=2 saved=7 sim=0.95
      src/koru/context.py:157-163  (_planfile_command_base)
      src/koru/gc.py:99-107  (_planfile_command_base)
  [F0047]   FUZZ  _read_proc_cwd  L=7 N=2 saved=7 sim=0.93
      src/koru/wizard/project.py:42-48  (_read_proc_cwd)
      src/koruapi/dashboard_projects.py:222-228  (_read_proc_cwd_path)
  [F0045]   FUZZ  save_config  L=7 N=2 saved=7 sim=0.93
      src/koru/cli_shell.py:101-107  (save_config)
      src/koru/configurator/store.py:27-34  (save_project_config)
  [F0038]   FUZZ  json_response  L=7 N=2 saved=7 sim=0.92
      packages/coru/src/coru/supervisor/http_util.py:12-18  (json_response)
      src/koruapi/server.py:20-26  (_json_response)
  [F0043]   FUZZ  _identify_failing_services  L=7 N=2 saved=7 sim=0.89
      src/koru/autonomy/operator/operator_wup.py:680-686  (_identify_failing_services)
      src/koru/autonomy/operator/operator_wup.py:689-695  (_identify_interrupted_services)
  [F0041]   FUZZ  _extract_chat  L=7 N=2 saved=7 sim=0.88
      packages/dsl2coru/src/dsl2coru/pb_codec.py:207-213  (_extract_chat)
      packages/dsl2coru/src/dsl2coru/pb_codec.py:216-224  (_extract_text)
  [F0042]   FUZZ  _confirm_replace_existing  L=7 N=2 saved=7 sim=0.87
      src/koru/autonomy/operator/operator_processes.py:343-349  (_confirm_replace_existing)
      src/koru/autonomy/operator/operator_process_guard.py:264-271  (confirm_replace_existing)
  [F0044]   FUZZ  history  L=7 N=2 saved=7 sim=0.87
      src/koru/bounded_contexts/autonomous_checkpoint/application.py:83-89  (history)
      src/koru/bounded_contexts/env_config/application.py:65-71  (history)
  [258406aa1abf3ccd]   EXAC  _require_fastmcp  L=6 N=2 saved=6 sim=1.00
      packages/mcp2coru/src/mcp2coru/server.py:9-14  (_require_fastmcp)
      packages/mcp2koru/src/mcp2koru/server.py:9-14  (_require_fastmcp)
  [e4f69d6ce48d3dc0]   EXAC  all_events  L=6 N=2 saved=6 sim=1.00
      src/koru/cqrs/event_store.py:119-124  (all_events)
      src/koru/cqrs/event_store.py:197-202  (all_events)
  [d5c3295002f07996]   EXAC  events_for_aggregate  L=6 N=2 saved=6 sim=1.00
      src/koru/cqrs/event_store.py:126-131  (events_for_aggregate)
      src/koru/cqrs/event_store.py:204-209  (events_for_aggregate)
  [af3561a785bacc8b]   EXAC  is_wayland  L=6 N=2 saved=6 sim=1.00
      src/koruvision/capture_mss.py:40-45  (is_wayland)
      src/koruvision/providers/env.py:20-24  (is_wayland)
  [4b60b1bcf17e7c24]   STRU  _desktop_capture_enabled  L=6 N=2 saved=6 sim=1.00
      packages/coru/src/coru/cli_calibration.py:37-42  (_desktop_capture_enabled)
      packages/coru/src/coru/cli_checks.py:71-76  (_coru_readiness_strict)
  [be501d3b90a4ac07]   STRU  _collect_manage_issue_problems  L=6 N=2 saved=6 sim=1.00
      packages/coru/src/coru/repair/diagnostics.py:98-103  (_collect_manage_issue_problems)
      packages/coru/src/coru/repair/diagnostics.py:132-137  (_collect_manage_action_problems)
  [0710f1bef3aa0a6c]   STRU  _extract_status  L=3 N=3 saved=6 sim=1.00
      packages/dsl2coru/src/dsl2coru/pb_codec.py:147-149  (_extract_status)
      packages/dsl2coru/src/dsl2coru/pb_codec.py:182-184  (_extract_ensure)
      packages/dsl2coru/src/dsl2coru/pb_codec.py:227-229  (_extract_sync)
  [6bffcd9bb5d5e36f]   STRU  _serialize_status  L=3 N=3 saved=6 sim=1.00
      packages/dsl2coru/src/dsl2coru/serializer.py:16-18  (_serialize_status)
      packages/dsl2coru/src/dsl2coru/serializer.py:44-46  (_serialize_ensure)
      packages/dsl2coru/src/dsl2coru/serializer.py:82-84  (_serialize_sync)
  [5c89921502e44cf7]   STRU  uri_for_cmd  L=6 N=2 saved=6 sim=1.00
      packages/uri2coru/src/uri2coru/uri.py:29-34  (uri_for_cmd)
      packages/uri2koru/src/uri2koru/uri.py:28-33  (uri_for_cmd)
  [216de124459efb05]   STRU  _error_stagnation_threshold  L=6 N=2 saved=6 sim=1.00
      src/koru/autonomy/cycle/cycle.py:206-211  (_error_stagnation_threshold)
      src/koru/autonomy/planning_llm_runtime.py:23-28  (request_timeout)
  [8b82987ab9561a93]   STRU  process_cwd  L=6 N=2 saved=6 sim=1.00
      src/koru/autonomy/operator/operator_process_guard.py:45-50  (process_cwd)
      src/koru/autonomy/operator/operator_processes.py:91-96  (_process_cwd)
  [f7f221a1339ae592]   STRU  _scan_result_is_create_failed_only  L=6 N=2 saved=6 sim=1.00
      src/koru/autonomy/phases/scan_phase.py:88-93  (_scan_result_is_create_failed_only)
      src/koru/autonomy/phases/scan_phase.py:96-101  (_scan_result_is_duplicate_only)
  [b249349ec570c160]   STRU  _make_ide_builder  L=6 N=2 saved=6 sim=1.00
      src/koru/autonomy/replay_parser.py:42-47  (_make_ide_builder)
      src/koru/autonomy/replay_parser.py:50-55  (_make_ticket_builder)
  [10dd57a987c3e95b]   STRU  _previous_serve_config  L=3 N=3 saved=6 sim=1.00
      src/koru/configurator/prompting.py:60-62  (_previous_serve_config)
      src/koru/task_dedupe.py:14-16  (_source_context)
      src/koruapi/dashboard_config.py:67-69  (_saved_serve_config)
  [08e658ea14cb595d]   STRU  _check_autopilot_chat_control  L=6 N=2 saved=6 sim=1.00
      src/koru/doctor.py:295-300  (_check_autopilot_chat_control)
      src/koru/doctor.py:440-445  (_check_pytest_collect)
  [0d005aa18043a63d]   STRU  chat_control_command_hints  L=6 N=2 saved=6 sim=1.00
      src/koru/doctor_chat_control.py:267-272  (chat_control_command_hints)
      src/koru/doctor_reporting_checks.py:145-150  (_chat_control_command_hints)
  [becaae80b8e4fa55]   STRU  _read_json_file  L=6 N=2 saved=6 sim=1.00
      src/koru/doctor_plugin_bundle.py:12-17  (_read_json_file)
      src/koruide/daemon/metadata.py:73-78  (read_daemon_metadata)
  [2df6406b0fae7195]   STRU  vql_max_age_seconds  L=6 N=2 saved=6 sim=1.00
      src/koru/integrations/autonomy_session.py:21-26  (vql_max_age_seconds)
      src/koruvision/providers/obs_websocket.py:32-37  (obs_screenshot_width)
  [1c512b73f34f3551]   STRU  set_component_enabled  L=6 N=2 saved=6 sim=1.00
      src/koru/topology.py:364-369  (set_component_enabled)
      src/koru/topology.py:372-377  (set_pipeline_enabled)
  [484cbd493df1c900]   STRU  keyboard  L=6 N=2 saved=6 sim=1.00
      src/koruide/ides/jetbrains.py:68-73  (keyboard)
      src/koruide/ides/zed.py:49-54  (keyboard)
  [F0040]   FUZZ  _parse_chat  L=7 N=2 saved=7 sim=0.85
      packages/dsl2coru/src/dsl2coru/parser.py:122-128  (_parse_chat)
      packages/dsl2coru/src/dsl2coru/parser.py:131-140  (_parse_text)
  [F0034]   FUZZ  _split_quick_action  L=6 N=2 saved=6 sim=0.92
      src/koru/autonomy/operator/operator_loop_quick_actions.py:256-261  (_split_quick_action)
      src/koru/autonomy/replay_quick_actions.py:84-90  (_split_quick_action_text)
  [F0033]   FUZZ  replay  L=6 N=2 saved=6 sim=0.92
      packages/dsl2coru/src/dsl2coru/events.py:166-171  (replay)
      packages/dsl2koru/src/dsl2koru/events.py:164-169  (replay)
  [F0035]   FUZZ  _path_is_relative_to  L=6 N=2 saved=6 sim=0.88
      src/koru/autonomy/operator/operator_runtime.py:88-93  (_path_is_relative_to)
      src/koru/self_control.py:185-190  (_is_relative_to)
  [F0037]   FUZZ  _read_proc_cmdline  L=6 N=2 saved=6 sim=0.86
      src/koru/wizard/project.py:34-39  (_read_proc_cmdline)
      src/koruide/ide.py:216-223  (_read_cmdline)
  [0d7e470a2273975b]   EXAC  main  L=5 N=2 saved=5 sim=1.00
      packages/dsl2coru/src/dsl2coru/cli.py:34-38  (main)
      packages/dsl2koru/src/dsl2koru/cli.py:34-38  (main)
  [26ead517a722bf54]   EXAC  _handle_subcommand  L=5 N=2 saved=5 sim=1.00
      packages/dsl2coru/src/dsl2coru/cli.py:200-204  (_handle_subcommand)
      packages/dsl2koru/src/dsl2koru/cli.py:175-179  (_handle_subcommand)
  [20f510bd73dd85e4]   EXAC  envelope_from_json  L=5 N=2 saved=5 sim=1.00
      packages/dsl2coru/src/dsl2coru/codec.py:45-49  (envelope_from_json)
      packages/dsl2koru/src/dsl2koru/codec.py:45-49  (envelope_from_json)
  [a06569fb85c4f8bf]   EXAC  get_backend  L=5 N=2 saved=5 sim=1.00
      packages/nlp2coru/src/nlp2coru/llm_backend.py:88-92  (get_backend)
      packages/nlp2koru/src/nlp2koru/llm_backend.py:90-94  (get_backend)
  [e33387610a1ba207]   EXAC  png_dimensions  L=5 N=2 saved=5 sim=1.00
      src/koruvision/capture_mss.py:48-52  (png_dimensions)
      src/koruvision/providers/base.py:54-58  (png_dimensions)
  [ec19a11b25e7c9d7]   STRU  parse_text  L=5 N=2 saved=5 sim=1.00
      packages/dsl2coru/src/dsl2coru/codec.py:24-28  (parse_text)
      packages/dsl2koru/src/dsl2koru/codec.py:24-28  (parse_text)
  [317f28deca4b61d0]   STRU  _parse_ui_click  L=5 N=2 saved=5 sim=1.00
      packages/dsl2coru/src/dsl2coru/parser.py:188-192  (_parse_ui_click)
      packages/dsl2coru/src/dsl2coru/parser.py:195-199  (_parse_ui_nl)
  [3be4a90cebac6fff]   STRU  encode_text_to_protobuf  L=5 N=2 saved=5 sim=1.00
      packages/dsl2coru/src/dsl2coru/pb_codec.py:279-283  (encode_text_to_protobuf)
      packages/dsl2koru/src/dsl2koru/pb_codec.py:139-143  (encode_text_to_protobuf)
  [c7b6c1484a2d6306]   STRU  _parse_query_lane_status  L=5 N=2 saved=5 sim=1.00
      packages/dsl2koru/src/dsl2koru/grammar.py:29-33  (_parse_query_lane_status)
      packages/dsl2koru/src/dsl2koru/grammar.py:36-40  (_parse_validate_lane)
  [c0991cbe06d43b2a]   STRU  coru_run_command_pb  L=5 N=2 saved=5 sim=1.00
      packages/mcp2coru/src/mcp2coru/tools.py:20-24  (coru_run_command_pb)
      packages/mcp2koru/src/mcp2koru/tools.py:20-24  (koru_run_command_pb)
  [baca39d842972662]   STRU  _cmd_repair_history  L=5 N=2 saved=5 sim=1.00
      packages/uri2coru/src/uri2coru/decode.py:14-18  (_cmd_repair_history)
      packages/uri2coru/src/uri2coru/decode.py:66-70  (_block_repair_history)
  [84b7aabad69d2bbd]   STRU  _koru_package_version  L=5 N=2 saved=5 sim=1.00
      src/koru/agents.py:85-89  (_koru_package_version)
      src/koru/autonomy/configuration/config_startup.py:40-44  (koru_distribution_version)
  [0ecbec51bf9cb1b0]   STRU  _env_float  L=5 N=2 saved=5 sim=1.00
      src/koru/autonomy/nxdo_discovery.py:125-129  (_env_float)
      src/koru/autonomy/nxdo_discovery.py:132-136  (_env_int)
  [63f1c3b70d9a6d6a]   STRU  _blocked_interface_items  L=5 N=2 saved=5 sim=1.00
      src/koru/autonomy/operator/operator_loop_interfaces.py:53-57  (_blocked_interface_items)
      src/koru/doctor_autopilot_checks.py:272-276  (_daemon_plugin_rows)
  [e608a5a393583e20]   STRU  _socket_inode  L=5 N=2 saved=5 sim=1.00
      src/koru/autonomy/readiness/readiness.py:462-466  (_socket_inode)
      src/koruide/daemon/metadata.py:118-122  (_inode)
  [78e38092902981cb]   STRU  _package_version  L=5 N=2 saved=5 sim=1.00
      src/koru/autopilot/install_manager.py:172-176  (_package_version)
      src/koru/self_control.py:136-140  (_installed_version)
  [f214ebc61ba391f5]   STRU  runtime_for_project  L=5 N=2 saved=5 sim=1.00
      src/koru/cqrs/__init__.py:61-65  (runtime_for_project)
      src/koru/cqrs/__init__.py:68-76  (runtime_for_storage_dir)
  [8745b82e7c4fd665]   STRU  _check_autopilot_debug_log  L=5 N=2 saved=5 sim=1.00
      src/koru/doctor.py:260-264  (_check_autopilot_debug_log)
      src/koru/doctor.py:311-315  (_check_windsurf_chat_column_control)
  [216d583ed2c65b80]   STRU  windsurf_line_mentions_chat_open_command  L=5 N=2 saved=5 sim=1.00
      src/koru/doctor_chat_control.py:383-387  (windsurf_line_mentions_chat_open_command)
      src/koru/doctor_reporting_checks.py:312-316  (_windsurf_line_mentions_chat_open_command)
  [71fd4695f2c835ff]   STRU  _koru_version  L=5 N=2 saved=5 sim=1.00
      src/koru/local_manager_client.py:23-27  (_koru_version)
      src/koru/local_manager_state.py:20-24  (koru_version)
  [1da513afdd4b2df0]   STRU  planfile_dir  L=5 N=2 saved=5 sim=1.00
      src/koru/runtime.py:42-46  (planfile_dir)
      src/koruapi/dashboard_serve_utils.py:158-162  (_build_handler_for)
  [a85ea5a7e37dcddf]   STRU  _handle_error  L=5 N=2 saved=5 sim=1.00
      src/korudsl/library.py:58-62  (_handle_error)
      src/korudsl/library.py:65-69  (_handle_correct)
  [3feaa15cb204afa2]   STRU  terminal  L=5 N=2 saved=5 sim=1.00
      src/koruide/ides/antigravity.py:35-39  (terminal)
      src/koruide/ides/qoder.py:34-38  (terminal)
  [3bb87e332b7bbbe9]   STRU  detection  L=5 N=2 saved=5 sim=1.00
      src/koruide/ides/vscode.py:27-31  (detection)
      src/koruide/ides/windsurf.py:28-34  (detection)
  [322d974cc48eae57]   STRU  aliases  L=5 N=2 saved=5 sim=1.00
      src/koruide/ides/vscode.py:47-51  (aliases)
      src/koruide/ides/vscodium.py:33-37  (aliases)
  [F0024]   FUZZ  _optional_str  L=5 N=2 saved=5 sim=0.97
      src/koru/autonomy/drive_result.py:165-169  (_optional_str)
      src/koru/observability_dsl.py:395-399  (_optional_str)
  [F0032]   FUZZ  plugin  L=5 N=2 saved=5 sim=0.96
      src/koruide/ides/jetbrains.py:61-65  (plugin)
      src/koruide/ides/zed.py:42-46  (plugin)
  [F0022]   FUZZ  schema_for_verb  L=5 N=2 saved=5 sim=0.95
      packages/dsl2coru/src/dsl2coru/schema_registry.py:62-66  (schema_for_verb)
      packages/dsl2koru/src/dsl2koru/schema_registry.py:27-31  (schema_for_verb)
  [F0025]   FUZZ  _wayland_session  L=5 N=2 saved=5 sim=0.93
      src/koru/autonomy/operator_pipeline.py:354-358  (_wayland_session)
      src/koru/ide_adapters/gillm_recovery.py:49-53  (_is_wayland_session)
  [F0029]   FUZZ  _source_tool  L=5 N=2 saved=5 sim=0.92
      src/koru/queue/runner.py:34-38  (_source_tool)
      src/koru/queue/ticket.py:40-44  (_source_tool)
  [F0027]   FUZZ  state_vscdb_path  L=5 N=2 saved=5 sim=0.92
      src/koru/ide_adapters/shared.py:162-166  (state_vscdb_path)
      src/koruide/ides/base.py:141-145  (state_vscdb_path)
  [F0028]   FUZZ  _int  L=5 N=2 saved=5 sim=0.90
      src/koru/integrations/photo_vql_llm_detect.py:333-337  (_int)
      src/koru/ticket_evidence.py:305-309  (_int_or_none)
  [F0023]   FUZZ  _coerce_event_ts  L=5 N=2 saved=5 sim=0.90
      src/koru/autonomy/cycle_events.py:23-27  (_coerce_event_ts)
      src/koru/autonomy/events.py:57-61  (_event_ts)
  [F0026]   FUZZ  summary  L=5 N=2 saved=5 sim=0.89
      src/koru/doctor_models.py:38-42  (summary)
      src/koru/self_control.py:87-91  (summary)
  [F0031]   FUZZ  __init__  L=5 N=2 saved=5 sim=0.89
      src/koruide/__init__.py:33-37  (__init__)
      src/koruide/__init__.py:39-43  (_gillm_missing)
  [F0021]   FUZZ  _set_chat  L=5 N=2 saved=5 sim=0.86
      packages/dsl2coru/src/dsl2coru/pb_codec.py:84-88  (_set_chat)
      packages/dsl2coru/src/dsl2coru/pb_codec.py:91-97  (_set_text)
  [F0030]   FUZZ  _write_sprint_file  L=5 N=2 saved=5 sim=0.85
      src/koruapi/dashboard_tickets.py:230-234  (_write_sprint_file)
      src/koru/task_io.py:40-45  (_write_yaml)
  [d11f9391aeb7f051]   EXAC  _terminal_ide_hint  L=4 N=2 saved=4 sim=1.00
      packages/coru/src/coru/cli.py:850-853  (_terminal_ide_hint)
      packages/coru/src/coru/cli_terminal.py:26-29  (_terminal_ide_hint)
  [7cafaf118d44de19]   EXAC  decode_protobuf  L=4 N=2 saved=4 sim=1.00
      packages/dsl2coru/src/dsl2coru/pb_codec.py:273-276  (decode_protobuf)
      packages/dsl2koru/src/dsl2koru/pb_codec.py:133-136  (decode_protobuf)
  [07b42f4655a7b6a4]   EXAC  __post_init__  L=4 N=2 saved=4 sim=1.00
      packages/mcp2coru/src/mcp2coru/server.py:21-24  (__post_init__)
      packages/mcp2koru/src/mcp2koru/server.py:21-24  (__post_init__)
  [962ce98f78874f51]   EXAC  _cycle_attr  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomy/cycle/cycle_chat_activity.py:80-83  (_cycle_attr)
      src/koru/autonomy/cycle/cycle_drive_retry.py:84-87  (_cycle_attr)
  [d994225d45fadf8d]   EXAC  _terminal_host_ide_id  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomy/operator/operator_plugin_wait.py:27-30  (_terminal_host_ide_id)
      src/koru/ide_adapters/ide_reload.py:511-514  (_terminal_host_ide_id)
  [550fc3ddceaad290]   STRU  _handle_exec  L=4 N=2 saved=4 sim=1.00
      packages/cli2coru/src/cli2coru/cli.py:40-43  (_handle_exec)
      packages/cli2koru/src/cli2koru/cli.py:40-43  (_handle_exec)
  [708ce22a2f938271]   STRU  coru_run_command  L=4 N=2 saved=4 sim=1.00
      packages/mcp2coru/src/mcp2coru/tools.py:8-11  (coru_run_command)
      packages/mcp2koru/src/mcp2koru/tools.py:8-11  (koru_run_command)
  [7ca26e968f2542e2]   STRU  coru_run_dsl  L=4 N=2 saved=4 sim=1.00
      packages/mcp2coru/src/mcp2coru/tools.py:14-17  (coru_run_dsl)
      packages/mcp2koru/src/mcp2koru/tools.py:14-17  (koru_run_dsl)
  [d65b8fbb50933866]   STRU  status_in_skip_list  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomy/checkpoint/checkpoint.py:204-207  (status_in_skip_list)
      src/koru/autonomy/cycle/cycle_common.py:17-20  (_status_in_skip_list)
  [567c95f995899ebb]   STRU  _build_queue_command  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomy/cycle_queue_scan.py:57-60  (_build_queue_command)
      src/koru/autonomy/phases/queue_phase.py:48-51  (build_queue_command)
  [7c9e9272487e6fed]   STRU  _looks_like_autonomous_up_command  L=4 N=2 saved=4 sim=1.00
      src/koru/autonomy/operator/operator_processes.py:123-126  (_looks_like_autonomous_up_command)
      src/koruobserve/providers_cli.py:10-13  (screencast_session_path)
  [a081dc2ccbd1c8f8]   STRU  _deferred_submit_unverified_grace_seconds  L=4 N=2 saved=4 sim=1.00
      src/koruide/daemon/handlers_ack.py:290-293  (_deferred_submit_unverified_grace_seconds)
      src/koruide/host_setup.py:42-45  (_ydotoold_socket_path)
  [F0016]   FUZZ  get_events  L=4 N=2 saved=4 sim=0.96
      packages/rest2coru/src/rest2coru/app.py:55-58  (get_events)
      packages/rest2koru/src/rest2koru/app.py:56-59  (get_events)
  [F0020]   FUZZ  __init__  L=4 N=2 saved=4 sim=0.93
      src/koruide/command_catalog_store.py:63-66  (__init__)
      src/koruide/command_telemetry.py:27-30  (__init__)
  [F0019]   FUZZ  _get_config  L=4 N=2 saved=4 sim=0.89
      src/koruapi/dashboard_routes.py:90-93  (_get_config)
      src/koruapi/dashboard_routes.py:100-103  (_get_context)
  [F0017]   FUZZ  list_running_ides  L=4 N=2 saved=4 sim=0.88
      src/koru/remote/client.py:50-53  (list_running_ides)
      src/koru/remote/client.py:55-58  (list_connected_plugins)
  [b2839dfd88070156]   EXAC  _ide_from_vscode_pid  L=3 N=2 saved=3 sim=1.00
      packages/coru/src/coru/cli.py:835-837  (_ide_from_vscode_pid)
      packages/coru/src/coru/cli_terminal.py:11-13  (_ide_from_vscode_pid)
  [0ef5883de15b8a06]   EXAC  _vscode_family_env_hint  L=3 N=2 saved=3 sim=1.00
      packages/coru/src/coru/cli.py:840-842  (_vscode_family_env_hint)
      packages/coru/src/coru/cli_terminal.py:16-18  (_vscode_family_env_hint)
  [494f7040b5a29b28]   EXAC  _windsurf_terminal_marker  L=3 N=2 saved=3 sim=1.00
      packages/coru/src/coru/cli.py:845-847  (_windsurf_terminal_marker)
      packages/coru/src/coru/cli_terminal.py:21-23  (_windsurf_terminal_marker)
  [9830c9e6217c53fe]   EXAC  envelope_from_bytes  L=3 N=2 saved=3 sim=1.00
      packages/dsl2coru/src/dsl2coru/codec.py:36-38  (envelope_from_bytes)
      packages/dsl2koru/src/dsl2koru/codec.py:36-38  (envelope_from_bytes)
  [612455214cf99e7e]   EXAC  get_fallback_model  L=3 N=2 saved=3 sim=1.00
      packages/nlp2coru/src/nlp2coru/openrouter_config.py:63-65  (get_fallback_model)
      packages/nlp2koru/src/nlp2koru/openrouter_config.py:63-65  (get_fallback_model)
  [874d2545784625c8]   EXAC  get_ollama_base_url  L=3 N=2 saved=3 sim=1.00
      packages/nlp2coru/src/nlp2coru/openrouter_config.py:68-70  (get_ollama_base_url)
      packages/nlp2koru/src/nlp2koru/openrouter_config.py:68-70  (get_ollama_base_url)
  [daadb38a8779d73e]   EXAC  should_use_ollama_fallback  L=3 N=2 saved=3 sim=1.00
      packages/nlp2coru/src/nlp2coru/openrouter_config.py:73-75  (should_use_ollama_fallback)
      packages/nlp2koru/src/nlp2koru/openrouter_config.py:73-75  (should_use_ollama_fallback)
  [01715126eaca72c6]   EXAC  validate_all  L=3 N=2 saved=3 sim=1.00
      packages/rest2coru/src/rest2coru/app.py:28-30  (validate_all)
      packages/rest2koru/src/rest2koru/app.py:29-31  (validate_all)
  [691a97cbc778581c]   EXAC  allow_keyboard_autopilot_fallback  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomy/cycle/cycle_gate.py:341-343  (allow_keyboard_autopilot_fallback)
      src/koru/autonomy/env.py:323-325  (allow_keyboard_autopilot_fallback)
  [7ee750a1b7660a3e]   EXAC  to_json  L=3 N=2 saved=3 sim=1.00
      src/koru/deployment_events/batch.py:34-36  (to_json)
      src/koru/deployment_events/models.py:98-100  (to_json)
  [727da6a61b64086c]   EXAC  __init__  L=3 N=2 saved=3 sim=1.00
      src/koru/local_manager_state.py:57-59  (__init__)
      src/koru/local_manager_state.py:73-75  (__init__)
  [836645be6056623e]   EXAC  _bound_port  L=3 N=2 saved=3 sim=1.00
      src/koru/local_service.py:329-331  (_bound_port)
      src/koruapi/dashboard_serve_utils.py:170-172  (_bound_port)
  [dfeb14021be03fc6]   EXAC  capture_one  L=3 N=2 saved=3 sim=1.00
      src/koruvision/providers/cli_tools.py:37-39  (capture_one)
      src/koruvision/providers/obs_websocket.py:229-231  (capture_one)
  [8ed48e3ec37f0414]   STRU  envelope_to_bytes  L=3 N=2 saved=3 sim=1.00
      packages/dsl2coru/src/dsl2coru/codec.py:31-33  (envelope_to_bytes)
      packages/dsl2koru/src/dsl2koru/codec.py:31-33  (envelope_to_bytes)
  [d9a971aa6171193c]   STRU  _parse_status  L=3 N=2 saved=3 sim=1.00
      packages/dsl2coru/src/dsl2coru/parser.py:56-58  (_parse_status)
      packages/dsl2coru/src/dsl2coru/parser.py:96-98  (_parse_ensure)
  [17c825446e10cd5f]   STRU  _set_env  L=3 N=2 saved=3 sim=1.00
      packages/dsl2coru/src/dsl2coru/pb_codec.py:33-35  (_set_env)
      packages/dsl2coru/src/dsl2coru/pb_codec.py:38-40  (_set_query)
  [ee946c0cbdf0032c]   STRU  _extract_env  L=3 N=2 saved=3 sim=1.00
      packages/dsl2coru/src/dsl2coru/pb_codec.py:152-154  (_extract_env)
      packages/dsl2coru/src/dsl2coru/pb_codec.py:157-159  (_extract_query)
  [8023064d62f0ab26]   STRU  _serialize_query  L=3 N=2 saved=3 sim=1.00
      packages/dsl2coru/src/dsl2coru/serializer.py:26-28  (_serialize_query)
      packages/dsl2coru/src/dsl2coru/serializer.py:105-107  (_serialize_ui_key)
  [44896c597fe520b5]   STRU  _serialize_ui_click  L=3 N=2 saved=3 sim=1.00
      packages/dsl2coru/src/dsl2coru/serializer.py:110-112  (_serialize_ui_click)
      packages/dsl2coru/src/dsl2coru/serializer.py:115-117  (_serialize_ui_nl)
  [c7928b5e56a5a509]   STRU  _set_query_lane_status  L=3 N=2 saved=3 sim=1.00
      packages/dsl2koru/src/dsl2koru/pb_codec.py:28-30  (_set_query_lane_status)
      packages/dsl2koru/src/dsl2koru/pb_codec.py:33-35  (_set_validate_lane)
  [6e4a5073c9e5aad0]   STRU  _extract_query_lane_status  L=3 N=2 saved=3 sim=1.00
      packages/dsl2koru/src/dsl2koru/pb_codec.py:78-80  (_extract_query_lane_status)
      packages/dsl2koru/src/dsl2koru/pb_codec.py:83-85  (_extract_validate_lane)
  [169231925d2d93b5]   STRU  _normalize_autonomous_argv  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomous.py:1155-1157  (_normalize_autonomous_argv)
      src/koru/wizard/cli.py:51-53  (propose_projects)
  [8e7a26ce69f52271]   STRU  _apply_auto_pipeline_flags  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomous.py:1174-1176  (_apply_auto_pipeline_flags)
      src/koru/autonomous.py:1179-1181  (_apply_replace_existing_flags)
  [3da708360c5e1041]   STRU  llm_needs_input_ticket_queue_name  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomy/cycle/cycle_chat_activity_config.py:95-97  (llm_needs_input_ticket_queue_name)
      src/koru/autonomy/cycle/cycle_chat_activity_config.py:100-102  (llm_needs_input_ticket_priority)
  [c2157008fcba0025]   STRU  _auto_llm_ready_enabled  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomy/cycle/cycle_skip_conditions.py:41-43  (_auto_llm_ready_enabled)
      src/koru/autonomy/operator_pipeline.py:408-410  (_self_control_autorepair_enabled)
  [6e8f4ef0b45bb9e8]   STRU  _chat_selectors_for  L=3 N=2 saved=3 sim=1.00
      src/koru/integrations/vdisplay_client.py:3178-3180  (_chat_selectors_for)
      src/koru/integrations/vdisplay_client.py:3183-3185  (_submit_selectors_for)
  [a76daab0eab71bd5]   STRU  redup_scan_command  L=3 N=2 saved=3 sim=1.00
      src/koru/redup_integration.py:22-24  (redup_scan_command)
      src/koru/redup_integration.py:27-29  (redup_check_command)
  [c2ebc39776cc26a8]   STRU  build_dashboard_handler  L=3 N=2 saved=3 sim=1.00
      src/koruapi/dashboard_routes.py:605-607  (build_dashboard_handler)
      src/koruapi/dashboard_serve.py:94-96  (_build_handler)
  [f45ec1832a13dbbb]   STRU  supported_autopilot_ide_ids  L=3 N=2 saved=3 sim=1.00
      src/koruide/ide.py:132-134  (supported_autopilot_ide_ids)
      src/koruide/ide.py:142-144  (vscode_extension_plugin_ide_ids)
  [F0006]   FUZZ  _queue_loop_waiting_ticket_label  L=3 N=2 saved=3 sim=1.00
      src/koru/autonomy/cycle/cycle_common.py:12-14  (_queue_loop_waiting_ticket_label)
      src/koru/autonomy/checkpoint/checkpoint.py:22-25  (queue_loop_waiting_ticket_label)
  [F0004]   FUZZ  coru_run_command_pb  L=3 N=2 saved=3 sim=0.99
      packages/mcp2coru/src/mcp2coru/server.py:40-42  (coru_run_command_pb)
      packages/mcp2koru/src/mcp2koru/server.py:40-42  (koru_run_command_pb)
  [F0002]   FUZZ  coru_run_command  L=3 N=2 saved=3 sim=0.98
      packages/mcp2coru/src/mcp2coru/server.py:30-32  (coru_run_command)
      packages/mcp2koru/src/mcp2koru/server.py:30-32  (koru_run_command)
  [F0003]   FUZZ  coru_run_dsl  L=3 N=2 saved=3 sim=0.98
      packages/mcp2coru/src/mcp2coru/server.py:35-37  (coru_run_dsl)
      packages/mcp2koru/src/mcp2koru/server.py:35-37  (koru_run_dsl)
  [F0005]   FUZZ  coru_to_dsl  L=3 N=2 saved=3 sim=0.98
      packages/mcp2coru/src/mcp2coru/server.py:45-47  (coru_to_dsl)
      packages/mcp2koru/src/mcp2koru/server.py:45-47  (koru_to_dsl)
  [F0011]   FUZZ  from_json  L=3 N=2 saved=3 sim=0.97
      src/koru/deployment_events/batch.py:49-51  (from_json)
      src/koru/deployment_events/models.py:182-184  (from_json)
  [F0008]   FUZZ  builder  L=3 N=2 saved=3 sim=0.93
      src/koru/autonomy/replay_parser.py:44-46  (builder)
      src/koru/autonomy/replay_parser.py:52-54  (builder)
  [F0009]   FUZZ  __init__  L=3 N=2 saved=3 sim=0.92
      src/koru/configurator/prompting.py:18-20  (__init__)
      src/koru/wizard/prompters.py:22-24  (__init__)
  [F0010]   FUZZ  add_events  L=3 N=2 saved=3 sim=0.91
      src/koru/deployment_events/analyzer.py:17-19  (add_events)
      src/koru/deployment_events/batch.py:22-24  (add_event)
  [F0001]   FUZZ  _cmd_roundtrip  L=3 N=2 saved=3 sim=0.90
      packages/dsl2coru/src/dsl2coru/cli.py:154-156  (_cmd_roundtrip)
      packages/dsl2koru/src/dsl2koru/cli.py:135-137  (_cmd_roundtrip)
  [F0013]   FUZZ  is_https_url  L=3 N=2 saved=3 sim=0.89
      src/koru/wizard/templates.py:97-99  (is_https_url)
      src/koru/wizard/templates.py:102-104  (_looks_like_url)
  [F0007]   FUZZ  discover_ide_candidates  L=3 N=2 saved=3 sim=0.89
      src/koru/autonomy/operator/operator_onboarding.py:154-156  (discover_ide_candidates)
      src/koru/wizard/cli.py:46-48  (discover_installed_ides)
  [F0014]   FUZZ  keyboard  L=3 N=2 saved=3 sim=0.88
      src/koruide/ides/base.py:159-161  (keyboard)
      src/koruide/ides/base.py:237-241  (keyboard)
  [F0012]   FUZZ  _b  L=3 N=2 saved=3 sim=0.86
      src/koru/policy.py:149-151  (_b)
      src/koru/policy.py:159-161  (_ci_str)

REFACTOR[297] (ranked by priority):
  [1] ○ extract_function   → src/koru/utils/_scan_pyqual_report.py
      WHY: 3 occurrences of 26-line block across 1 files — saves 52 lines
      FILES: src/koru/scan.py
  [2] ◐ extract_module     → packages/utils/create_app.py
      WHY: 2 occurrences of 55-line block across 2 files — saves 55 lines
      FILES: packages/rest2coru/src/rest2coru/app.py, packages/rest2koru/src/rest2koru/app.py
  [3] ◐ extract_class      → packages/utils/complete.py
      WHY: 2 occurrences of 48-line block across 2 files — saves 48 lines
      FILES: packages/nlp2coru/src/nlp2coru/llm_backend.py, packages/nlp2koru/src/nlp2koru/llm_backend.py
  [4] ○ extract_function   → src/koru/autopilot/utils/_add_calibrate_parser.py
      WHY: 2 occurrences of 42-line block across 1 files — saves 42 lines
      FILES: src/koru/autopilot/cli_parser.py
  [5] ○ extract_function   → src/koru/autopilot/utils/check_plugin_version_mismatch_issue.py
      WHY: 2 occurrences of 41-line block across 1 files — saves 41 lines
      FILES: src/koru/autopilot/install_checks.py
  [6] ○ extract_function   → src/koru/autonomy/utils/collect_git_evidence.py
      WHY: 2 occurrences of 40-line block across 1 files — saves 40 lines
      FILES: src/koru/autonomy/verification_engine.py
  [7] ◐ extract_function   → src/koru/autonomy/utils/handle_post_run_verify.py
      WHY: 2 occurrences of 39-line block across 2 files — saves 39 lines
      FILES: src/koru/autonomy/cycle_queue_scan.py, src/koru/autonomy/phases/queue_phase.py
  [8] ○ extract_function   → src/utils/activity_enabled.py
      WHY: 13 occurrences of 3-line block across 10 files — saves 36 lines
      FILES: src/koru/activity_log.py, src/koru/autonomy/cycle/cycle_chat_activity_config.py, src/koru/autonomy/operator/operator_operator.py, src/koru/autonomy/operator/operator_processes.py, src/koru/autonomy/operator_pipeline.py +5 more
  [9] ○ extract_function   → src/koru/utils/emit_intent.py
      WHY: 7 occurrences of 6-line block across 1 files — saves 36 lines
      FILES: src/koru/observability_events.py
  [10] ○ extract_function   → src/koru/utils/_run.py
      WHY: 6 occurrences of 8-line block across 6 files — saves 40 lines
      FILES: src/koru/autonomy/cycle/cycle_chat_activity_tickets.py, src/koru/autonomy/operator_pipeline.py, src/koru/dev_sync.py, src/koru/scan.py, src/koru/ticket_evidence.py +1 more
  [11] ◐ extract_function   → src/koru/utils/analyze_chat_control.py
      WHY: 2 occurrences of 35-line block across 2 files — saves 35 lines
      FILES: src/koru/doctor_chat_control.py, src/koru/doctor_reporting_checks.py
  [12] ◐ extract_function   → packages/dsl2coru/src/dsl2coru/handlers/utils/run_command.py
      WHY: 2 occurrences of 33-line block across 2 files — saves 33 lines
      FILES: packages/dsl2coru/src/dsl2coru/handlers/command.py, packages/dsl2coru/src/dsl2coru/handlers/query.py
  [13] ◐ extract_function   → src/koru/utils/build_chat_control_detail_bits.py
      WHY: 2 occurrences of 33-line block across 2 files — saves 33 lines
      FILES: src/koru/doctor_chat_control.py, src/koru/doctor_reporting_checks.py
  [14] ◐ extract_function   → src/koru/utils/_run_idle_diagnostics.py
      WHY: 2 occurrences of 34-line block across 2 files — saves 34 lines
      FILES: src/koru/autonomous.py, src/koru/autonomy/cycle_diagnostics.py
  [15] ◐ extract_function   → src/koru/autonomy/utils/_ensure_standardized_discovery_follow_up.py
      WHY: 2 occurrences of 32-line block across 2 files — saves 32 lines
      FILES: src/koru/autonomy/cycle_queue_scan.py, src/koru/autonomy/phases/scan_phase.py
  [16] ○ extract_function   → src/koru/utils/provision_cursor.py
      WHY: 3 occurrences of 15-line block across 1 files — saves 30 lines
      FILES: src/koru/mcp_provision.py
  [17] ○ extract_function   → src/utils/_build_local_serve_parser.py
      WHY: 2 occurrences of 29-line block across 2 files — saves 29 lines
      FILES: src/koru/cli_local_serve.py, src/koruapi/local.py
  [18] ○ extract_function   → src/koru/utils/chat_control_result.py
      WHY: 2 occurrences of 29-line block across 2 files — saves 29 lines
      FILES: src/koru/doctor_chat_control.py, src/koru/doctor_reporting_checks.py
  [19] ○ extract_function   → src/koru/autonomy/utils/_emit_queue_iteration_event.py
      WHY: 2 occurrences of 29-line block across 2 files — saves 29 lines
      FILES: src/koru/autonomy/cycle_queue_scan.py, src/koru/autonomy/phases/queue_phase.py
  [20] ○ extract_function   → src/koru/utils/allow_cross_ide_autopilot.py
      WHY: 5 occurrences of 7-line block across 3 files — saves 28 lines
      FILES: src/koru/autonomy/env.py, src/koru/integrations/photo_vql_drive.py, src/koru/integrations/vdisplay_client.py
  [21] ○ extract_function   → packages/utils/main.py
      WHY: 2 occurrences of 26-line block across 2 files — saves 26 lines
      FILES: packages/cli2coru/src/cli2coru/cli.py, packages/cli2koru/src/cli2koru/cli.py
  [22] ○ extract_function   → packages/utils/run_shell.py
      WHY: 2 occurrences of 26-line block across 2 files — saves 26 lines
      FILES: packages/cli2coru/src/cli2coru/shell.py, packages/cli2koru/src/cli2koru/shell.py
  [23] ○ extract_function   → packages/utils/load_project_metadata.py
      WHY: 2 occurrences of 25-line block across 2 files — saves 25 lines
      FILES: packages/nlp2coru/src/nlp2coru/openrouter_config.py, packages/nlp2koru/src/nlp2koru/openrouter_config.py
  [24] ○ extract_function   → src/koru/wizard/utils/_finalise_ticket.py
      WHY: 2 occurrences of 25-line block across 2 files — saves 25 lines
      FILES: src/koru/wizard/cli.py, src/koru/wizard/orchestrator.py
  [25] ○ extract_function   → packages/coru/src/coru/repair/utils/_exec_cross_ide_guidance.py
      WHY: 2 occurrences of 25-line block across 1 files — saves 25 lines
      FILES: packages/coru/src/coru/repair/pipeline.py
  [26] ○ extract_function   → src/koruide/utils/message_sent.py
      WHY: 3 occurrences of 12-line block across 1 files — saves 24 lines
      FILES: src/koruide/protocol.py
  [27] ○ extract_function   → src/koru/utils/windsurf_chat_column_indexes.py
      WHY: 2 occurrences of 25-line block across 2 files — saves 25 lines
      FILES: src/koru/doctor_chat_control.py, src/koru/doctor_reporting_checks.py
  [28] ○ extract_function   → src/koru/utils/windsurf_chat_column_result.py
      WHY: 2 occurrences of 23-line block across 2 files — saves 23 lines
      FILES: src/koru/doctor_chat_control.py, src/koru/doctor_reporting_checks.py
  [29] ○ extract_function   → src/koruapi/utils/env2llm_get_desktop.py
      WHY: 2 occurrences of 23-line block across 1 files — saves 23 lines
      FILES: src/koruapi/env2llm_registry.py
  [30] ○ extract_function   → packages/coru/src/coru/supervisor/utils/stop_daemon.py
      WHY: 2 occurrences of 24-line block across 1 files — saves 24 lines
      FILES: packages/coru/src/coru/supervisor/daemon_ctl.py
  [31] ○ extract_function   → src/koruapi/utils/env2llm_get_registry.py
      WHY: 2 occurrences of 24-line block across 1 files — saves 24 lines
      FILES: src/koruapi/env2llm_registry.py
  [32] ○ extract_function   → src/koru/autonomy/utils/_run_code2llm_discovery_after_idle.py
      WHY: 2 occurrences of 25-line block across 2 files — saves 25 lines
      FILES: src/koru/autonomy/cycle_queue_scan.py, src/koru/autonomy/phases/scan_phase.py
  [33] ○ extract_function   → packages/coru/src/coru/utils/sync_plugins_for_ide.py
      WHY: 2 occurrences of 21-line block across 1 files — saves 21 lines
      FILES: packages/coru/src/coru/ecosystem.py
  [34] ○ extract_function   → src/koru/autonomy/operator/utils/_plugin_reconnected_after_wait.py
      WHY: 2 occurrences of 21-line block across 1 files — saves 21 lines
      FILES: src/koru/autonomy/operator/operator_plugin_wait.py
  [35] ○ extract_function   → src/koru/autonomy/operator/utils/ancestor_pids.py
      WHY: 2 occurrences of 21-line block across 2 files — saves 21 lines
      FILES: src/koru/autonomy/operator/operator_process_guard.py, src/koru/autonomy/operator/operator_processes.py
  [36] ○ extract_function   → packages/utils/_register_tools.py
      WHY: 2 occurrences of 22-line block across 2 files — saves 22 lines
      FILES: packages/mcp2coru/src/mcp2coru/server.py, packages/mcp2koru/src/mcp2koru/server.py
  [37] ○ extract_function   → src/koruvision/providers/utils/capture_one_with_providers.py
      WHY: 2 occurrences of 23-line block across 1 files — saves 23 lines
      FILES: src/koruvision/providers/detector.py
  [38] ○ extract_function   → src/koru/utils/_stdio_info.py
      WHY: 5 occurrences of 5-line block across 5 files — saves 20 lines
      FILES: src/koru/autonomous.py, src/koru/autonomy/checkpoint/checkpoint.py, src/koru/autonomy/cycle/cycle.py, src/koru/autonomy/operator/operator_daemon.py, src/koru/autonomy/operator/operator_processes.py
  [39] ○ extract_function   → src/koru/autonomy/operator/utils/_wup_process_match.py
      WHY: 2 occurrences of 20-line block across 2 files — saves 20 lines
      FILES: src/koru/autonomy/operator/operator_process_guard.py, src/koru/autonomy/operator/operator_processes.py
  [40] ○ extract_function   → src/korullm/strategies/utils/assess_drive_failure.py
      WHY: 2 occurrences of 20-line block across 2 files — saves 20 lines
      FILES: src/korullm/strategies/codex.py, src/korullm/strategies/ollama.py
  [41] ○ extract_function   → src/koru/utils/_live_plugin_version.py
      WHY: 2 occurrences of 19-line block across 2 files — saves 19 lines
      FILES: src/koru/autonomy/operator/operator_plugin_runtime.py, src/koru/decision_engine.py
  [42] ○ extract_function   → src/koru/autonomy/operator/utils/cleanup_autonomous_session.py
      WHY: 2 occurrences of 19-line block across 2 files — saves 19 lines
      FILES: src/koru/autonomy/operator/operator_daemon.py, src/koru/autonomy/operator/operator_runtime.py
  [43] ○ extract_function   → src/koru/utils/_installed_editable_source_root.py
      WHY: 2 occurrences of 19-line block across 2 files — saves 19 lines
      FILES: src/koru/autopilot/install_manager.py, src/koru/self_control.py
  [44] ○ extract_class      → src/koru/bounded_contexts/topology/utils/toggle_component.py
      WHY: 2 occurrences of 20-line block across 1 files — saves 20 lines
      FILES: src/koru/bounded_contexts/topology/application.py
  [45] ○ extract_function   → src/koru/autonomy/cycle/utils/autopilot_redrive_cooldown_seconds.py
      WHY: 2 occurrences of 17-line block across 1 files — saves 17 lines
      FILES: src/koru/autonomy/cycle/cycle_chat_activity_config.py
  [46] ○ extract_function   → src/koru/utils/_post_workers_register.py
      WHY: 2 occurrences of 17-line block across 1 files — saves 17 lines
      FILES: src/koru/local_service.py
  [47] ○ extract_function   → src/koru/autonomy/cycle/utils/_try_imgl_gui_fallback.py
      WHY: 2 occurrences of 16-line block across 1 files — saves 16 lines
      FILES: src/koru/autonomy/cycle/cycle_drive_retry.py
  [48] ○ extract_function   → src/koru/utils/allow_gillm_autopilot_fallback.py
      WHY: 5 occurrences of 4-line block across 2 files — saves 16 lines
      FILES: src/koru/autonomy/env.py, src/koru/ide_adapters/ide_reload.py
  [49] ○ extract_function   → src/koru/utils/_dsl_main.py
      WHY: 5 occurrences of 4-line block across 3 files — saves 16 lines
      FILES: src/koru/cli.py, src/koru/cli_local_serve.py, src/koru/cli_serve.py
  [50] ○ extract_function   → src/koruapi/utils/nlp2uri_missing_message.py
      WHY: 3 occurrences of 8-line block across 3 files — saves 16 lines
      FILES: src/koruapi/desktop_uri.py, src/koruapi/env2llm_registry.py, src/koruapi/nlp2oql_bridge.py
  [51] ○ extract_function   → packages/uri2coru/src/uri2coru/utils/_cmd_lane_status.py
      WHY: 4 occurrences of 5-line block across 1 files — saves 15 lines
      FILES: packages/uri2coru/src/uri2coru/decode.py
  [52] ○ extract_function   → src/koru/utils/_topology_component_toggler.py
      WHY: 2 occurrences of 15-line block across 1 files — saves 15 lines
      FILES: src/koru/cli_topology.py
  [53] ○ extract_function   → src/koru/ide_adapters/utils/reload_via_reopen_workspace.py
      WHY: 2 occurrences of 15-line block across 1 files — saves 15 lines
      FILES: src/koru/ide_adapters/ide_reload.py
  [54] ○ extract_function   → src/koru/integrations/utils/_controls_find.py
      WHY: 4 occurrences of 5-line block across 1 files — saves 15 lines
      FILES: src/koru/integrations/vdisplay_client.py
  [55] ○ extract_function   → src/koruapi/utils/tool_env2llm_get_registry.py
      WHY: 4 occurrences of 5-line block across 1 files — saves 15 lines
      FILES: src/koruapi/mcp_server_env2llm.py
  [56] ○ extract_function   → src/koruide/ides/utils/detection.py
      WHY: 4 occurrences of 5-line block across 4 files — saves 15 lines
      FILES: src/koruide/ides/antigravity.py, src/koruide/ides/cursor.py, src/koruide/ides/qoder.py, src/koruide/ides/zed.py
  [57] ○ extract_function   → packages/utils/_python_type.py
      WHY: 2 occurrences of 16-line block across 2 files — saves 16 lines
      FILES: packages/dsl2coru/src/dsl2coru/codegen.py, packages/dsl2koru/src/dsl2koru/codegen.py
  [58] ○ extract_function   → packages/coru/src/coru/repair/utils/_installed_extension_dir.py
      WHY: 2 occurrences of 14-line block across 2 files — saves 14 lines
      FILES: packages/coru/src/coru/repair/diagnostics.py, packages/coru/src/coru/repair/pipeline.py
  [59] ○ extract_function   → src/koru/integrations/utils/_canonical_ide.py
      WHY: 3 occurrences of 7-line block across 3 files — saves 14 lines
      FILES: src/koru/integrations/photo_vql_target.py, src/koru/integrations/photo_vql_validation.py, src/koru/integrations/vdisplay_client.py
  [60] ○ extract_function   → scripts/utils/update_plugin_version_source.py
      WHY: 2 occurrences of 14-line block across 1 files — saves 14 lines
      FILES: scripts/sync-vscode-plugin-version.py
  [61] ○ extract_function   → src/koru/autonomy/phases/utils/_should_skip_repeated_create_failed_scan.py
      WHY: 2 occurrences of 14-line block across 1 files — saves 14 lines
      FILES: src/koru/autonomy/phases/scan_phase.py
  [62] ○ extract_function   → src/koru/autopilot/utils/_action_install_plugin.py
      WHY: 3 occurrences of 7-line block across 1 files — saves 14 lines
      FILES: src/koru/autopilot/cli_command.py
  [63] ○ extract_function   → src/koru/autopilot/utils/_open_new_ide_window_for_plugin_build_action.py
      WHY: 2 occurrences of 14-line block across 1 files — saves 14 lines
      FILES: src/koru/autopilot/install_manager.py
  [64] ○ extract_function   → src/utils/env_truthy.py
      WHY: 2 occurrences of 14-line block across 2 files — saves 14 lines
      FILES: src/koru/env_flags.py, src/koruide/utils.py
  [65] ○ extract_function   → src/koruapi/utils/_empty_desktop_result.py
      WHY: 2 occurrences of 14-line block across 1 files — saves 14 lines
      FILES: src/koruapi/calibration_validator.py
  [66] ○ extract_class      → src/koru/autonomy/utils/show_decisions.py
      WHY: 2 occurrences of 15-line block across 1 files — saves 15 lines
      FILES: src/koru/autonomy/replay_handlers.py
  [67] ○ extract_function   → src/koruapi/utils/wrapper.py
      WHY: 2 occurrences of 15-line block across 1 files — saves 15 lines
      FILES: src/koruapi/invoke_handlers.py
  [68] ○ extract_function   → packages/utils/_run_results.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: packages/dsl2coru/src/dsl2coru/cli.py, packages/dsl2koru/src/dsl2koru/cli.py
  [69] ○ extract_function   → packages/utils/_handle.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: packages/rest2coru/src/rest2coru/app.py, packages/rest2koru/src/rest2koru/app.py
  [70] ○ extract_function   → src/koru/autonomy/utils/_parse_iso_datetime.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: src/koru/autonomy/ide_work.py, src/koru/autonomy/post_run_verify.py
  [71] ○ extract_function   → packages/utils/main.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: packages/rest2coru/src/rest2coru/cli.py, packages/rest2koru/src/rest2koru/cli.py
  [72] ○ extract_function   → packages/utils/parse_coru_uri.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: packages/uri2coru/src/uri2coru/uri.py, packages/uri2koru/src/uri2koru/uri.py
  [73] ○ extract_function   → src/koru/utils/_try_imgl_gui_fallback.py
      WHY: 2 occurrences of 13-line block across 1 files — saves 13 lines
      FILES: src/koru/autonomous.py
  [74] ○ extract_function   → src/koru/autonomy/phases/utils/_remember_scan_create_failed_state.py
      WHY: 2 occurrences of 13-line block across 1 files — saves 13 lines
      FILES: src/koru/autonomy/phases/scan_phase.py
  [75] ○ extract_class      → src/utils/_reply_needs_plugin_retry.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: src/koru/autonomy/cycle/cycle_drive_retry.py, src/korullm/strategies/ide_chat.py
  [76] ○ extract_class      → src/koru/bounded_contexts/local_manager/utils/register_worker.py
      WHY: 2 occurrences of 14-line block across 1 files — saves 14 lines
      FILES: src/koru/bounded_contexts/local_manager/application.py
  [77] ○ extract_function   → src/koru/utils/_try_vdisplay_control_fallback.py
      WHY: 2 occurrences of 15-line block across 2 files — saves 15 lines
      FILES: src/koru/autonomous.py, src/koru/autonomy/cycle/cycle_drive_retry.py
  [78] ○ extract_function   → src/koruapi/utils/tool_ide_control_plan.py
      WHY: 2 occurrences of 14-line block across 1 files — saves 14 lines
      FILES: src/koruapi/mcp_server_ide.py
  [79] ○ extract_function   → packages/utils/build_model_registry.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: packages/dsl2coru/src/dsl2coru/codegen.py, packages/dsl2koru/src/dsl2koru/codegen.py
  [80] ○ extract_function   → src/koru/utils/_bridge_hypotheses_payload.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: src/koru/autopilot/commands/drive.py, src/koru/ide_doctor_cli.py
  [81] ○ extract_function   → src/utils/parse_boolish.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: src/koru/env_flags.py, src/koruide/utils.py
  [82] ○ extract_function   → src/koruide/ides/utils/plugin.py
      WHY: 3 occurrences of 6-line block across 3 files — saves 12 lines
      FILES: src/koruide/ides/antigravity.py, src/koruide/ides/qoder.py, src/koruide/ides/windsurf.py
  [83] ○ extract_function   → src/korullm/strategies/utils/assess_drive_failure.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: src/korullm/strategies/claude.py, src/korullm/strategies/gpt.py
  [84] ○ extract_function   → src/koruvision/providers/utils/list_monitors.py
      WHY: 4 occurrences of 4-line block across 4 files — saves 12 lines
      FILES: src/koruvision/providers/cli_tools.py, src/koruvision/providers/grim.py, src/koruvision/providers/portal_screencast.py, src/koruvision/providers/portal_screenshot.py
  [85] ○ extract_function   → utils/resolve_coru_bin.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: packages/coru/src/coru/supervisor/systemd_unit.py, src/koru/autopilot/systemd_cli.py
  [86] ○ extract_function   → packages/utils/main.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: packages/mcp2coru/src/mcp2coru/cli.py, packages/mcp2koru/src/mcp2koru/cli.py
  [87] ○ extract_function   → packages/utils/coru_to_dsl.py
      WHY: 4 occurrences of 4-line block across 3 files — saves 12 lines
      FILES: packages/mcp2coru/src/mcp2coru/tools.py, packages/mcp2koru/src/mcp2koru/tools.py, packages/nlpshim/src/nlpshim/control.py
  [88] ○ extract_function   → src/utils/resolve_xdg_path.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: src/koru/autopilot/utils/client_helpers.py, src/koruide/utils.py
  [89] ○ extract_function   → src/koru/utils/chat_control_has_failures.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: src/koru/doctor_chat_control.py, src/koru/doctor_reporting_checks.py
  [90] ○ extract_function   → src/koru/utils/windsurf_chat_column_detail_bits.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: src/koru/doctor_chat_control.py, src/koru/doctor_reporting_checks.py
  [91] ○ extract_function   → src/koru/utils/_path_step_autopilot_intent.py
      WHY: 5 occurrences of 3-line block across 1 files — saves 12 lines
      FILES: src/koru/observability_dsl.py
  [92] ○ extract_function   → src/koruapi/utils/_handle_mcp_list_tickets.py
      WHY: 3 occurrences of 6-line block across 1 files — saves 12 lines
      FILES: src/koruapi/invoke_handlers.py
  [93] ○ extract_function   → src/korullm/strategies/utils/idle_marker_patterns.py
      WHY: 3 occurrences of 6-line block across 3 files — saves 12 lines
      FILES: src/korullm/strategies/claude.py, src/korullm/strategies/gpt.py, src/korullm/strategies/ollama.py
  [94] ○ extract_function   → packages/utils/_cmd_encode.py
      WHY: 2 occurrences of 13-line block across 2 files — saves 13 lines
      FILES: packages/dsl2coru/src/dsl2coru/cli.py, packages/dsl2koru/src/dsl2koru/cli.py
  [95] ○ extract_class      → packages/coru/src/coru/supervisor/utils/do_GET.py
      WHY: 4 occurrences of 4-line block across 1 files — saves 12 lines
      FILES: packages/coru/src/coru/supervisor/http_server.py
  [96] ○ extract_function   → src/koru/wizard/gui/utils/api_select_ide.py
      WHY: 4 occurrences of 4-line block across 1 files — saves 12 lines
      FILES: src/koru/wizard/gui/app.py
  [97] ○ extract_function   → src/koru/utils/_first_action_token.py
      WHY: 2 occurrences of 12-line block across 2 files — saves 12 lines
      FILES: src/koru/autonomy/configuration/config_cli_config.py, src/koru/cli_auto.py
  [98] ○ extract_function   → packages/coru/src/coru/utils/_terminal_shell_context.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: packages/coru/src/coru/cli.py, packages/coru/src/coru/cli_terminal.py
  [99] ○ extract_function   → packages/utils/setup_openrouter_env.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: packages/nlp2coru/src/nlp2coru/openrouter_config.py, packages/nlp2koru/src/nlp2koru/openrouter_config.py
  [100] ○ extract_function   → packages/utils/get_openrouter_headers.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: packages/nlp2coru/src/nlp2coru/openrouter_config.py, packages/nlp2koru/src/nlp2koru/openrouter_config.py
  [101] ○ extract_function   → src/koru/utils/_bridge_status_payload.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: src/koru/autopilot/commands/drive.py, src/koru/ide_doctor_cli.py
  [102] ○ extract_function   → src/utils/_trace_event_matches.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: src/koruapi/dashboard_observability.py, src/koruobserve/cli.py
  [103] ○ extract_function   → src/koru/autonomy/operator/utils/_ensure_trusted_publisher_for_plugin.py
      WHY: 2 occurrences of 11-line block across 1 files — saves 11 lines
      FILES: src/koru/autonomy/operator/operator_operator.py
  [104] ○ extract_function   → src/utils/_event_to_record.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: src/koru/cqrs/event_store.py, src/koruapi/dashboard_observability.py
  [105] ○ extract_function   → src/koru/utils/chat_control_recovered_after_retry.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: src/koru/doctor_chat_control.py, src/koru/doctor_reporting_checks.py
  [106] ○ extract_function   → src/koru/bounded_contexts/utils/history.py
      WHY: 3 occurrences of 6-line block across 3 files — saves 12 lines
      FILES: src/koru/bounded_contexts/planfile_queue/application.py, src/koru/bounded_contexts/repairs/application.py, src/koru/bounded_contexts/tasks/application.py
  [107] ○ extract_class      → src/koru/utils/_submit_retry_is_known_unsafe_without_engine.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: src/koru/autonomy/drive/drive_retry_policy.py, src/koru/decision_engine.py
  [108] ○ extract_function   → packages/utils/envelope_to_dict.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: packages/dsl2coru/src/dsl2coru/pb_codec.py, packages/dsl2koru/src/dsl2koru/pb_codec.py
  [109] ○ extract_class      → packages/utils/complete.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: packages/nlp2coru/src/nlp2coru/llm_backend.py, packages/nlp2koru/src/nlp2koru/llm_backend.py
  [110] ○ extract_function   → src/utils/_cli_version.py
      WHY: 3 occurrences of 5-line block across 3 files — saves 10 lines
      FILES: src/koru/cli_parser.py, src/koruapi/cli.py, src/korudsl/cli.py
  [111] ○ extract_function   → packages/utils/_cmd_decode.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: packages/dsl2coru/src/dsl2coru/cli.py, packages/dsl2koru/src/dsl2koru/cli.py
  [112] ○ extract_function   → packages/dsl2coru/src/dsl2coru/handlers/utils/_build_ensure_args.py
      WHY: 3 occurrences of 5-line block across 1 files — saves 10 lines
      FILES: packages/dsl2coru/src/dsl2coru/handlers/argv.py
  [113] ○ extract_function   → packages/utils/_load_schemas.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: packages/dsl2coru/src/dsl2coru/schema_registry.py, packages/dsl2koru/src/dsl2koru/schema_registry.py
  [114] ○ extract_function   → src/koru/utils/_build_nlp2uri_desktop_backend.py
      WHY: 3 occurrences of 5-line block across 1 files — saves 10 lines
      FILES: src/koru/agent_backend_runtime.py
  [115] ○ extract_function   → src/utils/_current_koru_version.py
      WHY: 3 occurrences of 5-line block across 3 files — saves 10 lines
      FILES: src/koru/autonomy/operator/operator_daemon.py, src/koruide/daemon/metadata.py, src/koruide/daemon/protocol.py
  [116] ○ extract_function   → src/koru/autonomy/utils/trace_show_decisions.py
      WHY: 2 occurrences of 10-line block across 1 files — saves 10 lines
      FILES: src/koru/autonomy/replay_builders.py
  [117] ○ extract_function   → src/utils/_versioned_plugin_vsix_candidates.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: src/koru/autopilot/install_plugin_cli.py, src/koruide/plugin_installer.py
  [118] ○ extract_function   → src/utils/load_koru_project_pipeline.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: src/koru/project_pipeline.py, src/koruapi/dashboard_serve_utils.py
  [119] ○ extract_function   → src/koruide/daemon/utils/_clear_pending_plugin_drive.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: src/koruide/daemon/handlers_ack.py, src/koruide/daemon/handlers_drive.py
  [120] ○ extract_function   → src/koruide/utils/extension_id_for_ide.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: src/koruide/plugin_installer.py, src/koruide/plugin_version.py
  [121] ○ extract_function   → packages/utils/_cmd_replay.py
      WHY: 2 occurrences of 11-line block across 2 files — saves 11 lines
      FILES: packages/dsl2coru/src/dsl2coru/cli.py, packages/dsl2koru/src/dsl2koru/cli.py
  [122] ○ extract_function   → src/koru/utils/_is_topology_enabled.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: src/koru/autonomous.py, src/koru/autonomy/cycle/cycle_skip_conditions.py
  [123] ○ extract_function   → src/koru/autonomy/utils/current_head.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: src/koru/autonomy/checkpoint/checkpoint.py, src/koru/autonomy/phases/utils.py
  [124] ○ extract_function   → packages/coru/src/coru/utils/_project_from_argv.py
      WHY: 2 occurrences of 9-line block across 1 files — saves 9 lines
      FILES: packages/coru/src/coru/cli.py
  [125] ○ extract_function   → src/koru/utils/_default_runner.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: src/koru/autonomy/code2llm_discovery.py, src/koru/self_control.py
  [126] ○ extract_function   → src/koru/autonomy/utils/_reply_requires_manual_chat_focus.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: src/koru/autonomy/cycle/cycle_drive_retry.py, src/koru/autonomy/drive_result.py
  [127] ○ extract_function   → src/utils/scan_while_waiting_input_enabled.py
      WHY: 4 occurrences of 3-line block across 4 files — saves 9 lines
      FILES: src/koru/autonomy/cycle/cycle_gate.py, src/koru/autopilot/install_manager.py, src/koru/integrations/imgl_client.py, src/koruide/plugin_installer.py
  [128] ○ extract_function   → src/koru/autopilot/utils/_action_drive.py
      WHY: 2 occurrences of 9-line block across 1 files — saves 9 lines
      FILES: src/koru/autopilot/cli_command.py
  [129] ○ extract_function   → src/koru/utils/_cursor_project_config.py
      WHY: 4 occurrences of 3-line block across 1 files — saves 9 lines
      FILES: src/koru/mcp_provision.py
  [130] ○ extract_function   → src/korudsl/utils/_handle_wait.py
      WHY: 4 occurrences of 3-line block across 1 files — saves 9 lines
      FILES: src/korudsl/library.py
  [131] ○ extract_class      → packages/utils/to_dict.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: packages/dsl2coru/src/dsl2coru/result.py, packages/dsl2koru/src/dsl2koru/result.py
  [132] ○ extract_function   → packages/utils/result_to_pb.py
      WHY: 2 occurrences of 10-line block across 2 files — saves 10 lines
      FILES: packages/dsl2coru/src/dsl2coru/pb_codec.py, packages/dsl2koru/src/dsl2koru/pb_codec.py
  [133] ○ extract_function   → utils/_read_package_build_sha.py
      WHY: 2 occurrences of 9-line block across 2 files — saves 9 lines
      FILES: packages/coru/src/coru/repair/diagnostics.py, src/koruide/plugin_installer.py
  [134] ○ extract_function   → packages/utils/_print_result.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: packages/cli2coru/src/cli2coru/cli.py, packages/cli2koru/src/cli2koru/cli.py
  [135] ○ extract_function   → packages/coru/src/coru/supervisor/utils/_lane_environ.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: packages/coru/src/coru/supervisor/daemon_ctl.py, packages/coru/src/coru/supervisor/probe.py
  [136] ○ extract_function   → packages/utils/_cmd_validate_schema.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: packages/dsl2coru/src/dsl2coru/cli.py, packages/dsl2koru/src/dsl2koru/cli.py
  [137] ○ extract_function   → packages/utils/_set_body.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: packages/dsl2coru/src/dsl2coru/pb_codec.py, packages/dsl2koru/src/dsl2koru/pb_codec.py
  [138] ○ extract_function   → src/koru/utils/_pid_alive.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: src/koru/autonomy/readiness/readiness.py, src/koru/autopilot/lane_context.py
  [139] ○ extract_function   → packages/utils/_handle_run.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: packages/cli2coru/src/cli2coru/cli.py, packages/cli2koru/src/cli2koru/cli.py
  [140] ○ extract_function   → scripts/utils/get_plugin_version_from_source.py
      WHY: 2 occurrences of 8-line block across 1 files — saves 8 lines
      FILES: scripts/sync-vscode-plugin-version.py
  [141] ○ extract_function   → src/utils/llm_reflection_summary_max_age_seconds.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: src/koru/autonomy/cycle/cycle_chat_activity_config.py, src/koruide/daemon/handlers.py
  [142] ○ extract_function   → src/koru/autonomy/phases/utils/_create_failed_scan_cooldown_seconds.py
      WHY: 2 occurrences of 8-line block across 1 files — saves 8 lines
      FILES: src/koru/autonomy/phases/scan_phase.py
  [143] ○ extract_function   → src/koru/autonomy/utils/scan_force.py
      WHY: 2 occurrences of 8-line block across 1 files — saves 8 lines
      FILES: src/koru/autonomy/replay_builders.py
  [144] ○ extract_function   → src/koru/integrations/utils/_env_float.py
      WHY: 2 occurrences of 8-line block across 1 files — saves 8 lines
      FILES: src/koru/integrations/photo_vql_config.py
  [145] ○ extract_function   → src/koru/utils/_check_git_commit_policy.py
      WHY: 3 occurrences of 4-line block across 1 files — saves 8 lines
      FILES: src/koru/policy.py
  [146] ○ extract_function   → src/koruapi/utils/_sprint_signature.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: src/koruapi/dashboard_context.py, src/koruapi/dashboard_runtime.py
  [147] ○ extract_class      → packages/coru/src/coru/supervisor/utils/start_lane_daemon.py
      WHY: 2 occurrences of 8-line block across 1 files — saves 8 lines
      FILES: packages/coru/src/coru/supervisor/service.py
  [148] ○ extract_class      → packages/utils/__init__.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: packages/dsl2coru/src/dsl2coru/events.py, packages/dsl2koru/src/dsl2koru/events.py
  [149] ○ extract_function   → src/koru/utils/_set_component_enabled.py
      WHY: 2 occurrences of 9-line block across 1 files — saves 9 lines
      FILES: src/koru/cli_topology.py
  [150] ○ extract_class      → src/koruide/utils/_plugin_version_mismatch_message.py
      WHY: 2 occurrences of 8-line block across 1 files — saves 8 lines
      FILES: src/koruide/drive_orchestrator.py
  [151] ○ extract_function   → packages/coru/src/coru/utils/_terminal_shell_context_fallback.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: packages/coru/src/coru/cli.py, packages/coru/src/coru/cli_terminal.py
  [152] ○ extract_function   → packages/utils/validate_payload.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: packages/dsl2coru/src/dsl2coru/codec.py, packages/dsl2koru/src/dsl2koru/codec.py
  [153] ○ extract_function   → packages/utils/validate_schemas.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: packages/dsl2coru/src/dsl2coru/schema_registry.py, packages/dsl2koru/src/dsl2koru/schema_registry.py
  [154] ○ extract_function   → packages/utils/to_dict.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: packages/uri2coru/src/uri2coru/nlp2uri.py, packages/uri2koru/src/uri2koru/nlp2uri.py
  [155] ○ extract_function   → src/koru/autonomy/operator/utils/_ps_rows.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/autonomy/operator/operator_process_guard.py, src/koru/autonomy/operator/operator_processes.py
  [156] ○ extract_function   → src/koru/autonomy/utils/_project_venv_roots.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/autonomy/operator/operator_runtime.py, src/koru/autonomy/readiness/readiness.py
  [157] ○ extract_function   → src/utils/_plugin_package_version.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/autopilot/install_plugin_cli.py, src/koruide/plugin_installer.py
  [158] ○ extract_function   → src/utils/_plugin_package_name.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/autopilot/install_plugin_cli.py, src/koruide/plugin_installer.py
  [159] ○ extract_function   → src/koru/utils/_peek_project_from_argv.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/cli.py, src/koru/cli_auto.py
  [160] ○ extract_function   → src/koru/autonomy/utils/_initialize_cycle_telemetry.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/autonomy/cycle_planning.py, src/koru/autonomy/operator/operator_loop_interfaces.py
  [161] ○ extract_function   → src/koru/autonomy/operator/utils/as_managed.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/autonomy/operator/operator_process_guard.py, src/koru/autonomy/operator/operator_processes.py
  [162] ○ extract_function   → src/koru/autonomy/utils/_make_ticket_open_builder.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: src/koru/autonomy/replay_parser.py
  [163] ○ extract_function   → src/koru/integrations/utils/_auto_open_ide_enabled.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: src/koru/integrations/vdisplay_client.py
  [164] ○ extract_function   → src/koru/utils/is_shell_agent.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: src/koru/tillm_bridge.py
  [165] ○ extract_function   → src/koru/utils/shell_tool_registry_entries.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: src/koru/tillm_bridge.py
  [166] ○ extract_function   → src/koruobserve/utils/cmd_providers_list.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: src/koruobserve/providers_cli.py
  [167] ○ extract_function   → src/koruvision/providers/utils/capture_one.py
      WHY: 2 occurrences of 8-line block across 2 files — saves 8 lines
      FILES: src/koruvision/providers/browser_getdisplay.py, src/koruvision/providers/portal_screencast.py
  [168] ○ extract_function   → packages/utils/validate_payload.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: packages/dsl2coru/src/dsl2coru/codegen.py, packages/dsl2koru/src/dsl2koru/codegen.py
  [169] ○ extract_function   → src/koru/utils/_planfile_command_base.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/context.py, src/koru/gc.py
  [170] ○ extract_function   → src/utils/_read_proc_cwd.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/wizard/project.py, src/koruapi/dashboard_projects.py
  [171] ○ extract_function   → src/koru/utils/save_config.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/cli_shell.py, src/koru/configurator/store.py
  [172] ○ extract_function   → utils/json_response.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: packages/coru/src/coru/supervisor/http_util.py, src/koruapi/server.py
  [173] ○ extract_function   → src/koru/autonomy/operator/utils/_identify_failing_services.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: src/koru/autonomy/operator/operator_wup.py
  [174] ○ extract_function   → packages/dsl2coru/src/dsl2coru/utils/_extract_chat.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: packages/dsl2coru/src/dsl2coru/pb_codec.py
  [175] ○ extract_function   → src/koru/autonomy/operator/utils/_confirm_replace_existing.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/autonomy/operator/operator_process_guard.py, src/koru/autonomy/operator/operator_processes.py
  [176] ○ extract_function   → src/koru/bounded_contexts/utils/history.py
      WHY: 2 occurrences of 7-line block across 2 files — saves 7 lines
      FILES: src/koru/bounded_contexts/autonomous_checkpoint/application.py, src/koru/bounded_contexts/env_config/application.py
  [177] ○ extract_function   → packages/utils/_require_fastmcp.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: packages/mcp2coru/src/mcp2coru/server.py, packages/mcp2koru/src/mcp2koru/server.py
  [178] ○ extract_function   → src/koru/cqrs/utils/all_events.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/cqrs/event_store.py
  [179] ○ extract_function   → src/koru/cqrs/utils/events_for_aggregate.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/cqrs/event_store.py
  [180] ○ extract_function   → src/koruvision/utils/is_wayland.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koruvision/capture_mss.py, src/koruvision/providers/env.py
  [181] ○ extract_function   → packages/coru/src/coru/utils/_desktop_capture_enabled.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: packages/coru/src/coru/cli_calibration.py, packages/coru/src/coru/cli_checks.py
  [182] ○ extract_function   → packages/coru/src/coru/repair/utils/_collect_manage_issue_problems.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: packages/coru/src/coru/repair/diagnostics.py
  [183] ○ extract_function   → packages/dsl2coru/src/dsl2coru/utils/_extract_status.py
      WHY: 3 occurrences of 3-line block across 1 files — saves 6 lines
      FILES: packages/dsl2coru/src/dsl2coru/pb_codec.py
  [184] ○ extract_function   → packages/dsl2coru/src/dsl2coru/utils/_serialize_status.py
      WHY: 3 occurrences of 3-line block across 1 files — saves 6 lines
      FILES: packages/dsl2coru/src/dsl2coru/serializer.py
  [185] ○ extract_function   → packages/utils/uri_for_cmd.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: packages/uri2coru/src/uri2coru/uri.py, packages/uri2koru/src/uri2koru/uri.py
  [186] ○ extract_function   → src/koru/autonomy/utils/_error_stagnation_threshold.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koru/autonomy/cycle/cycle.py, src/koru/autonomy/planning_llm_runtime.py
  [187] ○ extract_function   → src/koru/autonomy/operator/utils/process_cwd.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koru/autonomy/operator/operator_process_guard.py, src/koru/autonomy/operator/operator_processes.py
  [188] ○ extract_function   → src/koru/autonomy/phases/utils/_scan_result_is_create_failed_only.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/autonomy/phases/scan_phase.py
  [189] ○ extract_function   → src/koru/autonomy/utils/_make_ide_builder.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/autonomy/replay_parser.py
  [190] ○ extract_function   → src/utils/_previous_serve_config.py
      WHY: 3 occurrences of 3-line block across 3 files — saves 6 lines
      FILES: src/koru/configurator/prompting.py, src/koru/task_dedupe.py, src/koruapi/dashboard_config.py
  [191] ○ extract_function   → src/koru/utils/_check_autopilot_chat_control.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/doctor.py
  [192] ○ extract_function   → src/koru/utils/chat_control_command_hints.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koru/doctor_chat_control.py, src/koru/doctor_reporting_checks.py
  [193] ○ extract_function   → src/utils/_read_json_file.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koru/doctor_plugin_bundle.py, src/koruide/daemon/metadata.py
  [194] ○ extract_function   → src/utils/vql_max_age_seconds.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koru/integrations/autonomy_session.py, src/koruvision/providers/obs_websocket.py
  [195] ○ extract_function   → src/koru/utils/set_component_enabled.py
      WHY: 2 occurrences of 6-line block across 1 files — saves 6 lines
      FILES: src/koru/topology.py
  [196] ○ extract_function   → src/koruide/ides/utils/keyboard.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koruide/ides/jetbrains.py, src/koruide/ides/zed.py
  [197] ○ extract_function   → packages/dsl2coru/src/dsl2coru/utils/_parse_chat.py
      WHY: 2 occurrences of 7-line block across 1 files — saves 7 lines
      FILES: packages/dsl2coru/src/dsl2coru/parser.py
  [198] ○ extract_function   → src/koru/autonomy/utils/_split_quick_action.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koru/autonomy/operator/operator_loop_quick_actions.py, src/koru/autonomy/replay_quick_actions.py
  [199] ○ extract_class      → packages/utils/replay.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: packages/dsl2coru/src/dsl2coru/events.py, packages/dsl2koru/src/dsl2koru/events.py
  [200] ○ extract_function   → src/koru/utils/_path_is_relative_to.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koru/autonomy/operator/operator_runtime.py, src/koru/self_control.py
  [201] ○ extract_function   → src/utils/_read_proc_cmdline.py
      WHY: 2 occurrences of 6-line block across 2 files — saves 6 lines
      FILES: src/koru/wizard/project.py, src/koruide/ide.py
  [202] ○ extract_function   → packages/utils/main.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: packages/dsl2coru/src/dsl2coru/cli.py, packages/dsl2koru/src/dsl2koru/cli.py
  [203] ○ extract_function   → packages/utils/_handle_subcommand.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: packages/dsl2coru/src/dsl2coru/cli.py, packages/dsl2koru/src/dsl2koru/cli.py
  [204] ○ extract_function   → packages/utils/envelope_from_json.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: packages/dsl2coru/src/dsl2coru/codec.py, packages/dsl2koru/src/dsl2koru/codec.py
  [205] ○ extract_function   → packages/utils/get_backend.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: packages/nlp2coru/src/nlp2coru/llm_backend.py, packages/nlp2koru/src/nlp2koru/llm_backend.py
  [206] ○ extract_function   → src/koruvision/utils/png_dimensions.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koruvision/capture_mss.py, src/koruvision/providers/base.py
  [207] ○ extract_function   → packages/utils/parse_text.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: packages/dsl2coru/src/dsl2coru/codec.py, packages/dsl2koru/src/dsl2koru/codec.py
  [208] ○ extract_function   → packages/dsl2coru/src/dsl2coru/utils/_parse_ui_click.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: packages/dsl2coru/src/dsl2coru/parser.py
  [209] ○ extract_function   → packages/utils/encode_text_to_protobuf.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: packages/dsl2coru/src/dsl2coru/pb_codec.py, packages/dsl2koru/src/dsl2koru/pb_codec.py
  [210] ○ extract_function   → packages/dsl2koru/src/dsl2koru/utils/_parse_query_lane_status.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: packages/dsl2koru/src/dsl2koru/grammar.py
  [211] ○ extract_function   → packages/utils/coru_run_command_pb.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: packages/mcp2coru/src/mcp2coru/tools.py, packages/mcp2koru/src/mcp2koru/tools.py
  [212] ○ extract_function   → packages/uri2coru/src/uri2coru/utils/_cmd_repair_history.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: packages/uri2coru/src/uri2coru/decode.py
  [213] ○ extract_function   → src/koru/utils/_koru_package_version.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/agents.py, src/koru/autonomy/configuration/config_startup.py
  [214] ○ extract_function   → src/koru/autonomy/utils/_env_float.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: src/koru/autonomy/nxdo_discovery.py
  [215] ○ extract_function   → src/koru/utils/_blocked_interface_items.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/autonomy/operator/operator_loop_interfaces.py, src/koru/doctor_autopilot_checks.py
  [216] ○ extract_function   → src/utils/_socket_inode.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/autonomy/readiness/readiness.py, src/koruide/daemon/metadata.py
  [217] ○ extract_function   → src/koru/utils/_package_version.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/autopilot/install_manager.py, src/koru/self_control.py
  [218] ○ extract_function   → src/koru/cqrs/utils/runtime_for_project.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: src/koru/cqrs/__init__.py
  [219] ○ extract_function   → src/koru/utils/_check_autopilot_debug_log.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: src/koru/doctor.py
  [220] ○ extract_function   → src/koru/utils/windsurf_line_mentions_chat_open_command.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/doctor_chat_control.py, src/koru/doctor_reporting_checks.py
  [221] ○ extract_function   → src/koru/utils/_koru_version.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/local_manager_client.py, src/koru/local_manager_state.py
  [222] ○ extract_function   → src/utils/planfile_dir.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/runtime.py, src/koruapi/dashboard_serve_utils.py
  [223] ○ extract_function   → src/korudsl/utils/_handle_error.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: src/korudsl/library.py
  [224] ○ extract_function   → src/koruide/ides/utils/terminal.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koruide/ides/antigravity.py, src/koruide/ides/qoder.py
  [225] ○ extract_function   → src/koruide/ides/utils/detection.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koruide/ides/vscode.py, src/koruide/ides/windsurf.py
  [226] ○ extract_function   → src/koruide/ides/utils/aliases.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koruide/ides/vscode.py, src/koruide/ides/vscodium.py
  [227] ○ extract_function   → src/koru/utils/_optional_str.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/autonomy/drive_result.py, src/koru/observability_dsl.py
  [228] ○ extract_function   → src/koruide/ides/utils/plugin.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koruide/ides/jetbrains.py, src/koruide/ides/zed.py
  [229] ○ extract_function   → packages/utils/schema_for_verb.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: packages/dsl2coru/src/dsl2coru/schema_registry.py, packages/dsl2koru/src/dsl2koru/schema_registry.py
  [230] ○ extract_function   → src/koru/utils/_wayland_session.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/autonomy/operator_pipeline.py, src/koru/ide_adapters/gillm_recovery.py
  [231] ○ extract_function   → src/koru/queue/utils/_source_tool.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/queue/runner.py, src/koru/queue/ticket.py
  [232] ○ extract_class      → src/utils/state_vscdb_path.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/ide_adapters/shared.py, src/koruide/ides/base.py
  [233] ○ extract_function   → src/koru/utils/_int.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/integrations/photo_vql_llm_detect.py, src/koru/ticket_evidence.py
  [234] ○ extract_function   → src/koru/autonomy/utils/_coerce_event_ts.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/autonomy/cycle_events.py, src/koru/autonomy/events.py
  [235] ○ extract_function   → src/koru/utils/summary.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/doctor_models.py, src/koru/self_control.py
  [236] ○ extract_class      → src/koruide/utils/__init__.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: src/koruide/__init__.py
  [237] ○ extract_function   → packages/dsl2coru/src/dsl2coru/utils/_set_chat.py
      WHY: 2 occurrences of 5-line block across 1 files — saves 5 lines
      FILES: packages/dsl2coru/src/dsl2coru/pb_codec.py
  [238] ○ extract_function   → src/utils/_write_sprint_file.py
      WHY: 2 occurrences of 5-line block across 2 files — saves 5 lines
      FILES: src/koru/task_io.py, src/koruapi/dashboard_tickets.py
  [239] ○ extract_function   → packages/coru/src/coru/utils/_terminal_ide_hint.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: packages/coru/src/coru/cli.py, packages/coru/src/coru/cli_terminal.py
  [240] ○ extract_function   → packages/utils/decode_protobuf.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: packages/dsl2coru/src/dsl2coru/pb_codec.py, packages/dsl2koru/src/dsl2koru/pb_codec.py
  [241] ○ extract_function   → packages/utils/__post_init__.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: packages/mcp2coru/src/mcp2coru/server.py, packages/mcp2koru/src/mcp2koru/server.py
  [242] ○ extract_function   → src/koru/autonomy/cycle/utils/_cycle_attr.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomy/cycle/cycle_chat_activity.py, src/koru/autonomy/cycle/cycle_drive_retry.py
  [243] ○ extract_function   → src/koru/utils/_terminal_host_ide_id.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomy/operator/operator_plugin_wait.py, src/koru/ide_adapters/ide_reload.py
  [244] ○ extract_function   → packages/utils/_handle_exec.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: packages/cli2coru/src/cli2coru/cli.py, packages/cli2koru/src/cli2koru/cli.py
  [245] ○ extract_function   → packages/utils/coru_run_command.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: packages/mcp2coru/src/mcp2coru/tools.py, packages/mcp2koru/src/mcp2koru/tools.py
  [246] ○ extract_function   → packages/utils/coru_run_dsl.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: packages/mcp2coru/src/mcp2coru/tools.py, packages/mcp2koru/src/mcp2koru/tools.py
  [247] ○ extract_function   → src/koru/autonomy/utils/status_in_skip_list.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomy/checkpoint/checkpoint.py, src/koru/autonomy/cycle/cycle_common.py
  [248] ○ extract_function   → src/koru/autonomy/utils/_build_queue_command.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomy/cycle_queue_scan.py, src/koru/autonomy/phases/queue_phase.py
  [249] ○ extract_function   → src/utils/_looks_like_autonomous_up_command.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koru/autonomy/operator/operator_processes.py, src/koruobserve/providers_cli.py
  [250] ○ extract_function   → src/koruide/utils/_deferred_submit_unverified_grace_seconds.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koruide/daemon/handlers_ack.py, src/koruide/host_setup.py
  [251] ○ extract_function   → packages/utils/get_events.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: packages/rest2coru/src/rest2coru/app.py, packages/rest2koru/src/rest2koru/app.py
  [252] ○ extract_function   → src/koruide/utils/__init__.py
      WHY: 2 occurrences of 4-line block across 2 files — saves 4 lines
      FILES: src/koruide/command_catalog_store.py, src/koruide/command_telemetry.py
  [253] ○ extract_function   → src/koruapi/utils/_get_config.py
      WHY: 2 occurrences of 4-line block across 1 files — saves 4 lines
      FILES: src/koruapi/dashboard_routes.py
  [254] ○ extract_class      → src/koru/remote/utils/list_running_ides.py
      WHY: 2 occurrences of 4-line block across 1 files — saves 4 lines
      FILES: src/koru/remote/client.py
  [255] ○ extract_function   → packages/coru/src/coru/utils/_ide_from_vscode_pid.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: packages/coru/src/coru/cli.py, packages/coru/src/coru/cli_terminal.py
  [256] ○ extract_function   → packages/coru/src/coru/utils/_vscode_family_env_hint.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: packages/coru/src/coru/cli.py, packages/coru/src/coru/cli_terminal.py
  [257] ○ extract_function   → packages/coru/src/coru/utils/_windsurf_terminal_marker.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: packages/coru/src/coru/cli.py, packages/coru/src/coru/cli_terminal.py
  [258] ○ extract_function   → packages/utils/envelope_from_bytes.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: packages/dsl2coru/src/dsl2coru/codec.py, packages/dsl2koru/src/dsl2koru/codec.py
  [259] ○ extract_function   → packages/utils/get_fallback_model.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: packages/nlp2coru/src/nlp2coru/openrouter_config.py, packages/nlp2koru/src/nlp2koru/openrouter_config.py
  [260] ○ extract_function   → packages/utils/get_ollama_base_url.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: packages/nlp2coru/src/nlp2coru/openrouter_config.py, packages/nlp2koru/src/nlp2koru/openrouter_config.py
  [261] ○ extract_function   → packages/utils/should_use_ollama_fallback.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: packages/nlp2coru/src/nlp2coru/openrouter_config.py, packages/nlp2koru/src/nlp2koru/openrouter_config.py
  [262] ○ extract_function   → packages/utils/validate_all.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: packages/rest2coru/src/rest2coru/app.py, packages/rest2koru/src/rest2koru/app.py
  [263] ○ extract_function   → src/koru/autonomy/utils/allow_keyboard_autopilot_fallback.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/autonomy/cycle/cycle_gate.py, src/koru/autonomy/env.py
  [264] ○ extract_function   → src/koru/deployment_events/utils/to_json.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/deployment_events/batch.py, src/koru/deployment_events/models.py
  [265] ○ extract_function   → src/koru/utils/__init__.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/local_manager_state.py
  [266] ○ extract_function   → src/utils/_bound_port.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/local_service.py, src/koruapi/dashboard_serve_utils.py
  [267] ○ extract_function   → src/koruvision/providers/utils/capture_one.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koruvision/providers/cli_tools.py, src/koruvision/providers/obs_websocket.py
  [268] ○ extract_function   → packages/utils/envelope_to_bytes.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: packages/dsl2coru/src/dsl2coru/codec.py, packages/dsl2koru/src/dsl2koru/codec.py
  [269] ○ extract_function   → packages/dsl2coru/src/dsl2coru/utils/_parse_status.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: packages/dsl2coru/src/dsl2coru/parser.py
  [270] ○ extract_function   → packages/dsl2coru/src/dsl2coru/utils/_set_env.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: packages/dsl2coru/src/dsl2coru/pb_codec.py
  [271] ○ extract_function   → packages/dsl2coru/src/dsl2coru/utils/_extract_env.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: packages/dsl2coru/src/dsl2coru/pb_codec.py
  [272] ○ extract_function   → packages/dsl2coru/src/dsl2coru/utils/_serialize_query.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: packages/dsl2coru/src/dsl2coru/serializer.py
  [273] ○ extract_function   → packages/dsl2coru/src/dsl2coru/utils/_serialize_ui_click.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: packages/dsl2coru/src/dsl2coru/serializer.py
  [274] ○ extract_function   → packages/dsl2koru/src/dsl2koru/utils/_set_query_lane_status.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: packages/dsl2koru/src/dsl2koru/pb_codec.py
  [275] ○ extract_function   → packages/dsl2koru/src/dsl2koru/utils/_extract_query_lane_status.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: packages/dsl2koru/src/dsl2koru/pb_codec.py
  [276] ○ extract_function   → src/koru/utils/_normalize_autonomous_argv.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/autonomous.py, src/koru/wizard/cli.py
  [277] ○ extract_function   → src/koru/utils/_apply_auto_pipeline_flags.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/autonomous.py
  [278] ○ extract_function   → src/koru/autonomy/cycle/utils/llm_needs_input_ticket_queue_name.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/autonomy/cycle/cycle_chat_activity_config.py
  [279] ○ extract_function   → src/koru/autonomy/utils/_auto_llm_ready_enabled.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/autonomy/cycle/cycle_skip_conditions.py, src/koru/autonomy/operator_pipeline.py
  [280] ○ extract_function   → src/koru/integrations/utils/_chat_selectors_for.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/integrations/vdisplay_client.py
  [281] ○ extract_function   → src/koru/utils/redup_scan_command.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/redup_integration.py
  [282] ○ extract_function   → src/koruapi/utils/build_dashboard_handler.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koruapi/dashboard_routes.py, src/koruapi/dashboard_serve.py
  [283] ○ extract_function   → src/koruide/utils/supported_autopilot_ide_ids.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koruide/ide.py
  [284] ○ extract_function   → src/koru/autonomy/utils/_queue_loop_waiting_ticket_label.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/autonomy/checkpoint/checkpoint.py, src/koru/autonomy/cycle/cycle_common.py
  [285] ○ extract_function   → packages/utils/coru_run_command_pb.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: packages/mcp2coru/src/mcp2coru/server.py, packages/mcp2koru/src/mcp2koru/server.py
  [286] ○ extract_function   → packages/utils/coru_run_command.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: packages/mcp2coru/src/mcp2coru/server.py, packages/mcp2koru/src/mcp2koru/server.py
  [287] ○ extract_function   → packages/utils/coru_run_dsl.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: packages/mcp2coru/src/mcp2coru/server.py, packages/mcp2koru/src/mcp2koru/server.py
  [288] ○ extract_function   → packages/utils/coru_to_dsl.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: packages/mcp2coru/src/mcp2coru/server.py, packages/mcp2koru/src/mcp2koru/server.py
  [289] ○ extract_function   → src/koru/deployment_events/utils/from_json.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/deployment_events/batch.py, src/koru/deployment_events/models.py
  [290] ○ extract_function   → src/koru/autonomy/utils/builder.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/autonomy/replay_parser.py
  [291] ○ extract_function   → src/koru/utils/__init__.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/configurator/prompting.py, src/koru/wizard/prompters.py
  [292] ○ extract_function   → src/koru/deployment_events/utils/add_events.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/deployment_events/analyzer.py, src/koru/deployment_events/batch.py
  [293] ○ extract_function   → packages/utils/_cmd_roundtrip.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: packages/dsl2coru/src/dsl2coru/cli.py, packages/dsl2koru/src/dsl2koru/cli.py
  [294] ○ extract_function   → src/koru/wizard/utils/is_https_url.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/wizard/templates.py
  [295] ○ extract_function   → src/koru/utils/discover_ide_candidates.py
      WHY: 2 occurrences of 3-line block across 2 files — saves 3 lines
      FILES: src/koru/autonomy/operator/operator_onboarding.py, src/koru/wizard/cli.py
  [296] ○ extract_function   → src/koruide/ides/utils/keyboard.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koruide/ides/base.py
  [297] ○ extract_function   → src/koru/utils/_b.py
      WHY: 2 occurrences of 3-line block across 1 files — saves 3 lines
      FILES: src/koru/policy.py

QUICK_WINS[193] (low risk, high savings — do first):
  [1] extract_function   saved=52L  → src/koru/utils/_scan_pyqual_report.py
      FILES: scan.py
  [4] extract_function   saved=42L  → src/koru/autopilot/utils/_add_calibrate_parser.py
      FILES: cli_parser.py
  [5] extract_function   saved=41L  → src/koru/autopilot/utils/check_plugin_version_mismatch_issue.py
      FILES: install_checks.py
  [6] extract_function   saved=40L  → src/koru/autonomy/utils/collect_git_evidence.py
      FILES: verification_engine.py
  [10] extract_function   saved=40L  → src/koru/utils/_run.py
      FILES: cycle_chat_activity_tickets.py, operator_pipeline.py, dev_sync.py +3
  [8] extract_function   saved=36L  → src/utils/activity_enabled.py
      FILES: activity_log.py, cycle_chat_activity_config.py, operator_operator.py +7
  [9] extract_function   saved=36L  → src/koru/utils/emit_intent.py
      FILES: observability_events.py
  [16] extract_function   saved=30L  → src/koru/utils/provision_cursor.py
      FILES: mcp_provision.py
  [17] extract_function   saved=29L  → src/utils/_build_local_serve_parser.py
      FILES: cli_local_serve.py, local.py
  [18] extract_function   saved=29L  → src/koru/utils/chat_control_result.py
      FILES: doctor_chat_control.py, doctor_reporting_checks.py

DEPENDENCY_RISK[3] (duplicates spanning multiple packages):
  resolve_coru_bin  packages=2  files=2
      packages/coru/src/coru/supervisor/systemd_unit.py
      src/koru/autopilot/systemd_cli.py
  _read_package_build_sha  packages=2  files=2
      packages/coru/src/coru/repair/diagnostics.py
      src/koruide/plugin_installer.py
  json_response  packages=2  files=2
      packages/coru/src/coru/supervisor/http_util.py
      src/koruapi/server.py

EFFORT_ESTIMATE (total ≈ 115.3h):
  hard   _scan_pyqual_report                 saved=52L  ~104min
  hard   create_app                          saved=55L  ~165min
  hard   complete                            saved=48L  ~144min
  hard   _add_calibrate_parser               saved=42L  ~126min
  hard   check_plugin_version_mismatch_issue saved=41L  ~123min
  hard   collect_git_evidence                saved=40L  ~120min
  hard   handle_post_run_verify              saved=39L  ~117min
  medium activity_enabled                    saved=36L  ~72min
  medium emit_intent                         saved=36L  ~72min
  medium _run                                saved=40L  ~80min
  ... +287 more (~5793min)

METRICS-TARGET:
  dup_groups:  297 → 0
  saved_lines: 3214 lines recoverable
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 7097 func | 672f | 2026-07-17
# generated in 0.04s

NEXT[10] (ranked by impact):
  [1] !! SPLIT           src/koru/integrations/vdisplay_client.py
      WHY: 7512L, 0 classes, max CC=15
      EFFORT: ~4h  IMPACT: 112680

  [2] !! SPLIT           packages/coru/src/coru/cli.py
      WHY: 3786L, 3 classes, max CC=16
      EFFORT: ~4h  IMPACT: 60576

  [3] !  SPLIT-FUNC      run_daemon_command  CC=15  fan=26
      WHY: CC=15 exceeds 15
      EFFORT: ~1h  IMPACT: 390

  [4] !  SPLIT-FUNC      _maybe_reexec_into_project_python  CC=16  fan=17
      WHY: CC=16 exceeds 15
      EFFORT: ~1h  IMPACT: 272

  [5] !  SPLIT-FUNC      action_vdisplay_up  CC=15  fan=18
      WHY: CC=15 exceeds 15
      EFFORT: ~1h  IMPACT: 270

  [6] !  SPLIT-FUNC      _checkbox_picker  CC=19  fan=14
      WHY: CC=19 exceeds 15
      EFFORT: ~1h  IMPACT: 266

  [7] !  SPLIT-FUNC      desktop_uri_handle  CC=15  fan=17
      WHY: CC=15 exceeds 15
      EFFORT: ~1h  IMPACT: 255

  [8] !  SPLIT-FUNC      _run_fleet_up  CC=15  fan=15
      WHY: CC=15 exceeds 15
      EFFORT: ~1h  IMPACT: 225

  [9] !  SPLIT-FUNC      sync_prepare_capture_flags_to_env  CC=15  fan=15
      WHY: CC=15 exceeds 15
      EFFORT: ~1h  IMPACT: 225

  [10] !! SPLIT           tree.txt
      WHY: 2722L, 0 classes, max CC=0
      EFFORT: ~4h  IMPACT: 0


RISKS[3]:
  ⚠ Splitting src/koru/integrations/vdisplay_client.py may break 295 import paths
  ⚠ Splitting packages/coru/src/coru/cli.py may break 202 import paths
  ⚠ Splitting tree.txt may break 0 import paths

METRICS-TARGET:
  CC̄:          3.8 → ≤2.7
  max-CC:      20 → ≤10
  god-modules: 57 → 0
  high-CC(≥15): 14 → ≤7
  hub-types:   0 → ≤0

PATTERNS (language parser shared logic):
  _extract_declarations() in base.py — unified extraction for:
    - TypeScript: interfaces, types, classes, functions, arrow funcs
    - PHP: namespaces, traits, classes, functions, includes
    - Ruby: modules, classes, methods, requires
    - C++: classes, structs, functions, #includes
    - C#: classes, interfaces, methods, usings
    - Java: classes, interfaces, methods, imports
    - Go: packages, functions, structs
    - Rust: modules, functions, traits, use statements

  Shared regex patterns per language:
    - import: language-specific import/require/using patterns
    - class: class/struct/trait declarations with inheritance
    - function: function/method signatures with visibility
    - brace_tracking: for C-family languages ({ })
    - end_keyword_tracking: for Ruby (module/class/def...end)

  Benefits:
    - Consistent extraction logic across all languages
    - Reduced code duplication (~70% reduction in parser LOC)
    - Easier maintenance: fix once, apply everywhere
    - Standardized FunctionInfo/ClassInfo models

HISTORY:
  prev CC̄=3.8 → now CC̄=3.8
```

## Intent

Closed-loop automation across semcod/* repositories.
