// FFCommon.cs (C#5-safe)
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;

#if WINDOWS
using System.Management;         // WMI for CommandLine + ParentProcessId
using System.Windows.Forms;      // NotifyIcon
using System.Drawing;            // SystemIcons
#endif

public static class FFCommon
{
    // ---------- Paths & logging ----------
    public static string GetBaseDir()
    {
#if WINDOWS
        string baseDir = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        return Path.Combine(baseDir, "FF");
#else
        string xdg = Environment.GetEnvironmentVariable("XDG_DATA_HOME");
        if (string.IsNullOrEmpty(xdg))
        {
            string home = Environment.GetEnvironmentVariable("HOME");
            if (string.IsNullOrEmpty(home)) home = ".";
            xdg = Path.Combine(home, ".local", "share");
        }
        return Path.Combine(xdg, "FF");
#endif
    }

    public static string GetLogsDir()
    {
        string d = Path.Combine(GetBaseDir(), "logs");
        EnsureDirectory(d);
        return d;
    }

    public static string GetStateDir()
    {
        string d = Path.Combine(GetBaseDir(), "state");
        EnsureDirectory(d);
        return d;
    }

    public static string GetStateFile()
    {
        return Path.Combine(GetStateDir(), "focus_state.txt");
    }

    public static void EnsureDirectory(string path)
    {
        if (!Directory.Exists(path)) Directory.CreateDirectory(path);
    }

    public static string GetLocalTime (string Format = "yyyy-MM-dd")
    {
	    return DateTime.UtcNow.ToLocalTime ().ToString (Format);
    }

    public static void LogEmpty (string Component)
    {
        try
        {
            string file = Path.Combine(GetLogsDir(), Component + "-" + GetLocalTime () + ".log");
            File.AppendAllText(file, Environment.NewLine);
        }
        catch { }
    }

    public static void Log(string component, string message)
    {
        try
        {
            string file = Path.Combine(GetLogsDir(), component + "-" + GetLocalTime () + ".log");
            File.AppendAllText(file, GetLocalTime ("o") + " " + message + Environment.NewLine);
        }
        catch { }
    }

    public static void LogException(string component, string context, Exception ex)
    {
        try
        {
            string file = Path.Combine(GetLogsDir(), component + "-" + GetLocalTime () + ".log");
            StringBuilder sb = new StringBuilder();
            sb.Append(GetLocalTime ("o")).Append(" ").Append(context).Append(": ")
              .Append(ex.GetType().FullName).Append(": ").Append(ex.Message).AppendLine()
              .Append(ex.StackTrace).AppendLine();
            File.AppendAllText(file, sb.ToString());
        }
        catch { }
    }

    public static void OpenLogsFolderFailSafe()
    {
        try
        {
#if WINDOWS
            Process.Start("explorer.exe", GetLogsDir());
#else
            TryStart("xdg-open", GetLogsDir());
#endif
        }
        catch { }
    }

    public static void NotifyError(string title, string body)
    {
        try
        {
#if WINDOWS
            using (NotifyIcon ni = new NotifyIcon())
            {
                ni.Visible = true;
                ni.Icon = SystemIcons.Information;
                ni.BalloonTipTitle = title;
                ni.BalloonTipText = body;
                ni.ShowBalloonTip(3000);
                System.Threading.Thread.Sleep(3200);
                ni.Visible = false;
            }
#else
            TryStart("notify-send", title + "\n" + body);
#endif
        }
        catch { }
    }

    // ---------- Firefox profiles ----------
    public class ProfileInfo { public string Name; public string PathOnDisk; public bool IsDefault; }

    public static string GetProfilesIniPath()
    {
#if WINDOWS
        string roaming = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
        return Path.Combine(roaming, "Mozilla", "Firefox", "profiles.ini");
#else
        string home = Environment.GetEnvironmentVariable("HOME");
        if (string.IsNullOrEmpty(home)) home = ".";
        return Path.Combine(home, ".mozilla", "firefox", "profiles.ini");
#endif
    }

    public static List<ProfileInfo> ReadProfilesIni()
    {
        List<ProfileInfo> list = new List<ProfileInfo>();
        try
        {
            string ini = GetProfilesIniPath();
            if (!File.Exists(ini)) return list;

            string[] lines = File.ReadAllLines(ini);
            ProfileInfo current = null;
            string baseDir = Path.GetDirectoryName(ini);
            int i = 0;
            while (i < lines.Length)
            {
                string line = lines[i].Trim();
                if (line.StartsWith("[Profile", StringComparison.OrdinalIgnoreCase))
                {
                    if (current != null) list.Add(current);
                    current = new ProfileInfo();
                }
                else if (current != null)
                {
                    int eq = line.IndexOf('=');
                    if (eq > 0)
                    {
                        string key = line.Substring(0, eq).Trim();
                        string val = line.Substring(eq + 1).Trim();
                        if (string.Equals(key, "Name", StringComparison.OrdinalIgnoreCase)) current.Name = val;
                        else if (string.Equals(key, "Path", StringComparison.OrdinalIgnoreCase))
                        {
                            bool isRelative = false;
                            int j = i - 1;
                            while (j >= 0 && j >= i - 5)
                            {
                                string l2 = lines[j].Trim();
                                int eq2 = l2.IndexOf('=');
                                if (eq2 > 0 && string.Equals(l2.Substring(0, eq2).Trim(), "IsRelative", StringComparison.OrdinalIgnoreCase))
                                { isRelative = l2.Substring(eq2 + 1).Trim() == "1"; break; }
                                j--;
                            }
                            current.PathOnDisk = isRelative ? Path.Combine(baseDir, val) : val;
                        }
                        else if (string.Equals(key, "Default", StringComparison.OrdinalIgnoreCase)) current.IsDefault = (val == "1");
                    }
                }
                i++;
            }
            if (current != null) list.Add(current);
        }
        catch (Exception ex) { LogException("FFCommon", "ReadProfilesIni", ex); }
        return list;
    }

    public static string GetDefaultProfileName()
    {
        try
        {
            List<ProfileInfo> info = ReadProfilesIni();
            int k = 0;
            while (k < info.Count)
            {
                if (info[k].IsDefault && !string.IsNullOrEmpty(info[k].Name)) return info[k].Name;
                k++;
            }
            if (info.Count > 0 && !string.IsNullOrEmpty(info[0].Name)) return info[0].Name;
        }
        catch (Exception ex) { LogException("FFCommon", "GetDefaultProfileName", ex); }
        return "default";
    }

    // ---------- Focus state ----------
    // focus_state.txt:
    // LastFocusedProfile=<name>
    // <profile>|<ticksUtc>
    public static void LoadFocusState(out string lastFocusedProfile, out Dictionary<string, long> focusTicks)
    {
        lastFocusedProfile = string.Empty;
        focusTicks = new Dictionary<string, long>(StringComparer.OrdinalIgnoreCase);
        try
        {
            string f = GetStateFile();
            if (!File.Exists(f)) return;
            string[] lines = File.ReadAllLines(f);
            int i = 0;
            while (i < lines.Length)
            {
                string line = lines[i].Trim();
                if (line.StartsWith("LastFocusedProfile=", StringComparison.Ordinal))
                    lastFocusedProfile = line.Substring("LastFocusedProfile=".Length);
                else if (line.Length > 0)
                {
                    int p = line.IndexOf('|');
                    if (p > 0)
                    {
                        string name = line.Substring(0, p);
                        string num = line.Substring(p + 1);
                        long ticks;
                        if (long.TryParse(num, out ticks)) focusTicks[name] = ticks;
                    }
                }
                i++;
            }
        }
        catch (Exception ex) { LogException("FFCommon", "LoadFocusState", ex); }
    }

    public static void SaveFocusState(string lastFocusedProfile, Dictionary<string, long> focusTicks)
    {
        try
        {
            StringBuilder sb = new StringBuilder();
            sb.Append("LastFocusedProfile=").Append(lastFocusedProfile == null ? string.Empty : lastFocusedProfile).AppendLine();
            foreach (KeyValuePair<string, long> kv in focusTicks)
                sb.Append(kv.Key).Append('|').Append(kv.Value).AppendLine();
            File.WriteAllText(GetStateFile(), sb.ToString());
        }
        catch (Exception ex) { LogException("FFCommon", "SaveFocusState", ex); }
    }

    public static void UpdateFocusedProfile(string profileName)
    {
        if (string.IsNullOrEmpty(profileName)) return;
        string last; Dictionary<string, long> map;
        LoadFocusState(out last, out map);
        map[profileName] = DateTime.UtcNow.Ticks;
        SaveFocusState(profileName, map);
        Log("FFFocusTracker", "Focused profile now: " + profileName);
    }

    // ---------- Process helpers ----------
    public class FFProc { public int Pid; public string ProfileName; public DateTime StartTimeUtc; }

    public static List<FFProc> GetRunningFirefoxProcesses()
    {
        List<FFProc> raw = new List<FFProc>();
        try
        {
            Process[] procs = Process.GetProcesses();
            int i = 0;
            while (i < procs.Length)
            {
                Process p = procs[i];
                try
                {
                    string n = p.ProcessName;
                    bool isFF = string.Equals(n, "firefox", StringComparison.OrdinalIgnoreCase) ||
                                string.Equals(n, "firefox-bin", StringComparison.OrdinalIgnoreCase) ||
                                string.Equals(n, "firefox.exe", StringComparison.OrdinalIgnoreCase);
                    if (isFF)
                    {
                        string prof = ResolveProfileNameForPid(p.Id); // <— parent-chain resolve
                        DateTime st; try { st = p.StartTime.ToUniversalTime(); } catch { st = DateTime.MinValue; }
                        FFProc f = new FFProc(); f.Pid = p.Id; f.ProfileName = prof; f.StartTimeUtc = st;
                        raw.Add(f);
                    }
                }
                catch { }
                finally { try { p.Dispose(); } catch { } }
                i++;
            }

            // keep most-recent-start per profile
            Dictionary<string, FFProc> byProf = new Dictionary<string, FFProc>(StringComparer.OrdinalIgnoreCase);
            int k = 0;
            while (k < raw.Count)
            {
                string key = string.IsNullOrEmpty(raw[k].ProfileName) ? "" : raw[k].ProfileName;
                FFProc cur;
                if (!byProf.TryGetValue(key, out cur) || raw[k].StartTimeUtc > cur.StartTimeUtc) byProf[key] = raw[k];
                k++;
            }
            return new List<FFProc>(byProf.Values);
        }
        catch (Exception ex) { LogException("FFCommon", "GetRunningFirefoxProcesses", ex); return new List<FFProc>(); }
    }

    public static string NormalizePath(string p)
    {
        if (string.IsNullOrEmpty(p)) return p;
        string r = p.Replace('\\', '/');
        while (r.Length > 1 && r.EndsWith("/")) r = r.Substring(0, r.Length - 1);
        return r;
    }

    public static string GetProcessCommandLine(int pid)
    {
        try
        {
#if WINDOWS
            using (ManagementObjectSearcher s = new ManagementObjectSearcher("SELECT CommandLine FROM Win32_Process WHERE ProcessId = " + pid))
            {
                foreach (ManagementObject o in s.Get())
                {
                    object cl = o["CommandLine"];
                    if (cl != null) return cl.ToString();
                }
            }
            return string.Empty;
#else
            string path = "/proc/" + pid + "/cmdline";
            if (!File.Exists(path)) return string.Empty;
            byte[] data = File.ReadAllBytes(path);
            if (data == null || data.Length == 0) return string.Empty;
            for (int i = 0; i < data.Length; i++) if (data[i] == 0) data[i] = (byte)' ';
            return Encoding.UTF8.GetString(data);
#endif
        }
        catch { return string.Empty; }
    }

    public static string ExtractProfileFromCmd(string cmd)
    {
        if (string.IsNullOrEmpty(cmd)) return string.Empty;
        try { Match m = new Regex("-P\\s+\"?([^\"\\s]+)\"?", RegexOptions.IgnoreCase).Match(cmd); if (m.Success) return m.Groups[1].Value; }
        catch { }
        return string.Empty;
    }

    public static string ExtractProfilePathFromCmd(string cmd)
    {
        if (string.IsNullOrEmpty(cmd)) return string.Empty;
        try { Match m = new Regex("-profile\\s+\"?([^\"]+)\"?", RegexOptions.IgnoreCase).Match(cmd); if (m.Success) return m.Groups[1].Value; }
        catch { }
        return string.Empty;
    }

    // --- Robust profile resolution: walk parent chain until we find the launcher with -P / -profile ---
    public static string ResolveProfileNameForPid(int pid)
    {
        try
        {
            List<ProfileInfo> infos = ReadProfilesIni();
            Dictionary<string, string> pathToName = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            int i = 0; while (i < infos.Count) { if (!string.IsNullOrEmpty(infos[i].PathOnDisk) && !string.IsNullOrEmpty(infos[i].Name)) pathToName[NormalizePath(infos[i].PathOnDisk)] = infos[i].Name; i++; }

            int cur = pid; int guard = 0;
            while (cur > 0 && guard < 50)
            {
                string cl = GetProcessCommandLine(cur);
                string prof = ExtractProfileFromCmd(cl);
                if (!string.IsNullOrEmpty(prof)) return prof;

                string ppath = ExtractProfilePathFromCmd(cl);
                if (!string.IsNullOrEmpty(ppath))
                {
                    string np = NormalizePath(ppath);
                    string mapped;
                    if (pathToName.TryGetValue(np, out mapped) && !string.IsNullOrEmpty(mapped)) return mapped;
                }

                int parent = GetParentPid(cur);
                if (parent <= 0 || parent == cur) break;
                cur = parent; guard++;
            }
        }
        catch (Exception ex) { LogException("FFCommon", "ResolveProfileNameForPid", ex); }
        return string.Empty;
    }

    public static int GetParentPid(int pid)
    {
        try
        {
#if WINDOWS
            using (ManagementObjectSearcher s = new ManagementObjectSearcher("SELECT ParentProcessId FROM Win32_Process WHERE ProcessId = " + pid))
            {
                foreach (ManagementObject o in s.Get())
                {
                    object pp = o["ParentProcessId"];
                    if (pp != null) return Convert.ToInt32((uint)pp);
                }
            }
            return 0;
#else
            string path = "/proc/" + pid + "/status";
            if (!File.Exists(path)) return 0;
            string[] lines = File.ReadAllLines(path);
            int i = 0; while (i < lines.Length) { if (lines[i].StartsWith("PPid:")) { int n; if (int.TryParse(lines[i].Substring(5).Trim(), out n)) return n; } i++; }
            return 0;
#endif
        }
        catch { return 0; }
    }

    // ---------- Launch ----------
    public static bool TryStart(string file, string args)
    {
        try
	{
		ProcessStartInfo psi = new ProcessStartInfo();
		psi.FileName = file;
		psi.Arguments = args;
		psi.UseShellExecute = false;
		psi.CreateNoWindow = true;
		return Process.Start(psi) != null;
	}
        catch { return false; }
    }

    public static string FindFirefoxExecutable()
    {
#if WINDOWS
        try
        {
            ProcessStartInfo psi = new ProcessStartInfo(); psi.FileName = "where"; psi.Arguments = "firefox"; psi.UseShellExecute = false; psi.RedirectStandardOutput = true; psi.CreateNoWindow = true;
            using (Process p = Process.Start(psi))
            {
                string outp = p.StandardOutput.ReadToEnd(); p.WaitForExit(1500);
                if (!string.IsNullOrEmpty(outp))
                {
                    string[] lines = outp.Split(new char[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
                    if (lines.Length > 0 && File.Exists(lines[0])) return lines[0];
                }
            }
        } catch { }
        string pf = Environment.GetEnvironmentVariable("ProgramFiles"); if (!string.IsNullOrEmpty(pf)) { string p1 = Path.Combine(pf, "Mozilla Firefox", "firefox.exe"); if (File.Exists(p1)) return p1; }
        string pf86 = Environment.GetEnvironmentVariable("ProgramFiles(x86)"); if (!string.IsNullOrEmpty(pf86)) { string p2 = Path.Combine(pf86, "Mozilla Firefox", "firefox.exe"); if (File.Exists(p2)) return p2; }
        return "firefox";
#else
        return "firefox";
#endif
    }

    public static bool LaunchFirefox(string profileName, string url)
    {
        try
        {
            string ff = FindFirefoxExecutable();
            StringBuilder args = new StringBuilder();
            if (!string.IsNullOrEmpty(profileName))
		    args.Append(" -P \"").Append(profileName).Append("\"");
            if (!string.IsNullOrEmpty(url))
		    args.Append(" -new-tab \"").Append(url).Append("\"");

            ProcessStartInfo psi = new ProcessStartInfo();
	    psi.FileName = ff;
	    psi.Arguments = args.ToString();
	    psi.UseShellExecute = false;
	    psi.CreateNoWindow = true;

            Process p = Process.Start(psi);
            Log("FFLinkRouter", "Launch firefox: profile='" + profileName + "' url='" + url + "' exe='" + ff + "'");
            return p != null;
        }
        catch (Exception ex) { LogException("FFLinkRouter", "LaunchFirefox", ex); return false; }
    }
}
