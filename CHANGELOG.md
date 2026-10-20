# Changelog

All notable changes to the **AirportRTW89** project are documented in this file.

## [v1.0.0] - 2026-10-20 (Production Milestone: 200+ Mbps Symmetric Throughput)

### 🚀 Highlights
- **Full Realtek RTL8922AE (Wi-Fi 7) Support**: Production-stable Wi-Fi 7 data-plane operation under macOS Sequoia 15.8.1 (AMD MacPro7,1 / Darwin 24.6.0).
- **Symmetric 200+ Mbps Real-World Throughput**: Overcame historical 20 Mbps and 35 Mbps bottlenecks to achieve **204.35 Mbps Download / 200.46 Mbps Upload**.
- **Zero Kernel Panics**: Resolved airportd disassociate NULL-pointer dereference crash on boot and reconnects.
- **Enterprise / 802.1X PEAP Authentication**: Native connection support for campus and corporate enterprise networks (e.g., `eduroam`, `Enterprise-WPA`).
- **Eliminated "Hidden Network" Alerts**: Reimplemented IOCTL 48 (`AP_IE_LIST`) with synthetic IE fallbacks, clearing macOS CoreWLAN security warnings.

---

### Detailed Technical Commit History

#### 1. Performance & Throughput Enhancements
- **Batch TX DMA Kick-off (`dd188a7`)**:
  - Transitioned from single-packet `outputStart` to batch pulling (up to 32 frames) in `AirportRTW::outputStart`.
  - Implemented `rtw88_tx_write_batch` and `rtw88_tx_flush_kick` in `Senmiko.c`, aggregating multiple MPDUs into a single PCIe doorbell kick-off to allow the RTL8922AE MAC to build high-efficiency VHT A-MPDU aggregates.
- **NAPI Immediate Wakeup & Backpressure Relief (`dd188a7`)**:
  - Relocated TX resume callbacks to `rtw88_napi_thread_wrapper`.
  - Wired `ifp->iface->signalOutputThread()` in `ItlRtw89::resumeTransmit` to instantaneously resume sleeping kernel output threads upon TX descriptor reclamation.
- **Active TX Descriptor & TXBD Reclamation (`dd188a7`, `3bcd57c`, `f81ccec`)**:
  - Lowered TXBD reclamation threshold to `bd_cnt < 64` in `driver/pci.c`, eliminating queue starvation.
  - Added proactive ring reclamation in `rtw88_be_ring_avail` when free descriptors fall below 64 slots.
- **VHT 80 MHz Protocol Negotiation (`260d01d`, `3bcd57c`)**:
  - Initialized `ic->ic_sup_mcs` (MCS 0–15), `ic->ic_vhtcaps`, and VHT MCS 0–9 map in `ItlRtw89::attachNet80211`.
  - Enabled `IEEE80211_F_VHTON` globally so association requests advertise full VHT capabilities to APs.
  - Dynamically synchronized `sta->deflink.bandwidth` and center RF frequencies during association.
- **Open Network A-MPDU Aggregation (`260d01d`)**:
  - Lifted OpenBSD net80211 restriction in `ieee80211_output.c` that suppressed hardware A-MPDU packet aggregation on unencrypted networks.
- **Stack Memory Frame Buffering (`3bcd57c`)**:
  - Switched frame encapsulation buffering to stack memory for standard Ethernet frames (<= 2048 bytes), avoiding tens of thousands of `IOMalloc`/`IOFree` kernel heap cycles per second.

#### 2. Stability & Crash Fixes
- **Prevent airportd NULL-Deref Panic (`7feedee`)**:
  - Eliminated dangerous manual assignment `ic->ic_bss = NULL` before `ieee80211_new_state(ic, IEEE80211_S_SCAN, -1)` in `setDISASSOCIATE` and `setASSOCIATE`.
  - Added null pointer guards in `ItlRtw89::newstate`.
- **RTL8922AE PCI MSI Interrupt & Power State Fix (`af6dd10`)**:
  - Fixed PCI MSI interrupt configuration and eliminated PM Capability corruption.
- **Station Iterator & C2H RA Report Fix (`dd188a7`)**:
  - Implemented `ieee80211_iterate_stations_atomic` in `rtw88_compat.c`, ensuring firmware rate adaptation (C2H) reports and RX PPDU RSSI updates are processed.

#### 3. Wi-Fi Protocol & Compatibility Fixes
- **AP_IE_LIST & Hidden Network Warning Fix (`f81ccec`)**:
  - Unlocked `getAP_IE_LIST`, `getRSN_IE`, and `setRSN_IE` by removing conditional compilation constraints.
  - Implemented synthetic Tag 0 (SSID), Tag 1 (Rates), and Tag 48 (RSN) element fallback in `AirportSTAIOCTL.cpp` and `AirportRTWSkywalkInterface.cpp`.
  - Corrected beacon TLV slice parsing in `ieee80211_input.c` during `IEEE80211_S_RUN` state.
- **802.1X PEAP Enterprise Handshake (`36d3783`)**:
  - Signaled `LINK_STATE_UP` immediately upon 802.1X association response arrival, triggering macOS `eapolclient`.
  - Added support for `APPLE80211_CIPHER_MSK` and PMKSA cache lookups.
- **Watchdog Timer & Reconnection Deadlock (`36d3783`)**:
  - Routed `ItlRtw89::watchdog` through `ieee80211_watchdog(ifp)` to ensure management frame timeouts reset gracefully without sticking in `AUTH`/`ASSOC`.
- **Intelligent 5 GHz BSS Selection (`260d01d`, `3bcd57c`)**:
  - Integrated `ieee80211_ess_is_better` candidate scoring across all association interfaces to automatically lock onto 5 GHz 80 MHz nodes.

#### 4. Build System & Toolchain
- **Automated C Archive Compilation (`2fb38a5`)**:
  - Set `alwaysOutOfDate = 1` on all Xcode `Build RTW89 C Archive` phases to ensure `librtw89_c.a` is unconditionally rebuilt whenever C sources change.
