// FFCommon.cs (C#5-safe)
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.CompilerServices;
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
				Notification.Icon = SystemIcons.Information;
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

	// ---------- Firefox profiles ----------
	public class ProfileInfo { public string Name; public string PathOnDisk; public bool IsDefault; }

	public static string GetProfilesIniPath ()
	{
#if WINDOWS
		string Roaming = Environment.GetFolderPath (Environment.SpecialFolder.ApplicationData);
		return Path.Combine (Roaming, "Mozilla", "Firefox", "profiles.ini");
#else
		string Home = Environment.GetEnvironmentVariable ("HOME");
		if (string.IsNullOrEmpty (Home))
			Home = ".";
		return Path.Combine (Home, ".mozilla", "firefox", "profiles.ini");
#endif
	}

	public static List<ProfileInfo> ReadProfilesIni ()
	{
		List<ProfileInfo> Profiles = new List<ProfileInfo> ();
		try
		{
			string ProfilesIniPath = GetProfilesIniPath ();
			if (!File.Exists (ProfilesIniPath))
				return Profiles;

			string[] ProfileLines = File.ReadAllLines (ProfilesIniPath);
			ProfileInfo CurrentProfile = null;
			string ParentProfilesPath = Path.GetDirectoryName (ProfilesIniPath);
			int i = 0;
			while (i < ProfileLines.Length)
			{
				string ProfileLine = ProfileLines[i].Trim ();
				if (ProfileLine.StartsWith ("[Profile", StringComparison.OrdinalIgnoreCase))
				{
					if (CurrentProfile != null)
						Profiles.Add (CurrentProfile);
					CurrentProfile = new ProfileInfo ();
				}
				else if (CurrentProfile != null)
				{
					int Equal = ProfileLine.IndexOf ('=');
					if (Equal > 0)
					{
						string Key = ProfileLine.Substring (0, Equal).Trim ();
						string Value = ProfileLine.Substring (Equal + 1).Trim ();

						if (string.Equals (Key, "Name", StringComparison.OrdinalIgnoreCase))
						{
							CurrentProfile.Name = Value;
						}
						else if (string.Equals (Key, "Path", StringComparison.OrdinalIgnoreCase))
						{
							bool bIsRelative = false;
							int k = i - 1;
							while (k >= 0 && k >= i - 5)
							{
								string L2 = ProfileLines[k].Trim ();
								int Equal2 = L2.IndexOf ('=');
								if (Equal2 > 0 && string.Equals (L2.Substring (0, Equal2).Trim (), "IsRelative", StringComparison.OrdinalIgnoreCase))
								{
									bIsRelative = L2.Substring (Equal2 + 1).Trim () == "1";
									break;
								}
								k--;
							}

							CurrentProfile.PathOnDisk = bIsRelative ? Path.Combine (ParentProfilesPath, Value) : Value;
						}
						else if (string.Equals (Key, "Default", StringComparison.OrdinalIgnoreCase))
						{
							CurrentProfile.IsDefault = (Value == "1");
						}
					}
				}
				i++;
			}

			if (CurrentProfile != null)
				Profiles.Add (CurrentProfile);
		}
		catch (Exception ex)
		{
			LogException ("FFCommon", "ReadProfilesIni", ex);
		}

		return Profiles;
	}

	public static string GetDefaultProfileName ()
	{
		try
		{
			List<ProfileInfo> Profiles = ReadProfilesIni ();
			int k = 0;
			while (k < Profiles.Count)
			{
				if (Profiles[k].IsDefault && !string.IsNullOrEmpty (Profiles[k].Name))
					return Profiles[k].Name;

				k++;
			}

			if (Profiles.Count > 0 && !string.IsNullOrEmpty (Profiles[0].Name))
				return Profiles[0].Name;
		}
		catch (Exception ex)
		{
			LogException ("FFCommon", "GetDefaultProfileName", ex);
		}

		return "default";
	}

	// ---------- Focus state ----------
	// focus_state.txt:
	// LastFocusedProfile=<name>
	// <profile>|<ticksUtc>
	public static void LoadFocusState (out string LastFocusedProfile, out Dictionary<string, long> FocusTicks)
	{
		LastFocusedProfile = string.Empty;
		FocusTicks = new Dictionary<string, long> (StringComparer.OrdinalIgnoreCase);
		try
		{
			string StateFile = GetStateFile ();
			if (!File.Exists (StateFile))
				return;

			string[] StateLines = File.ReadAllLines (StateFile);
			int i = 0;
			while (i < StateLines.Length)
			{
				string State = StateLines[i].Trim ();
				if (State.StartsWith ("LastFocusedProfile=", StringComparison.Ordinal))
				{
					LastFocusedProfile = State.Substring ("LastFocusedProfile=".Length);
				}
				else if (State.Length > 0)
				{
					int Profile = State.IndexOf ('|');
					if (Profile > 0)
					{
						string NameOfProfile = State.Substring (0, Profile);
						string StateTicks = State.Substring (Profile + 1);

						long Ticks;
						if (long.TryParse (StateTicks, out Ticks))
							FocusTicks[NameOfProfile] = Ticks;
					}
				}

				i++;
			}
		}
		catch (Exception ex)
		{
			LogException ("FFCommon", "LoadFocusState", ex);
		}
	}

	public static void SaveFocusState (string lastFocusedProfile, Dictionary<string, long> focusTicks)
	{
		try
		{
			StringBuilder SB = new StringBuilder ();
			SB.Append ("LastFocusedProfile=").Append (lastFocusedProfile == null ? string.Empty : lastFocusedProfile).AppendLine ();

			foreach (KeyValuePair<string, long> kv in focusTicks)
				SB.Append (kv.Key).Append ('|').Append (kv.Value).AppendLine ();

			File.WriteAllText (GetStateFile (), SB.ToString ());
		}
		catch (Exception ex)
		{
			LogException ("FFCommon", "SaveFocusState", ex);
		}
	}

	public static void UpdateFocusedProfile (string profileName)
	{
		if (string.IsNullOrEmpty (profileName))
			return;

		string last;
		Dictionary<string, long> map;

		LoadFocusState (out last, out map);
		map[profileName] = DateTime.UtcNow.Ticks;
		SaveFocusState (profileName, map);

		Log ("FFFocusTracker", "Focused profile now: " + profileName);
	}

	// ---------- Process helpers ----------
	public class FFProc
	{
		public int Pid;
		public string ProfileName;
		public DateTime StartTimeUtc;
	}

	public static List<FFProc> GetRunningFirefoxProcesses ()
	{
		List<FFProc> FirefoxProcesses = new List<FFProc> ();
		try
		{
			Process[] Processes = Process.GetProcesses ();
			int i = 0;
			while (i < Processes.Length)
			{
				Process Process = Processes[i];
				try
				{
					string ProcessName = Process.ProcessName;
					bool bIsFirefox = string.Equals (ProcessName, "firefox", StringComparison.OrdinalIgnoreCase) ||
						    string.Equals (ProcessName, "firefox-bin", StringComparison.OrdinalIgnoreCase) ||
						    string.Equals (ProcessName, "firefox.exe", StringComparison.OrdinalIgnoreCase);

					if (bIsFirefox)
					{
						string ProfileName = ResolveProfileNameForPid (Process.Id); // <— parent-chain resolve
						DateTime st;

						try
						{
							st = Process.StartTime.ToUniversalTime ();
						}
						catch
						{
							st = DateTime.MinValue;
						}

						FFProc FirefoxProcess = new FFProc ();
						FirefoxProcess.Pid = Process.Id;
						FirefoxProcess.ProfileName = ProfileName;
						FirefoxProcess.StartTimeUtc = st;

						FirefoxProcesses.Add (FirefoxProcess);
					}
				}
				catch { }
				finally
				{
					try
					{
						Process.Dispose ();
					}
					catch { }
				}

				i++;
			}

			// keep most-recent-start per profile
			Dictionary<string, FFProc> ByProfile = new Dictionary<string, FFProc> (StringComparer.OrdinalIgnoreCase);
			int k = 0;
			while (k < FirefoxProcesses.Count)
			{
				string Key = string.IsNullOrEmpty (FirefoxProcesses[k].ProfileName) ? "" : FirefoxProcesses[k].ProfileName;

				FFProc Process;
				if (!ByProfile.TryGetValue (Key, out Process) || FirefoxProcesses[k].StartTimeUtc > Process.StartTimeUtc)
					ByProfile[Key] = FirefoxProcesses[k];

				k++;
			}

			return new List<FFProc> (ByProfile.Values);
		}
		catch (Exception ex)
		{
			LogException ("FFCommon", "GetRunningFirefoxProcesses", ex);
			return new List<FFProc> ();
		}
	}

	public static string NormalisePath (string InPath)
	{
		if (string.IsNullOrEmpty (InPath))
			return InPath;

		string r = InPath.Replace ('\\', '/');
		while (r.Length > 1 && r.EndsWith ("/"))
			r = r.Substring (0, r.Length - 1);
		return r;
	}

	public static string GetProcessCommandLine (int ProcessId)
	{
		try
		{
#if WINDOWS
			using (ManagementObjectSearcher Searcher = new ManagementObjectSearcher ("SELECT CommandLine FROM Win32_Process WHERE ProcessId = " + ProcessId))
			{
				foreach (ManagementObject o in Searcher.Get ())
				{
					object CommandLine = o["CommandLine"];
					if (CommandLine != null)
						return CommandLine.ToString ();
				}
			}

			return string.Empty;
#else
			string Proc = "/proc/" + ProcessId + "/cmdline";
			if (!File.Exists (Proc))
				return string.Empty;

			byte[] ProcData = File.ReadAllBytes (Proc);
			if (ProcData == null || ProcData.Length == 0)
				return string.Empty;

			for (int i = 0; i < ProcData.Length; i++)
				if (ProcData[i] == 0)
					ProcData[i] = (byte)' ';

			return Encoding.UTF8.GetString (ProcData);
#endif
		}
		catch { return string.Empty; }
	}

	public static string ExtractProfileFromCmd (string Cmd)
	{
		if (string.IsNullOrEmpty (Cmd))
			return string.Empty;
		try
		{
			Match m = new Regex ("-P\\s+\"?([^\"\\s]+)\"?", RegexOptions.IgnoreCase).Match (Cmd);
			if (m.Success)
				return m.Groups[1].Value;
		}
		catch { }

		return string.Empty;
	}

	public static string ExtractProfilePathFromCmd (string Cmd)
	{
		if (string.IsNullOrEmpty (Cmd))
			return string.Empty;
		try
		{
			Match m = new Regex ("-profile\\s+\"?([^\"]+)\"?", RegexOptions.IgnoreCase).Match (Cmd);
			if (m.Success)
				return m.Groups[1].Value;
		}
		catch { }

		return string.Empty;
	}

	// --- Robust profile resolution: walk parent chain until we find the launcher with -P / -profile ---
	public static string ResolveProfileNameForPid (int ProcessId)
	{
		try
		{
			List<ProfileInfo> infos = ReadProfilesIni ();
			Dictionary<string, string> pathToName = new Dictionary<string, string> (StringComparer.OrdinalIgnoreCase);
			int i = 0;
			while (i < infos.Count)
			{
				if (!string.IsNullOrEmpty (infos[i].PathOnDisk) && !string.IsNullOrEmpty (infos[i].Name))
					pathToName[NormalisePath (infos[i].PathOnDisk)] = infos[i].Name;
				i++;
			}

			int CurrentPid = ProcessId;
			int Guard = 0;
			while (CurrentPid > 0 && Guard < 50)
			{
				string CommandLine = GetProcessCommandLine (CurrentPid);
				string Profile = ExtractProfileFromCmd (CommandLine);
				if (!string.IsNullOrEmpty (Profile))
					return Profile;

				string ProfilePath = ExtractProfilePathFromCmd (CommandLine);
				if (!string.IsNullOrEmpty (ProfilePath))
				{
					string np = NormalisePath (ProfilePath);
					string mapped;

					if (pathToName.TryGetValue (np, out mapped) && !string.IsNullOrEmpty (mapped))
						return mapped;
				}

				int parent = GetParentPid (CurrentPid);
				if (parent <= 0 || parent == CurrentPid)
					break;

				CurrentPid = parent;
				Guard++;
			}
		}
		catch (Exception ex)
		{
			LogException ("FFCommon", "ResolveProfileNameForPid", ex);
		}

		return string.Empty;
	}

	public static int GetParentPid (int ProcessId)
	{
		try
		{
#if WINDOWS
			using (ManagementObjectSearcher Searcher = new ManagementObjectSearcher ("SELECT ParentProcessId FROM Win32_Process WHERE ProcessId = " + ProcessId))
			{
				foreach (ManagementObject o in Searcher.Get ())
				{
					object pp = o["ParentProcessId"];
					if (pp != null) return Convert.ToInt32 ((uint)pp);
				}
			}

			return 0;
#else
			string Path = "/proc/" + ProcessId + "/status";
			if (!File.Exists (Path))
				return 0;
			string[] ProcLines = File.ReadAllLines (Path);
			int i = 0;
			while (i < ProcLines.Length)
			{
				if (ProcLines[i].StartsWith ("PPid:"))
				{
					int n;
					if (int.TryParse (ProcLines[i].Substring (5).Trim (), out n))
						return n;
				}

				i++;
			}

			return 0;
#endif
		}
		catch
		{
			return 0;
		}
	}

	// ---------- Launch ----------
	public static bool TryStart (string File, string Args)
	{
		try
		{
			ProcessStartInfo psi = new ProcessStartInfo ();
			psi.FileName = File;
			psi.Arguments = Args;
			psi.UseShellExecute = false;
			psi.CreateNoWindow = true;

			return Process.Start (psi) != null;
		}
		catch
		{
			return false;
		}
	}

	public static string FindFirefoxExecutable ()
	{
#if WINDOWS
		try
		{
			ProcessStartInfo ProcessInfo = new ProcessStartInfo ();
			ProcessInfo.FileName = "where";
			ProcessInfo.Arguments = "firefox";
			ProcessInfo.UseShellExecute = false;
			ProcessInfo.RedirectStandardOutput = true;
			ProcessInfo.CreateNoWindow = true;

			using (Process Process = Process.Start (ProcessInfo))
			{
				string StandardOutput = Process.StandardOutput.ReadToEnd ();
				Process.WaitForExit (1500);

				if (!string.IsNullOrEmpty (StandardOutput))
				{
					string[] Lines = StandardOutput.Split (new char[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
					if (Lines.Length > 0 && File.Exists (Lines[0]))
						return Lines[0];
				}
			}
		}
		catch { }
		string ProgramFiles = Environment.GetEnvironmentVariable ("ProgramFiles");
		if (!string.IsNullOrEmpty (ProgramFiles))
		{
			string P1 = Path.Combine (ProgramFiles, "Mozilla Firefox", "firefox.exe");
			if (File.Exists (P1))
				return P1;
		}

		string ProgramFilesx86 = Environment.GetEnvironmentVariable ("ProgramFiles (x86)");
		if (!string.IsNullOrEmpty (ProgramFilesx86))
		{
			string P2 = Path.Combine (ProgramFilesx86, "Mozilla Firefox", "firefox.exe");
			if (File.Exists (P2))
				return P2;
		}
#endif
		return "firefox";
	}

	public static bool LaunchFirefox (string ProfileName, string Url)
	{
		try
		{
			string FirefoxBinary = FindFirefoxExecutable ();
			StringBuilder Args = new StringBuilder ();

			if (!string.IsNullOrEmpty (ProfileName))
				Args.Append (" -P \"").Append (ProfileName).Append ("\"");

			if (!string.IsNullOrEmpty (Url))
				Args.Append (" -new-tab \"").Append (Url).Append ("\"");

			ProcessStartInfo ProcessInfo = new ProcessStartInfo ();
			ProcessInfo.FileName = FirefoxBinary;
			ProcessInfo.Arguments = Args.ToString ();
			ProcessInfo.UseShellExecute = false;
			ProcessInfo.CreateNoWindow = true;

			Process Firefox = Process.Start (ProcessInfo);
			Log ("FFLinkRouter", "Launch firefox: profile='" + ProfileName + "' url='" + Url + "' exe='" + FirefoxBinary + "'");

			return Firefox != null;
		}
		catch (Exception ex)
		{
			LogException ("FFLinkRouter", "LaunchFirefox", ex);
			return false;
		}
	}
}