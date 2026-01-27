"""
Public Registry API Clients

These clients fetch REAL data from public company registries.
Gemini is NOT used for data generation - only for parsing complex responses.
"""


from .sec_edgar import SECEdgarAPI

from .gleif_api import GLEIFAPI

__all__ = [

    "SECEdgarAPI", 

    "GLEIFAPI",
    "JURISDICTION_CODES"
]
