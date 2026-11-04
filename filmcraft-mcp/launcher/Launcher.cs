// Lanceur FilmCraft pour Claude Code.
// Démarre FilmCraft avec le canal de contrôle (127.0.0.1:9876) et le jeton partagé avec
// le MCP « filmcraft ». Si FilmCraft tourne déjà, ouvre les fichiers donnés dans l'instance
// existante et la met au premier plan.
// Compilation : build.ps1 (csc .NET Framework 4, C# 5).
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Windows.Forms;

static class Launcher
{
    const int Port = 9876;
    const int TokenHexLength = 64;
    const int ConnectTimeoutMs = 400;
    const int ReplyTimeoutMs = 15000;

    [STAThread]
    static int Main(string[] args)
    {
        try
        {
            string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string exe = Path.Combine(local, @"Programs\FilmCraft\filmcraft.exe");
            if (!File.Exists(exe))
            {
                return Fail("FilmCraft est introuvable :\n" + exe + "\n\nRéinstalle-le avec filmcraft-mcp\\install.ps1.");
            }
            string token = EnsureToken(Path.Combine(local, @"FilmCraft-Claude\control.token"));
            if (IsListening())
            {
                SendToRunningApp(token, args);
                return 0;
            }
            StartApp(exe, token, args);
            return 0;
        }
        catch (Exception e)
        {
            return Fail(e.Message);
        }
    }

    static void StartApp(string exe, string token, string[] files)
    {
        var parts = new List<string> { "--control", Port.ToString() };
        foreach (string f in files)
        {
            parts.Add(Quote(Path.GetFullPath(f)));
        }
        var psi = new ProcessStartInfo(exe, string.Join(" ", parts.ToArray()));
        psi.UseShellExecute = false;
        psi.WorkingDirectory = Path.GetDirectoryName(exe);
        psi.EnvironmentVariables["FILMCRAFT_CONTROL_TOKEN"] = token;
        Process.Start(psi);
    }

    // Lit le jeton existant ou en crée un (32 octets aléatoires en hexadécimal),
    // dans un fichier lisible uniquement par l'utilisateur courant.
    static string EnsureToken(string path)
    {
        if (File.Exists(path))
        {
            string existing = File.ReadAllText(path).Trim();
            if (IsHexToken(existing))
            {
                return existing;
            }
        }
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        var bytes = new byte[TokenHexLength / 2];
        using (var rng = new RNGCryptoServiceProvider())
        {
            rng.GetBytes(bytes);
        }
        var sb = new StringBuilder(TokenHexLength);
        foreach (byte b in bytes)
        {
            sb.Append(b.ToString("x2"));
        }
        string token = sb.ToString();
        File.WriteAllText(path, token, new UTF8Encoding(false));
        RestrictToCurrentUser(path);
        return token;
    }

    static bool IsHexToken(string s)
    {
        if (s.Length != TokenHexLength) return false;
        foreach (char c in s)
        {
            if (!Uri.IsHexDigit(c)) return false;
        }
        return true;
    }

    static void RestrictToCurrentUser(string path)
    {
        var security = new FileSecurity();
        security.SetAccessRuleProtection(true, false);
        security.AddAccessRule(new FileSystemAccessRule(
            WindowsIdentity.GetCurrent().User, FileSystemRights.FullControl, AccessControlType.Allow));
        File.SetAccessControl(path, security);
    }

    static bool IsListening()
    {
        using (var client = new TcpClient())
        {
            try
            {
                IAsyncResult ar = client.BeginConnect("127.0.0.1", Port, null, null);
                bool ok = ar.AsyncWaitHandle.WaitOne(ConnectTimeoutMs) && client.Connected;
                if (ok) client.EndConnect(ar);
                return ok;
            }
            catch (SocketException)
            {
                return false;
            }
        }
    }

    // FilmCraft tourne déjà : ouvre le projet (.fcproj) ou importe les médias, puis focus.
    static void SendToRunningApp(string token, string[] files)
    {
        var requests = new List<string>();
        var media = new List<string>();
        foreach (string f in files)
        {
            string full = Path.GetFullPath(f);
            if (full.EndsWith(".fcproj", StringComparison.OrdinalIgnoreCase))
            {
                requests.Add(Execute("file.open", "{\"path\":" + Json(full) + "}"));
            }
            else
            {
                media.Add(Json(full));
            }
        }
        if (media.Count > 0)
        {
            requests.Add(Execute("file.import", "{\"paths\":[" + string.Join(",", media.ToArray()) + "]}"));
        }
        requests.Add("\"method\":\"ui.focus\",\"params\":{}");

        using (var client = new TcpClient("127.0.0.1", Port))
        using (NetworkStream stream = client.GetStream())
        {
            stream.ReadTimeout = ReplyTimeoutMs;
            var writer = new StreamWriter(stream, new UTF8Encoding(false));
            var reader = new StreamReader(stream, Encoding.UTF8);
            int id = 1;
            foreach (string body in requests)
            {
                writer.Write("{\"id\":" + id++ + ",\"token\":" + Json(token) + "," + body + "}\n");
                writer.Flush();
                string reply = reader.ReadLine() ?? "";
                if (reply.Contains("\"ok\":false"))
                {
                    MessageBox.Show(reply, "FilmCraft", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                }
            }
        }
    }

    static string Execute(string command, string paramsJson)
    {
        return "\"method\":\"engine.execute\",\"params\":{\"command\":" + Json(command) + ",\"params\":" + paramsJson + "}";
    }

    static string Json(string s)
    {
        var sb = new StringBuilder("\"");
        foreach (char c in s)
        {
            switch (c)
            {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                default:
                    if (c < ' ') sb.Append("\\u" + ((int)c).ToString("x4"));
                    else sb.Append(c);
                    break;
            }
        }
        return sb.Append('"').ToString();
    }

    // Règles de CommandLineToArgvW : doubler les antislashs qui précèdent un guillemet ou la fin
    // (sinon "C:\dossier\" avalerait les arguments suivants).
    static string Quote(string arg)
    {
        var sb = new StringBuilder("\"");
        int backslashes = 0;
        foreach (char c in arg)
        {
            if (c == '\\')
            {
                backslashes++;
                continue;
            }
            sb.Append('\\', c == '"' ? backslashes * 2 + 1 : backslashes);
            sb.Append(c);
            backslashes = 0;
        }
        sb.Append('\\', backslashes * 2);
        return sb.Append('"').ToString();
    }

    static int Fail(string message)
    {
        MessageBox.Show(message, "Lanceur FilmCraft", MessageBoxButtons.OK, MessageBoxIcon.Error);
        return 1;
    }
}
