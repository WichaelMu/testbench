import sys;

def exec():
    In = input();
    Duplicates = {};
    while (In != 'x'):
        if (In in Duplicates):
            Duplicates[In] = Duplicates[In] + 1;
        else:
            Duplicates[In] = 1;
        In = input();

    print ("----- Printing Duplicates -----");
    for K, V in Duplicates.items():
        if (V > 1):
            print (F"{K} - {V}");

if (__name__ == "__main__"):
    exec();
    sys.exit(0);
