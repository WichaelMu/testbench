// =============================
// File: FFCommon.cs
// =============================
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Runtime.CompilerServices;
using System.Threading;

#if WINDOWS
using Microsoft.Win32;
using System.Management;
using System.Windows.Forms;
#endif

public static class FFCommon
{
    // ----------------------
    // Paths & Logging
    // ----------------------
public static string GetBaseDir ()
	{
#if WINDOWS
		string baseDir = Environment.GetFolderPath (Environment.SpecialFolder.LocalApplicationData);
		return Path.Combine (baseDir, "FF");
#else
		string XDG = Environment.GetEnvironmentVariable ("XDG_DATA_HOME");

		if (string.IsNullOrEmpty (XDG))
		{
			string Home = Environment.GetEnvironmentVariable ("HOME");
			if (string.IsNullOrEmpty (Home))
				Home = ".";

			XDG = Path.Combine (Home, ".local", "share");
		}

		return Path.Combine (XDG, "FF");
#endif
	}

	[MethodImpl (MethodImplOptions.AggressiveInlining)]
	public static string GetLogsDir ()
	{
		// string d = Path.Combine (GetBaseDir ());
		// EnsureDirectory (d);
		return GetBaseDir ();
	}

	[MethodImpl (MethodImplOptions.AggressiveInlining)]
	public static string GetStateDir ()
	{
		// string StateDirectory = Path.Combine (GetBaseDir ());
		// EnsureDirectory (StateDirectory);
		return GetBaseDir ();
	}

	[MethodImpl (MethodImplOptions.AggressiveInlining)]
	public static string GetStateFile ()
	{
		return Path.Combine (GetStateDir (), "focus_state.txt");
	}

	[MethodImpl (MethodImplOptions.AggressiveInlining)]
	public static void EnsureDirectory (string Path)
	{
		if (!Directory.Exists (Path))
			Directory.CreateDirectory (Path);
	}

	[MethodImpl (MethodImplOptions.AggressiveInlining)]
	public static string GetLocalTime (string Format = "yyyy-MM-dd")
	{
		return DateTime.UtcNow.ToLocalTime ().ToString (Format);
	}

	[MethodImpl (MethodImplOptions.AggressiveInlining)]
	static string GetLogFile (string Component)
	{
		const string kLogExtension = ".log";
		return Path.Combine (GetLogsDir (), Component + kLogExtension);
	}

	public static void LogEmpty (string Component)
	{
		try
		{
			string LogFile = GetLogFile (Component);
			File.AppendAllText (LogFile, Environment.NewLine);
		}
		catch { }
	}

	[MethodImpl (MethodImplOptions.AggressiveInlining)]
	public static void Log (string Component, string Message)
	{
		try
		{
			string LogFile = GetLogFile (Component);
			File.AppendAllText (LogFile, GetLocalTime ("o") + " " + Message + Environment.NewLine);
		}
		catch { }
	}

	public static void LogException (string component, string context, Exception ex)
	{
		try
		{
			string LogFile = GetLogFile (component);

			StringBuilder SB = new StringBuilder ();
			SB.Append (GetLocalTime ("o")).Append (" ").Append (context).Append (": ")
			  .Append (ex.GetType ().FullName).Append (": ").Append (ex.Message).AppendLine ()
			  .Append (ex.StackTrace).AppendLine ();

			File.AppendAllText (LogFile, SB.ToString ());
		}
		catch { }
	}

	public static void OpenLogsFolderFailSafe ()
	{
		try
		{
#if WINDOWS
			Process.Start ("explorer.exe", GetLogsDir ());
#else
			TryStart ("xdg-open", GetLogsDir ());
#endif
		}
		catch { }
	}

	public static void NotifyError (string Title, string Body)
	{
		try
		{
#if WINDOWS
			using (NotifyIcon Notification = new NotifyIcon ())
			{
				Notification.Visible = true;
#if !FW_WINDOWS
				Notification.Icon = SystemIcons.Information;
#endif
				Notification.BalloonTipTitle = Title;
				Notification.BalloonTipText = Body;
				Notification.ShowBalloonTip (3000);
				System.Threading.Thread.Sleep (3200);
				Notification.Visible = false;
			}
#else
			TryStart ("notify-send", $"{Title}\n{Body}");
#endif
		}
		catch { }
	}

    // ----------------------
    // Firefox profiles
    // ----------------------
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

    public class ProfileInfo
    {
        public string Name;
        public string PathOnDisk;
        public bool IsDefault;
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
                                if (eq2 > 0)
                                {
                                    string k2 = l2.Substring(0, eq2).Trim();
                                    string v2 = l2.Substring(eq2 + 1).Trim();
                                    if (string.Equals(k2, "IsRelative", StringComparison.OrdinalIgnoreCase))
                                    {
                                        isRelative = v2 == "1";
                                        break;
                                    }
                                }
                                j--;
                            }
                            if (isRelative) current.PathOnDisk = Path.Combine(baseDir, val);
                            else current.PathOnDisk = val;
                        }
                        else if (string.Equals(key, "Default", StringComparison.OrdinalIgnoreCase)) current.IsDefault = (val == "1");
                    }
                }
                i++;
            }
            if (current != null) list.Add(current);
        }
        catch (Exception ex)
        {
            LogException("FFCommon", "ReadProfilesIni", ex);
        }
        return list;
    }

    public static string GetDefaultProfileName()
    {
        try
        {
            List<ProfileInfo> info = ReadProfilesIni();
            int i = 0;
            while (i < info.Count)
            {
                if (info[i].IsDefault && !string.IsNullOrEmpty(info[i].Name)) return info[i].Name;
                i++;
            }
            if (info.Count > 0 && !string.IsNullOrEmpty(info[0].Name)) return info[0].Name;
        }
        catch (Exception ex)
        {
            LogException("FFCommon", "GetDefaultProfileName", ex);
        }
        return "default";
    }

    // ----------------------
    // Focus state persistence
    // ----------------------
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
                {
                    lastFocusedProfile = line.Substring("LastFocusedProfile=".Length);
                }
                else if (line.Length > 0)
                {
                    int p = line.IndexOf('|');
                    if (p > 0)
                    {
                        string name = line.Substring(0, p);
                        string num = line.Substring(p + 1);
                        long ticks;
                        if (long.TryParse(num, out ticks))
                        {
                            focusTicks[name] = ticks;
                        }
                    }
                }
                i++;
            }
        }
        catch (Exception ex)
        {
            LogException("FFCommon", "LoadFocusState", ex);
        }
    }

    public static void SaveFocusState(string lastFocusedProfile, Dictionary<string, long> focusTicks)
    {
        try
        {
            StringBuilder sb = new StringBuilder();
            sb.Append("LastFocusedProfile=");
            sb.Append(lastFocusedProfile ?? string.Empty);
            sb.AppendLine();
            foreach (KeyValuePair<string, long> kv in focusTicks)
            {
                sb.Append(kv.Key);
                sb.Append('|');
                sb.Append(kv.Value);
                sb.AppendLine();
            }
            File.WriteAllText(GetStateFile(), sb.ToString());
        }
        catch (Exception ex)
        {
            LogException("FFCommon", "SaveFocusState", ex);
        }
    }

    public static void UpdateFocusedProfile(string profileName)
    {
        if (string.IsNullOrEmpty(profileName)) return;
        string last;
        Dictionary<string, long> map;
        LoadFocusState(out last, out map);
        long ticks = DateTime.UtcNow.Ticks;
        map[profileName] = ticks;
        last = profileName;
        SaveFocusState(last, map);
        Log("FFFocusTracker", $"Focused profile now: {profileName}{Environment.NewLine}");
    }

    // ----------------------
    // Process helpers
    // ----------------------
    public class FFProc
    {
        public int Pid;
        public string ProfileName;
        public DateTime StartTimeUtc;
    }

    public static List<FFProc> GetRunningFirefoxProcesses()
    {
        List<FFProc> list = new List<FFProc>();
        try
        {
            Process[] procs = Process.GetProcesses();
            int i = 0;
            while (i < procs.Length)
            {
                Process p = procs[i];
                try
                {
                    string name = p.ProcessName;
                    bool isFF = string.Equals(name, "firefox", StringComparison.OrdinalIgnoreCase)
                                || string.Equals(name, "firefox-bin", StringComparison.OrdinalIgnoreCase)
                                || string.Equals(name, "firefox.exe", StringComparison.OrdinalIgnoreCase);
                    if (isFF)
                    {
                        string cmd = GetProcessCommandLine(p.Id);
                        string prof = ExtractProfileFromCmd(cmd);
                        DateTime st;
                        try { st = p.StartTime.ToUniversalTime(); }
                        catch { st = DateTime.MinValue; }
                        FFProc ff = new FFProc();
                        ff.Pid = p.Id;
                        ff.ProfileName = prof;
                        ff.StartTimeUtc = st;
                        list.Add(ff);
                    }
                }
                catch { }
                finally { try { p.Dispose(); } catch { } }
                i++;
            }

            // fill from -profile path
            List<ProfileInfo> infos = ReadProfilesIni();
            Dictionary<string, string> pathToName = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            int k = 0;
            while (k < infos.Count)
            {
                if (!string.IsNullOrEmpty(infos[k].PathOnDisk) && !string.IsNullOrEmpty(infos[k].Name))
                {
                    pathToName[NormalisePath(infos[k].PathOnDisk)] = infos[k].Name;
                }
                k++;
            }
            int z = 0;
            while (z < list.Count)
            {
                if (string.IsNullOrEmpty(list[z].ProfileName))
                {
                    string cl = GetProcessCommandLine(list[z].Pid);
                    string ppath = ExtractProfilePathFromCmd(cl);
                    if (!string.IsNullOrEmpty(ppath))
                    {
                        string np = NormalisePath(ppath);
                        string mapped;
                        if (pathToName.TryGetValue(np, out mapped))
                        {
                            list[z].ProfileName = mapped;
                        }
                    }
                }
                z++;
            }
        }
        catch (Exception ex)
        {
            LogException("FFCommon", "GetRunningFirefoxProcesses", ex);
        }
        return list;
    }

    public static string NormalisePath(string p)
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
            using (ManagementObjectSearcher s = new ManagementObjectSearcher("SELECT CommandLine, ProcessId FROM Win32_Process WHERE ProcessId = " + pid))
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
        try
        {
            Regex r1 = new Regex("-P\\s+\"?([^\"\\s]+)\"?", RegexOptions.IgnoreCase);
            Match m = r1.Match(cmd);
            if (m.Success) return m.Groups[1].Value;
        }
        catch { }
        return string.Empty;
    }

    public static string ExtractProfilePathFromCmd(string cmd)
    {
        if (string.IsNullOrEmpty(cmd)) return string.Empty;
        try
        {
            Regex r1 = new Regex("-profile\\s+\"?([^\"]+)\"?", RegexOptions.IgnoreCase);
            Match m = r1.Match(cmd);
            if (m.Success) return m.Groups[1].Value;
        }
        catch { }
        return string.Empty;
    }

    public static bool TryStart(string file, string args)
    {
        try
        {
            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = file;
            psi.Arguments = args;
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;
            Process p = Process.Start(psi);
            return p != null;
        }
        catch { return false; }
    }

    // ----------------------
    // Firefox executable & launcher
    // ----------------------
    public static string FindFirefoxExecutable()
    {
#if WINDOWS
        try
        {
            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = "where";
            psi.Arguments = "firefox";
            psi.UseShellExecute = false;
            psi.RedirectStandardOutput = true;
            psi.CreateNoWindow = true;
            using (Process p = Process.Start(psi))
            {
                string outp = p.StandardOutput.ReadToEnd();
                p.WaitForExit(1500);
                if (!string.IsNullOrEmpty(outp))
                {
                    string[] lines = outp.Split(new char[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
                    if (lines.Length > 0 && File.Exists(lines[0])) return lines[0];
                }
            }
        }
        catch { }
        string pf = Environment.GetEnvironmentVariable("ProgramFiles");
        if (!string.IsNullOrEmpty(pf))
        {
            string p1 = Path.Combine(pf, "Mozilla Firefox", "firefox.exe");
            if (File.Exists(p1)) return p1;
        }
        string pf86 = Environment.GetEnvironmentVariable("ProgramFiles(x86)");
        if (!string.IsNullOrEmpty(pf86))
        {
            string p2 = Path.Combine(pf86, "Mozilla Firefox", "firefox.exe");
            if (File.Exists(p2)) return p2;
        }
        return "firefox";
#else
        if (File.Exists("/usr/bin/firefox")) return "/usr/bin/firefox";
        if (File.Exists("/usr/lib/firefox/firefox")) return "/usr/lib/firefox/firefox";
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
            {
                args.Append(" -P \"");
                args.Append(profileName);
                args.Append("\"");
            }
            if (!string.IsNullOrEmpty(url))
            {
                args.Append(" -new-tab \"");
                args.Append(url);
                args.Append("\"");
            }

            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = ff;
            psi.Arguments = args.ToString();
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;

#if !WINDOWS
            // force X11 so xdotool/xprop can see it
            psi.EnvironmentVariables["MOZ_ENABLE_WAYLAND"] = "0";
#endif

            Process p = Process.Start(psi);
            Log("FFLinkRouter", "Launch firefox: profile='" + profileName + "' url='" + url + "' exe='" + ff + "'");
            return p != null;
        }
        catch (Exception ex)
        {
            LogException("FFLinkRouter", "LaunchFirefox", ex);
            return false;
        }
    }
}
