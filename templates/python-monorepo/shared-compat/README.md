# shared-compat — Compatibility shim pattern

Wzorzec dla **Python monorepo** gdzie chcesz mieć:

- **Canonical impl** w `packages/<APP_NAME>-shared-py/src/shared/`
- **Legacy import path** `<APP_NAME>.shared.X` zachowane (no breaking changes)
- **Single source of truth** — zmiana w canonical = automatyczna zmiana
  we wszystkich shim files

## Kiedy używać

Pattern z c2004 deployment, opracowany dla:

- Migracji z `monolith/shared/` → `packages/shared-py/`
- Stopniowego refaktoru dużej codebase
- Multi-package monorepo gdzie shared utilities trzeba dzielić między ≥2 modułami

## Pliki w template

| Plik | Rola |
|---|---|
| `_compat.py.template` | Helper z `export_backend_shared_module()` + `export_connect_module()` |

## Install

```bash
APP_NAME=myapp

# 1. Stwórz packages dir structure (canonical impl)
mkdir -p packages/${APP_NAME}-shared-py/src/shared/{types,cqrs,events}

# 2. Skopiuj _compat helper do legacy shared/
mkdir -p src/${APP_NAME}/shared
cp templates/python-monorepo/shared-compat/_compat.py.template \
   src/${APP_NAME}/shared/_compat.py
sed -i "s/<APP_NAME>/${APP_NAME}/g" src/${APP_NAME}/shared/_compat.py

# 3. Dla każdego shim file (np. types/base.py):
cat > src/${APP_NAME}/shared/types/base.py <<EOF
"""Compatibility wrapper for ${APP_NAME}.shared.types.base.

Canonical: packages/${APP_NAME}-shared-py/src/shared/types/base.py
"""
from __future__ import annotations
from ${APP_NAME}.shared._compat import export_backend_shared_module

__all__ = export_backend_shared_module(globals(), "types/base")
EOF
```

## Test

```bash
# Canonical:
mkdir -p packages/${APP_NAME}-shared-py/src/shared/types
cat > packages/${APP_NAME}-shared-py/src/shared/types/base.py <<'EOF'
class BaseEntity:
    pass
__all__ = ["BaseEntity"]
EOF

# Test import:
python3 -c "from ${APP_NAME}.shared.types.base import BaseEntity; print('OK')"
```

## Zachowanie

`export_backend_shared_module(globals(), "types/base")`:

1. Walks UP od `_compat.py` żeby znaleźć `packages/<APP_NAME>-shared-py/src/shared/`
2. Loaduje canonical module via `importlib.util` (omija `sys.path`)
3. Honour canonical's `__all__` jeśli zdefiniowany; otherwise auto-detect public symbols
4. Copy do `target_globals` + zwraca listę names jako `__all__`

## Reference deployment (c2004)

c2004 ma elaborate compatibility wrapper system:

- `backend/shared/_compat.py` — Helper module (canonical impl)
- 30+ shim files w `backend/shared/{types,cqrs,events,bus}/` (każdy ~6 linii)
- Canonical impl w `packages/backend-shared-py/src/shared/`

Empirycznie: **88% size reduction** w shim files (14640 → 1812 bytes total)
po przeniesieniu canonical impl do packages/.

## Companion: connect_compat dla cross-package imports

Dla monorepo z `connect-X/`, `connect-Y/` packages (każdy z własnym pyproject):

```python
# w backend/app/cqrs/menu/registration.py:
from ${APP_NAME}.connect_compat import export_connect_module
__all__ = export_connect_module(globals(), "connect_data.events")
```

`export_connect_module` automatycznie znajdzie `connect-data/backend/connect_data/`
+ doda do `sys.path` raz.

## Anti-patterns

❌ **Nie pisz nowego kodu w `<APP_NAME>/shared/`** — pisz w
`packages/<APP_NAME>-shared-py/src/shared/`, a w shared/ ewentualnie dodaj
compat wrapper.

❌ **Nie hardcoduj `getattr(_module, "Foo")` + manualne `__all__`** —
`export_backend_shared_module` robi to automatycznie używając canonical's
`__all__` lub heurystyki.

❌ **Don't bypass shim** w testach — testy też powinny używać `from <APP_NAME>.shared.X import ...` żeby walidować shim path.

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `Cannot locate packages/.../src/shared` | sprawdź czy package directory istnieje + `pyproject.toml` ma `[tool.setuptools.packages]` |
| `ImportError: Canonical module not found` | sprawdź `rel_path` — bez `.py` extension, slash-separated |
| Cyclic import | canonical nie powinien import-ować z shim layer; sprawdź dependency direction |
| `sys.path pollution` | użyj importlib.util loader (już w template) zamiast `sys.path.insert` |
