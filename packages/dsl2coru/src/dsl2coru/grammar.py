"""Text DSL grammar — compatibility shim.

Canonical implementations live in :mod:`dsl2coru.parser` (text → payload)
and :mod:`dsl2coru.serializer` (payload → text). This module re-exports
every name it historically defined so existing imports keep working.
"""

from __future__ import annotations

from dsl2coru.parser import _PARSERS as _PARSERS
from dsl2coru.parser import _flag as _flag
from dsl2coru.parser import _parse_auto as _parse_auto
from dsl2coru.parser import _parse_calibration as _parse_calibration
from dsl2coru.parser import _parse_chat as _parse_chat
from dsl2coru.parser import _parse_doctor as _parse_doctor
from dsl2coru.parser import _parse_ensure as _parse_ensure
from dsl2coru.parser import _parse_env as _parse_env
from dsl2coru.parser import _parse_lane as _parse_lane
from dsl2coru.parser import _parse_query as _parse_query
from dsl2coru.parser import _parse_repair_history as _parse_repair_history
from dsl2coru.parser import _parse_repair_run as _parse_repair_run
from dsl2coru.parser import _parse_status as _parse_status
from dsl2coru.parser import _parse_sync as _parse_sync
from dsl2coru.parser import _parse_text as _parse_text
from dsl2coru.parser import _parse_ui_click as _parse_ui_click
from dsl2coru.parser import _parse_ui_common as _parse_ui_common
from dsl2coru.parser import _parse_ui_key as _parse_ui_key
from dsl2coru.parser import _parse_ui_nl as _parse_ui_nl
from dsl2coru.parser import _parse_ui_type as _parse_ui_type
from dsl2coru.parser import _split_command as _split_command
from dsl2coru.parser import _truthy as _truthy
from dsl2coru.parser import _ui_args as _ui_args
from dsl2coru.parser import normalize_verb as normalize_verb
from dsl2coru.parser import parse_line as parse_line
from dsl2coru.serializer import _SERIALIZERS as _SERIALIZERS
from dsl2coru.serializer import _append_flag as _append_flag
from dsl2coru.serializer import _serialize_auto as _serialize_auto
from dsl2coru.serializer import _serialize_calibration as _serialize_calibration
from dsl2coru.serializer import _serialize_chat as _serialize_chat
from dsl2coru.serializer import _serialize_doctor as _serialize_doctor
from dsl2coru.serializer import _serialize_ensure as _serialize_ensure
from dsl2coru.serializer import _serialize_env as _serialize_env
from dsl2coru.serializer import _serialize_lane as _serialize_lane
from dsl2coru.serializer import _serialize_query as _serialize_query
from dsl2coru.serializer import _serialize_repair_history as _serialize_repair_history
from dsl2coru.serializer import _serialize_repair_run as _serialize_repair_run
from dsl2coru.serializer import _serialize_status as _serialize_status
from dsl2coru.serializer import _serialize_sync as _serialize_sync
from dsl2coru.serializer import _serialize_text as _serialize_text
from dsl2coru.serializer import _serialize_ui_click as _serialize_ui_click
from dsl2coru.serializer import _serialize_ui_key as _serialize_ui_key
from dsl2coru.serializer import _serialize_ui_nl as _serialize_ui_nl
from dsl2coru.serializer import _serialize_ui_type as _serialize_ui_type
from dsl2coru.serializer import to_text as to_text
