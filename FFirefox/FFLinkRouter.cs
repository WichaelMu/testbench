using System;
using System.Collections.Generic;

public class FFLinkRouter
{
	[STAThread]
	public static void Main (string[] Args)
	{
		try
		{
			string Url = ExtractUrlArg (Args);
			if (string.IsNullOrEmpty (Url))
			{
				FFCommon.Log ("FFLinkRouter", "No URL argument detected.");
				return;
			}

			if (ShouldDefaultFirefox ())
			{
				string DefaultProfile = FFCommon.GetDefaultProfileName ();
				FFCommon.Log ("FFLinkRouter", $"FF_DEFAULT_FIREFOX set. Defaulting: {Url}");
				FFCommon.LaunchFirefox (DefaultProfile, Url);
				return;
			}

			FFCommon.Log ("FFLinkRouter", "Routing URL: " + Url);

			string LastFocusedProfile;
			Dictionary<string, long> FocusTicks;
			FFCommon.LoadFocusState (out LastFocusedProfile, out FocusTicks);

			List<FFCommon.FFProc> Running = FFCommon.GetRunningFirefoxProcesses ();

			string Chosen = string.Empty;
			string Reason = string.Empty;

			if (Running != null && Running.Count > 0)
			{
				// 1) LAST FOCUSED among RUNNING (top priority)
				long bestTicks = long.MinValue;
				int i = 0;
				while (i < Running.Count)
				{
					string RunningProfileName = Running[i].ProfileName;
					if (!string.IsNullOrEmpty (RunningProfileName))
					{
						long MTime;
						if (FocusTicks.TryGetValue (RunningProfileName, out MTime) && MTime > bestTicks)
						{
							bestTicks = MTime;
							Chosen = RunningProfileName;
						}
					}
					i++;
				}
				if (!string.IsNullOrEmpty (Chosen))
					Reason = "Picked by LAST-FOCUSED among running.";

				// Extra safety: if no ticks (e.g., first run) but we have LastFocusedProfile and it's running, use it.
				if (string.IsNullOrEmpty (Chosen) && !string.IsNullOrEmpty (LastFocusedProfile))
				{
					int k = 0;
					while (k < Running.Count)
					{
						if (string.Equals (Running[k].ProfileName, LastFocusedProfile, StringComparison.OrdinalIgnoreCase))
						{
							Chosen = LastFocusedProfile;
							Reason = "Picked by LastFocusedProfile name (no ticks yet).";

							break;
						}
						k++;
					}
				}

				// 2) If still nothing, LAST LAUNCHED among RUNNING
				if (string.IsNullOrEmpty (Chosen))
				{
					DateTime Latest = DateTime.MinValue;
					string LatestProfile = string.Empty;
					int k = 0;
					while (k < Running.Count)
					{
						if (!string.IsNullOrEmpty (Running[k].ProfileName) && Running[k].StartTimeUtc > Latest)
						{
							Latest = Running[k].StartTimeUtc;
							LatestProfile = Running[k].ProfileName;
						}
						k++;
					}
					if (!string.IsNullOrEmpty (LatestProfile))
					{
						Chosen = LatestProfile;
						Reason = "Picked by last launched among running (no focus state yet).";
					}
				}

				if (string.IsNullOrEmpty (Chosen))
				{
					Chosen = FFCommon.GetDefaultProfileName ();
					Reason = "Running firefox found but no profile resolved; defaulting.";
				}
			}
			else
			{
				Chosen = FFCommon.GetDefaultProfileName ();
				Reason = "No firefox running; using default.";
			}

			FFCommon.Log ("FFLinkRouter", "Decision: profile='" + Chosen + "' reason='" + Reason + "'");
			if (!FFCommon.LaunchFirefox (Chosen, Url))
			{
				FFCommon.NotifyError ("FF Link Router", "Failed to launch Firefox. Opening logs.");
				FFCommon.OpenLogsFolderFailSafe ();
			}
		}
		catch (Exception ex)
		{
			FFCommon.LogException ("FFLinkRouter", "Main", ex);
			FFCommon.NotifyError ("FF Link Router crashed", ex.Message);
			FFCommon.OpenLogsFolderFailSafe ();
		}
		finally
		{
			// Log an empty line on every Link Route.
			FFCommon.LogEmpty ("FFLinkRouter");
		}
	}

	private static string ExtractUrlArg (string[] args)
	{
		if (args == null || args.Length == 0)
			return string.Empty;

		string a = args[0];
		if (string.IsNullOrEmpty (a))
			return string.Empty;

		return a.Trim ().Trim ('"');
	}

	static bool ShouldDefaultFirefox ()
	{
		string FFDefault = Environment.GetEnvironmentVariable ("FF_DEFAULT_FIREFOX");
		return !string.IsNullOrEmpty (FFDefault);
	}
}