"""offers module: retailers, per-retailer product offers and the cheapest price.

Owns tables: retailer, product_offer.

PUBLIC INTERFACE: everything exported below. Other modules import ONLY from here,
never from `models` or `repository`.
"""

from app.modules.offers.router import router as offers_router
from app.modules.offers.schemas import OfferListOut, OfferOut, RetailerOut
from app.modules.offers.service import OfferService

__all__ = ["OfferListOut", "OfferOut", "OfferService", "RetailerOut", "offers_router"]
