import sys;

__NEXT__ = "x";

def get_spreadsheet():
    Columns = {};
    ColumnNames = [];

    # Initial Input of Column Names.
    In = input("Enter Column Names...\n")

    while (In != __NEXT__):
        if (len (In) == 0):
            print ("Column names cannot be empty!");
            sys.exit(1);
        Columns[In] = [];
        ColumnNames.append (In);

        In = input();
    
    # For each Column, add items...
    for C in ColumnNames:
        In = input (F"Enter values for {C}...\n");
        while (In != __NEXT__):
            Columns[C].append (In);

            In = input();

        print (F"Count of {C}: {len (Columns[C])}");

    Collated = {};

    # Academic Item will always be assumed First.
    IdentifyingColumn = ColumnNames[0];
    for AcademicItem in Columns[IdentifyingColumn]:
        if (AcademicItem not in Collated):
            Collated[AcademicItem] = [];
    
    IntPtr = 0;
    while (IntPtr < len (Columns[IdentifyingColumn])):
        TempCollated = {};
        TAcademicItem = Columns[IdentifyingColumn][IntPtr];
        for N in ColumnNames[1:]:
            TempCollated[N] = Columns[N][IntPtr];
        Collated[TAcademicItem].append (TempCollated);

        IntPtr = IntPtr + 1;

    return Collated;

def exec_comparisons(A, B):
    FailedRows = 0;
    for AK, AV in A.items():
        if (AK not in B):
            print (F"{AK} not in B");
            continue;
        for AD in AV:
            bFoundMatching = True;
            for AK2, AV2 in AD.items():
                for BD in B[AK]:
                    bEqualityEvaluation = AV2 == BD[AK2];
                    bFoundMatching = bFoundMatching and bEqualityEvaluation;
                    # print (F"\t\t{bEqualityEvaluation} | {bFoundMatching} | {AV2} | {BD[AK2]} | {BD} | {AK2} | {B[AK]}");
                    if (not bFoundMatching):
                        FailedRows = FailedRows + 1;
                        print (F"----- Data Validation Failed for: {AK}!\nItems First:  {AD}.\nItems Second: {BD} -----");
            # if (bFoundMatching):
                # print (F"Data Valid on:\n\tA: {AD}\n\tB: {BD}");
                # break;
    print (F"----- {FailedRows} Failed -----");


def exec():
    print ("Entering Spreadsheet Eins...");
    FirstInput  = get_spreadsheet();

    print ("\nEntering Spreadsheet Zwei...");
    SecondInput = get_spreadsheet();

    print ("\n");

    ############################################################################
    # Core Verify Logic...
    exec_comparisons(FirstInput, SecondInput);


if (__name__ == "__main__"):
    exec();
    sys.exit(0);
