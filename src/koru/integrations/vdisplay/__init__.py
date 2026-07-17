"""Split-out submodules of the (large) koru.integrations.vdisplay_client.

Cohesive clusters are being extracted here from the historical monolith;
vdisplay_client.py re-exports them for backward compatibility, so existing
`from koru.integrations.vdisplay_client import X` imports keep working.

Modules:

* :mod:`koru.integrations.vdisplay.portal_input` — RemoteDesktop portal type-in
* :mod:`koru.integrations.vdisplay.pointer_calibration` — ABS/adaptive pointer
* :mod:`koru.integrations.vdisplay.env_session` — prepare/session env flags
* :mod:`koru.integrations.vdisplay.desktop_probe` — monitors / IDE surface preflight
* :mod:`koru.integrations.vdisplay.surface_capture` — surface-registry capture confirm
"""
