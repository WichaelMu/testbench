#include "Headers/FFCommon.hpp"
#include "Headers/FFFocusTracker.hpp"
#include <string>
#include <vector>
#include <thread>
#include <chrono>

#if FF_WINDOWS
    #include <windows.h>
    #include <psapi.h>
    #include <wbemidl.h>
#else
    #include <X11/Xlib.h>
    #include <X11/Xatom.h>
    #include <unistd.h>
#endif

using namespace std;

namespace
{
#if FF_WINDOWS
    static int GetForegroundFirefoxPid()
    {
        HWND H = GetForegroundWindow();
        if (H == nullptr)
        {
            return 0;
        }
        DWORD Pid = 0;
        GetWindowThreadProcessId(H, &Pid);
        if (Pid == 0)
        {
            return 0;
        }

        // Confirm process name is firefox.exe
        HANDLE Proc = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, FALSE, Pid);
        if (Proc == nullptr)
        {
            return static_cast<int>(Pid);
        }

        char Name[260] = {0};
        if (GetModuleBaseNameA(Proc, nullptr, Name, 259) > 0)
        {
            std::string S(Name);
            std::transform(S.begin(), S.end(), S.begin(), ::tolower);
            if (S != "firefox.exe")
            {
                CloseHandle(Proc);
                return 0;
            }
        }
        CloseHandle(Proc);
        return static_cast<int>(Pid);
    }
#else
    static int GetActiveWindowPidX11()
    {
        const char* DisplayName = getenv("DISPLAY");
        if (DisplayName == nullptr || *DisplayName == '\0')
        {
            return 0;
        }

        Display* Dpy = XOpenDisplay(nullptr);
        if (Dpy == nullptr)
        {
            return 0;
        }

        Atom NetActive = XInternAtom(Dpy, "_NET_ACTIVE_WINDOW", True);
        Atom NetWmPid  = XInternAtom(Dpy, "_NET_WM_PID", True);

        if (NetActive == None || NetWmPid == None)
        {
            XCloseDisplay(Dpy);
            return 0;
        }

        Atom Type;
        int Format;
        unsigned long NItems;
        unsigned long BytesAfter;
        unsigned char* Prop = nullptr;
        Window Root = DefaultRootWindow(Dpy);

        int Pid = 0;

        if (XGetWindowProperty(Dpy, Root, NetActive, 0, (~0L), False, AnyPropertyType,
                               &Type, &Format, &NItems, &BytesAfter, &Prop) == Success && Prop != nullptr)
        {
            Window Win = *(Window*)Prop;
            XFree(Prop);
            Prop = nullptr;

            if (Win != None)
            {
                if (XGetWindowProperty(Dpy, Win, NetWmPid, 0, 1, False, AnyPropertyType,
                                       &Type, &Format, &NItems, &BytesAfter, &Prop) == Success && Prop != nullptr)
                {
                    if (Format == 32 && NItems == 1)
                    {
                        Pid = *(int*)Prop;
                    }
                    XFree(Prop);
                    Prop = nullptr;
                }
            }
        }

        XCloseDisplay(Dpy);
        return Pid;
    }
#endif

    static std::string ProfileFromPid(int Pid)
    {
        if (Pid <= 0)
        {
            return std::string();
        }

        std::string Cmd = FFCommon::GetProcessCommandLineByPid(Pid);
        if (Cmd.empty())
        {
            // Fallback: enumerate firefox processes and match by pid
            std::vector<FirefoxProc> L = FFCommon::ListRunningFirefox();
            size_t I = 0;
            while (I < L.size())
            {
                if (L[I].Pid == Pid)
                {
                    Cmd = L[I].CmdLine;
                    break;
                }
                ++I;
            }
        }

        if (Cmd.empty())
        {
            return std::string();
        }

        std::string Name = FFCommon::ExtractProfileFromCmdline(Cmd);
        if (!Name.empty())
        {
            return Name;
        }

        std::string PPath = FFCommon::ExtractProfilePathFromCmdline(Cmd);
        if (!PPath.empty())
        {
            return FFCommon::MapPathToProfileName(PPath);
        }

        return std::string();
    }
}

int RunFocusTracker()
{
    if (!FFCommon::InitPaths())
    {
        return 2;
    }

#if FF_WINDOWS
    int PidSelf = static_cast<int>(GetCurrentProcessId());
    std::string Disp = "<n/a>";
    std::string WDisp = "<n/a>";
    std::string Sess = "WINDOWS";
#else
    int PidSelf = static_cast<int>(getpid());
    const char* D = getenv("DISPLAY");
    const char* W = getenv("WAYLAND_DISPLAY");
    const char* T = getenv("XDG_SESSION_TYPE");
    std::string Disp = D ? D : "<null>";
    std::string WDisp = W ? W : "<null>";
    std::string Sess = T ? T : "<null>";
#endif

    FFCommon::Log("FFFocusTracker", "Starting (PID=" + std::to_string(PidSelf) +
                                    ") DISPLAY=" + Disp + " WAYLAND_DISPLAY=" + WDisp +
                                    " XDG_SESSION_TYPE=" + Sess);

    std::string LastSent;

    while (true)
    {
        try
        {
#if FF_WINDOWS
            int Pid = GetForegroundFirefoxPid();
#else
            int Pid = GetActiveWindowPidX11();
#endif
            if (Pid > 0)
            {
                std::string Prof = ProfileFromPid(Pid);
                if (!Prof.empty())
                {
                    if (LastSent != Prof)
                    {
                        FFCommon::WriteLastFocused(Prof);
                        FFCommon::Log("FFFocusTracker", "Focused profile now: " + Prof);
                        LastSent = Prof;
                    }
                }
            }
            else
            {
                // On Wayland without X11, this will be zero; fallback guesses are done by router.
            }
        }
        catch (...)
        {
            FFCommon::LogError("FFFocusTracker", "Loop exception.");
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(400));
    }

    return 0;
}

int main(int Argc, char** Argv)
{
    (void)Argc; (void)Argv;
    return RunFocusTracker();
}
