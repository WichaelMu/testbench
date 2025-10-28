// FFFocusTracker.cs
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;

public class FFFocusTracker
{
#if WINDOWS
    [DllImport("user32.dll")] private static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
#endif

    [STAThread]
    public static void Main(string[] args)
    {
        FFCommon.Log("FFFocusTracker", "Starting focus tracker...");
        try { RunLoop(); }
        catch (Exception ex)
        {
            FFCommon.LogException("FFFocusTracker", "Main", ex);
            FFCommon.NotifyError("FF Focus Tracker crashed", ex.Message);
            FFCommon.OpenLogsFolderFailSafe();
        }
    }

    private static void RunLoop()
    {
        string lastSent = string.Empty;
        while (true)
        {
            try
            {
                string prof = DetectActiveFirefoxProfile();
                if (!string.IsNullOrEmpty(prof) && !string.Equals(prof, lastSent, StringComparison.OrdinalIgnoreCase))
                {
                    FFCommon.UpdateFocusedProfile(prof);
                    lastSent = prof;
                }
            }
            catch (Exception ex) { FFCommon.LogException("FFFocusTracker", "RunLoopDetect", ex); }
            Thread.Sleep(400);
        }
    }

    private static string DetectActiveFirefoxProfile()
    {
#if WINDOWS
        IntPtr h = GetForegroundWindow();
        if (h == IntPtr.Zero) return string.Empty;
        uint pid; GetWindowThreadProcessId(h, out pid);
        try
        {
            Process p = Process.GetProcessById((int)pid);
            try
            {
                string n = p.ProcessName;
                bool isFF = string.Equals(n, "firefox", StringComparison.OrdinalIgnoreCase) || string.Equals(n, "firefox.exe", StringComparison.OrdinalIgnoreCase);
                if (!isFF) return string.Empty;
                // Robust: resolve via parent chain so we always get the owning profile
                return FFCommon.ResolveProfileNameForPid((int)pid);
            }
            finally { try { p.Dispose(); } catch { } }
        }
        catch { return string.Empty; }
#else
        // X11: xdotool path (Wayland may restrict)
        try
        {
            string pidStr = ExecAndRead("xdotool", "getactivewindow getwindowpid");
            int n;
            if (!string.IsNullOrEmpty(pidStr) && int.TryParse(pidStr.Trim(), out n))
            {
                Process pr = null; try { pr = Process.GetProcessById(n); } catch { pr = null; }
                if (pr != null)
                {
                    string name = pr.ProcessName;
                    bool isFF = string.Equals(name, "firefox", StringComparison.OrdinalIgnoreCase) || string.Equals(name, "firefox-bin", StringComparison.OrdinalIgnoreCase);
                    try { pr.Dispose(); } catch { }
                    if (!isFF) return string.Empty;
                }
                return FFCommon.ResolveProfileNameForPid(n);
            }
        } catch { }

        // xprop fallback
        try
        {
            string wid = ExecAndRead("sh", "-c \"xprop -root _NET_ACTIVE_WINDOW | awk -F '# ' '{print $2}'\"");
            if (!string.IsNullOrEmpty(wid))
            {
                string pid = ExecAndRead("sh", "-c \"xprop -id " + wid.Trim() + " _NET_WM_PID | awk '{print $3}'\"");
                int n; if (int.TryParse(pid.Trim(), out n)) return FFCommon.ResolveProfileNameForPid(n);
            }
        } catch { }

        return string.Empty;
#endif
    }

#if !WINDOWS
    private static string ExecAndRead(string file, string args)
    {
        try
        {
            ProcessStartInfo psi = new ProcessStartInfo(); psi.FileName = file; psi.Arguments = args;
            psi.UseShellExecute = false; psi.RedirectStandardOutput = true; psi.RedirectStandardError = true; psi.CreateNoWindow = true;
            using (Process p = Process.Start(psi)) { string s = p.StandardOutput.ReadToEnd(); p.WaitForExit(800); return s.Trim(); }
        } catch { return string.Empty; }
    }
#endif
}
