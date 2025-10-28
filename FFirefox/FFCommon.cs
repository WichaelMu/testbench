// Common.cs
// Shared utilities for FocusTracker and LinkRouter
// No "SmartOpen" anywhere.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text.RegularExpressions;
using System.Threading;

#if WINDOWS
using Microsoft.Win32;
using System.Management;
#endif

public static class FAppPaths
{
    // Single switch to rename the app folder (logs/state). No branding here.
    public const string AppDirName = "FF"; // lives under LocalApplicationData

    public static string AppDir
        => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), AppDirName);

    public static string LogCurrent
        => Path.Combine(AppDir, "ff-current.log");

    public static string LogPrev
        => Path.Combine(AppDir, "ff-prev.log");

    public static string StateFile
        => Path.Combine(AppDir, "lastprofile.txt");

#if WINDOWS
    public static string FirefoxBase
        => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), @"Mozilla\Firefox");
#elif LINUX
    public static string FirefoxBase
        => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Personal), ".mozilla", "firefox");
#endif

    public static string ProfilesIni
        => Path.Combine(FirefoxBase, "profiles.ini");

    public static string InstallsIni
        => Path.Combine(FirefoxBase, "installs.ini");
}

public static class FLog
{
    private static readonly Mutex LogMutex = new Mutex(false, @"Local\FF_Log");

    public static void RotateForNewSession()
    {
        try
        {
            Directory.CreateDirectory(FAppPaths.AppDir);

            if (File.Exists(FAppPaths.LogPrev))
            {
                File.Delete(FAppPaths.LogPrev);
            }

            if (File.Exists(FAppPaths.LogCurrent))
            {
                try { File.Move(FAppPaths.LogCurrent, FAppPaths.LogPrev); }
                catch
                {
                    try { File.Copy(FAppPaths.LogCurrent, FAppPaths.LogPrev, true); } catch {}
                    try { File.Delete(FAppPaths.LogCurrent); } catch {}
                }
            }

            WriteRaw("===== SESSION START " + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff") + " =====");
        }
        catch {}
    }

    public static void Write(string Tag, string Message)
    {
        try
        {
            Directory.CreateDirectory(FAppPaths.AppDir);

            bool bLocked = LogMutex.WaitOne(500);
            if (bLocked)
            {
                try { WriteRaw("[" + Tag + "] " + Message); }
                finally { LogMutex.ReleaseMutex(); }
            }
        }
        catch {}
    }

    private static void WriteRaw(string Message)
    {
        string Line = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff") + " " + Message + Environment.NewLine;
        File.AppendAllText(FAppPaths.LogCurrent, Line);
    }
}

public static class FState
{
    // Registry path on Windows (no branding)
    private const string RegistryKeyPath = @"Software\FF";

    public static void SetLastProfile(string ProfileName)
    {
        try
        {
            Directory.CreateDirectory(FAppPaths.AppDir);
            File.WriteAllText(FAppPaths.StateFile, ProfileName ?? "");
        }
        catch {}

#if WINDOWS
        try
        {
            using (RegistryKey UserKey = Registry.CurrentUser.CreateSubKey(RegistryKeyPath))
            {
                UserKey.SetValue("LastProfile", ProfileName ?? "", RegistryValueKind.String);
                UserKey.SetValue("LastProfileTimeUtc", DateTime.UtcNow.ToString("o"), RegistryValueKind.String);
            }
        }
        catch {}
#endif
    }

    public static string GetLastProfile()
    {
        try
        {
            if (File.Exists(FAppPaths.StateFile))
            {
                string Text = File.ReadAllText(FAppPaths.StateFile);
                string Clean = (Text ?? "").Trim();
                if (!string.IsNullOrEmpty(Clean)) { return Clean; }
            }
        }
        catch {}

#if WINDOWS
        try
        {
            using (RegistryKey Key = Registry.CurrentUser.OpenSubKey(RegistryKeyPath))
            {
                if (Key != null)
                {
                    object Value = Key.GetValue("LastProfile");
                    if (Value != null)
                    {
                        string Clean = Value.ToString();
                        if (!string.IsNullOrEmpty(Clean)) { return Clean; }
                    }
                }
            }
        }
        catch {}
#endif
        return null;
    }
}

public static class FFirefoxProfiles
{
    public class FProfile
    {
        public string Name;
        public string Path;
    }

    public static List<FProfile> LoadAll()
    {
        List<FProfile> ProfileList = new List<FProfile>();

        if (!File.Exists(FAppPaths.ProfilesIni))
        {
            return ProfileList;
        }

        string IniDirectory = Path.GetDirectoryName(FAppPaths.ProfilesIni);
        string CurrentSection = null;
        Dictionary<string, string> KeyValues =
            new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        foreach (string RawLine in File.ReadAllLines(FAppPaths.ProfilesIni))
        {
            string Line = RawLine.Trim();
            if (Line.Length == 0 || Line.StartsWith(";")) { continue; }

            if (Line.StartsWith("[") && Line.EndsWith("]"))
            {
                if (CurrentSection != null &&
                    CurrentSection.StartsWith("Profile", StringComparison.OrdinalIgnoreCase) &&
                    KeyValues.ContainsKey("Path"))
                {
                    ProfileList.Add(Build(IniDirectory, KeyValues));
                }

                CurrentSection = Line.Trim('[', ']');
                KeyValues.Clear();
                continue;
            }

            int EqualsIndex = Line.IndexOf('=');
            if (EqualsIndex > 0)
            {
                string Key = Line.Substring(0, EqualsIndex).Trim();
                string Value = Line.Substring(EqualsIndex + 1).Trim();
                KeyValues[Key] = Value;
            }
        }

        if (CurrentSection != null &&
            CurrentSection.StartsWith("Profile", StringComparison.OrdinalIgnoreCase) &&
            KeyValues.ContainsKey("Path"))
        {
            ProfileList.Add(Build(IniDirectory, KeyValues));
        }

        return ProfileList;
    }

    private static FProfile Build(string IniDirectory, Dictionary<string, string> KeyValues)
    {
        string Name = KeyValues.ContainsKey("Name") ? KeyValues["Name"] : null;
        string PathRaw = (KeyValues["Path"] ?? "").Replace('/', Path.DirectorySeparatorChar);
        bool bRelative = KeyValues.ContainsKey("IsRelative") && KeyValues["IsRelative"] == "1";
        string AbsolutePath = bRelative ? Path.Combine(IniDirectory, PathRaw) : PathRaw;

        FProfile Result = new FProfile();
        Result.Name = Name ?? Path.GetFileName(AbsolutePath);
        Result.Path = AbsolutePath;
        return Result;
    }

    public static string MapPathToName(string AbsolutePath)
    {
        List<FProfile> AllProfiles = LoadAll();
        foreach (FProfile Profile in AllProfiles)
        {
            if (string.Equals(Profile.Path, AbsolutePath, StringComparison.OrdinalIgnoreCase))
            {
                return Profile.Name;
            }
        }
        return null;
    }

    public static string GetProfilePathByName(string ProfileName)
    {
        if (string.IsNullOrEmpty(ProfileName)) { return null; }
        List<FProfile> All = LoadAll();
        foreach (FProfile P in All)
        {
            if (P.Name.Equals(ProfileName, StringComparison.OrdinalIgnoreCase))
            {
                return P.Path;
            }
        }
        return null;
    }

    public static string GetDefaultProfileName()
    {
        if (!File.Exists(FAppPaths.InstallsIni)) { return null; }

        string IniDirectory = Path.GetDirectoryName(FAppPaths.InstallsIni);
        string CurrentSection = null;
        Dictionary<string, string> KeyValues =
            new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        foreach (string RawLine in File.ReadAllLines(FAppPaths.InstallsIni))
        {
            string Line = RawLine.Trim();
            if (Line.Length == 0 || Line.StartsWith(";")) { continue; }

            if (Line.StartsWith("[") && Line.EndsWith("]"))
            {
                CurrentSection = Line.Trim('[', ']');
                KeyValues.Clear();
                continue;
            }

            int EqualsIndex = Line.IndexOf('=');
            if (EqualsIndex <= 0) { continue; }

            string Key = Line.Substring(0, EqualsIndex).Trim();
            string Value = Line.Substring(EqualsIndex + 1).Trim();

            if (Key.Equals("Default", StringComparison.OrdinalIgnoreCase))
            {
                string Relative = Value.Replace('/', Path.DirectorySeparatorChar);
                string Absolute = Path.IsPathRooted(Relative) ? Relative : Path.Combine(IniDirectory, Relative);
                string Name = MapPathToName(Absolute);
                if (!string.IsNullOrEmpty(Name)) { return Name; }
            }
        }
        return null;
    }
}

public static class FFirefoxPlatform
{
    public static string FindFirefoxExe()
    {
#if WINDOWS
        string X64 = @"C:\Program Files\Mozilla Firefox\firefox.exe";
        string X86 = @"C:\Program Files (x86)\Mozilla Firefox\firefox.exe";
        if (File.Exists(X64)) { return X64; }
        if (File.Exists(X86)) { return X86; }
        return null;
#else
        return "firefox"; // rely on PATH
#endif
    }

    public static DateTime GetLockMTimeUtc(string ProfilePath)
    {
        if (string.IsNullOrEmpty(ProfilePath)) { return DateTime.MinValue; }

#if LINUX
        string LockUnix = Path.Combine(ProfilePath, "lock");
        string LockParent = Path.Combine(ProfilePath, "parent.lock");
        DateTime T1 = File.Exists(LockUnix) ? File.GetLastWriteTimeUtc(LockUnix) : DateTime.MinValue;
        DateTime T2 = File.Exists(LockParent) ? File.GetLastWriteTimeUtc(LockParent) : DateTime.MinValue;
        return T1 > T2 ? T1 : T2;
#else
        string LockParent = Path.Combine(ProfilePath, "parent.lock");
        try { return File.GetLastWriteTimeUtc(LockParent); } catch { return DateTime.MinValue; }
#endif
    }

    public static bool IsProfileRunningByLocks(string ProfileName)
    {
        string ProfilePath = FFirefoxProfiles.GetProfilePathByName(ProfileName);
        if (string.IsNullOrEmpty(ProfilePath)) { return false; }

#if LINUX
        if (File.Exists(Path.Combine(ProfilePath, "lock"))) { return true; }
        if (File.Exists(Path.Combine(ProfilePath, "parent.lock"))) { return true; }
        return false;
#else
        return File.Exists(Path.Combine(ProfilePath, "parent.lock"));
#endif
    }

#if WINDOWS
    public static string ProfileNameFromPidWindows(int Pid)
    {
        HashSet<int> Visited = new HashSet<int>();
        int CurrentPid = Pid;

        while (CurrentPid != 0 && !Visited.Contains(CurrentPid))
        {
            Visited.Add(CurrentPid);

            ManagementObjectSearcher Searcher =
                new ManagementObjectSearcher("SELECT ProcessId, ParentProcessId, CommandLine FROM Win32_Process WHERE ProcessId=" + CurrentPid.ToString());

            foreach (ManagementObject ObjectRow in Searcher.Get())
            {
                string CommandLine = (ObjectRow["CommandLine"] ?? "").ToString();

                Match ProfileMatch = Regex.Match(CommandLine, @"-P\s+""([^""]+)""");
                if (!ProfileMatch.Success) { ProfileMatch = Regex.Match(CommandLine, @"-P\s+([^\s""]+)"); }
                if (ProfileMatch.Success) { return ProfileMatch.Groups[1].Value; }

                Match PathMatch = Regex.Match(CommandLine, @"-profile\s+""([^""]+)""");
                if (!PathMatch.Success) { PathMatch = Regex.Match(CommandLine, @"-profile\s+([^\s""]+)"); }
                if (PathMatch.Success)
                {
                    string Absolute = PathMatch.Groups[1].Value.Replace('/', '\\');
                    string Name = FFirefoxProfiles.MapPathToName(Absolute);
                    if (!string.IsNullOrEmpty(Name)) { return Name; }
                }

                CurrentPid = Convert.ToInt32(ObjectRow["ParentProcessId"]);
            }

            if (CurrentPid == Pid) { break; }
        }

        return null;
    }
#endif

#if LINUX
    public static string ProfileNameFromPidLinux(int Pid)
    {
        string CommandLine = SafeRead("/proc/" + Pid.ToString() + "/cmdline");
        if (string.IsNullOrEmpty(CommandLine)) { return null; }

        CommandLine = CommandLine.Replace('\0', ' ');

        Match ProfileMatch = Regex.Match(CommandLine, @"-P\s+""?([^\s""]+)""?");
        if (ProfileMatch.Success) { return ProfileMatch.Groups[1].Value; }

        Match PathMatch = Regex.Match(CommandLine, @"-profile\s+""?([^\s""]+)""?");
        if (PathMatch.Success)
        {
            string Absolute = PathMatch.Groups[1].Value.Replace('/', Path.DirectorySeparatorChar);
            return FFirefoxProfiles.MapPathToName(Absolute);
        }
        return null;
    }

    public static bool IsProfileRunningByProc(string ProfileName)
    {
        if (string.IsNullOrEmpty(ProfileName)) { return false; }

        Process[] Processes = Process.GetProcesses();
        foreach (Process Proc in Processes)
        {
            try
            {
                if (!Proc.ProcessName.StartsWith("firefox", StringComparison.OrdinalIgnoreCase)) { continue; }
                string Name = ProfileNameFromPidLinux(Proc.Id);
                if (!string.IsNullOrEmpty(Name) && Name.Equals(ProfileName, StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }
            catch {}
        }
        return false;
    }

    private static string SafeRead(string AbsolutePath)
    {
        try { return File.ReadAllText(AbsolutePath); } catch { return null; }
    }
#endif
}
