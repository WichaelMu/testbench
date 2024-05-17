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
    Dupes = 0;
    Rows = 0;
    for K, V in Duplicates.items():
        if (V > 1):
            print (F"{K} - {V}");
            Dupes = Dupes + 1;
            Rows = Rows + V - 1;

    print ("----- Printing Results -----");
    print (F"\tThere are {Dupes} duplicates.");
    print (F"\tAccounting for {Rows} rows.");

if (__name__ == "__main__"):
    exec();
    sys.exit(0);
