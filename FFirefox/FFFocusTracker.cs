using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;
using System.IO;
using System.Collections.Generic;


public class FFFocusTracker
{
#if WINDOWS
	[DllImport ("user32.dll")]
	static extern IntPtr GetForegroundWindow ();

	[DllImport ("user32.dll")]
	static extern uint GetWindowThreadProcessId (IntPtr hWnd, out uint lpdwProcessId);
#endif

#if LINUX
	[System.Runtime.InteropServices.DllImport ("libc")]
	static extern System.IntPtr signal (int SignalNumber, SigHandler Handler);

	delegate void SigHandler (int SignalNumber);

	static readonly SigHandler UnixSignalHandler = OnUnixSignal;

	const int SIGINT = 2;
	const int SIGHUP = 1;
	const int SIGQUIT = 3;
	const int SIGTERM = 15;
#endif


	static DateTime LastNoWindowLogUTC = DateTime.MinValue;
	static DateTime LastGNOMEFalseLogUTC = DateTime.MinValue;

	public static void Main (string[] Args)
	{
		int ProcessId = System.Diagnostics.Process.GetCurrentProcess ().Id;
#if LINUX
		string Display = Environment.GetEnvironmentVariable ("DISPLAY");
		string WaylandDisplay = Environment.GetEnvironmentVariable ("WAYLAND_DISPLAY");
		string XDGSessionType = Environment.GetEnvironmentVariable ("XDG_SESSION_TYPE");
		FFCommon.Log ("FFFocusTracker", "LINUX -- Starting focus tracker (PID=" + ProcessId + "... DISPLAY=" + (Display ?? "<null>") + " WAYLAND_DISPLAY=" + (WaylandDisplay ?? "<null>") + " XDG_SESSION_TYPE=" + (XDGSessionType ?? "<null>"));

#elif WINDOWS
		FFCommon.Log ("FFFocusTracker", $"Windows -- Starting focus tracker (PID={ProcessId)}");
#endif

		RegisterShutdownHooks ();

		try
		{
			FFCommon.SendNotification ("FFFocusTracker", "FFFocusTracker has begun.");
			RunLoop ();
		}
		catch (Exception ex)
		{
			FFCommon.LogException ("FFFocusTracker", "Main", ex);
			FFCommon.SendNotification ("FF Focus Tracker crashed", ex.Message);
			FFCommon.OpenLogsFolderFailSafe ();
		}
	}

	static void RunLoop ()
	{
		string LastSeenProfile = string.Empty;

		Thread.Sleep (10_000);

		while (true)
		{
			try
			{
				string ActiveProfile = DetectActiveFirefoxProfile ();
				if (!string.IsNullOrEmpty (ActiveProfile))
				{
					if (!string.Equals (ActiveProfile, LastSeenProfile, StringComparison.OrdinalIgnoreCase))
					{
						FFCommon.UpdateFocusedProfile (ActiveProfile);
						LastSeenProfile = ActiveProfile;
					}
				}
				else
				{
					DateTime Now = DateTime.UtcNow;
					if ((Now - LastNoWindowLogUTC).TotalSeconds > 15.0)
					{
						// FFCommon.Log ("FFFocusTracker", "No active Firefox window detected (Wayland blocked, missing xdotool/xprop, or non-Firefox focused).");
						LastNoWindowLogUTC = Now;
					}
				}
			}
			catch (Exception Ex)
			{
				FFCommon.LogException ("FFFocusTracker", "RunLoopDetect", Ex);
			}

			Thread.Sleep (400);
		}
	}

	static string DetectActiveFirefoxProfile ()
	{
#if WINDOWS
		IntPtr ForegroundWIndow = GetForegroundWindow ();
		if (ForegroundWIndow == IntPtr.Zero)
			return string.Empty;
		uint ProcessId;
		GetWindowThreadProcessId (ForegroundWIndow, out ProcessId);

		if (ProcessId == 0)
			return string.Empty;

		return ProfileFromPid ((int)ProcessId);
#elif LINUX
		// 1) Try GNOME Shell D-Bus
		string Profile = TryGnomeShellPid ();
		if (!string.IsNullOrEmpty (Profile))
			return Profile;

		// 2) Try xdotool (X11)
		Profile = TryXdotool ();
		if (!string.IsNullOrEmpty (Profile))
			return Profile;

		// 3) Try xprop (X11)
		Profile = TryXprop ();
		if (!string.IsNullOrEmpty (Profile))
			return Profile;

		// 4) HARD FALLBACK: infer from running firefox processes
		Profile = FallbackGuessFromRunning ();
		if (!string.IsNullOrEmpty (Profile))
			return Profile;

		return string.Empty;
#endif
	}

#if LINUX
	static string TryGnomeShellPid ()
	{
		string gdbus = FindOnPath ("gdbus");
		if (string.IsNullOrEmpty (gdbus))
			return string.Empty;

		string StandardOut = ExecAndRead (gdbus, "call --session --dest org.gnome.Shell --object-path /org/gnome/Shell --method org.gnome.Shell.Eval \"global.display.get_focus_window ().get_pid ()\"", 900);
		if (string.IsNullOrEmpty (StandardOut))
			return string.Empty;

		if (StandardOut.StartsWith ("(false", StringComparison.OrdinalIgnoreCase))
		{
			DateTime now = DateTime.UtcNow;
			if ((now - LastGNOMEFalseLogUTC).TotalSeconds > 10.0)
			{
				// FFCommon.Log ("FFFocusTracker", "GNOME Shell Eval exists but returned false (Eval disabled by shell).");
				LastGNOMEFalseLogUTC = now;
			}
			return string.Empty;
		}

		string Digits = ExtractDigits (StandardOut);
		int ProcessId;
		if (!int.TryParse (Digits, out ProcessId) || ProcessId <= 0)
			return string.Empty;

		return ProfileFromPid (ProcessId);
	}

	static string TryXdotool ()
	{
		string xdotool = FindOnPath ("xdotool");
		if (string.IsNullOrEmpty (xdotool))
		{
			// log once every 30s that xdotool is missing
			return string.Empty;
		}

		string ProcessIdAsString = ExecAndRead (xdotool, "getactivewindow getwindowpid", 800);
		if (string.IsNullOrEmpty (ProcessIdAsString))
			return string.Empty;

		int ProcessId;
		if (!int.TryParse (ProcessIdAsString.Trim (), out ProcessId) || ProcessId <= 0)
			return string.Empty;

		return ProfileFromPid (ProcessId);
	}

	static string TryXprop ()
	{
		string Shell = FindOnPath ("sh");
		if (string.IsNullOrEmpty (Shell))
			return string.Empty;

		string ActiveWindow = ExecAndRead (Shell, "-c \"xprop -root _NET_ACTIVE_WINDOW | awk -F '# ' '{print $2}'\"", 900);
		if (string.IsNullOrEmpty (ActiveWindow))
			return string.Empty;

		string ProcessIdAsString = ExecAndRead (Shell, "-c \"xprop -id " + ActiveWindow.Trim () + " _NET_WM_PID | awk '{print $3}'\"", 900);
		if (string.IsNullOrEmpty (ProcessIdAsString))
			return string.Empty;

		int ProcessId;
		if (!int.TryParse (ProcessIdAsString.Trim (), out ProcessId) || ProcessId <= 0)
			return string.Empty;

		return ProfileFromPid (ProcessId);
	}

	// --- NEW: If we can’t see focus at all, guess from running firefoxes.
	static string FallbackGuessFromRunning ()
	{
		try
		{
			string LastFocusedFromState;
			Dictionary<string, long> Ticks;
			FFCommon.LoadFocusState (out LastFocusedFromState, out Ticks);

			List<FFCommon.FFProc> Running = FFCommon.GetRunningFirefoxProcesses ();
			if (Running == null || Running.Count == 0)
				return string.Empty;

			// 1) exactly one firefox with a profile -> use it
			if (Running.Count == 1 && !string.IsNullOrEmpty (Running[0].ProfileName))
			{
				FFCommon.Log ("FFFocusTracker", "FallbackGuessFromRunning: single Firefox detected -> " + Running[0].ProfileName);
				return Running[0].ProfileName;
			}

			// 2) If we have a lastFocused in state and it's currently running, re-affirm it
			if (!string.IsNullOrEmpty (LastFocusedFromState))
			{
				int i = 0;
				while (i < Running.Count)
				{
					if (string.Equals (Running[i].ProfileName, LastFocusedFromState, StringComparison.OrdinalIgnoreCase))
					{
						// FFCommon.Log ("FFFocusTracker", "FallbackGuessFromRunning: re-affirming last-focused from state -> " + lastFocused);
						return LastFocusedFromState;
					}
					i++;
				}
			}

			// 3) Else pick the most recently started firefox that has a profile name
			DateTime Newest = DateTime.MinValue;
			string NewestProfile = string.Empty;
			int k = 0;
			while (k < Running.Count)
			{
				if (!string.IsNullOrEmpty (Running[k].ProfileName))
				{
					if (Running[k].StartTimeUtc > Newest)
					{
						Newest = Running[k].StartTimeUtc;
						NewestProfile = Running[k].ProfileName;
					}
				}
				k++;
			}

			if (!string.IsNullOrEmpty (NewestProfile))
			{
				FFCommon.Log ("FFFocusTracker", "FallbackGuessFromRunning: picked most recently launched firefox -> " + NewestProfile);
				return NewestProfile;
			}

			// 4) If we still have nothing but we do have multiple processes without names, give up quietly.
			return string.Empty;
		}
		catch (Exception Ex)
		{
			FFCommon.LogException ("FFFocusTracker", "FallbackGuessFromRunning", Ex);
			return string.Empty;
		}
	}

	static string ExecAndRead (string File, string Args, int TimeoutMilliseconds)
	{
		try
		{
			ProcessStartInfo Exec = new ProcessStartInfo ();
			Exec.FileName = File;
			Exec.Arguments = Args;
			Exec.UseShellExecute = false;
			Exec.RedirectStandardOutput = true;
			Exec.RedirectStandardError = true;
			Exec.CreateNoWindow = true;
			using (Process p = Process.Start (Exec))
			{
				string StandardOut = p.StandardOutput.ReadToEnd ();
				p.WaitForExit (TimeoutMilliseconds);
				return StandardOut.Trim ();
			}
		}
		catch { return string.Empty; }
	}

	static string FindOnPath (string Name)
	{
		string PathVariable = Environment.GetEnvironmentVariable ("PATH");
		if (string.IsNullOrEmpty (PathVariable))
			return string.Empty;

		string[] Parts = PathVariable.Split (':');
		int i = 0;
		while (i < Parts.Length)
		{
			string CombinedFilePath = Path.Combine (Parts[i], Name);
			if (File.Exists (CombinedFilePath))
				return CombinedFilePath;

			i++;
		}

		return string.Empty;
	}

	static string ExtractDigits (string s)
	{
		if (string.IsNullOrEmpty (s))
			return string.Empty;

		System.Text.StringBuilder SB = new System.Text.StringBuilder ();

		int i = 0;
		while (i < s.Length)
		{
			char c = s[i];
			if (c >= '0' && c <= '9') SB.Append (c);
			i++;
		}

		return SB.ToString ();
	}
#endif

	static string ProfileFromPid (int ProcessId)
	{
		try
		{
			Process p = null;
			try
			{
				p = Process.GetProcessById (ProcessId);
			}
			catch
			{
				p = null;
			}

			if (p == null)
				return string.Empty;

			string Name = p.ProcessName;

			bool bIsFF = string.Equals (Name, "firefox", StringComparison.OrdinalIgnoreCase)
				  || string.Equals (Name, "firefox-bin", StringComparison.OrdinalIgnoreCase);

			try
			{
				p.Dispose ();
			}
			catch { }

			if (!bIsFF)
				return string.Empty;

			string CommandLine = FFCommon.GetProcessCommandLine (ProcessId);
			if (string.IsNullOrEmpty (CommandLine))
				return string.Empty;

			string Profile = FFCommon.ExtractProfileFromCmd (CommandLine);
			if (!string.IsNullOrEmpty (Profile))
				return Profile;

			string ppath = FFCommon.ExtractProfilePathFromCmd (CommandLine);
			if (!string.IsNullOrEmpty (ppath))
			{
				List<FFCommon.ProfileInfo> ProfileInfo = FFCommon.ReadProfilesIni ();
				int i = 0;
				string np = FFCommon.NormalisePath (ppath); // from your current FFCommon.cs
				while (i < ProfileInfo.Count)
				{
					if (FFCommon.NormalisePath (ProfileInfo[i].PathOnDisk) == np)
						return ProfileInfo[i].Name;
					i++;
				}
			}
		}
		catch { }
		return string.Empty;
	}

	static volatile bool ShutdownLogged = false;
	static string ShutdownReason = string.Empty;

	static void RegisterShutdownHooks ()
	{
		try
		{
#if LINUX
			try
			{
				InstallUnixSignalHandlers ();
			}
			catch { }
#endif

			AppDomain.CurrentDomain.ProcessExit += OnProcessExit;
			AppDomain.CurrentDomain.DomainUnload += OnDomainUnload;
			AppDomain.CurrentDomain.UnhandledException += OnUnhandledException;
			try { Console.CancelKeyPress += OnCancelKeyPress; } catch { }
#if WINDOWS
			try { Microsoft.Win32.SystemEvents.SessionEnding += OnSessionEnding; } catch { }
#endif
		}
		catch { }
	}

	static void OnProcessExit (object Sender, EventArgs e)
	{
		LogShutdown ("ProcessExit");
	}

	static void OnDomainUnload (object Sender, EventArgs e)
	{
		LogShutdown ("DomainUnload");
	}

	static void OnUnhandledException (object Sender, UnhandledExceptionEventArgs e)
	{
		try
		{
			if (e != null && e.ExceptionObject != null)
			{
				string ExceptionMessage = e.ExceptionObject.ToString ();
				if (string.IsNullOrEmpty (ShutdownReason))
					ShutdownReason = "UnhandledException: " + ExceptionMessage;
				else
					ShutdownReason = ShutdownReason + " | UnhandledException: " + ExceptionMessage;

				FFCommon.Log ("FFFocusTracker", "Unhandled exception observed: " + ExceptionMessage);
			}
		}
		catch { }

		LogShutdown (null);
	}

	static void OnCancelKeyPress (object Sender, ConsoleCancelEventArgs e)
	{
		try
		{
			string Intercept = (e == null) ? "" : e.SpecialKey.ToString ();
			if (string.IsNullOrEmpty (ShutdownReason))
				ShutdownReason = "ConsoleCancel: " + Intercept;
			else
				ShutdownReason = ShutdownReason + " | ConsoleCancel: " + Intercept;
		}
		catch { }
	}

#if WINDOWS
	static void OnSessionEnding (object Sender, Microsoft.Win32.SessionEndingEventArgs e)
	{
		try
		{
			string Why = (e == null) ? "" : e.Reason.ToString ();
			if (string.IsNullOrEmpty (ShutdownReason))
				ShutdownReason = "SessionEnding: " + Why;
			else
				ShutdownReason = ShutdownReason + " | SessionEnding: " + Why;
		}
		catch { }
	}
#endif

	static void LogShutdown (string Signal)
	{
		if (ShutdownLogged)
			return;

		ShutdownLogged = true;

		string Reason = ShutdownReason;
		if (!string.IsNullOrEmpty (Signal))
			Reason = string.IsNullOrEmpty (Reason) ? Signal : (Signal + " | " + Reason);

		if (!string.IsNullOrEmpty (Reason))
			FFCommon.Log ("FFFocusTracker", "FFFocusTracker is shutting down. Reason: " + Reason);
		else
			FFCommon.Log ("FFFocusTracker", "FFFocusTracker is shutting down.");
	}
}
