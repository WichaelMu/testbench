// FFLinkRouter.cs
// Routes http/https clicks to the desired Firefox profile.

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text.RegularExpressions;

class FLinkRouter
{
    static void Main(string[] Args)
    {
        using (System.Threading.Mutex SingleInstanceMutex = new System.Threading.Mutex(false, @"Local\FFLinkRouter_SingleInstance"))
        {
            bool bEntered = SingleInstanceMutex.WaitOne(3000);
            if (!bEntered) { return; }

            string Url = (Args != null && Args.Length > 0) ? Args[0] : "";
            if (!string.IsNullOrEmpty(Url)) { Url = Url.Trim('"'); }

            FLog.Write("Router ", "Click: " + Url);

            string FirefoxExe = FFirefoxPlatform.FindFirefoxExe();
            if (FirefoxExe == null)
            {
                FLog.Write("Router ", "firefox not found");
                return;
            }

            bool bFirefoxRunning = IsFirefoxRunning();

            // 1) Tracked last-focused profile (from the tracker)
            string LastProfile = FState.GetLastProfile();
#if LINUX
            bool bIsRunning = FFirefoxPlatform.IsProfileRunningByProc(LastProfile) || FFirefoxPlatform.IsProfileRunningByLocks(LastProfile);
#else
            bool bIsRunning = FFirefoxPlatform.IsProfileRunningByLocks(LastProfile);
#endif
            if (!string.IsNullOrEmpty(LastProfile) && bIsRunning)
            {
                FLog.Write("Router ", "Using tracked LastProfile = " + LastProfile);
                LaunchIntoProfile(FirefoxExe, LastProfile, Url);
                return;
            }

            // 2) Heuristic: latest mtime among running profiles (excluding default when possible)
            string Reason;
            string Picked = PickByActivityHeuristic(out Reason);
            if (!string.IsNullOrEmpty(Picked))
            {
                FLog.Write("Router ", "Using heuristic (" + Reason + ") profile = " + Picked);
                LaunchIntoProfile(FirefoxExe, Picked, Url);
                return;
            }

            // 3) Fallbacks
            if (!bFirefoxRunning)
            {
#if WINDOWS
                FLog.Write("Router ", "Firefox not running → -osint");
                Process.Start(FirefoxExe, "-osint -url \"" + Url + "\"");
#else
                FLog.Write("Router ", "Firefox not running → start firefox URL");
                Process.Start(FirefoxExe, "\"" + Url + "\"");
#endif
            }
            else
            {
                FLog.Write("Router ", "Fallback: -new-tab without profile");
#if WINDOWS
                Process.Start(FirefoxExe, "-new-tab \"" + Url + "\"");
#else
                Process.Start(FirefoxExe, "--new-tab \"" + Url + "\"");
#endif
            }
        }
    }

    private static void LaunchIntoProfile(string FirefoxExe, string ProfileName, string Url)
    {
#if WINDOWS
        FLog.Write("Router ", "Launch: -P \"" + ProfileName + "\" -new-tab " + Url);
        Process.Start(FirefoxExe, "-P \"" + ProfileName + "\" -new-tab \"" + Url + "\"");
#else
        string ProfilePath = FFirefoxProfiles.GetProfilePathByName(ProfileName);
        FLog.Write("Router ", "Launch: --profile \"" + ProfilePath + "\" --new-tab " + Url);
        Process.Start(FirefoxExe, "--profile \"" + ProfilePath + "\" --new-tab \"" + Url + "\"");
#endif
    }

    private static bool IsFirefoxRunning()
    {
#if WINDOWS
        return Process.GetProcessesByName("firefox").Length > 0;
#else
        Process[] Processes = Process.GetProcesses();
        foreach (Process P in Processes)
        {
            try
            {
                if (P.ProcessName.StartsWith("firefox", StringComparison.OrdinalIgnoreCase)) { return true; }
            }
            catch {}
        }
        return false;
#endif
    }

    private static string PickByActivityHeuristic(out string Reason)
    {
        Reason = "mtime";
        List<FFirefoxProfiles.FProfile> All = FFirefoxProfiles.LoadAll();

        // Running set
        List<FFirefoxProfiles.FProfile> Running = new List<FFirefoxProfiles.FProfile>();
        foreach (FFirefoxProfiles.FProfile P in All)
        {
#if LINUX
            bool bRun = FFirefoxPlatform.IsProfileRunningByProc(P.Name) || FFirefoxPlatform.IsProfileRunningByLocks(P.Name);
#else
            bool bRun = FFirefoxPlatform.IsProfileRunningByLocks(P.Name);
#endif
            if (bRun) { Running.Add(P); }
        }
        if (Running.Count == 0) { return null; }

        string DefaultName = FFirefoxProfiles.GetDefaultProfileName();

        List<FFirefoxProfiles.FProfile> Candidates = new List<FFirefoxProfiles.FProfile>();
        foreach (FFirefoxProfiles.FProfile P in Running)
        {
            if (DefaultName == null || !P.Name.Equals(DefaultName, StringComparison.OrdinalIgnoreCase))
            {
                Candidates.Add(P);
            }
        }
        if (Candidates.Count == 0) { Candidates = Running; }

        Candidates.Sort((FFirefoxProfiles.FProfile A, FFirefoxProfiles.FProfile B) =>
            DateTime.Compare(FFirefoxPlatform.GetLockMTimeUtc(B.Path), FFirefoxPlatform.GetLockMTimeUtc(A.Path)));

        return Candidates[0].Name;
    }
}
