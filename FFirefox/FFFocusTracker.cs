// FFFocusTracker.cs
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;

public class FFFocusTracker
{
#if WINDOWS
    [DllImport ("user32.dll")] private static extern IntPtr GetForegroundWindow ();
    [DllImport ("user32.dll")] private static extern uint GetWindowThreadProcessId (IntPtr hWnd, out uint lpdwProcessId);
#endif

	[STAThread]
	public static void Main (string[] args)
	{
		FFCommon.Log ("FFFocusTracker", "Starting focus tracker...");
		try { RunLoop (); }
		catch (Exception ex)
		{
			FFCommon.LogException ("FFFocusTracker", "Main", ex);
			FFCommon.NotifyError ("FF Focus Tracker crashed", ex.Message);
			FFCommon.OpenLogsFolderFailSafe ();
		}
		finally
		{
			// Log an empty line on every Link Route.
			FFCommon.LogEmpty ("FFFocusTracker");
		}
	}

	private static void RunLoop ()
	{
		string LastSent = string.Empty;
		while (true)
		{
			try
			{
				string ActiveProfile = DetectActiveFirefoxProfile ();
				if (!string.IsNullOrEmpty (ActiveProfile) && !string.Equals (ActiveProfile, LastSent, StringComparison.OrdinalIgnoreCase))
				{
					FFCommon.UpdateFocusedProfile (ActiveProfile);
					LastSent = ActiveProfile;
				}
			}
			catch (Exception ex) { FFCommon.LogException ("FFFocusTracker", "RunLoopDetect", ex); }
			Thread.Sleep (400);
		}
	}

	private static string DetectActiveFirefoxProfile ()
	{
#if WINDOWS
		IntPtr HwndActiveWindow = GetForegroundWindow ();
		if (HwndActiveWindow == IntPtr.Zero)
			return string.Empty;
		uint ProcessId;
		GetWindowThreadProcessId (HwndActiveWindow, out ProcessId);
		try
		{
			Process Process = Process.GetProcessById ((int)ProcessId);
			try
			{
				string ProcessName = Process.ProcessName;
				bool bIsFirefox = string.Equals (ProcessName, "firefox", StringComparison.OrdinalIgnoreCase) || string.Equals (ProcessName, "firefox.exe", StringComparison.OrdinalIgnoreCase);
				if (!bIsFirefox)
					return string.Empty;
				// Robust: resolve via parent chain so we always get the owning profile
				return FFCommon.ResolveProfileNameForPid ((int)ProcessId);
			}
			finally
			{
				try
				{
					Process.Dispose ();
				}
				catch { }
			}
		}
		catch
		{
			return string.Empty;
		}
#else
		// X11: xdotool path (Wayland may restrict)
		try
		{
			string ProcessIdString = ExecAndRead ("xdotool", "getactivewindow getwindowpid");
			int ProcessId;
			if (!string.IsNullOrEmpty (ProcessIdString) && int.TryParse (ProcessIdString.Trim (), out ProcessId))
			{
				Process Process = null;
				try
				{
					Process = Process.GetProcessById (ProcessId);
				}
				catch
				{
					Process = null;
				}

				if (Process != null)
				{
					string ProcessName = Process.ProcessName;
					bool bIsFirefox = string.Equals (ProcessName, "firefox", StringComparison.OrdinalIgnoreCase) || string.Equals (ProcessName, "firefox-bin", StringComparison.OrdinalIgnoreCase);
					try
					{
						Process.Dispose ();
					}
					catch { }

					if (!bIsFirefox)
						return string.Empty;
				}

				return FFCommon.ResolveProfileNameForPid (ProcessId);
			}
		}
		catch { }

		// xprop fallback
		try
		{
			string WindowId = ExecAndRead ("sh", "-c \"xprop -root _NET_ACTIVE_WINDOW | awk -F '# ' '{print $2}'\"");
			if (!string.IsNullOrEmpty (WindowId))
			{
				string ProcessId = ExecAndRead ("sh", "-c \"xprop -id " + WindowId.Trim () + " _NET_WM_PID | awk '{print $3}'\"");

				int n;
				if (int.TryParse (ProcessId.Trim (), out n))
					return FFCommon.ResolveProfileNameForPid (n);
			}
		}
		catch { }

		return string.Empty;
#endif
	}

#if !WINDOWS
	private static string ExecAndRead (string File, string Args)
	{
		try
		{
			ProcessStartInfo ProcessInfo = new ProcessStartInfo ();
			ProcessInfo.FileName = File;
			ProcessInfo.Arguments = Args;
			ProcessInfo.UseShellExecute = false;
			ProcessInfo.RedirectStandardOutput = true;
			ProcessInfo.RedirectStandardError = true;
			ProcessInfo.CreateNoWindow = true;

			using (Process RunningProcess = Process.Start (ProcessInfo))
			{
				string s = RunningProcess.StandardOutput.ReadToEnd ();
				RunningProcess.WaitForExit (800);
				return s.Trim ();
			}
		}
		catch
		{
			return string.Empty;
		}
	}
#endif
}
