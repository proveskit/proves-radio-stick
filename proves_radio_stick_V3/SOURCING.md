# V3 sourcing check (Phase 0)

Checked 2026-09-26 against the JLCPCB parts API and LCSC. Stock moves daily;
re-run before ordering. "Basic" = no JLC loading fee; "Extended" = per-unique-
part loading fee.

## New parts for V3

| Ref (planned) | Part | LCSC | Type | JLC stock | ~$ (qty 1) | Notes |
|---|---|---|---|---|---|---|
| U1 | STM32U585CIU6, UFQFPN-48 | C5271026 | Extended | 103 | 11.73 | **Thin stock.** Buy into JLC parts library now. |
| Y1 (HSE) | X322516MLB4SI 16 MHz 3225, CL 9 pF, ±10 ppm | C13738 | **Basic** | 132k | 0.09 | Load caps 12 pF (C1547, Basic), confirm gm margin per ST AN2867 |
| Y2 (LSE) | SC-32S 32.768 kHz 3215, CL 7 pF | C97604 | Extended | 168k | 0.19 | No Basic 32.768 kHz exists. Load caps 10 pF (C32949, Basic) |
| U2 (ESD) | USBLC6-2SC6 (ST) | C7519 | Extended | 44k | 0.18 | Cheaper second sources: C2827654, C2687116 |
| J5 (STDC14) | HX PZ1.27-2x7P ZZ, male 2x7 1.27 mm THT | C22438122 | Extended | 10k | 0.11 | THT, like SMA and J3 already are. Samtec FTSH-107 only has ~12 in stock |
| SW3 (user) | KMR221GLFS | C72443 | Extended | 8k | 0.65 | Same part as SW1/SW2, so no extra fee |

Don't use C41397116 (`PM1.27-2x7P`): it's a **female** socket.

## Carried over from V2 (re-checked)

| Part | LCSC | Type | JLC stock | Action |
|---|---|---|---|---|
| E22-400M30S | C411292 | Extended | 250 | OK. Buy with the MCU |
| TPS62085RLTT | C2070694 | Extended | **216** | Switch to **TPS62085RLTR C130072** (same die, big reel, 1284 in stock) |
| TPS22918DBVR | C131941 | Extended | 13.7k | OK |
| TYPE-C-31-M-12 | C165948 | Extended | 169k | OK |
| Amphenol 132134 SMA | C3174425 | Extended | 1.6k | OK |
| KF128-2.54-10P terminal | C474928 | Extended | 2.5k | OK |
| BM03B-SRSS-TB JST-SH (J22) | C160389 | Extended | 33k | OK (kept by decision) |
| BLM21PG600SN1D ferrite | C18305 | Extended | 90k | OK |
| XFL4015-471MEC inductor | C18221164 | Extended | 3k | OK, $4.20 each |
| LQW18ANR12G 120 nH | C86138 | Extended | 15k | OK |
| GRM32ER61A107ME20L 100 µF | C84455 | Extended | 20k | OK |
| 162k / 510k buck divider | C54068 / C11616 | Extended | 13k / 8k | Could swap to Basic values (see below) |
| 100n, 10µ, 4.7µ, 1µ, 22µ, 47µ, 1n, 100p caps; 10k, 1k, 4.7k, 5.1k, 22, 33 Ω; KT-0603W LED | various | Basic | millions | OK |

## Removed from V2
RP2350 (C42411118), W25Q128JVS (C97521), ABM8 12 MHz (C20625731), L3 3.3 µH
(C42411119), NSR0320 BOOTSEL diode (C48192), R7/R8 22 Ω USB series, R93/R94.

## Findings that change the plan

1. **No MCU fallback.** STM32U575CIU6 (C5271012) has 0 stock. The only
   in-stock UFQFPN-48 U5 alternative is STM32U575CIU6**Q** (SMPS, 8 pcs), which
   needs a different power design. LQFP-48 U585 (C5271027 CIT6: 10 pcs,
   C5271025 CIT3: 21 pcs) would need a footprint change. **Action:** buy the
   CIU6 and E22 modules into the JLC parts library as soon as the design
   freezes, before Gerbers are final.
2. **Extended part count is about 18**, not ≤ 12. The unavoidable ones are
   the MCU, radio, power ICs, connectors, magnetics and LSE crystal. To trim:
   swap the 162k/510k TPS62085 feedback divider for Basic values (e.g. 100k /
   32.4k gives about 3.27 V; check which are Basic), and pick a Basic 100 µF
   bulk cap if one fits. That saves up to 3 fees, which is minor next to MCU
   and module cost.
3. **Per-board BOM** is dominated by the MCU ($11.73), E22 ($6.71), SMA
   ($4.49) and XFL4015 ($4.20). Expect roughly $30 in parts per board before
   PCB, assembly and loading fees.
