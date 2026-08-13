"""
Centralized business product catalog — single source of truth for prices,
models, captions, and payment rules. Prompts/tools should import from here.
"""
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class JammerModel:
    key: str
    display_name: str
    price_mmk: int
    image_prefix: str
    caption: str


VIP_SUBSCRIPTION_PRICE_MMK = 35000
JAMMER_MANDALAY_DEPOSIT_MMK = 10000

JAMMER_MODELS: Dict[str, JammerModel] = {
    "2_antenna": JammerModel(
        key="2_antenna",
        display_name="2 Antenna",
        price_mmk=140000,
        image_prefix="jammer_2ant",
        caption="📡 2 Antenna Jammer — 140,000 Ks",
    ),
    "3_antenna": JammerModel(
        key="3_antenna",
        display_name="3 Antenna",
        price_mmk=190000,
        image_prefix="jammer_3ant",
        caption="📡 3 Antenna Jammer — 190,000 Ks",
    ),
}

# Filename-prefix → caption (used by send_product_image)
PRODUCT_CAPTIONS: Dict[str, str] = {
    model.image_prefix: model.caption for model in JAMMER_MODELS.values()
}


def resolve_jammer_model(text: str) -> Optional[JammerModel]:
    """Map free-text model labels to a catalog entry."""
    if not text:
        return None
    normalized = text.strip().lower().replace("-", " ")
    if "3" in normalized and "ant" in normalized:
        return JAMMER_MODELS["3_antenna"]
    if "2" in normalized and "ant" in normalized:
        return JAMMER_MODELS["2_antenna"]
    return None


def jammer_min_amount(payment_type: str, model: Optional[JammerModel] = None) -> int:
    """
    Prepaid → full model price (or 0 if unknown).
    Mandalay COD deposit → 10,000.
    Plain COD with no deposit → 0 (skip amount check).
    """
    pt = (payment_type or "").strip().lower()
    if "deposit" in pt or "စရံ" in pt or "mandalay" in pt or "မန္တလေး" in pt:
        return JAMMER_MANDALAY_DEPOSIT_MMK
    if "prepaid" in pt or "ကြို" in pt:
        return model.price_mmk if model else 0
    return 0
