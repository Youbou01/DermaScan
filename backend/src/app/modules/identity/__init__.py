"""Identity module: accounts, health profile and blacklist.

Owns tables: user_account, user_profile, user_allergy,
user_blacklist_product, user_blacklist_ingredient.

PUBLIC INTERFACE: everything exported below. Other modules import ONLY from
here, never from models or repository.
"""

__all__: list[str] = []
