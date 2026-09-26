# SPDX-License-Identifier: Apache-2.0

# STLINK-V3MINIE on J5 (STDC14).
board_runner_args(stm32cubeprogrammer "--port=swd" "--reset-mode=hw")
# Any CMSIS-DAP probe (e.g. Raspberry Pi Debug Probe on J22).
board_runner_args(pyocd "--target=stm32u585ciux")
# ROM bootloader over USB: hold BOOT0 (SW1), tap RESET (SW2).
board_runner_args(dfu-util "--pid=0483:df11" "--alt=0" "--dfuse")
board_runner_args(jlink "--device=STM32U585CI" "--reset-after-load")

include(${ZEPHYR_BASE}/boards/common/stm32cubeprogrammer.board.cmake)
include(${ZEPHYR_BASE}/boards/common/openocd-stm32.board.cmake)
include(${ZEPHYR_BASE}/boards/common/pyocd.board.cmake)
include(${ZEPHYR_BASE}/boards/common/dfu-util.board.cmake)
include(${ZEPHYR_BASE}/boards/common/jlink.board.cmake)
