// FFLinkRouter.cs
using System;
using System.Collections.Generic;

public class FFLinkRouter
{
    [STAThread]
    public static void Main(string[] args)
    {
        try
        {
            string url = ExtractUrlArg(args);
            if (string.IsNullOrEmpty(url)) { FFCommon.Log("FFLinkRouter", "No URL argument detected."); return; }

	    if (ShouldDefaultFirefox ())
	    {
		    string DefaultProfile = FFCommon.GetDefaultProfileName ();
		    FFCommon.Log ("FFLinkRouter", $"FF_DEFAULT_FIREFOX set. Defaulting: {url}");
		    FFCommon.LaunchFirefox (DefaultProfile, url);
		    return;
	    }

            FFCommon.Log("FFLinkRouter", "Routing URL: " + url);

            string lastFocusedProfile;
            Dictionary<string, long> focusTicks;
            FFCommon.LoadFocusState(out lastFocusedProfile, out focusTicks);

            List<FFCommon.FFProc> running = FFCommon.GetRunningFirefoxProcesses();

            string chosen = string.Empty;
            string reason = string.Empty;

            if (running != null && running.Count > 0)
            {
                // 1) LAST FOCUSED among RUNNING (top priority)
                long bestTicks = long.MinValue;
                int i = 0;
                while (i < running.Count)
                {
                    string rp = running[i].ProfileName;
                    if (!string.IsNullOrEmpty(rp))
                    {
                        long t;
                        if (focusTicks.TryGetValue(rp, out t) && t > bestTicks)
                        { bestTicks = t; chosen = rp; }
                    }
                    i++;
                }
                if (!string.IsNullOrEmpty(chosen)) reason = "Picked by LAST-FOCUSED among running.";

                // Extra safety: if no ticks (e.g., first run) but we have LastFocusedProfile and it's running, use it.
                if (string.IsNullOrEmpty(chosen) && !string.IsNullOrEmpty(lastFocusedProfile))
                {
                    int k = 0; while (k < running.Count) { if (string.Equals(running[k].ProfileName, lastFocusedProfile, StringComparison.OrdinalIgnoreCase)) { chosen = lastFocusedProfile; reason = "Picked by LastFocusedProfile name (no ticks yet)."; break; } k++; }
                }

                // 2) If still nothing, LAST LAUNCHED among RUNNING
                if (string.IsNullOrEmpty(chosen))
                {
                    DateTime latest = DateTime.MinValue;
                    string latestProf = string.Empty;
                    int k = 0;
                    while (k < running.Count)
                    {
                        if (!string.IsNullOrEmpty(running[k].ProfileName) && running[k].StartTimeUtc > latest)
                        { latest = running[k].StartTimeUtc; latestProf = running[k].ProfileName; }
                        k++;
                    }
                    if (!string.IsNullOrEmpty(latestProf)) { chosen = latestProf; reason = "Picked by last launched among running (no focus state yet)."; }
                }

                if (string.IsNullOrEmpty(chosen)) { chosen = FFCommon.GetDefaultProfileName(); reason = "Running firefox found but no profile resolved; defaulting."; }
            }
            else
            {
                chosen = FFCommon.GetDefaultProfileName();
                reason = "No firefox running; using default.";
            }

            FFCommon.Log("FFLinkRouter", "Decision: profile='" + chosen + "' reason='" + reason + "'");
            if (!FFCommon.LaunchFirefox(chosen, url))
            {
                FFCommon.NotifyError("FF Link Router", "Failed to launch Firefox. Opening logs.");
                FFCommon.OpenLogsFolderFailSafe();
            }
        }
        catch (Exception ex)
        {
            FFCommon.LogException("FFLinkRouter", "Main", ex);
            FFCommon.NotifyError("FF Link Router crashed", ex.Message);
            FFCommon.OpenLogsFolderFailSafe();
        }
    }

    private static string ExtractUrlArg(string[] args)
    {
        if (args == null || args.Length == 0) return string.Empty;
        string a = args[0]; if (string.IsNullOrEmpty(a)) return string.Empty;
        return a.Trim().Trim('"');
    }

    static bool ShouldDefaultFirefox ()
    {
	    string FFDefault = Environment.GetEnvironmentVariable ("FF_DEFAULT_FIREFOX");
	    return !string.IsNullOrEmpty (FFDefault);
    }
}
