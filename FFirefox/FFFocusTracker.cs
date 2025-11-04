// =============================
// File: FFFocusTracker.cs
// =============================
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;
using System.IO;
using System.Collections.Generic;

public class FFFocusTracker
{
#if WINDOWS
    [DllImport("user32.dll")]
    private static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
#endif

    // So we don't spam the log
    private static DateTime _lastNoWindowLogUtc = DateTime.MinValue;
    private static DateTime _lastGnomeFalseLogUtc = DateTime.MinValue;

    public static void Main(string[] args)
    {
        string disp = Environment.GetEnvironmentVariable("DISPLAY");
        string wdisp = Environment.GetEnvironmentVariable("WAYLAND_DISPLAY");
        string sess = Environment.GetEnvironmentVariable("XDG_SESSION_TYPE");
        FFCommon.Log("FFFocusTracker", "Starting focus tracker... DISPLAY=" + (disp ?? "<null>") + " WAYLAND_DISPLAY=" + (wdisp ?? "<null>") + " XDG_SESSION_TYPE=" + (sess ?? "<null>"));
        try
        {
            RunLoop();
        }
        catch (Exception ex)
        {
            FFCommon.LogException("FFFocusTracker", "Main", ex);
            FFCommon.NotifyError("FF Focus Tracker crashed", ex.Message);
            FFCommon.OpenLogsFolderFailSafe();
        }
    }

    private static void RunLoop()
    {
        string lastSentProfile = string.Empty;

        while (true)
        {
            try
            {
                string prof = DetectActiveFirefoxProfile();
                if (!string.IsNullOrEmpty(prof))
                {
                    if (!string.Equals(prof, lastSentProfile, StringComparison.OrdinalIgnoreCase))
                    {
                        FFCommon.UpdateFocusedProfile(prof);
                        lastSentProfile = prof;
                    }
                }
                else
                {
                    DateTime now = DateTime.UtcNow;
                    if ((now - _lastNoWindowLogUtc).TotalSeconds > 15.0)
                    {
                        FFCommon.Log("FFFocusTracker", "No active Firefox window detected (Wayland blocked, missing xdotool/xprop, or non-Firefox focused).");
                        _lastNoWindowLogUtc = now;
                    }
                }
            }
            catch (Exception ex)
            {
                FFCommon.LogException("FFFocusTracker", "RunLoopDetect", ex);
            }

            Thread.Sleep(400);
        }
    }

    private static string DetectActiveFirefoxProfile()
    {
#if WINDOWS
        IntPtr h = GetForegroundWindow();
        if (h == IntPtr.Zero) return string.Empty;
        uint pid;
        GetWindowThreadProcessId(h, out pid);
        if (pid == 0) return string.Empty;
        return ProfileFromPid((int)pid);
#else
        // 1) Try GNOME Shell D-Bus
        string prof = TryGnomeShellPid();
        if (!string.IsNullOrEmpty(prof))
            return prof;

        // 2) Try xdotool (X11)
        prof = TryXdotool();
        if (!string.IsNullOrEmpty(prof))
            return prof;

        // 3) Try xprop (X11)
        prof = TryXprop();
        if (!string.IsNullOrEmpty(prof))
            return prof;

        // 4) HARD FALLBACK: infer from running firefox processes
        prof = FallbackGuessFromRunning();
        if (!string.IsNullOrEmpty(prof))
            return prof;

        return string.Empty;
#endif
    }

#if !WINDOWS
    private static string TryGnomeShellPid()
    {
        string gdbus = FindOnPath("gdbus");
        if (string.IsNullOrEmpty(gdbus))
            return string.Empty;

        string outp = ExecAndRead(gdbus,
            "call --session --dest org.gnome.Shell --object-path /org/gnome/Shell --method org.gnome.Shell.Eval \"global.display.get_focus_window().get_pid()\"",
            900);
        if (string.IsNullOrEmpty(outp))
            return string.Empty;

        if (outp.StartsWith("(false", StringComparison.OrdinalIgnoreCase))
        {
            DateTime now = DateTime.UtcNow;
            if ((now - _lastGnomeFalseLogUtc).TotalSeconds > 10.0)
            {
                // FFCommon.Log("FFFocusTracker", "GNOME Shell Eval exists but returned false (Eval disabled by shell).");
                _lastGnomeFalseLogUtc = now;
            }
            return string.Empty;
        }

        string digits = ExtractDigits(outp);
        int pid;
        if (!int.TryParse(digits, out pid) || pid <= 0)
            return string.Empty;

        return ProfileFromPid(pid);
    }

    private static string TryXdotool()
    {
        string xdotool = FindOnPath("xdotool");
        if (string.IsNullOrEmpty(xdotool))
        {
            // log once every 30s that xdotool is missing
            return string.Empty;
        }

        string pidStr = ExecAndRead(xdotool, "getactivewindow getwindowpid", 800);
        if (string.IsNullOrEmpty(pidStr))
            return string.Empty;

        int pid;
        if (!int.TryParse(pidStr.Trim(), out pid) || pid <= 0)
            return string.Empty;

        return ProfileFromPid(pid);
    }

    private static string TryXprop()
    {
        string sh = FindOnPath("sh");
        if (string.IsNullOrEmpty(sh))
            return string.Empty;

        string wid = ExecAndRead(sh, "-c \"xprop -root _NET_ACTIVE_WINDOW | awk -F '# ' '{print $2}'\"", 900);
        if (string.IsNullOrEmpty(wid))
            return string.Empty;

        string pidStr = ExecAndRead(sh, "-c \"xprop -id " + wid.Trim() + " _NET_WM_PID | awk '{print $3}'\"", 900);
        if (string.IsNullOrEmpty(pidStr))
            return string.Empty;

        int pid;
        if (!int.TryParse(pidStr.Trim(), out pid) || pid <= 0)
            return string.Empty;

        return ProfileFromPid(pid);
    }

    // --- NEW: If we can’t see focus at all, guess from running firefoxes.
    private static string FallbackGuessFromRunning()
    {
        try
        {
            string lastFocused;
            Dictionary<string, long> ticks;
            FFCommon.LoadFocusState(out lastFocused, out ticks);

            List<FFCommon.FFProc> running = FFCommon.GetRunningFirefoxProcesses();
            if (running == null || running.Count == 0)
                return string.Empty;

            // 1) exactly one firefox with a profile -> use it
            if (running.Count == 1 && !string.IsNullOrEmpty(running[0].ProfileName))
            {
                FFCommon.Log("FFFocusTracker", "FallbackGuessFromRunning: single Firefox detected -> " + running[0].ProfileName);
                return running[0].ProfileName;
            }

            // 2) If we have a lastFocused in state and it's currently running, re-affirm it
            if (!string.IsNullOrEmpty(lastFocused))
            {
                int i = 0;
                while (i < running.Count)
                {
                    if (string.Equals(running[i].ProfileName, lastFocused, StringComparison.OrdinalIgnoreCase))
                    {
                        // FFCommon.Log("FFFocusTracker", "FallbackGuessFromRunning: re-affirming last-focused from state -> " + lastFocused);
                        return lastFocused;
                    }
                    i++;
                }
            }

            // 3) Else pick the most recently started firefox that has a profile name
            DateTime newest = DateTime.MinValue;
            string newestProfile = string.Empty;
            int j = 0;
            while (j < running.Count)
            {
                if (!string.IsNullOrEmpty(running[j].ProfileName))
                {
                    if (running[j].StartTimeUtc > newest)
                    {
                        newest = running[j].StartTimeUtc;
                        newestProfile = running[j].ProfileName;
                    }
                }
                j++;
            }

            if (!string.IsNullOrEmpty(newestProfile))
            {
                FFCommon.Log("FFFocusTracker", "FallbackGuessFromRunning: picked most recently launched firefox -> " + newestProfile);
                return newestProfile;
            }

            // 4) If we still have nothing but we do have multiple processes without names, give up quietly.
            return string.Empty;
        }
        catch (Exception ex)
        {
            FFCommon.LogException("FFFocusTracker", "FallbackGuessFromRunning", ex);
            return string.Empty;
        }
    }

    private static string ProfileFromPid(int pid)
    {
        try
        {
            Process p = null;
            try { p = Process.GetProcessById(pid); } catch { p = null; }
            if (p == null) return string.Empty;

            string name = p.ProcessName;
            bool isFF = string.Equals(name, "firefox", StringComparison.OrdinalIgnoreCase)
                        || string.Equals(name, "firefox-bin", StringComparison.OrdinalIgnoreCase);
            try { p.Dispose(); } catch { }
            if (!isFF) return string.Empty;

            string cmd = FFCommon.GetProcessCommandLine(pid);
            if (string.IsNullOrEmpty(cmd)) return string.Empty;

            string prof = FFCommon.ExtractProfileFromCmd(cmd);
            if (!string.IsNullOrEmpty(prof)) return prof;

            string ppath = FFCommon.ExtractProfilePathFromCmd(cmd);
            if (!string.IsNullOrEmpty(ppath))
            {
                List<FFCommon.ProfileInfo> infos = FFCommon.ReadProfilesIni();
                int i = 0;
                string np = FFCommon.NormalisePath(ppath); // from your current FFCommon.cs
                while (i < infos.Count)
                {
                    if (FFCommon.NormalisePath(infos[i].PathOnDisk) == np)
                        return infos[i].Name;
                    i++;
                }
            }
        }
        catch { }
        return string.Empty;
    }

    private static string ExecAndRead(string file, string args, int timeoutMs)
    {
        try
        {
            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = file;
            psi.Arguments = args;
            psi.UseShellExecute = false;
            psi.RedirectStandardOutput = true;
            psi.RedirectStandardError = true;
            psi.CreateNoWindow = true;
            using (Process p = Process.Start(psi))
            {
                string s = p.StandardOutput.ReadToEnd();
                p.WaitForExit(timeoutMs);
                return s.Trim();
            }
        }
        catch { return string.Empty; }
    }

    private static string FindOnPath(string name)
    {
        string path = Environment.GetEnvironmentVariable("PATH");
        if (string.IsNullOrEmpty(path)) return string.Empty;
        string[] parts = path.Split(':');
        int i = 0;
        while (i < parts.Length)
        {
            string cand = Path.Combine(parts[i], name);
            if (File.Exists(cand)) return cand;
            i++;
        }
        return string.Empty;
    }

    private static string ExtractDigits(string s)
    {
        if (string.IsNullOrEmpty(s)) return string.Empty;
        System.Text.StringBuilder sb = new System.Text.StringBuilder();
        int i = 0;
        while (i < s.Length)
        {
            char c = s[i];
            if (c >= '0' && c <= '9') sb.Append(c);
            i++;
        }
        return sb.ToString();
    }
#endif
}
