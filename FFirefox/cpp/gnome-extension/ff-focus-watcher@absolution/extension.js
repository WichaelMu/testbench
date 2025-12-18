/* exported init, enable, disable */

const { Gio, GLib, Meta, Shell } = imports.gi;
const ByteArray = imports.byteArray;

let focusSignalId = null;

function extractAfterFlag(cmd, flag) {
    let idx = cmd.indexOf(flag);
    if (idx < 0) {
        return "";
    }

    idx += flag.length;

    while (idx < cmd.length && /\s/.test(cmd[idx])) {
        idx++;
    }

    if (idx >= cmd.length) {
        return "";
    }

    if (cmd[idx] === '"') {
        let end = cmd.indexOf('"', idx + 1);
        if (end > idx) {
            return cmd.substring(idx + 1, end);
        }

        return "";
    }

    let end = idx;
    while (end < cmd.length && !/\s/.test(cmd[end])) {
        end++;
    }

    return cmd.substring(idx, end);
}

function resolveProfile(pid) {
    try {
        let path = `/proc/${pid}/cmdline`;
        let [ok, contents] = GLib.file_get_contents(path);

        if (!ok) {
            return ["", ""];
        }

        let cmdline = ByteArray.toString(contents)
            .replace(/\0/g, " ")
            .trim();

        if (!cmdline) {
            return ["", ""];
        }

        let name = extractAfterFlag(cmdline, "-P");
        let profPath = extractAfterFlag(cmdline, "-profile");

        if (name) {
            return [name, ""];
        }

        if (profPath) {
            return ["", profPath];
        }

        return ["", ""];
    } catch (e) {
        log(`FF Focus Watcher: resolveProfile error: ${e}`);
        return ["", ""];
    }
}

function writeFocus(metaWindow) {
    try {
        let appName = "Boot";
        let pid = 0;
        let profileName = "";
        let profilePath = "";

        if (metaWindow) {
            pid = metaWindow.get_pid();

            let tracker = Shell.WindowTracker.get_default();
            let app = tracker.get_window_app(metaWindow);
            let wmClass = metaWindow.get_wm_class() || "";

            let isFirefox = false;

            if (wmClass.toLowerCase() === "firefox") {
                isFirefox = true;
            } else if (app) {
                let id = app.get_id() || "";
                if (id.toLowerCase().indexOf("firefox") >= 0) {
                    isFirefox = true;
                }
            }

            if (isFirefox) {
                // Match the old Python behaviour: "Firefox" for app
                appName = "Firefox";

                if (pid > 0) {
                    [profileName, profilePath] = resolveProfile(pid);
                }
            } else {
                if (app) {
                    appName = app.get_name();
                } else if (wmClass) {
                    appName = wmClass;
                } else {
                    appName = "Unknown";
                }
            }
        }

        // ISO-8601 timestamp; previous code wrote %Y-%m-%dT%H:%M:%S%z,
        // but FFLinkRouter never parsed the offset anyway.
        let ts = new Date().toISOString();

        let payload = {
            timestamp: ts,
            app: appName,
            pid: pid,
            profile_name: profileName,
            profile_path: profilePath
        };

        let dir = GLib.build_filenamev([GLib.get_home_dir(), ".local", "share", "FF"]);
        GLib.mkdir_with_parents(dir, 0o755);

        let file = GLib.build_filenamev([dir, "focus.json"]);
        let data = JSON.stringify(payload);
        GLib.file_set_contents(file, data + "\n");
    } catch (e) {
        log(`FF Focus Watcher: writeFocus error: ${e}`);
    }
}

function init() {
}

function enable() {
    // Seed Boot record, same semantics as before
    writeFocus(null);

    let display = global.display;

    focusSignalId = display.connect("notify::focus-window", () => {
        let win = display.focus_window;

        if (win) {
            writeFocus(win);
        }
    });
}

function disable() {
    if (focusSignalId) {
        global.display.disconnect(focusSignalId);
        focusSignalId = null;
    }
}
