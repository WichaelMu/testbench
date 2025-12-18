#include "Headers/FPlatform.hpp"
#include "Headers/FFCommon.hpp"

#if !FF_WINDOWS
int main() { return 0; }
#else

#include <windows.h>
#include <psapi.h>
#include <string>
#include <fstream>
#include <comdef.h>
#include <Wbemidl.h>
#pragma comment(lib, "wbemuuid.lib")
#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "oleaut32.lib")

using namespace std;

static bool InitWmi(IWbemServices** Out)
{
	*Out = nullptr;

	HRESULT Hr = CoInitializeEx(0, COINIT_MULTITHREADED);
	if (FAILED(Hr) && Hr != RPC_E_CHANGED_MODE)
	{
		return false;
	}

	Hr = CoInitializeSecurity(
		NULL, -1, NULL, NULL,
		RPC_C_AUTHN_LEVEL_DEFAULT,
		RPC_C_IMP_LEVEL_IMPERSONATE,
		NULL, EOAC_NONE, NULL);
	// ignore re-init errors

	IWbemLocator* Locator = nullptr;
	Hr = CoCreateInstance(CLSID_WbemLocator, 0, CLSCTX_INPROC_SERVER, IID_IWbemLocator, (LPVOID*)&Locator);
	if (FAILED(Hr))
	{
		return false;
	}

	IWbemServices* Services = nullptr;
	Hr = Locator->ConnectServer(_bstr_t(L"ROOT\\CIMV2"), NULL, NULL, 0, NULL, 0, 0, &Services);
	Locator->Release();
	if (FAILED(Hr))
	{
		return false;
	}

	Hr = CoSetProxyBlanket(
		Services,
		RPC_C_AUTHN_WINNT,
		RPC_C_AUTHZ_NONE,
		NULL,
		RPC_C_AUTHN_LEVEL_CALL,
		RPC_C_IMP_LEVEL_IMPERSONATE,
		NULL,
		EOAC_NONE);

	if (FAILED(Hr))
	{
		Services->Release();
		return false;
	}
	*Out = Services;
	return true;
}

static bool GetProcessCommandLineWmi(DWORD Pid, string& OutCmd)
{
	OutCmd.clear();

	IWbemServices* Services = nullptr;
	if (!InitWmi(&Services))
	{
		return false;
	}

	wchar_t Query[128];
	swprintf(Query, 128, L"SELECT CommandLine FROM Win32_Process WHERE ProcessId=%u", (unsigned)Pid);

	IEnumWbemClassObject* Enumerator = nullptr;
	HRESULT Hr = Services->ExecQuery(
		bstr_t("WQL"),
		bstr_t(Query),
		WBEM_FLAG_FORWARD_ONLY | WBEM_FLAG_RETURN_IMMEDIATELY,
		NULL,
		&Enumerator);

	if (FAILED(Hr) || !Enumerator)
	{
		Services->Release();
		return false;
	}

	IWbemClassObject* Obj = nullptr;
	ULONG Count = 0;
	Hr = Enumerator->Next(WBEM_INFINITE, 1, &Obj, &Count);
	if (SUCCEEDED(Hr) && Count == 1)
	{
		VARIANT V;
		VariantInit(&V);
		if (SUCCEEDED(Obj->Get(L"CommandLine", 0, &V, 0, 0)) && V.vt == VT_BSTR && V.bstrVal != nullptr)
		{
			_bstr_t B(V.bstrVal);
			wstring Ws((wchar_t*)B);
			int L = WideCharToMultiByte(CP_UTF8, 0, Ws.c_str(), -1, NULL, 0, NULL, NULL);
			string S(L > 0 ? L - 1 : 0, '\0');
			if (L > 1)
			{
				WideCharToMultiByte(CP_UTF8, 0, Ws.c_str(), -1, &S[0], L - 1, NULL, NULL);
			}
			OutCmd = S;
		}
		VariantClear(&V);
		Obj->Release();
	}
	Enumerator->Release();
	Services->Release();
	return !OutCmd.empty();
}

static bool IsFirefoxExe(const string& Exe)
{
	string L = Exe;
	for (char& C : L) { C = (char)tolower((unsigned char)C); }
	return L.find("firefox.exe") != string::npos || L == "firefox";
}

static string ExtractAfterFlag(const string& Cmd, const string& Flag)
{
	size_t P = Cmd.find(Flag);
	if (P == string::npos)
	{
		return string();
	}
	P += Flag.size();
	while (P < Cmd.size() && isspace((unsigned char)Cmd[P])) { ++P; }
	if (P >= Cmd.size())
	{
		return string();
	}
	if (Cmd[P] == '\"')
	{
		size_t Q = Cmd.find('\"', P + 1);
		if (Q == string::npos) { return string(); }
		return Cmd.substr(P + 1, Q - (P + 1));
	}
	size_t Q = Cmd.find_first_of(" \t", P);
	if (Q == string::npos) { Q = Cmd.size(); }
	return Cmd.substr(P, Q - P);
}

static bool ResolveProfileFromCmd(const string& Cmd, string& OutName, string& OutPath)
{
	OutName.clear();
	OutPath.clear();

	string Name = ExtractAfterFlag(Cmd, "-P");
	string Path = ExtractAfterFlag(Cmd, "-profile");
	if (!Name.empty())
	{
		string P;
		if (FFCommon::MapProfileNameToPath(Name, P))
		{
			OutName = Name;
			OutPath = P;
			return true;
		}
		// allow name even if path lookup fails; FF will still try by -P
		OutName = Name;
		return true;
	}
	if (!Path.empty())
	{
		OutPath = Path;
		return true;
	}
	return false;
}

static void WriteFocusJson(const string& Name, const string& Path, DWORD Pid)
{
	FFCommon::EnsureDataRoot();
	string J = string("{\"timestamp\":\"") + NowIso() + "\","
	         + "\"app\":\"Firefox\","
	         + "\"pid\":" + to_string((unsigned)Pid) + ","
	         + "\"profile_name\":\"" + Name + "\","
	         + "\"profile_path\":\"" + Path + "\"}";
	string OutPath = FFCommon::JoinPath(FFCommon::GetDataRoot(), "focus.json");
	ofstream Out(OutPath.c_str(), ios::out | ios::binary | ios::trunc);
	if (Out)
	{
		Out << J;
	}
}

int main()
{
	FFCommon::EnsureDataRoot();
	DWORD SelfPid = GetCurrentProcessId();
	FFCommon::Log("FFFocusTracker", string("WINDOWS -- Starting (PID=") + to_string((unsigned)SelfPid) + ")");

	HWND Last = nullptr;
	string LastName;
	string LastPath;

	while (true)
	{
		Sleep(350);

		HWND H = GetForegroundWindow();
		if (H == nullptr)
		{
			continue;
		}
		if (H == Last)
		{
			continue;
		}

		DWORD Pid = 0;
		GetWindowThreadProcessId(H, &Pid);
		if (Pid == 0 || Pid == SelfPid)
		{
			Last = H;
			continue;
		}

		// Check exe
		HANDLE HP = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, FALSE, Pid);
		if (!HP)
		{
			Last = H;
			continue;
		}

		char ExePath[MAX_PATH] = {0};
		DWORD Size = MAX_PATH;
		string Exe;
		if (QueryFullProcessImageNameA(HP, 0, ExePath, &Size))
		{
			Exe.assign(ExePath, Size);
		}
		CloseHandle(HP);

		if (Exe.empty() || !IsFirefoxExe(Exe))
		{
			Last = H;
			continue;
		}

		// Get command line via WMI
		string Cmd;
		if (!GetProcessCommandLineWmi(Pid, Cmd))
		{
			Last = H;
			continue;
		}

		string Name;
		string Path;
		if (!ResolveProfileFromCmd(Cmd, Name, Path))
		{
			Last = H;
			continue;
		}

		// Update files
		WriteFocusJson(Name, Path, Pid);
		FFCommon::RememberProfileFromWatcher(Name, Path);
		FFCommon::Log("FFFocusTracker", string("Focused profile now: ") + Name + " (" + Path + ")");
		Last = H;
		LastName = Name;
		LastPath = Path;
	}
	return 0;
}
#endif
