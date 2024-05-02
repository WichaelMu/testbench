import os;
import sys;
import subprocess as zsh;

def exec():
    argv = " ".join(sys.argv);
    print();

    DiffStr = argv;
    
    IntPtr = 0;
    FNames = "";
    for t in DiffStr.split('|'):
        t_FName = F"{str (IntPtr)}.descdiff";

        f = open (F"{t_FName}", "w");
        f.write (t);
        f.close ();

        IntPtr = IntPtr + 1;
        FNames = F"{FNames} {t_FName}";

if (__name__ == "__main__"):
    exec();
    print (F"{__name__} TERMINATES HERE.");
