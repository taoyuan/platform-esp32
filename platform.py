# Copyright 2014-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from platformio.managers.platform import PlatformBase


class Espressif32Platform(PlatformBase):

    def configure_default_packages(self, variables, targets):
        if "buildfs" in targets:
            self.packages['tool-mkspiffs']['optional'] = False
        if variables.get("upload_protocol"):
            self.packages['tool-openocd-esp32']['optional'] = False
        return PlatformBase.configure_default_packages(self, variables,
                                                       targets)

    def get_boards(self, id_=None):
        result = PlatformBase.get_boards(self, id_)
        if not result:
            return result
        if id_:
            return self._add_default_debug_tools(result)
        else:
            for key, value in result.items():
                result[key] = self._add_default_debug_tools(result[key])
        return result

    def _add_default_debug_tools(self, board):
        non_debug_protocols = ["esptool"]
        supported_debug_tools = [
            "esp-prog",
            "iot-bus-jtag",
            "jlink",
            "minimodule",
            "olimex-arm-usb-tiny-h",
            "olimex-arm-usb-ocd-h",
            "olimex-arm-usb-ocd",
            "olimex-jtag-tiny",
            "tumpa"
        ]

        debug = board.manifest.get("debug", {})
        upload_protocol = board.manifest.get("upload", {}).get("protocol")
        upload_protocols = board.manifest.get("upload", {}).get(
            "protocols", [])
        if debug:
            upload_protocols.extend(supported_debug_tools)
        if upload_protocol and upload_protocol not in upload_protocols:
            upload_protocols.append(upload_protocol)

        board.manifest['upload']['protocols'] = upload_protocols

        if "tools" not in debug:
            debug['tools'] = {}

        # Only FTDI based debug probes
        for link in upload_protocols:
            if link in non_debug_protocols or link in debug['tools']:
                continue

            if link == "jlink":
                openocd_interface = link
            elif link in ("esp-prog", "ftdi"):
                openocd_interface = "ftdi/esp32_devkitj_v1"
            else:
                openocd_interface = "ftdi/" + link

            server_args = [
                "-s", "$PACKAGE_DIR/share/openocd/scripts",
                "-f", "share/openocd/scripts/interface/%s.cfg" % openocd_interface,
                "-f", "share/openocd/scripts/board/%s" % debug.get("openocd_board")
            ]

            debug['tools'][link] = {
                "server": {
                    "package": "tool-openocd-esp32",
                    "executable": "bin/openocd",
                    "arguments": server_args
                },
                "init_break": "thb app_main",
                "init_cmds": [
                    "define pio_reset_halt_target",
                    "   mon reset halt",
                    "   flushregs",
                    "end",
                    "define pio_reset_target",
                    "   mon reset",
                    "end",
                    "target extended-remote $DEBUG_PORT",
                    "$INIT_BREAK",
                    "$LOAD_CMD",
                    "pio_reset_halt_target"
                ],
                "onboard": link in debug.get("onboard_tools", []),
                "default": link == debug.get("default_tool")

            }

        board.manifest['debug'] = debug
        return board
