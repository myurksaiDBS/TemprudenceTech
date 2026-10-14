// Temprudence Technologies - Windows Inventory Scanner launcher.
// Build: mcs -sdk:4.5 -target:exe -platform:anycpu -out:../assets/TemprudenceScanner.exe TemprudenceScanner.cs
// The console appends "##TTCFG##" + key=value lines to the end of this binary at download time.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Security.Principal;
using System.Text;

[assembly: AssemblyTitle("Temprudence Inventory Scanner")]
[assembly: AssemblyCompany("Temprudence Technologies - A Division of YFI Enterprises, LLC")]
[assembly: AssemblyProduct("Temprudence Inventory Scanner")]
[assembly: AssemblyVersion("1.1.0.0")]

class TemprudenceScanner
{
    static Dictionary<string, string> ReadConfig(string path)
    {
        var cfg = new Dictionary<string, string>();
        byte[] me = File.ReadAllBytes(path);
        byte[] marker = Encoding.ASCII.GetBytes("##TTCFG##");
        int found = -1;
        for (int i = me.Length - marker.Length; i >= 0 && i > me.Length - 8192; i--)
        {
            bool ok = true;
            for (int j = 0; j < marker.Length; j++) { if (me[i + j] != marker[j]) { ok = false; break; } }
            if (ok) { found = i; break; }
        }
        if (found < 0) return cfg;
        string text = Encoding.UTF8.GetString(me, found + marker.Length, me.Length - found - marker.Length);
        foreach (string line in text.Split('\n'))
        {
            int eq = line.IndexOf('=');
            if (eq > 0) cfg[line.Substring(0, eq).Trim()] = line.Substring(eq + 1).Trim();
        }
        return cfg;
    }

    static bool IsAdmin()
    {
        return new WindowsPrincipal(WindowsIdentity.GetCurrent()).IsInRole(WindowsBuiltInRole.Administrator);
    }

    static void Pause()
    {
        Console.WriteLine();
        Console.WriteLine("  Press Enter to close this window.");
        Console.ReadLine();
    }

    static int Main(string[] args)
    {
        string self = Assembly.GetExecutingAssembly().Location;
        Console.Title = "Temprudence Technologies - Inventory Scanner";
        if (!IsAdmin())
        {
            try
            {
                var psi = new ProcessStartInfo(self) { UseShellExecute = true, Verb = "runas" };
                Process.Start(psi);
                return 0;
            }
            catch (Exception)
            {
                Console.WriteLine("  Administrator approval was declined. Running a limited scan instead.");
            }
        }
        var cfg = ReadConfig(self);
        if (!cfg.ContainsKey("url") || !cfg.ContainsKey("key"))
        {
            Console.WriteLine("  This scanner has no console configuration. Download it again from the Temprudence console.");
            Pause();
            return 2;
        }
        string schedule = cfg.ContainsKey("schedule") && cfg["schedule"] == "1" ? "$env:TT_SCHEDULE='1'; " : "";
        string cmd = schedule + "[Net.ServicePointManager]::SecurityProtocol='Tls12'; iex (irm '" + cfg["url"] + "/api/scanner/script.ps1?k=" + cfg["key"] + "')";
        string enc = Convert.ToBase64String(Encoding.Unicode.GetBytes(cmd));
        var p = new ProcessStartInfo("powershell.exe", "-NoProfile -ExecutionPolicy Bypass -EncodedCommand " + enc) { UseShellExecute = false };
        try
        {
            var proc = Process.Start(p);
            proc.WaitForExit();
            Pause();
            return proc.ExitCode;
        }
        catch (Exception e)
        {
            Console.WriteLine("  Could not start PowerShell: " + e.Message);
            Pause();
            return 1;
        }
    }
}
