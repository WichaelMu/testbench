

def exec():
    InLArray = [];
    InRArray = [];

    print ("First...");
    FirstInput = input();
    while FirstInput != 'x':
        InLArray.append(FirstInput);
        FirstInput = input();

    print (F"Len (InLArray): {len (InLArray)}");
    print ("Second...");
    SecondInput = input()
    while SecondInput != 'x':
        InRArray.append(SecondInput);
        SecondInput = input();
    
    print (F"L: {len (InLArray)}, R: {len (InRArray)}");
    for L in InLArray:
        if L not in InRArray:
            print (F"{L} is not in SecondInput");

    for R in InRArray:
        if R not in InLArray:
            print (F"{R} is not in FirstInput");

if (__name__ == "__main__"):
    exec();
    print (F"{__name__} TERMINATES HERE");
