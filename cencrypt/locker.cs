using System;
using System.IO;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Runtime.CompilerServices;
using System.Text;

class FileEncryptor
{
    const int SaltSize = 32; // 256-bit
    const int KeySize = 32;  // AES-256
    const int IvSize = 16;   // AES block size
    const int Iterations = 100_000;

    static Dictionary<string, GlobalConfigurationSettings> Settings = new Dictionary<string, GlobalConfigurationSettings>();

    static void Main (string[] args)
    {
	Settings = ParseCommandLineArguments (args);
	
	if (!VerifyCommandLineArguments (Settings))
	{
	    O.Print ("Missing required parameters!");
	    return;
	}

        ECryptMode Mode = Settings["Mode"].GetValue<ECryptMode> ();
        string InputPath = Settings["Inbound"].GetValue<string> ();
        string OutputPath = Settings["Outbound"].GetValue<string> ();
        string Password = Settings["Key"].GetValue<string> ();

        try
        {
	    switch (Mode)
	    {
		case ECryptMode.Encrypt:
		    EncryptFile (InputPath, OutputPath, Password);
		    Console.WriteLine ("Encrypt complete.");
		    break;
		case ECryptMode.Decrypt:
		    DecryptFile (InputPath, OutputPath, Password);
		    Console.WriteLine ("Decrypt complete.");
		    break;
	    }
        }
        catch (Exception ex)
        {
            Console.WriteLine ($"Error during {Mode}.\n\t{ex.Message}");
        }
    }

    static void EncryptFile (string InputPath, string OutputPath, string Password)
    {
        byte[] Salt = RandomBytes (SaltSize);
        byte[] IV = RandomBytes (IvSize);
        byte[] Key = DeriveKey (Password, Salt);

        using (Aes AES = Aes.Create ())
        {
            AES.Key = Key;
            AES.IV = IV;
            AES.Mode = CipherMode.CBC;
            AES.Padding = PaddingMode.PKCS7;

            using (FileStream FSInput = new FileStream (InputPath, FileMode.Open, FileAccess.Read))
            using (FileStream FSOutput = new FileStream (OutputPath, FileMode.Create, FileAccess.Write))
            {
                FSOutput.Write (Salt, 0, Salt.Length);
                FSOutput.Write (IV, 0, IV.Length);

                using (CryptoStream CryptoStream = new CryptoStream (FSOutput, AES.CreateEncryptor (), CryptoStreamMode.Write))
                {
                    FSInput.CopyTo (CryptoStream);
                }
            }
        }
    }

    static void DecryptFile (string InputPath, string OutputPath, string Password)
    {
        using (FileStream FSInput = new FileStream (InputPath, FileMode.Open, FileAccess.Read))
        {
            byte[] Salt = new byte[SaltSize];
            byte[] IV = new byte[IvSize];
            FSInput.Read (Salt, 0, SaltSize);
            FSInput.Read (IV, 0, IvSize);

            byte[] Key = DeriveKey (Password, Salt);

            using (Aes AES = Aes.Create ())
            {
                AES.Key = Key;
                AES.IV = IV;
                AES.Mode = CipherMode.CBC;
                AES.Padding = PaddingMode.PKCS7;

                using (CryptoStream CryptoStream = new CryptoStream (FSInput, AES.CreateDecryptor (), CryptoStreamMode.Read))
                using (FileStream FSOutput = new FileStream (OutputPath, FileMode.Create, FileAccess.Write))
                {
                    CryptoStream.CopyTo (FSOutput);
                }
            }
        }
    }

    static byte[] DeriveKey (string Password, byte[] Salt)
    {
        using (Rfc2898DeriveBytes kdf = new Rfc2898DeriveBytes (Password, Salt, Iterations, HashAlgorithmName.SHA256))
        {
            return kdf.GetBytes (KeySize);
        }
    }

    static byte[] RandomBytes (int size)
    {
        byte[] Bytes = new byte[size];
        using (RandomNumberGenerator RNG = RandomNumberGenerator.Create ())
        {
            RNG.GetBytes (Bytes);
        }
        return Bytes;
    }
    
    static Dictionary<string, GlobalConfigurationSettings> ParseCommandLineArguments(params string[] ArgV)
    {
	Dictionary<string, GlobalConfigurationSettings> UserProvidedConfiguration = new Dictionary<string, GlobalConfigurationSettings>();

	Upsert (ref UserProvidedConfiguration, "Outbound", new GlobalConfigurationSettings ("OutResult"));

	int Iterator = 1;
	int ArgC = ArgV.Length;
	while (Iterator < ArgC)
	{
	    switch (ArgV[Iterator])
	    {
	    	case "--encrypt":
		    Iterator += 1;
		    
		    Upsert (ref UserProvidedConfiguration, "Mode", new GlobalConfigurationSettings (ECryptMode.Encrypt));
		    break;

	    	case "--decrypt":
		    Iterator += 1;
		    
		    Upsert (ref UserProvidedConfiguration, "Mode", new GlobalConfigurationSettings (ECryptMode.Decrypt));
		    break;

		case "--inbound":
		    Iterator += 1;
		    
		    if (!(Iterator < ArgC))
		    {
			O.Print ("Option --inbound requires one argument!", ConsoleColor.Red);
			break;
		    }

		    Upsert (ref UserProvidedConfiguration, "Inbound", new GlobalConfigurationSettings (ArgV[Iterator]));

		    Iterator += 1;
		    break;

		case "--outbound":
		    Iterator += 1;
		    
		    if (!(Iterator < ArgC))
		    {
			O.Print ("Option --outbound requires one argument!", ConsoleColor.Red);
			break;
		    }

		    Upsert (ref UserProvidedConfiguration, "Outbound", new GlobalConfigurationSettings (ArgV[Iterator]));

		    Iterator += 1;
		    break;

		case "--key":
		    Iterator += 1;
		    
		    if (!(Iterator < ArgC))
		    {
			O.Print ("Option --key requires one argument!", ConsoleColor.Red);
			break;
		    }

		    Upsert (ref UserProvidedConfiguration, "Key", new GlobalConfigurationSettings (ArgV[Iterator]));

		    Iterator += 1;
		    break;
	    }
	}

	return UserProvidedConfiguration;
    }
    
    static void Upsert(ref Dictionary<string, GlobalConfigurationSettings> UserProvidedConfiguration, string Option, GlobalConfigurationSettings Value)
    {
	if (UserProvidedConfiguration.ContainsKey (Option))
	    UserProvidedConfiguration[Option] = Value;
	else
	    UserProvidedConfiguration.Add(Option, Value);
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    static bool VerifyCommandLineArguments (Dictionary<string, GlobalConfigurationSettings> Check)
    {
	if (!Check.ContainsKey ("Mode"))
	    O.Print ("Missing Mode");
	if (!Check.ContainsKey ("Inbound"))
	    O.Print ("Missing Inbound");
	if (!Check.ContainsKey ("Key"))
	    O.Print ("Missing Key");
	return false;
    }
}

enum ECryptMode
{
    None,
    Encrypt,
    Decrypt
}

public struct GlobalConfigurationSettings
{
    public Type T;
    public object Value;

    public GlobalConfigurationSettings (object Value) : this ()
    {
	this.Value = Value;
	T = Value.GetType ();
    }
    
    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public R GetValue<R>()
    {
	if (Value.TryCast<R> (out R Casted))
	    return Casted;
	return default (R);
    }
}

public static class ObjectExtensions
{
    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static bool Is<T>(this object O) => O is T || O.GetType() == typeof(T);
    
    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static bool Is<T>(this object O, out T Casted)
    {
	Casted = O.Cast<T>();
	return Casted != null;
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static bool TryCast<T>(this object O, out T Casted) => O.Is<T>(out Casted);

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static object Cast(this object O, Type Type) => Convert.ChangeType(O, Type);

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static T Cast<T>(this object O)
    {
	return O is T R
	    ? R
	    : (T)Convert.ChangeType(O, typeof(T));
    }
}

public static class O
{
    public static void Print (string Content, ConsoleColor FColour = ConsoleColor.Gray, ConsoleColor BColour = ConsoleColor.Black)
    {
	SetColours (FColour, BColour);
	Console.WriteLine (Content);
	ResetColours ();
    }
    
    public static void SetColours (ConsoleColor FColour, ConsoleColor BColour = ConsoleColor.Black)
    {
	Console.ForegroundColor = FColour;
	Console.BackgroundColor = BColour;
    }
    
    public static void ResetColours()
    {
	SetColours (ConsoleColor.Gray);
    }
    
    [MethodImpl (MethodImplOptions.AggressiveInlining)]
    public static bool FileExists (string Path, string NameOfFile)
    {
	return File.Exists (Path + NameOfFile);
    }
}

public enum EWriteMode
{
    Append,
    Overwrite
}
