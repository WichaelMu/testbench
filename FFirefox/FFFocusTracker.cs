// FFFocusTracker.cs
// Tracks last focused Firefox profile and writes it to state/logs.
// WINDOWS: WinEvent hook on foreground window (MozillaWindowClass)
// LINUX:   Polls X11 _NET_ACTIVE_WINDOW and _NET_WM_PID.

using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;

#if WINDOWS
using System.Runtime.InteropServices;
using System.Windows.Forms;
using Microsoft.Win32;
#elif LINUX
using System.Runtime.InteropServices;
#endif

class FFocusTracker
{
    private static Mutex SingleInstanceMutex;

#if WINDOWS
    // WinEvent hook
    private delegate void FWinEventDelegate(
        IntPtr Hook,
        uint EventType,
        IntPtr WindowHandle,
        int ObjectId,
        int ChildId,
        uint ThreadId,
        uint EventTimeMs);

    [DllImport("user32.dll")]
    private static extern IntPtr SetWinEventHook(
        uint EventMin,
        uint EventMax,
        IntPtr ModuleHandle,
        FWinEventDelegate Callback,
        uint ProcessId,
        uint ThreadId,
        uint Flags);

    [DllImport("user32.dll")] private static extern bool UnhookWinEvent(IntPtr Hook);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr WindowHandle);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetClassName(IntPtr WindowHandle, StringBuilder ClassNameBuilder, int MaxCount);
    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr WindowHandle, out uint ProcessId);

    private const uint EventSystemForeground = 0x0003;
    private const uint WinEventOutOfContext  = 0x0000;

    private static IntPtr ForegroundHookHandle;
    private static FWinEventDelegate ForegroundHookProc = new FWinEventDelegate(WinEventCallback);
#elif LINUX
    [DllImport("libX11.so.6")] private static extern IntPtr XOpenDisplay(IntPtr Display);
    [DllImport("libX11.so.6")] private static extern IntPtr XDefaultRootWindow(IntPtr Display);
    [DllImport("libX11.so.6")] private static extern IntPtr XInternAtom(IntPtr Display, string Name, bool OnlyIfExists);
    [DllImport("libX11.so.6")] private static extern int XGetWindowProperty(
        IntPtr Display, IntPtr Window, IntPtr Property,
        IntPtr LongOffset, IntPtr LongLength, bool Delete,
        IntPtr ReqType, out IntPtr ActualType, out int ActualFormat,
        out IntPtr NItems, out IntPtr BytesAfter, out IntPtr PropReturn);
    [DllImport("libX11.so.6")] private static extern int XFree(IntPtr Data);
#endif

    static void Main()
    {
        bool bCreated;
        SingleInstanceMutex = new Mutex(true, @"Local\FFFocusTracker_SingleInstance", out bCreated);
        if (!bCreated)
        {
#if WINDOWS
            MessageBox.Show("Tracker is already running.", "FF", MessageBoxButtons.OK, MessageBoxIcon.Information);
#endif
            return;
        }

        FLog.RotateForNewSession();
        FLog.Write("Tracker", "Starting (PID " + Process.GetCurrentProcess().Id + ")");
        FLog.Write("Tracker", "Logs: current=" + FAppPaths.LogCurrent + " prev=" + FAppPaths.LogPrev);

#if WINDOWS
        SystemEvents.SessionEnding += (object Sender, SessionEndingEventArgs Args) =>
        {
            FLog.Write("Tracker", "SessionEnding: " + Args.Reason);
        };
        SystemEvents.PowerModeChanged += (object Sender, PowerModeChangedEventArgs Args) =>
        {
            if (Args.Mode == PowerModes.Suspend) { FLog.Write("Tracker", "Power: Suspend"); }
            if (Args.Mode == PowerModes.Resume)  { FLog.Write("Tracker", "Power: Resume"); }
        };

        ForegroundHookHandle = SetWinEventHook(
            EventSystemForeground, EventSystemForeground, IntPtr.Zero,
            ForegroundHookProc, 0, 0, WinEventOutOfContext);

        AppDomain.CurrentDomain.ProcessExit += (object Sender, EventArgs Args) =>
        {
            FLog.Write("Tracker", "ProcessExit");
            try { if (ForegroundHookHandle != IntPtr.Zero) { UnhookWinEvent(ForegroundHookHandle); } } catch {}
            try { SingleInstanceMutex.ReleaseMutex(); } catch {}
        };

        Thread.Sleep(Timeout.Infinite);

#elif LINUX
        IntPtr X11Display = XOpenDisplay(IntPtr.Zero);
        if (X11Display == IntPtr.Zero)
        {
            FLog.Write("Tracker", "XOpenDisplay failed; idle");
            Thread.Sleep(Timeout.Infinite);
            return;
        }

        IntPtr X11RootWindow = XDefaultRootWindow(X11Display);
        IntPtr X11AtomActiveWindow = XInternAtom(X11Display, "_NET_ACTIVE_WINDOW", true);
        IntPtr X11AtomWmPid        = XInternAtom(X11Display, "_NET_WM_PID", true);

        int LastObservedPid = -1;

        while (true)
        {
            try
            {
                IntPtr ActiveWindow = GetActiveWindow(X11Display, X11RootWindow, X11AtomActiveWindow);
                if (ActiveWindow != IntPtr.Zero)
                {
                    int WindowPid = GetWindowPid(X11Display, ActiveWindow, X11AtomWmPid);
                    if (WindowPid > 0 && WindowPid != LastObservedPid)
                    {
                        LastObservedPid = WindowPid;

                        // Only keep if firefox
                        string Comm = SafeRead("/proc/" + WindowPid.ToString() + "/comm");
                        if (Comm != null && Comm.Trim().StartsWith("firefox", StringComparison.OrdinalIgnoreCase))
                        {
                            string ProfileName = FFirefoxPlatform.ProfileNameFromPidLinux(WindowPid);
                            if (!string.IsNullOrEmpty(ProfileName))
                            {
                                FState.SetLastProfile(ProfileName);
                                FLog.Write("Tracker", "Focused profile = " + ProfileName + " (PID " + WindowPid + ")");
                            }
                        }
                    }
                }
            }
            catch {}
            Thread.Sleep(250);
        }
#endif
    }

#if WINDOWS
    private static void WinEventCallback(
        IntPtr Hook,
        uint EventType,
        IntPtr WindowHandle,
        int ObjectId,
        int ChildId,
        uint ThreadId,
        uint EventTimeMs)
    {
        if (WindowHandle == IntPtr.Zero) { return; }
        if (!IsWindowVisible(WindowHandle)) { return; }

        StringBuilder WindowClassBuilder = new StringBuilder(256);
        GetClassName(WindowHandle, WindowClassBuilder, WindowClassBuilder.Capacity);
        if (!string.Equals(WindowClassBuilder.ToString(), "MozillaWindowClass", StringComparison.Ordinal))
        {
            return;
        }

        uint FirefoxPidU;
        GetWindowThreadProcessId(WindowHandle, out FirefoxPidU);
        if (FirefoxPidU == 0) { return; }

        string ProfileName = FFirefoxPlatform.ProfileNameFromPidWindows((int)FirefoxPidU);
        if (string.IsNullOrEmpty(ProfileName)) { return; }

        FState.SetLastProfile(ProfileName);
        FLog.Write("Tracker", "Focused profile = " + ProfileName + " (PID " + FirefoxPidU + ")");
    }
#endif

#if LINUX
    private static IntPtr GetActiveWindow(IntPtr Display, IntPtr RootWindow, IntPtr AtomActive)
    {
        if (AtomActive == IntPtr.Zero) { return IntPtr.Zero; }

        IntPtr ActualType;
        int ActualFormat;
        IntPtr ItemsCount;
        IntPtr BytesAfter;
        IntPtr PropertyData;

        int Result = XGetWindowProperty(
            Display, RootWindow, AtomActive,
            (IntPtr)0, (IntPtr)1024, false, (IntPtr)0,
            out ActualType, out ActualFormat, out ItemsCount, out BytesAfter, out PropertyData);

        if (Result != 0 || PropertyData == IntPtr.Zero) { return IntPtr.Zero; }

        try { return System.Runtime.InteropServices.Marshal.ReadIntPtr(PropertyData); }
        finally { XFree(PropertyData); }
    }

    private static int GetWindowPid(IntPtr Display, IntPtr Window, IntPtr AtomPid)
    {
        if (AtomPid == IntPtr.Zero) { return -1; }

        IntPtr ActualType;
        int ActualFormat;
        IntPtr ItemsCount;
        IntPtr BytesAfter;
        IntPtr PropertyData;

        int Result = XGetWindowProperty(
            Display, Window, AtomPid,
            (IntPtr)0, (IntPtr)1024, false, (IntPtr)0,
            out ActualType, out ActualFormat, out ItemsCount, out BytesAfter, out PropertyData);

        if (Result != 0 || PropertyData == IntPtr.Zero) { return -1; }

        try { return System.Runtime.InteropServices.Marshal.ReadInt32(PropertyData); }
        finally { XFree(PropertyData); }
    }

    private static string SafeRead(string AbsolutePath)
    {
        try { return File.ReadAllText(AbsolutePath); } catch { return null; }
    }
#endif
}
