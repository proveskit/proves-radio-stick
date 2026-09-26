/*
 * PROVES Radio Stick V3 bring-up app.
 *
 * - USB CDC-ACM shell with the Zephyr LoRa shell ("lora send", "lora recv").
 * - Radio preset to the PROVES flight software link (437.4 MHz, BW 125 kHz,
 *   SF8, CR 4/5, preamble 8).
 * - Reads the USB-C CC pins and lowers TX power when the host only
 *   advertises default USB current (the E22 draws ~650 mA at 30 dBm).
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <stdio.h>
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/drivers/led.h>
#include <zephyr/drivers/lora.h>
#include <zephyr/logging/log.h>
#include <zephyr/shell/shell.h>

LOG_MODULE_REGISTER(radio_stick, LOG_LEVEL_INF);

#define FREQ_HZ      437400000
#define TX_POWER_MAX 22 /* SX1268 drive; the E22 PA brings this to ~30 dBm */
#define TX_POWER_LOW 10

static const struct adc_dt_spec cc[] = {
	ADC_DT_SPEC_GET_BY_NAME(DT_PATH(zephyr_user), cc1),
	ADC_DT_SPEC_GET_BY_NAME(DT_PATH(zephyr_user), cc2),
};

enum usb_current { USB_NONE, USB_DEFAULT, USB_1A5, USB_3A0 };

static const char *const usb_current_str[] = {
	"no CC (USB-A cable?)", "default (500/900 mA)", "1.5 A", "3.0 A",
};

/* USB Type-C vRd ranges seen across a 5.1k Rd. */
static enum usb_current read_usb_current(void)
{
	int32_t max_mv = 0;

	for (size_t i = 0; i < ARRAY_SIZE(cc); i++) {
		int16_t raw;
		struct adc_sequence seq = {.buffer = &raw, .buffer_size = sizeof(raw)};

		if (!adc_is_ready_dt(&cc[i]) || adc_channel_setup_dt(&cc[i]) < 0 ||
		    adc_sequence_init_dt(&cc[i], &seq) < 0 || adc_read_dt(&cc[i], &seq) < 0) {
			LOG_ERR("CC%d read failed", (int)i + 1);
			continue;
		}
		int32_t mv = raw;

		adc_raw_to_millivolts_dt(&cc[i], &mv);
		LOG_INF("CC%d = %d mV", (int)i + 1, mv);
		max_mv = MAX(max_mv, mv);
	}

	if (max_mv >= 1310) {
		return USB_3A0;
	}
	if (max_mv >= 700) {
		return USB_1A5;
	}
	if (max_mv >= 200) {
		return USB_DEFAULT;
	}
	return USB_NONE;
}

int main(void)
{
	const struct device *lora = DEVICE_DT_GET(DT_ALIAS(lora0));
	const struct device *leds = DEVICE_DT_GET(DT_PARENT(DT_ALIAS(led0)));
	enum usb_current cur = read_usb_current();
	int tx_power = (cur >= USB_1A5) ? TX_POWER_MAX : TX_POWER_LOW;
	char cmd[96];

	LOG_INF("USB-C host advertises %s -> TX power %d dBm", usb_current_str[cur], tx_power);

	if (!device_is_ready(lora)) {
		LOG_ERR("LoRa radio not ready");
		return 0;
	}

	snprintf(cmd, sizeof(cmd), "lora config freq %d bw 125 sf 8 cr 5 pre-len 8 tx-power %d",
		 FREQ_HZ, tx_power);
	if (shell_execute_cmd(NULL, cmd) < 0) {
		LOG_ERR("Radio preset failed: %s", cmd);
	}

	LOG_INF("Ready. Try: lora recv 10000  |  lora send hello");

	while (device_is_ready(leds)) {
		led_on(leds, 0);
		k_msleep(100);
		led_off(leds, 0);
		k_msleep(1900);
	}
	return 0;
}
