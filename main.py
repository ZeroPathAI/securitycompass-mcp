"""Legacy entry point.

Kept for backwards compatibility with configurations that point at this
file directly. The real entry point lives at
``src/zeropath_securitycompass_mcp/__main__.py``; new installs should use::

    python -m zeropath_securitycompass_mcp
or::
    zeropath-securitycompass-mcp
"""

from zeropath_securitycompass_mcp.__main__ import main

if __name__ == "__main__":
    main()
