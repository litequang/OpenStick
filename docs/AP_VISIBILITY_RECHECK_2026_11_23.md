# AP visibility and normalized visible-profile validation — 2026-11-23

The owner's phone reacceptance after the SIM recovery fix failed: Wi-Fi was
absent or could not be joined. Do not retain the prior pending phone test as a
PASS, or infer AP reachability from SIM-bound Internet and local AP-active state.

## Physical observations and bounded diagnostic action

Two requested fresh Windows broadcast scans found nearby APs but neither the
USB's saved SSID nor its current BSSID. Comparisons used private values only in
memory; no SSID/MAC/raw scan was logged or committed. The USB still reported the
owned shared AP, wcn36xx driver, supplicant completed, channel 11 / 2462 MHz,
20 dBm, power saving off, hidden disabled, MaxNumSta=10 and isolation=0. Actual
supplicant network settings matched the saved SSID with ignore_broadcast_ssid=0,
mode=2 and frequency=2462; rfkill was unblocked. SIM-bound Internet worked.

Kernel messages were matched on the device against public Linux v6.12 format
strings; only static templates/counts/ages were exported. Recorded categories
included old BSS/STA-context-not-found and several spurious-TX-completion messages.
No firmware-crash, HAL timeout or beacon/start-AP failure was established. These
messages do not identify the cause of missing over-the-air visibility.

One bounded down/up of the existing AP was performed under network/modem locks,
after pending/power checks. The first attempt acquired no lock and stopped with
NETWORK_BUSY before a receipt or mutation; acquisition was then retried, without
retrying a submitted uncertain network operation. AP restart completed, preserving
saved identity/security/configuration/radio, live SIM connection and USB admin.
No modem reset, cellular activation, Windows adapter change or device reboot.

The immediate ordinary scan still did not find the AP. A later directed SSID
scan did; a subsequent ordinary native BSS scan received a fresh Beacon or Probe
Response after the scan request, matching the saved SSID/current BSSID, channel
11, RSSI -38 dBm and beacon interval 100 TU. This proves a current over-the-air
response, not continuous beaconing, phone association or DHCP/Internet acceptance.
No radio power-cycle was needed or performed. Phone reacceptance is pending.

Microsoft documents the native BSS [host receive timestamp and frame source](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/ns-wlanapi-wlan_bss_entry).
The returned network list alone may contain cached entries; compare receive time
against scan request before claiming a new frame. Do not add blind periodic AP
restarts based on local active state, zero associated clients or one missed scan.

## Separate confirmed software defect

The real NM-rewritten AP keyfile had no hidden key, while the saved setting and
effective supplicant both selected visible SSID. OpenStick required an explicit
hidden key before AP activation and therefore rejected this legal normalized
profile with AP_OPTIONS_INVALID. Copying a normalized setup profile into the
shared AP or replaying it could consequently fail before any AP activation.

NetworkManager defines [hidden as default FALSE](https://networkmanager.dev/docs/api/latest/settings-802-11-wireless.html).
Validation now treats an omitted hidden key as false. A saved hidden=true with
the key absent still fails closed; malformed values, mode/UUID mismatches and
isolation validation remain rejected. Activation does not rewrite profiles or
weaken saved security, client-limit or consent checks. No automatic AP restart,
firmware/kernel change or new polling thread is introduced.

Regression tests cover both owned AP types, saved visible/hidden choices and
adoption of a normalized setup profile while preserving the cellular profile.
This is a correction for repeat activation/boot compatibility, not proof that
the missing default key caused the already active AP to become invisible.
CI, installation and final observations are recorded only after execution.

Final local complete suite: **907 PASS, two Windows skips, exit 0**. The first
run had one new-test fixture failure (no existing cellular profile had yet been
created); its setup was corrected to establish that profile before testing its
preservation. No product assertion or existing test was removed.
