# AirportRTW89 - Realtek RTL8922AE (Wi-Fi 7) 与 RTW89 系列黑苹果高性能无线网卡驱动

[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](LICENSE)
[![macOS Compatibility](https://img.shields.io/badge/macOS-Sonoma%20%7C%20Sequoia%20%7C%20Tahoe-success.svg)](README_CN.md)
[![Hardware](https://img.shields.io/badge/Hardware-RTL8922AE%20(Wi--Fi%207)-orange.svg)](README_CN.md)
[![Speed Verified](https://img.shields.io/badge/实测极速-双向%20200%2B%20Mbps-brightgreen.svg)](README_CN.md)

[English Documentation](README.md) | [发布说明 (Release Notes)](RELEASE_NOTES.md) | [更新日志 (Changelog)](CHANGELOG.md)

**AirportRTW89** 是专为搭载 Realtek **RTW89** 系列 PCIe 无线网卡的 macOS 设备（黑苹果 Hackintosh 及支持的硬件平台）量身打造的高性能内核扩展驱动（Kext）。

本项目在开源社区 [AirportRTW](https://github.com/souissiak1-maker/AirportRTW) 及 [OpenIntelWireless/itlwm](https://github.com/OpenIntelWireless/itlwm) 架构的基础上进行了深度重构与底层重写，实现了全球首个在 macOS Sequoia / Sonoma 下稳定量产运行的 **Realtek RTL8922AE (Wi-Fi 7 / 802.11be)** 驱动实现。不仅彻底攻克了开机 Panic、802.1X 校园网/企业网无法握手、macOS 提示“隐藏的网络”黄色警告等顽疾，更打通了 VHT 80MHz 与批量硬件 TX DMA 并发，实测达成**双向 200+ Mbps 对称极速**！

---

## 🚀 实机测速与性能里程碑

在 **macOS Sequoia 15.8.1 (AMD 平台 MacPro7,1 / 64-bit Darwin 24.6.0)** 真实校园网络环境测试中，RTL8922AE 实现了下行 **204.35 Mbps**、上行 **200.46 Mbps** 的双向极速：

![实测测速截图](docs/assets/speedtest_200mbps.png)

### 硬件底层遥测参数 (`ioreg`)
```text
工作信道与频点:      5220 MHz (5 GHz 44 信道)
协商频宽 (Bandwidth): 80 MHz (VHT 80)
空间流数 (Streams):   2x2 MIMO
硬件包聚合 (A-MPDU):  TX & RX DMA 硬件聚合已全面激活 (Mask 0x3)
实测下行速率:         204.35 Mbps
实测上行速率:         200.46 Mbps
丢包率:               0.00%
```

---

## 🌟 核心突破与深度修复解析

### 1. 全球首发支持 Realtek RTL8922AE (Wi-Fi 7) 全链路数据平面
- 适配 Realtek 新一代 `rtw8922a` 固件加载与 PCIe MSI 中断处理机制，消除电源管理状态异常（PM Cap 越界损坏）。
- 硬件 TX/RX 环形缓冲区全面桥接至 macOS IOKit Skywalk 网络协议栈，支持动态通道切换与射频校准。

### 2. 彻底根除 `airportd` 断开关联时的空指针内核崩溃 (Kernel Panic)
- **故障现场**：系统开机或 Wi-Fi 重连时，macOS 守护进程 `airportd` 会率先下发 `setDISASSOCIATE` 请求。早期代码直接将 `ic->ic_bss = NULL`，随后调用 `ieee80211_new_state`，导致 `ItlRtw89::newstate` 试图解引用空指针，引发瞬时崩溃（Kernel NULL Pointer Dereference Panic）。
- **攻克方案**：移除了任何针对 `ic->ic_bss` 的手工置空逻辑，严格遵循 net80211 的标准状态机销毁流程，并在所有状态回调中加入防御性空指针校验。

### 3. 完整支持 802.1X PEAP 校园网与企业网（如 eduroam / 常见高校及企业 802.1X 网络）
- **故障现场**：macOS 用户态负责 802.1X 认证的守护进程 `eapolclient` 仅在驱动上报 `kIO80211NetworkLinkUp`（`LINK_STATE_UP`）后才会激活。此前驱动由于条件宏判断，在 RSN 企业网模式下抑制了链路激活通知，导致 `eapolclient` 根本无法启动，企业网永久卡在正在连接。
- **攻克方案**：在接收到 AP 关联成功响应时，针对 802.1X AKM 显式触发 `ieee80211_set_link_state(ic, LINK_STATE_UP)`，并完整注入 MSK 与 PMKSA 秘钥映射，使得用户仅需输入校园网学号/账号密码即可无缝连入。

### 4. 彻底消除 macOS“使用隐藏的网络”黄色安全警告
- **故障现场**：连接开放网络或企业网后，macOS 状态栏经常弹出警告提示：“使用隐藏的网络可能暴露可识别个人身份的信息...”。追踪 `airportd` 日志发现系统每 18 秒循环调用 IOCTL 48 (`APPLE80211_IOC_AP_IE_LIST`)，驱动此前直接返回 `kIOReturnUnsupported` (-3903)，导致系统误以为 AP 隐藏了 SSID 广播。
- **攻克方案**：激活并重构全功能 `getAP_IE_LIST`，在 AP 信标元素不完整时，驱动级自动规范合成 Tag 0 (SSID)、Tag 1 (Rates)、Tag 48 (RSN) 标准信标信息流，`airportd` 永远能读取到完整的广播 SSID，警告彻底消除！

### 5. 突破测速 20 Mbps 与 35 Mbps 瓶颈（全链路提速至 200+ Mbps）
- **VHT 80MHz 全速率协商**：修复了 HT/VHT 速率位图全为 0 的历史 Bug，全面激活 `IEEE80211_F_VHTON` 标志位，使网卡向 AP 发送包含完整 VHT Capabilities 的关联请求，空口握手物理协商速率直达 866.7 Mbps。
- **解除开放网络 A-MPDU 封锁**：移除了底层历史代码对未加密网络（如 Campus Web Portal）禁用硬件 A-MPDU 聚合的安全限制。
- **批量 TX DMA 取包与单次门铃 Kick-off**：macOS Pull 模型每次仅拉取 1 个包并敲击一次 PCIe 门铃会导致硬件 DMA 碎片化。本驱动重构为批量提取至多 32 帧后统一执行单次 `rtw89_core_tx_kick_off`，让 MAC 硬件引擎有充裕时间聚合大尺寸 VHT A-MPDU！
- **主动式 TX 描述符回收与 NAPI 即刻唤醒**：在发包环接近饱和前就地触发主动回收；并在 NAPI 中断处理完后立即调用 `ifp->iface->signalOutputThread()` 唤醒内核输出线程，消除发包停顿与背压（Backpressure）。

---

## 📡 硬件支持列表

| 芯片型号 | 协议代际 | PCIe 设备 ID | macOS 支持现状 |
| :--- | :--- | :--- | :--- |
| **Realtek RTL8922AE** | Wi-Fi 7 (802.11be) | `10ec:8922` | **完美支持，实测通过 (200+ Mbps)** |
| **Realtek RTL8852CE** | Wi-Fi 6E (802.11ax) | `10ec:c852` | 驱动支持 |
| **Realtek RTL8852BE** | Wi-Fi 6 (802.11ax) | `10ec:b852` | 驱动支持 |
| **Realtek RTL8852AE** | Wi-Fi 6 (802.11ax) | `10ec:8852` | 驱动支持 |
| **Realtek RTL8852BTE**| Wi-Fi 6 (802.11ax) | `10ec:b85b` | 驱动支持 |
| **Realtek RTL8851BE** | Wi-Fi 6 (802.11ax) | `10ec:b851` | 驱动支持 |

---

## 💻 兼容的 macOS 系统版本

- **macOS Tahoe (26.x / Darwin 25.x)**：支持（需配合 OCLP 恢复老版无线协议栈）。
- **macOS Sequoia (15.x / Darwin 24.x)**：完美支持，经过长期实机生产力运行检验。
- **macOS Sonoma (14.x / Darwin 23.x)**：完全支持。
- **macOS Ventura (13.x) 及更早版本**：支持。

---

## 🛠️ OpenCore 安装与配置规范

### 1. 必备 Kext 清单
自 macOS Sonoma (14.x) 起，苹果移除了第三方和旧版 802.11 驱动架构。要在 Sonoma / Sequoia / Tahoe 上启用驱动，必须使用 OCLP 配合以下 Kext：
1. `Lilu.kext` (推荐 1.6.8 或更新)
2. `AMFIPass.kext` (推荐 1.4.1 或更新)
3. `IOSkywalkFamily.kext` (由 OCLP 打包提取)
4. `IO80211FamilyLegacy.kext` (需应用扫描节点放行补丁，见下文说明)
5. `AirportRTW.kext` (本项目编译产物)

> [!IMPORTANT]
> **关于 `IO80211FamilyLegacy.kext` 补丁说明与合规指引**：
> 在 macOS Sonoma 与 Sequoia 系统下，原版 `IO80211FamilyLegacy` 内置了针对原厂 AirPort 网卡的扫描属性校验与节点过滤机制。若未打补丁，系统状态栏将无法显示扫描到的 Wi-Fi 列表。
> 由于该 Kext 属于 Apple 专有闭源版权，**按照开源社区规范，源码仓库严禁直接上传 Apple 二进制文件（防止触发 DMCA 导致仓库被封禁）**。
> 我们为你提供了三种极为便捷的补丁方式：
> - **方式一（一键自动化脚本）**：运行仓库自带脚本 `python3 tools/patch_io80211legacy.py <IO80211FamilyLegacy路径>`。
> - **方式二（GitHub Releases / 网盘懒人包）**：直接在 GitHub Releases 附件区下载已经包含全部补丁 Kext 的开箱即用懒人包（`AirportRTW-Full-Bundle.zip`）。
> - **方式三（OpenCore 内存热补丁）**：在 OpenCore `Kernel -> Patch` 中添加动态替换规则，无需修改磁盘文件，系统升级不失效。

### 2. OpenCore `config.plist` 修改步骤

#### A. Kernel -> Block（屏蔽系统原生 Skywalk）
在 `Kernel -> Block` 中屏蔽 macOS 自带的 `IOSkywalkFamily`，以便注入打过补丁的版本：
```xml
<dict>
    <key>Arch</key>
    <string>Any</string>
    <key>Comment</key>
    <string>Block native IOSkywalkFamily</string>
    <key>Enabled</key>
    <true/>
    <key>Identifier</key>
    <string>com.apple.iokit.IOSkywalkFamily</string>
    <key>MaxKernel</key>
    <string></string>
    <key>MinKernel</key>
    <string>23.0.0</string>
    <key>Strategy</key>
    <string>Exclude</string>
</dict>
```

#### B. Kernel -> Add（加载顺序极其关键！）
在 `Kernel -> Add` 中，必须严格遵守以下加载次序，否则会导致加载失败或卡引导：
1. `Lilu.kext`
2. `AMFIPass.kext`
3. `IOSkywalkFamily.kext`
4. `IO80211FamilyLegacy.kext`
5. `IO80211FamilyLegacy.kext/Contents/PlugIns/AirPortBrcmNIC.kext` (OCLP 套件包含此插件)
6. `AirportRTW.kext`

`AirportRTW.kext` 配置范例：
```xml
<dict>
    <key>Arch</key>
    <string>x86_64</string>
    <key>BundlePath</key>
    <string>AirportRTW.kext</string>
    <key>Comment</key>
    <string>Realtek RTW89 / RTL8922AE 驱动</string>
    <key>Enabled</key>
    <true/>
    <key>ExecutablePath</key>
    <string>Contents/MacOS/AirportRTW</string>
    <key>MaxKernel</key>
    <string></string>
    <key>MinKernel</key>
    <string>23.0.0</string>
    <key>PlistPath</key>
    <string>Contents/Info.plist</string>
</dict>
```

#### C. 启动参数与安全设置
- **引导参数 (boot-args)**：加入 `amfi_get_out_of_my_way=0x1` 或 `amfi=0x80`，以及 `ipc_control_port_options=0`。
- **安全设置**：将 `Misc -> Security -> SecureBootModel` 设为 `Disabled`。
- 进入系统后运行 **OpenCore-Legacy-Patcher (OCLP)** 的 **Post-Install Root Patch**，打完补丁后重启即可正常开启 Wi-Fi。

---

## 🔨 本地源码编译

本项目已完整内嵌 `MacKernelSDK`，不需要配置繁琐的外部环境，安装有 Xcode 命令行工具的 macOS 均可直接编译。

```bash
# 克隆代码仓库
git clone https://github.com/<你的用户名>/<你的仓库名>.git
cd <你的仓库名>

# 编译 Ventura / Sonoma / Sequoia / Tahoe 适用的 Release 版本
xcodebuild -project AirportRTW.xcodeproj \
           -target "AirportRTW-Ventura" \
           -configuration Release \
           build
```

编译完成后，驱动二进制位于：
```text
build/Release/Ventura/AirportRTW.kext
```

---

## 🔍 运行状态诊断与命令

在终端中执行以下命令可直接查看驱动与硬件运行参数：
```bash
ioreg -r -c AirportRTW
```

重点关注以下指标：
- `RTW89LastReceiveFrequency`: 当前无线频点（如 `5220` 代表 5 GHz 44 信道）。
- `RTW89RAAssocBandwidth`: 当前协商频宽（`2` 代表 80 MHz）。
- `RTW89RAAssocSpatialStreams`: 空间流数（`2` 代表 2x2 MIMO 双流）。
- `RTW89TxDescAggregationEnabled`: 为 `1` 表示 A-MPDU 硬件聚合正常工作。
- `RTW89TxBackpressureCount`: 大流量测速期间应保持极低（< 100），表明发包环路畅通无阻。

---

## 📜 开源协议与版权致谢

### 开源协议
本项目采用 **GNU General Public License v2.0 (GPLv2)** 协议开源。详细条款见 [LICENSE](LICENSE)。
- 核心硬件驱动逻辑衍生自 Linux 内核 `rtw89` (`GPL-2.0`)。
- 整体驱动框架基于 `OpenIntelWireless/itlwm` (`GPL-2.0`)。
- 网络协议栈衍生自 OpenBSD `net80211` (`BSD-3-Clause / ISC`)，依照 GPL-2.0 组合条款作为整体工程分发。
- `rtw/hal_rtw89/firmware/` 下的固件二进制文件遵循 Realtek 原厂分发条款。

### 致谢
- [OpenIntelWireless](https://github.com/OpenIntelWireless): 提供了卓越的 itlwm 架构基础。
- [Linux Wireless Community](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/net/wireless/realtek/rtw89): 维护高质量的 Linux 原生 rtw89 驱动。
- [Realtek](https://www.realtek.com/): 硬件规范与固件。
- [souissiak1-maker/AirportRTW](https://github.com/souissiak1-maker/AirportRTW): 原始移植项目。
- [Dortania / OpenCore](https://github.com/dortania): 现代引导框架与无线协议栈补丁机制。
