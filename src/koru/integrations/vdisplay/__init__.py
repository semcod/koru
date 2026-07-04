"""Split-out submodules of the (large) koru.integrations.vdisplay_client.

Cohesive clusters are being extracted here from the historical monolith;
vdisplay_client.py re-exports them for backward compatibility, so existing
`from koru.integrations.vdisplay_client import X` imports keep working.
"""
