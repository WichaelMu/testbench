import sys;

def exec():
    ArgV = sys.argv;

    if (len (ArgV) == 1):
        print ("Specify a Maximum-bound Column.");
        sys.exit(1);

    Suffix = "";
    if (len (ArgV) == 3):
        Suffix = ArgV[2];

    To = sys.argv[1].lower();

    Difference = ord (To) - ord ('a') + 1;

    i = 1;
    while (i <= Difference):
        CL = F"CourseLoopReport{Suffix}";
        DL = F"DataLoad{Suffix}";
        VLK = F"VLOOKUP({CL}!$A2, {DL}!$A:${To.upper()}, {i}, FALSE)";
        Test = F"{CL}!{chr(i - 1 + ord('A'))}2";

        print (F'=IF({VLK}={Test}, {Test}, "V1: "&{Test}&" | V2: "&{VLK})');
        i = i + 1;

if (__name__ == "__main__"):
    exec();
    sys.exit(0);
