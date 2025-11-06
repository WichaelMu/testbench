#define LINUX
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
	public static string GetBaseDir ()
	{
#if WINDOWS
		string BaseDirectory = Environment.GetFolderPath (Environment.SpecialFolder.LocalApplicationData);
		return Path.Combine (BaseDirectory, "FF");
#elif LINUX
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

	public static void LogException (string Component, string Context, Exception Ex)
	{
		try
		{
			string LogFile = GetLogFile (Component);

			StringBuilder SB = new StringBuilder ();
			SB.Append (GetLocalTime ("o")).Append (" ").Append (Context).Append (": ")
			  .Append (Ex.GetType ().FullName).Append (": ").Append (Ex.Message).AppendLine ()
			  .Append (Ex.StackTrace).AppendLine ();

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
#elif LINUX
			TryStart ("xdg-open", GetLogsDir ());
#endif
		}
		catch { }
	}

	public static void SendNotification (string Title, string Body)
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
#elif LINUX
			TryStart ("notify-send", $"{Title}\n{Body}");
#endif
		}
		catch { }
	}

	public static string GetProfilesIniPath ()
	{
#if WINDOWS
		string Roaming = Environment.GetFolderPath (Environment.SpecialFolder.ApplicationData);
		return Path.Combine (Roaming, "Mozilla", "Firefox", "profiles.ini");
#elif LINUX
		string Home = Environment.GetEnvironmentVariable ("HOME");
		if (string.IsNullOrEmpty (Home))
			Home = ".";

		return Path.Combine (Home, ".mozilla", "firefox", "profiles.ini");
#endif
	}

	public class ProfileInfo
	{
		public string Name;
		public string PathOnDisk;
		public bool IsDefault;
	}

	public static List<ProfileInfo> ReadProfilesIni ()
	{
		List<ProfileInfo> ProfilesList = new List<ProfileInfo> ();
		try
		{
			string ProfilesIni = GetProfilesIniPath ();

			if (!File.Exists (ProfilesIni))
				return ProfilesList;

			string[] Lines = File.ReadAllLines (ProfilesIni);

			ProfileInfo CurrentProfile = null;
			string BaseDirectory = Path.GetDirectoryName (ProfilesIni);

			int i = 0;
			while (i < Lines.Length)
			{
				string Line = Lines[i].Trim ();
				if (Line.StartsWith ("[Profile", StringComparison.OrdinalIgnoreCase))
				{
					if (CurrentProfile != null) ProfilesList.Add (CurrentProfile);
					CurrentProfile = new ProfileInfo ();
				}
				else if (CurrentProfile != null)
				{
					int Equals1 = Line.IndexOf ('=');
					if (Equals1 > 0)
					{
						string Key1 = Line.Substring (0, Equals1).Trim ();
						string Value1 = Line.Substring (Equals1 + 1).Trim ();

						if (string.Equals (Key1, "Name", StringComparison.OrdinalIgnoreCase))
							CurrentProfile.Name = Value1;

						else if (string.Equals (Key1, "Path", StringComparison.OrdinalIgnoreCase))
						{
							bool bIsRelative = false;

							int k = i - 1;
							while (k >= 0 && k >= i - 5)
							{
								string Line2 = Lines[k].Trim ();
								int Equals2 = Line2.IndexOf ('=');

								if (Equals2 > 0)
								{
									string Key2 = Line2.Substring (0, Equals2).Trim ();
									string Value2 = Line2.Substring (Equals2 + 1).Trim ();
									if (string.Equals (Key2, "IsRelative", StringComparison.OrdinalIgnoreCase))
									{
										bIsRelative = Value2 == "1";
										break;
									}
								}

								k--;
							}

							if (bIsRelative)
								CurrentProfile.PathOnDisk = Path.Combine (BaseDirectory, Value1);
							else
								CurrentProfile.PathOnDisk = Value1;
						}
						else if (string.Equals (Key1, "Default", StringComparison.OrdinalIgnoreCase))
							CurrentProfile.IsDefault = (Value1 == "1");
					}
				}

				i++;
			}

			if (CurrentProfile != null)
				ProfilesList.Add (CurrentProfile);
		}
		catch (Exception ex)
		{
			LogException ("FFCommon", "ReadProfilesIni", ex);
		}

		return ProfilesList;
	}

	public static string GetDefaultProfileName ()
	{
		try
		{
			List<ProfileInfo> ProfilesInfo = ReadProfilesIni ();

			int i = 0;
			while (i < ProfilesInfo.Count)
			{
				if (ProfilesInfo[i].IsDefault && !string.IsNullOrEmpty (ProfilesInfo[i].Name))
					return ProfilesInfo[i].Name;

				i++;
			}

			if (ProfilesInfo.Count > 0 && !string.IsNullOrEmpty (ProfilesInfo[0].Name))
				return ProfilesInfo[0].Name;
		}
		catch (Exception ex)
		{
			LogException ("FFCommon", "GetDefaultProfileName", ex);
		}

		return "default";
	}

	public static void LoadFocusState (out string LastFocusedProfile, out Dictionary<string, long> FocusedTicks)
	{
		LastFocusedProfile = string.Empty;
		FocusedTicks = new Dictionary<string, long> (StringComparer.OrdinalIgnoreCase);

		try
		{
			string StateFile = GetStateFile ();
			if (!File.Exists (StateFile))
				return;

			string[] Lines = File.ReadAllLines (StateFile);

			int i = 0;
			while (i < Lines.Length)
			{
				string Line = Lines[i].Trim ();

				if (Line.StartsWith ("LastFocusedProfile=", StringComparison.Ordinal))
				{
					LastFocusedProfile = Line.Substring ("LastFocusedProfile=".Length);
				}
				else if (Line.Length > 0)
				{
					int LineSeparator = Line.IndexOf ('|');
					if (LineSeparator > 0)
					{
						string ProfileName = Line.Substring (0, LineSeparator);
						string TicksPart = Line.Substring (LineSeparator + 1);
						long Ticks;

						if (long.TryParse (TicksPart, out Ticks))
						{
							FocusedTicks[ProfileName] = Ticks;
						}
					}
				}

				i++;
			}
		}
		catch (Exception Ex)
		{
			LogException ("FFCommon", "LoadFocusState", Ex);
		}
	}

	public static void SaveFocusState (string LastFocusedProfile, Dictionary<string, long> FocusTicks)
	{
		try
		{
			StringBuilder SB = new StringBuilder ();
			SB.Append ("LastFocusedProfile=");
			SB.Append (LastFocusedProfile ?? string.Empty);
			SB.AppendLine ();

			foreach (KeyValuePair<string, long> KV in FocusTicks)
			{
				SB.Append (KV.Key);
				SB.Append ('|');
				SB.Append (KV.Value);
				SB.AppendLine ();
			}

			File.WriteAllText (GetStateFile (), SB.ToString ());
		}
		catch (Exception Ex)
		{
			LogException ("FFCommon", "SaveFocusState", Ex);
		}
	}

	public static void UpdateFocusedProfile (string ProfileName)
	{
		if (string.IsNullOrEmpty (ProfileName))
			return;

		string LastProfile;
		Dictionary<string, long> FocusTicks;

		LoadFocusState (out LastProfile, out FocusTicks);

		long Ticks = DateTime.UtcNow.Ticks;
		FocusTicks[ProfileName] = Ticks;
		LastProfile = ProfileName;

		SaveFocusState (LastProfile, FocusTicks);
		Log ("FFFocusTracker", $"Focused profile now: {ProfileName}");
	}

	public class FFProc
	{
		public int Pid;
		public string ProfileName;
		public DateTime StartTimeUtc;
	}

	public static List<FFProc> GetRunningFirefoxProcesses ()
	{
		List<FFProc> ProcessList = new List<FFProc> ();
		try
		{
			Process[] Processes = Process.GetProcesses ();

			int i = 0;
			while (i < Processes.Length)
			{
				Process p = Processes[i];
				try
				{
					string ProcsesName = p.ProcessName;
					bool bIsFF = string.Equals (ProcsesName, "firefox", StringComparison.OrdinalIgnoreCase)
						  || string.Equals (ProcsesName, "firefox-bin", StringComparison.OrdinalIgnoreCase)
						  || string.Equals (ProcsesName, "firefox.exe", StringComparison.OrdinalIgnoreCase);

					if (bIsFF)
					{
						string CommandLine = GetProcessCommandLine (p.Id);
						string Profile = ExtractProfileFromCmd (CommandLine);

						DateTime StartTime;
						try { StartTime = p.StartTime.ToUniversalTime (); }
						catch { StartTime = DateTime.MinValue; }

						FFProc Firefox = new FFProc ();
						Firefox.Pid = p.Id;
						Firefox.ProfileName = Profile;
						Firefox.StartTimeUtc = StartTime;

						ProcessList.Add (Firefox);
					}
				}
				catch { }
				finally
				{
					try
					{
						p.Dispose ();
					}
					catch { }
				}

				i++;
			}

			List<ProfileInfo> ProfilesInfo = ReadProfilesIni ();
			Dictionary<string, string> PathToName = new Dictionary<string, string> (StringComparer.OrdinalIgnoreCase);
			int k = 0;
			while (k < ProfilesInfo.Count)
			{
				if (!string.IsNullOrEmpty (ProfilesInfo[k].PathOnDisk) && !string.IsNullOrEmpty (ProfilesInfo[k].Name))
				{
					PathToName[NormalisePath (ProfilesInfo[k].PathOnDisk)] = ProfilesInfo[k].Name;
				}

				k++;
			}

			int z = 0;
			while (z < ProcessList.Count)
			{
				if (string.IsNullOrEmpty (ProcessList[z].ProfileName))
				{
					string CommandLine = GetProcessCommandLine (ProcessList[z].Pid);
					string ProfilePath = ExtractProfilePathFromCmd (CommandLine);

					if (!string.IsNullOrEmpty (ProfilePath))
					{
						string NormalisedPath = NormalisePath (ProfilePath);
						string Mapped;

						if (PathToName.TryGetValue (NormalisedPath, out Mapped))
						{
							ProcessList[z].ProfileName = Mapped;
						}
					}
				}

				z++;
			}
		}
		catch (Exception Ex)
		{
			LogException ("FFCommon", "GetRunningFirefoxProcesses", Ex);
		}

		return ProcessList;
	}

	public static string NormalisePath (string Path)
	{
		if (string.IsNullOrEmpty (Path))
			return Path;

		string Replaced = Path.Replace ('\\', '/');
		while (Replaced.Length > 1 && Replaced.EndsWith ("/"))
			Replaced = Replaced.Substring (0, Replaced.Length - 1);

		return Replaced;
	}

	public static string GetProcessCommandLine (int ProcessId)
	{
		try
		{
#if WINDOWS
			using (ManagementObjectSearcher s = new ManagementObjectSearcher ("SELECT CommandLine, ProcessId FROM Win32_Process WHERE ProcessId = " + ProcessId))
			{
				foreach (ManagementObject o in s.Get ())
				{
					object CommandLine = o["CommandLine"];
					if (CommandLine != null)
						return CommandLine.ToString ();
				}
			}

			return string.Empty;
#elif LINUX
			string ProcessPath = "/proc/" + ProcessId + "/cmdline";

			if (!File.Exists (ProcessPath))
				return string.Empty;

			byte[] ByteData = File.ReadAllBytes (ProcessPath);

			if (ByteData == null || ByteData.Length == 0)
				return string.Empty;

			for (int i = 0; i < ByteData.Length; i++)
				if (ByteData[i] == 0)
					ByteData[i] = (byte)' ';

			return Encoding.UTF8.GetString (ByteData);
#endif
		}
		catch { return string.Empty; }
	}

	public static string ExtractProfileFromCmd (string CommandLine)
	{
		if (string.IsNullOrEmpty (CommandLine))
			return string.Empty;

		try
		{
			Regex ProfileGroup = new Regex ("-P\\s+\"?([^\"\\s]+)\"?", RegexOptions.IgnoreCase);
			Match m = ProfileGroup.Match (CommandLine);

			if (m.Success)
				return m.Groups[1].Value;
		}
		catch { }

		return string.Empty;
	}

	public static string ExtractProfilePathFromCmd (string cmd)
	{
		if (string.IsNullOrEmpty (cmd))
			return string.Empty;

		try
		{
			Regex ProfilePathGroup = new Regex ("-profile\\s+\"?([^\"]+)\"?", RegexOptions.IgnoreCase);
			Match M = ProfilePathGroup.Match (cmd);

			if (M.Success)
				return M.Groups[1].Value;
		}
		catch { }
		return string.Empty;
	}

	public static bool TryStart (string File, string Args)
	{
		try
		{
			ProcessStartInfo Exec = new ProcessStartInfo ();
			Exec.FileName = File;
			Exec.Arguments = Args;
			Exec.UseShellExecute = false;
			Exec.CreateNoWindow = true;

			Process P = Process.Start (Exec);
			return P != null;
		}
		catch { return false; }
	}

	public static string FindFirefoxExecutable ()
	{
#if WINDOWS
		try
		{
			ProcessStartInfo Exec = new ProcessStartInfo ();
			Exec.FileName = "where";
			Exec.Arguments = "firefox";
			Exec.UseShellExecute = false;
			Exec.RedirectStandardOutput = true;
			Exec.CreateNoWindow = true;

			using (Process p = Process.Start (Exec))
			{
				string StandardOutput = p.StandardOutput.ReadToEnd ();
				p.WaitForExit (1500);

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
			string p1 = Path.Combine (ProgramFiles, "Mozilla Firefox", "firefox.exe");
			if (File.Exists (p1)) return p1;
		}

		string ProgramFilesx86 = Environment.GetEnvironmentVariable ("ProgramFiles(x86)");
		if (!string.IsNullOrEmpty (ProgramFilesx86))
		{
			string p2 = Path.Combine (ProgramFilesx86, "Mozilla Firefox", "firefox.exe");
			if (File.Exists (p2)) return p2;
		}

		return "firefox";
#elif LINUX
		if (File.Exists ("/usr/bin/firefox"))
			return "/usr/bin/firefox";

		if (File.Exists ("/usr/lib/firefox/firefox"))
			return "/usr/lib/firefox/firefox";

		return "firefox";
#endif
	}

	public static bool LaunchFirefox (string ProfileName, string Url)
	{
		try
		{
			string Firefox = FindFirefoxExecutable ();
			StringBuilder FirefoxLaunchArguments = new StringBuilder ();

			if (!string.IsNullOrEmpty (ProfileName))
			{
				FirefoxLaunchArguments.Append (" -P \"");
				FirefoxLaunchArguments.Append (ProfileName);
				FirefoxLaunchArguments.Append ("\"");
			}

			if (!string.IsNullOrEmpty (Url))
			{
				FirefoxLaunchArguments.Append (" -new-tab \"");
				FirefoxLaunchArguments.Append (Url);
				FirefoxLaunchArguments.Append ("\"");
			}

			ProcessStartInfo FirefoxExec = new ProcessStartInfo ();
			FirefoxExec.FileName = Firefox;
			FirefoxExec.Arguments = FirefoxLaunchArguments.ToString ();
			FirefoxExec.UseShellExecute = false;
			FirefoxExec.CreateNoWindow = true;

#if !WINDOWS
			// force X11 so xdotool/xprop can see it
			FirefoxExec.EnvironmentVariables["MOZ_ENABLE_WAYLAND"] = "0";
#endif

			Process P = Process.Start (FirefoxExec);
			Log ("FFLinkRouter", "Launch firefox: profile='" + ProfileName + "' url='" + Url + "' exe='" + Firefox + "'");

			return P != null;
		}
		catch (Exception Ex)
		{
			LogException ("FFLinkRouter", "LaunchFirefox", Ex);
			return false;
		}
	}
}
