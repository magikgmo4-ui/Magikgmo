from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Dict, List


class Side(Enum):
    LONG = auto()
    SHORT = auto()
    FLAT = auto()


class Engine(Enum):
    COINM_SHORT = auto()
    USDTM_LONG = auto()
    GOLD_CFD_LONG = auto()


@dataclass
class MarketState:
    symbol: str
    price: float

    close_m15: Optional[float] = None
    close_h1: Optional[float] = None
    close_h4: Optional[float] = None

    # structure / indicateurs (à fournir)
    lower_high: bool = False
    lower_low: bool = False
    higher_low: bool = False

    below_ma_50: bool = False
    below_ma_100: bool = False
    above_ma_50: bool = False
    above_ma_100: bool = False

    rsi_above_50_rising: bool = False
    buyer_volume_dominant: bool = False

    # filtres / contexte
    macro_high_impact_soon: bool = False
    btc_is_leader: bool = True  # pour ETH/SOL si besoin


@dataclass
class Zone:
    low: float
    high: float

    def contains(self, price: float) -> bool:
        return self.low <= price <= self.high


@dataclass
class PlanLevels:
    entry_zone: Zone
    invalidation_level: float
    invalidation_tf: str  # "H1", "H4", "M15"
    tps: List[float]


@dataclass
class Signal:
    engine: Engine
    symbol: str
    side: Side
    reason: str
    entry_zone: Optional[Zone] = None
    invalidation_level: Optional[float] = None
    invalidation_tf: Optional[str] = None
    tps: Optional[List[float]] = None


# -----------------------------
# CONFIG: tes niveaux actuels
# -----------------------------
CONFIG: Dict[str, PlanLevels] = {
    # COIN-M SHORT
    "BTCUSDT.P:COINM_SHORT": PlanLevels(
        entry_zone=Zone(68600, 68900),
        invalidation_level=69200,  # invalidation: close H1 > 69200
        invalidation_tf="H1",
        tps=[67200, 66200, 65000],
    ),
    "ETHUSDT.P:COINM_SHORT": PlanLevels(
        entry_zone=Zone(1955, 1970),
        invalidation_level=2020,
        invalidation_tf="H1",
        tps=[1920, 1900, 1850],
    ),

    # USDT-M LONG (exemple BTC)
    "BTCUSDT.P:USDTM_LONG": PlanLevels(
        entry_zone=Zone(69200, 69300),  # pullback zone après reclaim
        invalidation_level=68700,
        invalidation_tf="H1",
        tps=[70500, 71200],
    ),

    # GOLD CFD BUY
    "XAUUSD:GOLD_CFD_LONG": PlanLevels(
        entry_zone=Zone(5033, 5035),
        invalidation_level=5025,  # invalidation: close M15 < 5025
        invalidation_tf="M15",
        tps=[5055, 5065, 5075],
    ),
}


def coinm_short_signal(ms: MarketState) -> Optional[Signal]:
    key = f"{ms.symbol}:COINM_SHORT"
    if key not in CONFIG:
        return None
    lv = CONFIG[key]

    structure_ok = ms.lower_high and (ms.lower_low or True)
    ma_ok = ms.below_ma_50 or ms.below_ma_100
    macro_ok = not ms.macro_high_impact_soon

    if not (structure_ok and ma_ok and macro_ok):
        return None

    if lv.entry_zone.contains(ms.price):
        return Signal(
            engine=Engine.COINM_SHORT,
            symbol=ms.symbol,
            side=Side.SHORT,
            reason="COIN-M SHORT: LH structure + sous MAs + prix dans zone d'entrée",
            entry_zone=lv.entry_zone,
            invalidation_level=lv.invalidation_level,
            invalidation_tf=lv.invalidation_tf,
            tps=lv.tps,
        )
    return None


def usdtm_long_signal(ms: MarketState) -> Optional[Signal]:
    key = f"{ms.symbol}:USDTM_LONG"
    if key not in CONFIG:
        return None
    lv = CONFIG[key]

    if ms.macro_high_impact_soon:
        return None
    if not ms.rsi_above_50_rising:
        return None
    if not ms.buyer_volume_dominant:
        return None
    if not (ms.above_ma_50 and ms.above_ma_100):
        return None

    if not ms.btc_is_leader and ms.symbol != "BTCUSDT.P":
        return None

    if lv.entry_zone.contains(ms.price):
        return Signal(
            engine=Engine.USDTM_LONG,
            symbol=ms.symbol,
            side=Side.LONG,
            reason="USDT-M LONG: bull confirmé (RSI>50 rising + vol acheteur + au-dessus MAs) + pullback zone",
            entry_zone=lv.entry_zone,
            invalidation_level=lv.invalidation_level,
            invalidation_tf=lv.invalidation_tf,
            tps=lv.tps,
        )
    return None


def gold_cfd_buy_signal(ms: MarketState) -> Optional[Signal]:
    key = f"{ms.symbol}:GOLD_CFD_LONG"
    if key not in CONFIG:
        return None
    lv = CONFIG[key]

    structure_ok = ms.higher_low and ms.above_ma_50
    macro_ok = not ms.macro_high_impact_soon

    if not (structure_ok and macro_ok):
        return None

    if lv.entry_zone.contains(ms.price):
        return Signal(
            engine=Engine.GOLD_CFD_LONG,
            symbol=ms.symbol,
            side=Side.LONG,
            reason="GOLD CFD: HL structure + au-dessus MA + prix dans zone d'achat",
            entry_zone=lv.entry_zone,
            invalidation_level=lv.invalidation_level,
            invalidation_tf=lv.invalidation_tf,
            tps=lv.tps,
        )
    return None


def pick_one_signal(signals: List[Signal]) -> Optional[Signal]:
    # Priorité actuelle (journal): COIN-M SHORT > GOLD > USDT-M LONG
    priority = {
        Engine.COINM_SHORT: 1,
        Engine.GOLD_CFD_LONG: 2,
        Engine.USDTM_LONG: 3,
    }
    if not signals:
        return None
    signals.sort(key=lambda s: priority.get(s.engine, 99))
    return signals[0]


def evaluate_all(ms_list: List[MarketState]) -> Optional[Signal]:
    candidates: List[Signal] = []

    for ms in ms_list:
        for fn in (coinm_short_signal, gold_cfd_buy_signal, usdtm_long_signal):
            s = fn(ms)
            if s:
                candidates.append(s)

    return pick_one_signal(candidates)


def pretty(sig: Optional[Signal]) -> str:
    if not sig:
        return "No signal."
    z = sig.entry_zone
    ztxt = f"{z.low}-{z.high}" if z else "n/a"
    tps = ", ".join(str(x) for x in (sig.tps or [])) or "n/a"
    return (
        f"Signal: {sig.engine.name} | {sig.symbol} | {sig.side.name}\n"
        f"Reason: {sig.reason}\n"
        f"Entry zone: {ztxt}\n"
        f"Invalidation: {sig.invalidation_tf} {'>' if sig.side==Side.SHORT else '<'} {sig.invalidation_level}\n"
        f"TPs: {tps}"
    )


if __name__ == "__main__":
    # EXEMPLE (tu remplaces avec tes valeurs TradingView)
    btc = MarketState(
        symbol="BTCUSDT.P",
        price=68750,
        close_h1=68110,
        lower_high=True,
        lower_low=True,
        below_ma_50=True,
        macro_high_impact_soon=False,
    )

    eth = MarketState(
        symbol="ETHUSDT.P",
        price=1960,
        close_h1=1938,
        lower_high=True,
        below_ma_50=True,
        macro_high_impact_soon=False,
    )

    xau = MarketState(
        symbol="XAUUSD",
        price=5034,
        close_m15=5042,
        higher_low=True,
        above_ma_50=True,
        macro_high_impact_soon=False,
    )

    sig = evaluate_all([btc, eth, xau])
    print(pretty(sig))
