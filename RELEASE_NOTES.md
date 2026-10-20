# Release Notes - AirportRTW89 v1.0.0

**Production-grade, High-Performance macOS Wi-Fi Driver for Realtek RTL8922AE (Wi-Fi 7) and RTW89 Series**

### 📦 Release Highlights
- **Symmetric 200+ Mbps Throughput**: Verified 204.35 Mbps download and 200.46 Mbps upload on macOS Sequoia 15.8.1 with RTL8922AE on 5 GHz 80 MHz channel.
- **Kernel Panic Free**: Resolved all airportd disassociate NULL-pointer dereference panics.
- **Enterprise 802.1X PEAP Ready**: Connect seamlessly to campus/enterprise WPA-Enterprise networks (`eduroam`, `Enterprise-WPA`, etc.).
- **Clear Security Alerts**: Fixed AP IE list handling to eradicate macOS "Hidden Network" warning dialogs.
- **Self-Contained Build**: Bundled MacKernelSDK for zero-configuration building on modern Xcode.

### 💾 Installation Summary
1. Requires `Lilu.kext`, `AMFIPass.kext`, and OCLP-restored `IOSkywalkFamily.kext` & `IO80211FamilyLegacy.kext`.
2. Block native `IOSkywalkFamily` in OpenCore `Kernel -> Block`.
3. Add `AirportRTW.kext` in `Kernel -> Add` after legacy wireless components.
4. Run OCLP Post-Install Root Patch and reboot.
