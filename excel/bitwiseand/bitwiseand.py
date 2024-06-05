import sys;

def exec():
    FirstColumnName = input ("First Column Name: ");
    SecondColumnName = input ("Second Column Name: ");

    F = {};
    S = {};

    RetVal = [];

    In = input (F"{FirstColumnName}...");
    while (In != 'x'):
        if (In not in F):
            F[In] = 1;
        else:
            F[In] = F[In] + 1;
        In = input ();

    In = input(F"{SecondColumnName}...");
    while (In != 'x'):
        if (In not in S):
            S[In] = 1;
        else:
            S[In] = S[In] + 1;
        In = input ();

    print ("----- Printing AND -----");
    for K, V in F.items():
        if (K in S):
            print (K);

if (__name__ == "__main__"):
    exec();
    sys.exit(0);
