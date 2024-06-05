

def exec():
    FirstColumnName = input ("Name of first Column");
    SecondColumnName = input ("Name of second Column");

    InLArray = [];
    InRArray = [];

    print (F"{FirstColumnName}...");
    FirstInput = input();
    while FirstInput != 'x':
        InLArray.append(FirstInput);
        FirstInput = input();

    print (F"Len (InLArray): {len (InLArray)}");
    print (F"{SecondColumnName}...");
    SecondInput = input()
    while SecondInput != 'x':
        InRArray.append(SecondInput);
        SecondInput = input();
    
    print (F"L: {len (InLArray)}, R: {len (InRArray)}");
    NotL = 0;
    for L in InLArray:
        if L not in InRArray:
            print (F"{L} is not in {SecondColumnName}");
            NotL = NotL + 1;

    NotR = 0;
    for R in InRArray:
        if R not in InLArray:
            print (F"{R} is not in {FirstColumnName}");
            NotR = NotR + 1;

    print (F"Deltas:\n\t{FirstColumnName} not in {SecondColumnName}: {NotL}\n\t{SecondColumnName} not in {FirstColumnName}: {NotR}");

if (__name__ == "__main__"):
    exec();
    print (F"{__name__} TERMINATES HERE");
