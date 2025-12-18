#if defined (FF_WINDOWS)
    #include <string.h>   // for _stricmp
    #ifndef strcasecmp
        #define strcasecmp _stricmp
    #endif
#else
    #include <strings.h>  // declares strcasecmp / strncasecmp on POSIX
#endif

#include <iostream>
#include <cstdio>
#include <cctype>
#include <ctime>
#include <string>
#include <vector>
#include <tuple>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <sys/types.h>

#if FF_WINDOWS
  #include <windows.h>
  #include <shlobj.h>
  #include <direct.h>
  #define strcasecmp _stricmp
#else
  #include <sys/stat.h>
  #include <unistd.h>
  #include <dirent.h>
#endif

#include "Headers/FPlatform.hpp"
#include "Headers/FFCommon.hpp"

using namespace std;

static string NowIso ()
{
	time_t T = time (nullptr);
	char Buf[64] = {0};
	strftime (Buf, sizeof (Buf), "%Y-%m-%dT%H:%M:%S%z", localtime (&T));
	return string (Buf);
}

string FFCommon::JoinPath (const string& A, const string& B)
{
#if FF_WINDOWS
	const char Sep = '\\';
#else
	const char Sep = '/';
#endif
	if (A.empty ())
	{
		return B;
	}
	if (A.back () == Sep)
	{
		return A + B;
	}
	return A + Sep + B;
}

string FFCommon::GetDataRoot ()
{
#if FF_WINDOWS
	char Path[MAX_PATH] = {0};
	if (SHGetFolderPathA (nullptr, CSIDL_LOCAL_APPDATA, nullptr, SHGFP_TYPE_CURRENT, Path) != S_OK)
	{
		return string (".\\FF");
	}
	string Root = string (Path);
	if (!Root.empty () && (Root.back () == '\\' || Root.back () == '/'))
	{
		Root.pop_back ();
	}
	return Root + "\\FF";
#endif

#if FF_LINUX
	const char* Home = getenv ("HOME");
	string Base = (Home && *Home) ? string (Home) + "/.local/share" : string (".");
	if (!Base.empty () && Base.back () == '/')
	{
		Base.pop_back ();
	}

	std::cout << Base + "/FF" << std::endl;
	return Base + "/FF";
#endif
}

void FFCommon::EnsureDataRoot ()
{
	string Root = GetDataRoot ();
#if FF_WINDOWS
	if (_mkdir (Root.c_str ()) == 0 || errno == EEXIST)
	{
		return;
	}
#else
	struct stat St;
	if (stat (Root.c_str (), &St) == 0)
	{
		return;
	}
	mkdir (Root.c_str (), 0755);
#endif
}

void FFCommon::Log (const string& Component, const string& Message)
{
	EnsureDataRoot ();
	string Line = NowIso () + " " + Component + ": " + Message + "\n";
	string LogPath = JoinPath (GetDataRoot (), Component + ".log");
	ofstream Out (LogPath.c_str (), ios::out | ios::app | ios::binary);
	if (Out)
	{
		Out << Line;
		std::cout << Line << std::endl;
	}
}

// --- tiny JSON helpers (best-effort parse for simple flat strings/ints) ----

static bool ExtractJsonStringField (const string& Content, const char* Field, string& Out)
{
	Out.clear ();
	string Key = string ("\"") + Field + "\"";
	size_t P = Content.find (Key);
	if (P == string::npos)
	{
		return false;
	}
	P = Content.find (':', P);
	if (P == string::npos)
	{
		return false;
	}
	do { ++P; } while (P < Content.size () && isspace ((unsigned char)Content[P]));
	if (P >= Content.size ())
	{
		return false;
	}
	if (Content[P] == '\"')
	{
		size_t Q = Content.find ('\"', P + 1);
		if (Q == string::npos)
		{
			return false;
		}
		Out = Content.substr (P + 1, Q - (P + 1));
		return true;
	}
	size_t Q = Content.find_first_of (",}\n\r", P);
	if (Q == string::npos)
	{
		Q = Content.size ();
	}
	Out = Content.substr (P, Q - P);
	while (!Out.empty () && isspace ((unsigned char)Out.back ()))
	{
		Out.pop_back ();
	}
	return !Out.empty ();
}

static bool ExtractJsonIntField (const string& Content, const char* Field, int& Out)
{
	Out = 0;
	string S;
	if (!ExtractJsonStringField (Content, Field, S))
	{
		return false;
	}
	try
	{
		Out = stoi (S);
		return true;
	}
	catch (...)
	{
		return false;
	}
}

// --- focus.json / focus_stack.json -----------------------------------------

bool FFCommon::LoadFocusWatcherState (string& OutApp, int& OutPid, string& OutProfileName, string& OutProfilePath, string& OutReason)
{
	OutApp.clear ();
	OutPid = 0;
	OutProfileName.clear ();
	OutProfilePath.clear ();
	OutReason.clear ();

	string FocusPath = JoinPath (GetDataRoot (), "focus.json");
	ifstream In (FocusPath.c_str (), ios::in | ios::binary);
	if (!In)
	{
		OutReason = "focus.json not found";
		return false;
	}
	string Content ((istreambuf_iterator<char>(In)), istreambuf_iterator<char>());

	string App;
	string Name;
	string PPath;
	int Pid = 0;
	ExtractJsonStringField (Content, "app", App);
	ExtractJsonStringField (Content, "profile_name", Name);
	ExtractJsonStringField (Content, "profile_path", PPath);
	ExtractJsonIntField (Content, "pid", Pid);

	if (App.empty ())
	{
		OutReason = "app empty";
		return false;
	}

	string AppLower = App;
	for (char& C : AppLower)
	{
		C = (char)tolower ((unsigned char)C);
	}

	if (AppLower.rfind ("firefox", 0) != 0)
	{
		OutReason = "last focus not Firefox";
		return false;
	}

	if (!IsProfileValid (Name, PPath))
	{
		OutReason = "profile invalid";
		return false;
	}

	OutApp = App;
	OutPid = Pid;
	OutProfileName = Name;
	OutProfilePath = PPath;
	return true;
}

void FFCommon::RememberProfileFromWatcher (const string& ProfileName, const string& ProfilePath)
{
	if (ProfileName.empty () && ProfilePath.empty ())
	{
		return;
	}

	EnsureDataRoot ();
	string StackPath = JoinPath (GetDataRoot (), "focus_stack.json");

	vector<tuple<string,string,string>> Items;

	// load existing (best-effort)
	{
		ifstream In (StackPath.c_str (), ios::in | ios::binary);
		if (In)
		{
			string S ((istreambuf_iterator<char>(In)), istreambuf_iterator<char>());
			size_t Pos = 0;
			while (true)
			{
				size_t B = S.find ('{', Pos);
				if (B == string::npos)
				{
					break;
				}
				size_t E = S.find ('}', B);
				if (E == string::npos)
				{
					break;
				}
				string Obj = S.substr (B, E - B + 1);
				string N, P, TS;
				ExtractJsonStringField (Obj, "name", N);
				ExtractJsonStringField (Obj, "path", P);
				ExtractJsonStringField (Obj, "ts", TS);
				if (!N.empty () || !P.empty ())
				{
					Items.emplace_back (N, P, TS);
				}
				Pos = E + 1;
			}
		}
	}

	auto Same = [&](const tuple<string,string,string>& X) -> bool
	{
		return (!get<0>(X).empty () && !ProfileName.empty () && strcasecmp (get<0>(X).c_str (), ProfileName.c_str ()) == 0) ||
		       (!get<1>(X).empty () && !ProfilePath.empty () && get<1>(X) == ProfilePath);
	};

	for (auto It = Items.begin (); It != Items.end (); )
	{
		if (Same (*It))
		{
			It = Items.erase (It);
		}
		else
		{
			++It;
		}
	}

	Items.insert (Items.begin (), make_tuple (ProfileName, ProfilePath, NowIso ()));
	if (Items.size () > 10)
	{
		Items.resize (10);
	}

	ofstream Out (StackPath.c_str (), ios::out | ios::binary | ios::trunc);
	if (!Out)
	{
		return;
	}
	Out << "{ \"recent\": [";
	for (size_t I = 0; I < Items.size (); ++I)
	{
		if (I > 0)
		{
			Out << ",";
		}
		Out << "{";
		Out << "\"name\":\"" << get<0>(Items[I]) << "\",";
		Out << "\"path\":\"" << get<1>(Items[I]) << "\",";
		Out << "\"ts\":\""   << get<2>(Items[I]) << "\"";
		Out << "}";
	}
	Out << "] }";
}

bool FFCommon::GetLatestProfileFromWatcher (string& OutProfileName, string& OutProfilePath)
{
	OutProfileName.clear ();
	OutProfilePath.clear ();

	string StackPath = JoinPath (GetDataRoot (), "focus_stack.json");
	ifstream In (StackPath.c_str (), ios::in | ios::binary);
	if (In)
	{
		string S ((istreambuf_iterator<char>(In)), istreambuf_iterator<char>());
		size_t R = S.find ("\"recent\"");
		if (R != string::npos)
		{
			size_t B = S.find ('{', R);
			size_t E = (B == string::npos) ? string::npos : S.find ('}', B);
			if (B != string::npos && E != string::npos)
			{
				string Obj = S.substr (B, E - B + 1);
				string N, P;
				ExtractJsonStringField (Obj, "name", N);
				ExtractJsonStringField (Obj, "path", P);
				if (IsProfileValid (N, P))
				{
					OutProfileName = N;
					OutProfilePath = P;
					return true;
				}
			}
		}
	}

	// one-shot fallback to current focus.json
	string App, Reason, Name, Path;
	int Pid = 0;
	if (LoadFocusWatcherState (App, Pid, Name, Path, Reason))
	{
		OutProfileName = Name;
		OutProfilePath = Path;
		return true;
	}
	return false;
}

// --- profiles.ini parse utilities ------------------------------------------

static string ProfilesIniPath ()
{
#if FF_WINDOWS
	char Roaming[MAX_PATH] = {0};
	if (SHGetFolderPathA (nullptr, CSIDL_APPDATA, nullptr, SHGFP_TYPE_CURRENT, Roaming) != S_OK)
	{
		return string ("profiles.ini");
	}
	string Base = Roaming;
	if (!Base.empty () && (Base.back () == '\\' || Base.back () == '/'))
	{
		Base.pop_back ();
	}
	return Base + "\\Mozilla\\Firefox\\profiles.ini";
#else
	const char* Home = getenv ("HOME");
	string Base = (Home && *Home) ? string (Home) : string (".");
	if (!Base.empty () && Base.back () == '/')
	{
		Base.pop_back ();
	}
	return Base + "/.mozilla/firefox/profiles.ini";
#endif
}

static string NormPath (const string& P)
{
	string R = P;
	for (char& C : R)
	{
#if FF_WINDOWS
		if (C == '/')
		{
			C = '\\';
		}
#else
		if (C == '\\')
		{
			C = '/';
		}
#endif
	}
	for (char& C : R)
	{
		C = (char)tolower ((unsigned char)C);
	}
	return R;
}

bool FFCommon::IsProfileValid (const string& ProfileName, const string& ProfilePath)
{
	if (ProfileName.empty () && ProfilePath.empty ())
	{
		return false;
	}

	ifstream In (ProfilesIniPath ().c_str (), ios::in);
	if (!In)
	{
		return false;
	}
	string Line;
	string CurName;
	string CurPath;
	bool IsRel = true;

	auto Flush = [&](bool Final) -> bool
	{
		if (!CurName.empty () && !CurPath.empty ())
		{
			string Abs;
#if FF_WINDOWS
			char Roaming[MAX_PATH] = {0};
			SHGetFolderPathA (nullptr, CSIDL_APPDATA, nullptr, SHGFP_TYPE_CURRENT, Roaming);
			string Base = Roaming;
			if (!Base.empty () && (Base.back () == '\\' || Base.back () == '/'))
			{
				Base.pop_back ();
			}
			Abs = IsRel ? (Base + "\\Mozilla\\Firefox\\" + CurPath) : CurPath;
#else
			const char* Home = getenv ("HOME");
			string Base = (Home && *Home) ? string (Home) : string (".");
			if (!Base.empty () && Base.back () == '/')
			{
				Base.pop_back ();
			}
			Abs = IsRel ? (Base + "/.mozilla/firefox/" + CurPath) : CurPath;
#endif
			if (!ProfileName.empty () && strcasecmp (CurName.c_str (), ProfileName.c_str ()) == 0)
			{
				return true;
			}
			if (!ProfilePath.empty () && NormPath (Abs) == NormPath (ProfilePath))
			{
				return true;
			}
		}
		if (Final)
		{
			return false;
		}
		CurName.clear ();
		CurPath.clear ();
		IsRel = true;
		return false;
	};

	while (getline (In, Line))
	{
		if (!Line.empty () && Line.front () == '[')
		{
			if (Flush (false))
			{
				return true;
			}
			continue;
		}
		if (Line.rfind ("Name=", 0) == 0)
		{
			CurName = Line.substr (5);
		}
		else if (Line.rfind ("Path=", 0) == 0)
		{
			CurPath = Line.substr (5);
		}
		else if (Line.rfind ("IsRelative=", 0) == 0)
		{
			string V = Line.substr (11);
			IsRel = (V == "1");
		}
	}
	return Flush (true);
}

bool FFCommon::MapProfileNameToPath (const string& ProfileName, string& OutPath)
{
	OutPath.clear ();
	if (ProfileName.empty ())
	{
		return false;
	}
	ifstream In (ProfilesIniPath ().c_str (), ios::in);
	if (!In)
	{
		return false;
	}
	string Line;
	string CurName;
	string CurPath;
	bool IsRel = true;

	auto Emit = [&]() -> bool
	{
		if (!CurName.empty () && !CurPath.empty () && strcasecmp (CurName.c_str (), ProfileName.c_str ()) == 0)
		{
#if FF_WINDOWS
			char Roaming[MAX_PATH] = {0};
			SHGetFolderPathA (nullptr, CSIDL_APPDATA, nullptr, SHGFP_TYPE_CURRENT, Roaming);
			string Base = Roaming;
			if (!Base.empty () && (Base.back () == '\\' || Base.back () == '/'))
			{
				Base.pop_back ();
			}
			OutPath = IsRel ? (Base + "\\Mozilla\\Firefox\\" + CurPath) : CurPath;
#else
			const char* Home = getenv ("HOME");
			string Base = (Home && *Home) ? string (Home) : string (".");
			if (!Base.empty () && Base.back () == '/')
			{
				Base.pop_back ();
			}
			OutPath = IsRel ? (Base + "/.mozilla/firefox/" + CurPath) : CurPath;
#endif
			return true;
		}
		return false;
	};

	while (getline (In, Line))
	{
		if (!Line.empty () && Line.front () == '[')
		{
			if (Emit ())
			{
				return true;
			}
			CurName.clear ();
			CurPath.clear ();
			IsRel = true;
			continue;
		}
		if (Line.rfind ("Name=", 0) == 0)
		{
			CurName = Line.substr (5);
		}
		else if (Line.rfind ("Path=", 0) == 0)
		{
			CurPath = Line.substr (5);
		}
		else if (Line.rfind ("IsRelative=", 0) == 0)
		{
			string V = Line.substr (11);
			IsRel = (V == "1");
		}
	}
	return Emit ();
}

bool FFCommon::GetDefaultProfile (string& OutProfileName, string& OutProfilePath)
{
	OutProfileName.clear ();
	OutProfilePath.clear ();

	ifstream In (ProfilesIniPath ().c_str (), ios::in);
	if (!In)
	{
		return false;
	}
	string Line;
	string CurName;
	string CurPath;
	bool IsRel = true;
	bool IsDefault = false;

	auto Emit = [&]() -> bool
	{
		if (!CurName.empty () && !CurPath.empty () && IsDefault)
		{
#if FF_WINDOWS
			char Roaming[MAX_PATH] = {0};
			SHGetFolderPathA (nullptr, CSIDL_APPDATA, nullptr, SHGFP_TYPE_CURRENT, Roaming);
			string Base = Roaming;
			if (!Base.empty () && (Base.back () == '\\' || Base.back () == '/'))
			{
				Base.pop_back ();
			}
			OutProfilePath = IsRel ? (Base + "\\Mozilla\\Firefox\\" + CurPath) : CurPath;
#else
			const char* Home = getenv ("HOME");
			string Base = (Home && *Home) ? string (Home) : string (".");
			if (!Base.empty () && Base.back () == '/')
			{
				Base.pop_back ();
			}
			OutProfilePath = IsRel ? (Base + "/.mozilla/firefox/" + CurPath) : CurPath;
#endif
			OutProfileName = CurName;
			return true;
		}
		return false;
	};

	while (getline (In, Line))
	{
		if (!Line.empty () && Line.front () == '[')
		{
			if (Emit ())
			{
				return true;
			}
			CurName.clear ();
			CurPath.clear ();
			IsRel = true;
			IsDefault = false;
			continue;
		}
		if (Line.rfind ("Name=", 0) == 0)
		{
			CurName = Line.substr (5);
		}
		else if (Line.rfind ("Path=", 0) == 0)
		{
			CurPath = Line.substr (5);
		}
		else if (Line.rfind ("IsRelative=", 0) == 0)
		{
			string V = Line.substr (11);
			IsRel = (V == "1");
		}
		else if (Line.rfind ("Default=", 0) == 0)
		{
			string V = Line.substr (8);
			IsDefault = (V == "1" || V == "true" || V == "True");
		}
	}
	return Emit ();
}

bool FFCommon::ChooseProfileBySystemHeuristics (string& OutProfileName, string& OutProfilePath, string& OutReason)
{
	if (GetLatestProfileFromWatcher (OutProfileName, OutProfilePath))
	{
		OutReason = "Recent profile from watcher stack";
		return true;
	}
	if (GetDefaultProfile (OutProfileName, OutProfilePath))
	{
		OutReason = "Default profile via profiles.ini";
		return true;
	}
	OutReason = "No profile available";
	return false;
}

void FFCommon::ExplainSelection (const string& Where, const string& Reason, const string& Name, const string& Path)
{
	Log (Where, string ("Decision: profile='") + Name + "' path='" + Path + "' reason='" + Reason + "'");
}
