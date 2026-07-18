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
- **version**: `0.1.400`
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
  version: 0.1.400;
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
  vdisplay: vdisplay>=0.1.44;
  dev: "gillm>=0.1.9, pytest>=8.0,<10.0, pytest-cov>=5.0,<8.0, pytest-rerunfailures>=14.0,<17.0, pytest-timeout>=2.3,<3.0, pytest-xdist>=3.0,<4.0, ruff>=0.11,<0.16, mypy>=1.11,<3.0, pyright>=1.1.390,<2.0, hypothesis>=6.112,<7.0, pre-commit>=3.8,<5.0, types-PyYAML>=6.0,<7.0, goal>=2.1.264, costs>=0.1.53, pfix>=0.1.60, tagi>=0.49.0";
  api: "fastapi>=0.115,<1.0, uvicorn[standard]>=0.30,<1.0, httpx>=0.27,<1.0, prometheus-client>=0.21,<1.0";
  agent: "instructor>=1.6,<2.0, litellm>=1.51,<2.0, openai>=1.54,<3.0, tiktoken>=0.8,<1.0";
  fullm: fullm>=0.1.22;
  tillm: tillm>=0.1.35;
  obs: "nfo>=0.2.22,<1.0, opentelemetry-exporter-otlp>=1.28,<2.0, opentelemetry-instrumentation-fastapi>=0.49b0,<1.0, opentelemetry-instrumentation-httpx>=0.49b0,<1.0, opentelemetry-sdk>=1.28,<2.0, sentry-sdk>=2.18,<3.0, structlog>=24.4,<26.0";
  queue: "apscheduler>=3.10,<4.0, arq>=0.26,<1.0, redis>=5.1,<8.0";
  quality: "import-linter>=2.0,<3.0, mutmut>=3.2,<4.0, pyupgrade>=3.17,<4.0, refurb>=2.0,<3.0";
  all: "apscheduler>=3.10,<4.0, arq>=0.26,<1.0, fastapi>=0.115,<1.0, gillm>=0.1.9, hypothesis>=6.112,<7.0, httpx>=0.27,<1.0, import-linter>=2.0,<3.0, instructor>=1.6,<2.0, litellm>=1.51,<2.0, mss>=9.0,<11.0, mutmut>=3.2,<4.0, mypy>=1.11,<3.0, mss>=9.0,<11.0, nfo>=0.2.22,<1.0, openai>=1.54,<3.0, opentelemetry-exporter-otlp>=1.28,<2.0, opentelemetry-instrumentation-fastapi>=0.49b0,<1.0, opentelemetry-instrumentation-httpx>=0.49b0,<1.0, opentelemetry-sdk>=1.28,<2.0, pre-commit>=3.8,<5.0, prometheus-client>=0.21,<1.0, pyright>=1.1.390,<2.0, pytest>=8.0,<10.0, pytest-cov>=5.0,<8.0, pytest-rerunfailures>=14.0,<17.0, pytest-timeout>=2.3,<3.0, pytest-xdist>=3.0,<4.0, pyupgrade>=3.17,<4.0, redis>=5.1,<8.0, refurb>=2.0,<3.0, ruff>=0.11,<0.16, tillm>=0.1.35, sentry-sdk>=2.18,<3.0, structlog>=24.4,<26.0, tiktoken>=0.8,<1.0, types-PyYAML>=6.0,<7.0, uvicorn[standard]>=0.30,<1.0, websockets>=12.0,<17.0, goal>=2.1.264, costs>=0.1.53, pfix>=0.1.60, tagi>=0.49.0, curllm[mcp]>=1.0.0, env2llm[mqtt]>=0.1.10, fullm>=0.1.22, nlp2uri[envmap]>=0.4.7, planfile>=0.1.100, playwright>=1.40,<2.0, testql>=1.2.55, vdisplay>=0.1.44";
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

workflow[name="test:docker:capture"] {
  trigger: manual;
  step-1: run cmd=docker/capture/run.sh {{.CLI_ARGS}};
}

workflow[name="test:docker:novnc"] {
  trigger: manual;
  step-1: run cmd=docker compose -f docker/novnc/docker-compose.yml up --build -d;
  step-2: run cmd=echo "Open http://127.0.0.1:6080/vnc.html?autoconnect=true ; smoke: docker exec -it koru-novnc bash /home/koru/smoke-desktop.sh";
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
  keys: OPENROUTER_API_KEY, LLM_MODEL, KORU_LLM_NEEDS_INPUT_HEURISTIC, PFIX_AUTO_APPLY, PFIX_AUTO_INSTALL_DEPS, PFIX_AUTO_RESTART, PFIX_MAX_RETRIES, PFIX_DRY_RUN, PFIX_ENABLED, PFIX_GIT_COMMIT, PFIX_GIT_PREFIX, PFIX_CREATE_BACKUPS, OLLAMA_API_URL, OLLAMA_LLM_MODEL, KORU_FORCE_OLLAMA, KORU_VISION_INTERVAL, KORU_VISION_INTERVAL_MIN, KORU_VISION_PROVIDER, KORU_OBS_URL, KORU_OBS_PASSWORD, KORU_OBS_SOURCE, KORU_OBS_IMAGE_WIDTH, KORU_VISION_SCALE, KORU_VISION_PREFER_PORTAL, KORU_PORTAL_PYTHON, KORU_OBSERVE_PYTHON, KORU_MESH_FRAME_STORE, KORU_AGENT_LANE, KORU_PLANFILE_CMD, KORU_VDISPLAY_CONTROL_FALLBACK, KORU_VDISPLAY_SOURCE, KORU_VDISPLAY_LLM_VISION_DECISION, VDISPLAY_VISION_CHAT_DETECT, VDISPLAY_VISION_LLM_ENABLED, VDISPLAY_VISION_LLM_MODE, KORU_NXDO_MAX_TICKETS, KORU_NXDO_COOLDOWN_SECONDS, KORU_NXDO_MODEL, WAYLAND_DISPLAY, DISPLAY, XDG_SESSION_TYPE, ENV2LLM_PROJECT_DIR, KORU_PROJECT_ROOT, ENV2LLM_DESKTOP_PROBE, KORU_SERVE_NO_REPLACE, KORU_SERVE_WORKSPACE, NLP2CMD_INTEGRATION, KORU_PORTAL_CAPTURE, NLP2URI_CAPTURE_DIR, KORU_IMGL_STALE_BLOCK, KORU_IMGL_DIAG_BLOCK, XDG_RUNTIME_DIR, KORU_STRICT_PLUGIN_ACK, KORU_STRICT_PLUGIN_VERSION, KORU_PLUGIN_VERSION_POLICY, KORU_LLM_PICKER, KORU_AUTOPILOT_DRIVE_TIMEOUT_SECONDS, PYTEST_CURRENT_TEST, CURSOR_AGENT, CURSOR_CLI, TERM_PROGRAM_VERSION, WINDSURF_CASCADE_TERMINAL, GIO_LAUNCHED_DESKTOP_FILE, TERMINAL_EMULATOR, IDEA_INITIAL_DIRECTORY, PYCHARM_HOSTED, JETBRAINS_IDE, VSCODE_PID, WINDSURF_VERSION, WINDSURF_CSRF_TOKEN, CHROME_DESKTOP, TERM_PROGRAM, KORU_AUTOPILOT_IDE, XDG_CONFIG_HOME, KORU_COMMAND_CATALOG, KORU_COMMAND_PICKER, KORU_AUTOPILOT_INSTANCE, KORU_AUTOPILOT_SOCKET, LOCALAPPDATA, TEMP, XDG_STATE_HOME, KORU_AUTOPILOT_VSIX, KORU_AUTOPILOT_REASSERT_INSTALL, KORU_AUTOPILOT_FORCE_REASSERT_INSTALL, KORU_AUTOPILOT_BUILD_LOCAL_VSIX, PATH, KORU_OPERATOR_AUTOSTART_MCP, KORU_PLUGIN_DEBUG_LOG, KORU_AUTO_SKIP_WIZARD, VDISPLAY_AGENT_URL, KORU_OBSERVABILITY_TERMINAL, KORU_OBSERVABILITY_DSL_LOG, KORU_TILLM_CLIENT, KORU_DOCTOR_PYTEST_TIMEOUT, VIRTUAL_ENV, KORU_IDE_BACKEND, KORU_TOOL_REGISTRY, CI, GITHUB_ACTIONS, KORU_LOCAL_SERVICE_HOST, KORU_FLEET_WORKSPACE, KORU_EVENTS_URL, KORU_PLANFILE_API_URL, NO_COLOR, CLICOLOR_FORCE, KORU_TILLM_PATH, XDG_CURRENT_DESKTOP, KORU_SCAN_PATHS, KORU_SCAN_SEMCOD_ARTIFACTS, KORU_SCAN_EXECUTOR_KIND, KORU_INCLUDE_FIXTURES, KORU_LOCAL_MANAGER_URL, KORU_LOCAL_SERVICE_URL, KORU_LOCAL_MANAGER_ENABLED, KORU_LOCAL_SERVICE_PORT, KORU_IDE_CONSOLE_LOG_DIR, KORU_ACTIVITY_LOG, KORU_NFO_LOG_PATH, KORU_NFO_LOG, KORU_DEBUG, KORU_FORCE_COLOR, KORU_COLOR, KORU_DOCTOR_CONSOLE_LOG_LINES, USER, ANTIGRAVITY_AGENT, KORU_LLM_REFLECT, KORU_INTEGRATION_LEDGER_PATH, KORU_STDIO_FORMAT, KORU_TILLM_DRY_RUN, KORU_OS_INJECTOR_PROFILE, KORU_OS_INJECTOR_CONFIG, KORU_NLP2URI_DRY_RUN, KORU_IMGL_DRY_RUN, KORU_VDISPLAY_DRY_RUN, KORU_AUTO_INSTALL_DEPS, KORU_PLANNING_LLM, KORU_PLANNING_LLM_MODEL, KORU_PLANNING_LLM_TIMEOUT, KORU_PLANFILE_HEALTH_URL, KORU_OPERATOR_AUTOSTART_SERVER, KORU_SELF_CONTROL_AUTOREPAIR, KORU_TEST_REAL_SELF_CONTROL, KORU_INPROGRESS_STALE_MINUTES, KORU_SHELL_DRIVE_AUTODONE, TICKET_SOURCES, IDLE_DIAGNOSTICS_PROFILE, WUP_MODE, KORU_AUTOPILOT_ALLOW_KEYBOARD_FALLBACK, KORU_AUTOPILOT_GILLM_FALLBACK, KORU_AUTOPILOT_KEYBOARD_IF_NO_PLUGIN, KORU_AUTOPILOT_ALLOW_CROSS_IDE, KORU_LLM_ENDPOINT, OPENAI_API_KEY, KORU_LLM_PROVIDER, KORU_LLM_SHELL_FALLBACK, KORU_TILLM_MODEL, KORU_TILLM_EXECUTE_PROFILE, KORU_LLM_SHELL_TIMEOUT_SECONDS, KORU_LLM_HTTP_REFERER, KORU_LLM_X_TITLE, KORU_QUEUE_RUNNER_LOCK, KORU_TICKET_LEASE_SECONDS, KORU_SRC, IMGL_SRC, VDISPLAY_ROOT, VDISPLAY_SRC, KORU_VDISPLAY_AGENT_URL, VDISPLAY_SESSION_ID, KORU_VDISPLAY_CAPTURE_MATCHES_IDE, KORU_DRIVE_IDE, KORU_VDISPLAY_ABORT_ON_PROBE_FAIL, VDISPLAY_METADATA_DIR, KORU_VDISPLAY_VQL_PATH, KORU_VDISPLAY_PHOTO_PATH, KORU_VDISPLAY_PREFER_PHOTO_VQL, KORU_VDISPLAY_AUTO_IDE_CONTROL, KORU_VDISPLAY_AUTO_OPEN_IDE, VDISPLAY_CLI, VDISPLAY_OBSERVE_PYTHON, KORU_VDISPLAY_FOCUS_RECOVERY_ATTEMPTS, KORU_VDISPLAY_POST_FOCUS_CAPTURE_DELAY_S, KORU_VDISPLAY_RAISE_ALT_TAB_CYCLES, KORU_VDISPLAY_PHOTO_VQL_REFRESH, KORU_VDISPLAY_DEBUG_CAPTURE, KORU_VDISPLAY_IDE_CONTROL_RETRIES, KORU_VDISPLAY_IDE_CONTROL_RETRY_DELAY_S, KORU_IDE_CONTROL_PASTE_ONLY, KORU_IDE_CONTROL_FORCE_SUBMIT, KORU_VDISPLAY_USE_VQL_MOUSE_FOCUS, VDISPLAY_ALLOW_YDOTOOL_TYPING, KORU_VDISPLAY_PHOTO_VQL_MAP_FALLBACK, KORU_VDISPLAY_ALLOW_SURFACE_ONLY_ACTUATION, KORU_VDISPLAY_SURFACE_ONLY_FALLBACK, KORU_VDISPLAY_ALLOW_MAP_SOURCE_MISMATCH, KORU_VDISPLAY_VERIFY_AFTER_PASTE, KORU_VDISPLAY_SUBMIT_DELAY_S, KORU_IMGL_REST_URL, KORU_IMGL_FALLBACK, KORU_IMGL_DESKTOP, KORU_IMGL_IMAGE, KORU_IMGL_WINDOW, KORU_IMGL_CAPTURE_INTERACTIVE, KORU_VDISPLAY_ALLOW_IDE_MISMATCH, KORU_VDISPLAY_ALLOW_MAP_ON_MISMATCH, KORU_VDISPLAY_ALLOW_SURFACE_ON_CAPTURE_ERROR, KORU_VDISPLAY_LLM_CHAT_DETECT_TIMEOUT_S, KORU_VDISPLAY_LLM_CHAT_DETECT_MIN_CONFIDENCE, KORU_VDISPLAY_VQL_MAX_AGE_S, KORU_AUTONOMY_SESSION_DIR, KORU_VDISPLAY_SIDECAR_WRITE_GRACE_S, VDISPLAY_AGENT_PORT, KORU_AUTOPILOT_RESTART_IDE_ON_PLUGIN_BUILD_MISMATCH, KORU_AUTOPILOT_ALLOW_PLUGIN_VERSION_MISMATCH, KORU_AUTOPILOT_ALLOW_PLUGIN_BUILD_MISMATCH, KORU_AUTOPILOT_DRIVE_AUTO_DIRECT, KORU_DRIVE_VERIFY, KORU_AUTOPILOT_AUTO_RELOAD_IDE, KORU_AUTOPILOT_REUSE_WINDOW_RELOAD, KORU_AUTOPILOT_COMMAND_PALETTE_RELOAD, KORU_AUTOPILOT_NEW_WINDOW_RELOAD, KORU_AUTOPILOT_DETACHED_RELOAD, KORU_AUTOPILOT_RELOAD_VERIFY_PLUGIN, KORU_OS_INJECTOR_DRY_RUN, KORU_VDISPLAY_PORTAL_INPUT, KORU_VDISPLAY_PORTAL_TOKEN, KORU_VDISPLAY_RAISE_ALT_TAB, KORU_VDISPLAY_ADAPTIVE_POINTER, KORU_VDISPLAY_ABS_POINTER, KORU_VDISPLAY_ABS_RECALIBRATE, KORU_VDISPLAY_PHOTO_VQL_CODE_EDIT, KORU_AUTOPILOT_AUTO_LLM_READY, KORU_AUTOPILOT_NO_RESPONSE_REDRIVE_LIMIT, KORU_AUTO_SHELL_CLIENT, KORU_NLP2URI_DESKTOP_FALLBACK, KORU_AUTONOMOUS_SCAN_WHILE_WAITING, KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS, KORU_AUTOPILOT_OS_INJECTOR_COOLDOWN_SECONDS, KORU_AUTOPILOT_ESCALATION_COOLDOWN_SECONDS, KORU_LLM_REFLECTION_SUMMARY_MAX_AGE_SECONDS, KORU_LLM_NEEDS_INPUT_TICKET, KORU_LLM_NEEDS_INPUT_TICKET_QUEUE, KORU_LLM_NEEDS_INPUT_TICKET_PRIORITY, KORU_AUTOPILOT_CHAT_INTAKE_TICKET, KORU_AUTOPILOT_DRIVE_MAX_RETRIES, KORU_AUTOPILOT_ALLOW_WORKSPACE_MISMATCH, KORU_TILLM_TIMEOUT_SECONDS, KORU_ERROR_STAGNATION_DIAG_THRESHOLD, KORU_AUTOPILOT_RELOAD_RETRY_WAIT_SECONDS, WUP_PLANFILE_COMMAND, KORU_WUP_COMPOSE_HEALTH_TIMEOUT, KORU_WUP_COMPOSE_PROFILES, KORU_OPERATOR_AUTOSTART_ENVMAP, KORU_QUEUE_UNBLOCK, KORU_ONBOARDING_MAX_QUESTIONS, KORU_AUTONOMOUS_REEXECED, KORU_CLI_REEXECED, KORU_CLI_SYNC_DONE, KORU_READINESS_STRICT, KORU_AUTONOMOUS_START_LOCK, KORU_SUBMIT_UNVERIFIED_ALT_ATTEMPTS, KORU_SCAN_CREATE_FAILED_COOLDOWN_SECONDS, KORU_SCAN_DUPLICATE_COOLDOWN_SECONDS, KORU_AUTO_PIPELINE, KORU_ALLOW_BLIND_KEYBOARD_FALLBACK, KORU_PLUGIN_REJECTION_LOG_INTERVAL_SECONDS, KORU_VISION_BACKEND, DBUS_SESSION_BUS_ADDRESS, KORU_VISION_BROWSER_INTERVAL, KORU_SCREENCAST_SESSION, KORU_LLM_BACKEND, CODEX_HOME, OLLAMA_MODEL, OPENAI_MODEL, ANTHROPIC_MODEL;
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
    desc: Run Docker E2E tests only (slow; deselected by default addopts). See docs/docker-e2e-testing.md
    cmds:
      - scripts/koru-pytest.sh --serial tests/test_docker_e2e.py -v -m "" {{.CLI_ARGS}}

  test:docker:ide-matrix:
    desc: 'Run Docker OS x IDE smoke matrix (FAKE IDE/input stubs — not real GUI). Vars: SYSTEMS, IDES. Docs: docs/docker-e2e-testing.md'
    cmds:
      - KORU_DOCKER_SYSTEMS="{{.SYSTEMS}}" KORU_DOCKER_IDES="{{.IDES}}" bash scripts/docker-ide-matrix.sh
    vars:
      SYSTEMS: '{{.SYSTEMS | default ""}}'
      IDES: '{{.IDES | default ""}}'

  test:docker:capture:
    desc: Xvfb/mss capture smoke (not noVNC). See docs/docker-e2e-testing.md
    cmds:
      - docker/capture/run.sh {{.CLI_ARGS}}

  test:docker:novnc:
    desc: Build/start koru noVNC lab (http://127.0.0.1:6080). See docker/novnc/README.md
    cmds:
      - docker compose -f docker/novnc/docker-compose.yml up --build -d
      - 'echo "Open http://127.0.0.1:6080/vnc.html?autoconnect=true ; smoke: docker exec -it koru-novnc bash /home/koru/smoke-desktop.sh"'

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

*375 nodes · 500 edges · 74 modules · CC̄=3.7*

### Hubs (by degree)

| Function | CC | in | out | total |
|----------|----|----|-----|-------|
| `print` *(in project)* | 0 | 1044 | 0 | **1044** |
| `list` *(in src.koru.wizard.gui.static.wizard)* | 5 | 230 | 9 | **239** |
| `dispatch` *(in packages.dsl2koru.src.dsl2koru.bus)* | 11 ⚠ | 27 | 25 | **52** |
| `_flag` *(in packages.dsl2coru.src.dsl2coru.parser)* | 7 | 33 | 8 | **41** |
| `append_command` *(in packages.dsl2koru.src.dsl2koru.events.EventStore)* | 3 | 0 | 33 | **33** |
| `load_registry` *(in packages.coru.src.coru.supervisor.registry)* | 5 | 21 | 11 | **32** |
| `_run_lane_repair` *(in packages.coru.src.coru.cli)* | 7 | 7 | 24 | **31** |
| `detect_running_ides` *(in src.koruide.ide)* | 4 | 25 | 4 | **29** |

```toon markpact:analysis path=project/calls.toon.yaml
# code2llm call graph | /home/tom/github/semcod/koru
# generated in 0.55s
# nodes: 375 | edges: 500 | modules: 74
# CC̄=3.7

HUBS[20]:
  project.print
    CC=0  in:1044  out:0  total:1044
  src.koru.wizard.gui.static.wizard.list
    CC=5  in:230  out:9  total:239
  packages.dsl2koru.src.dsl2koru.bus.dispatch
    CC=11  in:27  out:25  total:52
  packages.dsl2coru.src.dsl2coru.parser._flag
    CC=7  in:33  out:8  total:41
  packages.dsl2koru.src.dsl2koru.events.EventStore.append_command
    CC=3  in:0  out:33  total:33
  packages.coru.src.coru.supervisor.registry.load_registry
    CC=5  in:21  out:11  total:32
  packages.coru.src.coru.cli._run_lane_repair
    CC=7  in:7  out:24  total:31
  src.koruide.ide.detect_running_ides
    CC=4  in:25  out:4  total:29
  src.koruide.plugin_installer._repo_root
    CC=4  in:25  out:4  total:29
  packages.nlp2coru.src.nlp2coru.cli._emit
    CC=4  in:24  out:4  total:28
  packages.coru.src.coru.cli_checks._trace
    CC=3  in:23  out:5  total:28
  packages.uri2coru.src.uri2coru.nlp2uri.nlp2uri
    CC=14  in:4  out:23  total:27
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
  packages.nlpshim.src.nlpshim.conversation_client.ConversationTestClient.message
    CC=9  in:0  out:22  total:22
  packages.coru.src.coru.cli._run_koru_lane
    CC=2  in:18  out:4  total:22

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
  packages.coru.src.coru.cli  [75 funcs]
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
  packages.coru.src.coru.cli_reexec  [13 funcs]
    already_running_in_project_venv  CC=6  out:11
    cwd_repo_root  CC=4  out:4
    installed_module_source_dir  CC=7  out:8
    local_module_source_dir  CC=4  out:3
    maybe_reexec_into_project_python  CC=5  out:8
    module_runtime_source_dir  CC=2  out:2
    project_repo_root  CC=2  out:2
    project_venv_candidates  CC=4  out:3
    project_venv_python  CC=5  out:3
    reexec_already_done  CC=3  out:4
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
  src.koru.autonomy.readiness.readiness  [1 funcs]
    _project_venv_python  CC=4  out:2
  src.koru.autopilot.lane_context  [1 funcs]
    _instance_matches_ide  CC=1  out:2
  src.koru.ide_doctor_cli  [1 funcs]
    _instance_from_socket_path  CC=5  out:7
  src.koru.integrations.imgl_client  [2 funcs]
    imgl_available  CC=2  out:3
    imgl_missing_message  CC=3  out:2
  src.koru.wizard.gui.static.wizard  [1 funcs]
    list  CC=5  out:9
  src.koruide.ide  [2 funcs]
    detect_running_ides  CC=4  out:4
    detect_terminal_host_context  CC=9  out:9
  src.koruide.plugin_installer  [1 funcs]
    _repo_root  CC=4  out:4

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
# generated in 0.55s
# nodes: 375 | edges: 500 | modules: 74
# CC̄=3.7

HUBS[20]:
  project.print
    CC=0  in:1044  out:0  total:1044
  src.koru.wizard.gui.static.wizard.list
    CC=5  in:230  out:9  total:239
  packages.dsl2koru.src.dsl2koru.bus.dispatch
    CC=11  in:27  out:25  total:52
  packages.dsl2coru.src.dsl2coru.parser._flag
    CC=7  in:33  out:8  total:41
  packages.dsl2koru.src.dsl2koru.events.EventStore.append_command
    CC=3  in:0  out:33  total:33
  packages.coru.src.coru.supervisor.registry.load_registry
    CC=5  in:21  out:11  total:32
  packages.coru.src.coru.cli._run_lane_repair
    CC=7  in:7  out:24  total:31
  src.koruide.ide.detect_running_ides
    CC=4  in:25  out:4  total:29
  src.koruide.plugin_installer._repo_root
    CC=4  in:25  out:4  total:29
  packages.nlp2coru.src.nlp2coru.cli._emit
    CC=4  in:24  out:4  total:28
  packages.coru.src.coru.cli_checks._trace
    CC=3  in:23  out:5  total:28
  packages.uri2coru.src.uri2coru.nlp2uri.nlp2uri
    CC=14  in:4  out:23  total:27
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
  packages.nlpshim.src.nlpshim.conversation_client.ConversationTestClient.message
    CC=9  in:0  out:22  total:22
  packages.coru.src.coru.cli._run_koru_lane
    CC=2  in:18  out:4  total:22

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
  packages.coru.src.coru.cli  [75 funcs]
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
  packages.coru.src.coru.cli_reexec  [13 funcs]
    already_running_in_project_venv  CC=6  out:11
    cwd_repo_root  CC=4  out:4
    installed_module_source_dir  CC=7  out:8
    local_module_source_dir  CC=4  out:3
    maybe_reexec_into_project_python  CC=5  out:8
    module_runtime_source_dir  CC=2  out:2
    project_repo_root  CC=2  out:2
    project_venv_candidates  CC=4  out:3
    project_venv_python  CC=5  out:3
    reexec_already_done  CC=3  out:4
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
  src.koru.autonomy.readiness.readiness  [1 funcs]
    _project_venv_python  CC=4  out:2
  src.koru.autopilot.lane_context  [1 funcs]
    _instance_matches_ide  CC=1  out:2
  src.koru.ide_doctor_cli  [1 funcs]
    _instance_from_socket_path  CC=5  out:7
  src.koru.integrations.imgl_client  [2 funcs]
    imgl_available  CC=2  out:3
    imgl_missing_message  CC=3  out:2
  src.koru.wizard.gui.static.wizard  [1 funcs]
    list  CC=5  out:9
  src.koruide.ide  [2 funcs]
    detect_running_ides  CC=4  out:4
    detect_terminal_host_context  CC=9  out:9
  src.koruide.plugin_installer  [1 funcs]
    _repo_root  CC=4  out:4

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
# code2llm | 1052f 168567L | python:771,typescript:94,shell:60,json:41,yaml:31,toml:16,yml:12,kotlin:6,txt:5,proto:4,go:2,javascript:1,rust:1,properties:1,xml:1 | 2026-07-18
# generated in 1.48s
# CC̅=3.7 | critical:9/7342 | dups:0 | cycles:0

HEALTH[9]:
  🟡 CC    main CC=17 (limit:15)
  🟡 CC    _type_text_at_vql_coords CC=15 (limit:15)
  🟡 CC    main CC=22 (limit:15)
  🟡 CC    main CC=16 (limit:15)
  🟡 CC    tool_propose_edits CC=16 (limit:15)
  🟡 CC    _code2llm_cc_locations CC=20 (limit:15)
  🟡 CC    _merge_call_graph_locations CC=22 (limit:15)
  🟡 CC    discover_bootstrap_candidates CC=18 (limit:15)
  🟡 CC    run_shell_llm_request CC=15 (limit:15)

REFACTOR[1]:
  1. split 9 high-CC methods  (CC>15)

PIPELINES[2213]:
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
  │ !! vdisplay_client           6836L  0C  274m  CC=15     ←7
  │ !! scan                      1796L  0C   65m  CC=22     ←7
  │ !! plugin_installer          1372L  3C   64m  CC=13     ←13
  │ !! install_manager           1328L  1C   58m  CC=14     ←3
  │ !! autonomous                1220L  0C   76m  CC=7      ←3
  │ !! readiness                 1093L  3C   47m  CC=12     ←5
  │ !! handlers_drive            1083L  0C   35m  CC=12     ←3
  │ !! operator_pipeline         1065L  2C   46m  CC=14     ←0
  │ !! cycle_drive_retry         1053L  0C   42m  CC=11     ←3
  │ !! ide                       1020L  2C   59m  CC=13     ←57
  │ !! drive_orchestrator         965L  1C   56m  CC=14     ←1
  │ !! mcp_server_planfile        965L  0C   33m  CC=16     ←1
  │ !! ide_reload                 901L  1C   39m  CC=12     ←5
  │ !! config_startup             894L  3C   42m  CC=13     ←5
  │ !! context                    876L  0C   32m  CC=12     ←7
  │ !! operator_wup               830L  3C   39m  CC=12     ←2
  │ !! cycle_chat_activity        791L  1C   26m  CC=11     ←2
  │ !! photo_vql_target           790L  1C   45m  CC=14     ←1
  │ !! cycle                      788L  0C   17m  CC=11     ←1
  │ !! cli_parser                 781L  0C   21m  CC=1      ←0
  │ !! code2llm_discovery         752L  1C   31m  CC=13     ←4
  │ !! operator_plugin_wait       745L  0C   19m  CC=14     ←1
  │ !! operator_runtime           707L  2C   32m  CC=9      ←9
  │ !! desktop_uri                703L  0C   31m  CC=13     ←4
  │ !! scan_phase                 702L  0C   27m  CC=11     ←0
  │ !! decision_trace             700L  1C   24m  CC=12     ←4
  │ !! cycle_skip_conditions      694L  0C   31m  CC=14     ←2
  │ !! handlers_ack               693L  0C   27m  CC=13     ←3
  │ !! init                       676L  3C   18m  CC=12     ←3
  │ !! koru-autoloop.sh           676L  0C   17m  CC=0.0    ←1
  │ !! doctor_reporting_checks    652L  1C   27m  CC=13     ←0
  │ !! cli_shell                  640L  2C   34m  CC=11     ←0
  │ !! self_control               628L  3C   27m  CC=12     ←2
  │ !! dashboard_routes           607L  0C   35m  CC=9      ←2
  │ !! ide_doctor_cli             595L  0C   24m  CC=11     ←2
  │ !! runner                     595L  0C   18m  CC=10     ←3
  │ !! operator_parser            585L  0C   15m  CC=8      ←2
  │ !! command_catalog            575L  1C    8m  CC=9      ←8
  │ !! cycle_orchestrator         565L  2C   12m  CC=12     ←1
  │ !! operator_loop_runner       545L  0C   11m  CC=7      ←1
  │ !! portal_input               536L  0C   25m  CC=14     ←0
  │ !! mcp_provision              532L  0C   28m  CC=10     ←5
  │ !! runners                    529L  0C   21m  CC=15     ←2
  │ !! photo_vql_validation       527L  0C   32m  CC=13     ←1
  │ !! command_picker             520L  2C   27m  CC=14     ←2
  │ !! install_checks             520L  1C   22m  CC=10     ←0
  │ !! cli_direct_drive           513L  0C   23m  CC=10     ←0
  │ doctor_project_health      499L  0C   24m  CC=14     ←0
  │ agent_backend_runtime      497L  10C   21m  CC=9      ←3
  │ context_render             496L  1C   21m  CC=14     ←4
  │ agents                     486L  1C   25m  CC=14     ←7
  │ shared                     485L  0C   25m  CC=9      ←1
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
  │ ticket                     420L  0C   25m  CC=12     ←13
  │ post_run_verify            416L  2C   17m  CC=14     ←3
  │ cli_fleet                  415L  1C   18m  CC=9      ←1
  │ autonomy_session           413L  0C   31m  CC=8      ←0
  │ cycle_config               404L  0C   11m  CC=12     ←2
  │ env                        401L  0C   19m  CC=12     ←8
  │ operator_loop_quick_actions   400L  0C   18m  CC=12     ←0
  │ photo_vql_user_guidance    395L  1C   30m  CC=9      ←1
  │ handlers_hello             392L  0C   13m  CC=12     ←0
  │ queue_clean                391L  2C   13m  CC=14     ←1
  │ command_scenario           390L  2C   19m  CC=8      ←4
  │ orchestrator               389L  1C   16m  CC=11     ←2
  │ portal_screencast          383L  1C    7m  CC=10     ←0
  │ invoke_handlers            379L  1C   24m  CC=6      ←0
  │ local_service              376L  1C   15m  CC=10     ←1
  │ photo_vql_monitor          376L  0C   15m  CC=14     ←5
  │ env2llm_registry           375L  0C   14m  CC=10     ←4
  │ context                    370L  1C   10m  CC=10     ←1
  │ operator_operator          368L  0C   20m  CC=8      ←0
  │ cli_command                366L  0C   24m  CC=6      ←0
  │ gc                         364L  2C   13m  CC=11     ←1
  │ server                     359L  1C   16m  CC=8      ←1
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
  │ !! fleet_bootstrap            328L  3C   11m  CC=18     ←1
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
  │ tagi_integration           302L  2C   13m  CC=13     ←3
  │ structured_report          300L  1C    8m  CC=13     ←1
  │ cycle_queue_scan           300L  0C   10m  CC=11     ←1
  │ cli_tagi                   299L  0C   16m  CC=7      ←0
  │ ide_control_cli            295L  0C   18m  CC=12     ←1
  │ operator_daemon            295L  0C   11m  CC=10     ←2
  │ vdisplay_agent_bootstrap   294L  0C   17m  CC=12     ←3
  │ cli_tillm_setup            292L  0C   15m  CC=10     ←1
  │ local_manager_state        292L  4C   21m  CC=14     ←0
  │ environment                292L  3C    8m  CC=14     ←5
  │ wizard.js                  292L  0C   38m  CC=13     ←120
  │ plugin_router              291L  3C   19m  CC=13     ←0
  │ queue_cli_helpers          290L  0C   10m  CC=9      ←1
  │ operator_plugin            289L  0C   19m  CC=13     ←4
  │ mcp_server_desktop_uri     282L  0C    9m  CC=1      ←0
  │ agent_backends             282L  3C   11m  CC=11     ←3
  │ cli_parser                 281L  0C    8m  CC=2      ←0
  │ cli_main                   281L  0C    6m  CC=14     ←0
  │ photo_vql_meta             278L  0C   11m  CC=13     ←1
  │ git_cli                    274L  0C   20m  CC=9      ←0
  │ window_focus               274L  0C    9m  CC=11     ←0
  │ environment_profile        271L  5C   11m  CC=9      ←4
  │ operator_process_guard     271L  3C   16m  CC=10     ←1
  │ browser_getdisplay         266L  1C   14m  CC=8      ←2
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
  │ shell_drive_finalize       248L  0C    8m  CC=9      ←1
  │ operator_onboarding        245L  1C   11m  CC=10     ←1
  │ surface_capture            245L  0C    9m  CC=13     ←0
  │ cli_snapshot               242L  2C    9m  CC=9      ←0
  │ decision_arbiter           241L  2C    9m  CC=9      ←1
  │ ide_install                241L  1C    6m  CC=9      ←1
  │ dashboard_serve            240L  1C   10m  CC=6      ←1
  │ interface_registry         239L  3C   15m  CC=8      ←7
  │ doctor_constants           237L  1C    0m  CC=0.0    ←0
  │ tillm_bridge               236L  0C   16m  CC=6      ←15
  │ planning_llm               235L  0C    7m  CC=5      ←0
  │ cli                        232L  0C   12m  CC=12     ←0
  │ mcp_server_env2llm         231L  0C   10m  CC=3      ←1
  │ obs_websocket              231L  1C   15m  CC=11     ←1
  │ dev_sync                   229L  1C    9m  CC=11     ←0
  │ cycle_planning             227L  0C    9m  CC=12     ←1
  │ scan_ticket_emission       225L  0C    7m  CC=11     ←1
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
  │ daemon_cli                 212L  0C   11m  CC=7      ←0
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
  │ desktop_probe              184L  0C    6m  CC=14     ←1
  │ openapi                    183L  0C    1m  CC=2      ←1
  │ cli_task                   183L  0C    5m  CC=11     ←0
  │ queue_phase                178L  0C    6m  CC=11     ←0
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
  │ control_policy             133L  0C    8m  CC=8      ←1
  │ vdisplay_up_cli            133L  0C    4m  CC=7      ←0
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
  │ runtime                    104L  0C    5m  CC=2      ←8
  │ cycle_finalize             104L  0C    1m  CC=4      ←1
  │ web-app.json               104L  0C    0m  CC=0.0    ←0
  │ __init__                   103L  0C    2m  CC=2      ←0
  │ systemd_cli                103L  0C    4m  CC=6      ←0
  │ testql_bridge              102L  0C    5m  CC=7      ←1
  │ cycle_drive_outcome        102L  0C    1m  CC=11     ←1
  │ env_session                102L  0C    7m  CC=8      ←1
  │ storage                    100L  0C    5m  CC=6      ←2
  │ fallback                   100L  1C    1m  CC=1      ←0
  │ drive_phase                 99L  0C    2m  CC=1      ←0
  │ read_model                  97L  1C    7m  CC=7      ←1
  │ __init__                    97L  0C    3m  CC=9      ←0
  │ operator_resources          96L  0C    1m  CC=4      ←0
  │ mcp_server                  96L  0C    0m  CC=0.0    ←0
  │ ide_control                 95L  1C    2m  CC=3      ←1
  │ __init__                    95L  2C    5m  CC=3      ←6
  │ locking                     94L  0C    5m  CC=5      ←3
  │ config                      94L  1C    3m  CC=4      ←4
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
  │ mcp_server_schema           32L  0C    1m  CC=1      ←0
  │ __init__                    32L  1C    0m  CC=0.0    ←0
  │ invoke                      31L  0C    1m  CC=4      ←2
  │ cli_parser                  31L  0C    1m  CC=1      ←1
  │ ide_status_systemmap        31L  0C    1m  CC=3      ←1
  │ cli_shim_builders           31L  0C    2m  CC=1      ←0
  │ human                       31L  0C    1m  CC=5      ←0
  │ utils                       30L  0C    2m  CC=4      ←3
  │ __init__                    30L  3C    0m  CC=0.0    ←0
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
  │ paths                       21L  0C    4m  CC=1      ←8
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
  │ __init__                    17L  0C    0m  CC=0.0    ←0
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
  packages/                       CC̄=3.8    ←in:0  →out:0
  │ !! cli                       3464L  3C  180m  CC=13     ←3
  │ !! pipeline                  1039L  2C   42m  CC=9      ←0
  │ !! cli_calibration            683L  0C   26m  CC=13     ←2
  │ !! diagnostics                504L  0C   27m  CC=14     ←1
  │ cli                        347L  0C   23m  CC=7      ←0
  │ pb_codec                   323L  0C   34m  CC=6      ←1
  │ cli_dispatch               246L  0C   11m  CC=9      ←1
  │ parser                     238L  0C   23m  CC=9      ←0
  │ cli_lane                   238L  0C   13m  CC=12     ←2
  │ ecosystem                  225L  2C   11m  CC=14     ←1
  │ cli_reexec                 220L  0C   13m  CC=7      ←0
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
  │ control                     64L  0C    5m  CC=6      ←3
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
  scripts/                        CC̄=2.8    ←in:0  →out:78  !! split
  │ koru-gate-capture          314L  0C   14m  CC=9      ←0
  │ scaffold-ide-plugin        310L  0C    7m  CC=7      ←0
  │ write-ide-plugin-tests     276L  0C    3m  CC=3      ←0
  │ planfile-sync-todo         251L  0C   12m  CC=14     ←0
  │ koru-pytest.sh             248L  0C    6m  CC=0.0    ←0
  │ autopilot-ide-autodetect-smoke.sh   182L  1C    4m  CC=0.0    ←0
  │ sync-plugin-version        149L  0C    4m  CC=7      ←0
  │ bump_version               137L  0C    7m  CC=8      ←0
  │ sync-plugin-build          136L  0C    6m  CC=13     ←0
  │ koru-semcod-gates.sh       135L  0C    2m  CC=0.0    ←0
  │ koru-soak-monitor.sh       129L  0C    6m  CC=0.0    ←0
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
  │ bridge-focus-core.ts       239L  1C   33m  CC=5      ←26
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
  ./                              CC̄=2.0    ←in:0  →out:0
  │ !! tree.txt                  2722L  0C    0m  CC=0.0    ←0
  │ !! ui.vql.json               1946L  0C    0m  CC=0.0    ←0
  │ !! planfile.yaml             1391L  0C    0m  CC=0.0    ←0
  │ !! Taskfile.yml               933L  0C    0m  CC=0.0    ←0
  │ !! goal.yaml                  554L  0C    0m  CC=0.0    ←0
  │ pyproject.toml             370L  0C    0m  CC=0.0    ←0
  │ Makefile                   276L  0C    0m  CC=0.0    ←0
  │ gillm_defs.txt             195L  0C    0m  CC=0.0    ←0
  │ koru.yaml                  163L  0C    0m  CC=0.0    ←0
  │ pipeline.yaml              142L  0C    0m  CC=0.0    ←0
  │ project.sh                 140L  0C    1m  CC=0.0    ←147
  │ wup.yaml                   113L  0C    0m  CC=0.0    ←0
  │ wup-shell-only.yaml        110L  0C    0m  CC=0.0    ←0
  │ prefact.yaml                93L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml          92L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  79L  0C    0m  CC=0.0    ←0
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
  docker/                         CC̄=2.0    ←in:0  →out:0
  │ smoke                      141L  0C    8m  CC=4      ←0
  │ start-vnc.sh               103L  0C    1m  CC=0.0    ←0
  │ Dockerfile                  61L  0C    0m  CC=0.0    ←0
  │ run.sh                      58L  0C    0m  CC=0.0    ←0
  │ smoke-desktop.sh            54L  0C    0m  CC=0.0    ←0
  │ Dockerfile                  45L  0C    0m  CC=0.0    ←0
  │ entrypoint-x11.sh           35L  0C    0m  CC=0.0    ←0
  │ docker-compose.yml          34L  0C    0m  CC=0.0    ←0
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
                                                      src.koru                        project                    src.koruide                  packages.coru                    src.koruapi  plugins.koru-autopilot-shared              packages.dsl2koru                        scripts                 src.koruvision                src.koruobserve              packages.dsl2coru              packages.nlp2coru                   src.korumesh                           koru              packages.uri2coru
                       src.koru                             ──                            622                            223                              4                             14                             58                              3                             ←1                             22                             12                             ←3                             25                             ←2                             18                             ←1  hub
                        project                           ←622                             ──                            ←26                           ←183                            ←17                                                           ←11                            ←76                            ←12                            ←22                            ←11                             ←6                             ←7                                                            ←6  hub
                    src.koruide                             40                             26                             ──                            ←28                            ←27                              9                                                                                                                           1                                                                                                                                                             hub
                  packages.coru                             42                            183                             28                             ──                                                             3                              3                                                            ←1                                                                                            4                                                                                               hub
                    src.koruapi                            100                             17                             27                                                            ──                             13                                                            ←1                              2                                                                                                                           3                              3                                 hub
  plugins.koru-autopilot-shared                            ←58                                                            ←9                             ←3                            ←13                             ──                                                                                           ←2                                                                                                                          ←2                                                                hub
              packages.dsl2koru                             ←3                             11                                                             1                                                                                           ──                                                                                                                         ←34                             ←2                                                                                            1  hub
                        scripts                              1                             76                                                                                            1                                                                                           ──                                                                                                                                                                                                                           !! fan-out
                 src.koruvision                              5                             12                                                             1                             ←2                              2                                                                                           ──                              1                                                                                            8                                                                hub
                src.koruobserve                              7                             22                             ←1                                                                                                                                                                                         7                             ──                                                                                            1                              1                                 hub
              packages.dsl2coru                              3                             11                                                                                                                                                         34                                                                                                                          ──                                                                                                                              !! fan-out
              packages.nlp2coru                              1                              6                                                            ←4                                                                                            2                                                                                                                                                         ──                                                                                            1  hub
                   src.korumesh                              2                              7                                                                                           ←3                              2                                                                                            2                              1                                                                                           ──                                                                hub
                           koru                              2                                                                                                                          ←3                                                                                                                                                         ←1                                                                                                                          ──                                 hub
              packages.uri2coru                              1                              6                                                                                                                                                          1                                                                                                                                                         ←1                                                                                           ──  hub
  CYCLES: none
  HUB: src.imgl/ (fan-in=5)
  HUB: src.koru/ (fan-in=217)
  HUB: plugins.koru-autopilot-shared/ (fan-in=91)
  HUB: src.koruobserve/ (fan-in=16)
  HUB: src.koruvision/ (fan-in=37)
  HUB: packages.koruenv/ (fan-in=10)
  HUB: packages.coru/ (fan-in=7)
  HUB: packages.mcp2coru/ (fan-in=6)
  HUB: koru/ (fan-in=22)
  HUB: src.korumesh/ (fan-in=12)
  HUB: packages.dsl2koru/ (fan-in=71)
  HUB: project/ (fan-in=1044)
  HUB: src.koruapi/ (fan-in=15)
  HUB: src.koruide/ (fan-in=278)
  HUB: packages.nlpshim/ (fan-in=6)
  HUB: packages.nlp2coru/ (fan-in=33)
  HUB: packages.uri2coru/ (fan-in=11)
  SMELL: packages.nlp2koru/ fan-out=17 → split needed
  SMELL: src.koru/ fan-out=1018 → split needed
  SMELL: packages.cli2coru/ fan-out=12 → split needed
  SMELL: src.koruobserve/ fan-out=38 → split needed
  SMELL: src.koruvision/ fan-out=29 → split needed
  SMELL: packages.coru/ fan-out=267 → split needed
  SMELL: scripts/ fan-out=78 → split needed
  SMELL: packages.uri2koru/ fan-out=16 → split needed
  SMELL: src.korumesh/ fan-out=14 → split needed
  SMELL: packages.dsl2koru/ fan-out=19 → split needed
  SMELL: src.koruapi/ fan-out=172 → split needed
  SMELL: src.koruide/ fan-out=81 → split needed
  SMELL: packages.cli2koru/ fan-out=11 → split needed
  SMELL: packages.nlp2coru/ fan-out=10 → split needed
  SMELL: packages.uri2coru/ fan-out=8 → split needed
  SMELL: packages.dsl2coru/ fan-out=48 → split needed
  SMELL: examples/ fan-out=12 → split needed

EXTERNAL:
  validation: run `vallm batch .` → validation.toon
  duplication: run `redup scan .` → duplication.toon
```

### Duplication (`project/duplication.toon.yaml`)

```toon markpact:analysis path=project/duplication.toon.yaml
# redup/duplication | 0 groups | 0f 0L | 2026-07-18

SUMMARY:
  files_scanned: 0
  total_lines:   0
  dup_groups:    0
  dup_fragments: 0
  saved_lines:   0
  scan_ms:       564013
```

### Evolution / Churn (`project/evolution.toon.yaml`)

```toon markpact:analysis path=project/evolution.toon.yaml
# code2llm/evolution | 7209 func | 683f | 2026-07-18
# generated in 0.30s

NEXT[7] (ranked by impact):
  [1] !! SPLIT           src/koru/integrations/vdisplay_client.py
      WHY: 6836L, 0 classes, max CC=15
      EFFORT: ~4h  IMPACT: 102540

  [2] !! SPLIT           packages/coru/src/coru/cli.py
      WHY: 3464L, 3 classes, max CC=13
      EFFORT: ~4h  IMPACT: 45032

  [3] !  SPLIT-FUNC      discover_bootstrap_candidates  CC=18  fan=27
      WHY: CC=18 exceeds 15
      EFFORT: ~1h  IMPACT: 486

  [4] !  SPLIT-FUNC      _merge_call_graph_locations  CC=22  fan=17
      WHY: CC=22 exceeds 15
      EFFORT: ~1h  IMPACT: 374

  [5] !  SPLIT-FUNC      _code2llm_cc_locations  CC=20  fan=16
      WHY: CC=20 exceeds 15
      EFFORT: ~1h  IMPACT: 320

  [6] !  SPLIT-FUNC      run_shell_llm_request  CC=15  fan=14
      WHY: CC=15 exceeds 15
      EFFORT: ~1h  IMPACT: 210

  [7] !! SPLIT           tree.txt
      WHY: 2722L, 0 classes, max CC=0
      EFFORT: ~4h  IMPACT: 0


RISKS[3]:
  ⚠ Splitting src/koru/integrations/vdisplay_client.py may break 274 import paths
  ⚠ Splitting packages/coru/src/coru/cli.py may break 180 import paths
  ⚠ Splitting tree.txt may break 0 import paths

METRICS-TARGET:
  CC̄:          3.8 → ≤2.7
  max-CC:      22 → ≤11
  god-modules: 59 → 0
  high-CC(≥15): 7 → ≤3
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
  prev CC̄=3.7 → now CC̄=3.8
```

## Intent

Closed-loop automation across semcod/* repositories.
