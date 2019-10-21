using System;
using System.Diagnostics;
using System.IO;

namespace SendToFtrackConnect
{
    class Program
    {
        static void Main(string[] args)
        {
            string sourceDir = Path.Combine(AppContext.BaseDirectory, "ftrack-connect");
            string targetDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "AppData\\Local\\ftrack\\ftrack-connect-plugins");


            // Quit ftrack
            bool error = false;
            string ftrackPath = "";
            Process[] processes = Process.GetProcessesByName("ftrack_connect_package");
            foreach (Process proc in processes)
            {
                try
                {
                    Console.WriteLine("Closing ftrack connect app");
                    ftrackPath = proc.MainModule.FileName;
                    proc.Kill();
                } catch
                {
                    error = true;
                }
            }

            Console.WriteLine("Copying files");

            DirectoryCopy(sourceDir, targetDir, true);



            if (!error)
            {
                if (!string.IsNullOrEmpty(ftrackPath))
                {
                    Console.WriteLine("Restarting ftrack connect app");
                    ProcessStartInfo startFtrack = new ProcessStartInfo();
                    startFtrack.WorkingDirectory = Path.GetDirectoryName(ftrackPath);
                    startFtrack.FileName = ftrackPath;

                    Process.Start(startFtrack);
                } else
                {
                    Console.WriteLine("Cannot locate ftrack, please start ftrack connect manually.\nPress any key to close this window.");
                    Console.ReadKey();
                }
            } else
            {
                Console.WriteLine("Failed to close process :-( Please restart ftrack manually.\nPress any key to close this window.");
                Console.ReadKey();
            }

            //Console.WriteLine(new DirectoryInfo(sourceDir).FullName);
        }



        private static void DirectoryCopy(string sourceDirName, string destDirName, bool copySubDirs)
        {
            // Get the subdirectories for the specified directory.
            DirectoryInfo dir = new DirectoryInfo(sourceDirName);
            Console.WriteLine("Copying " + dir.FullName);

            if (!dir.Exists)
            {
                Console.WriteLine("\tERR: The directory does not exist!");
                return;
            }

            DirectoryInfo[] dirs = dir.GetDirectories();
            // If the destination directory doesn't exist, create it.
            if (!Directory.Exists(destDirName))
            {
                Directory.CreateDirectory(destDirName);
            }

            // Get the files in the directory and copy them to the new location.
            FileInfo[] files = dir.GetFiles();
            foreach (FileInfo file in files)
            {
                string temppath = Path.Combine(destDirName, file.Name);
                file.CopyTo(temppath, false);
            }

            // If copying subdirectories, copy them and their contents to new location.
            if (copySubDirs)
            {
                foreach (DirectoryInfo subdir in dirs)
                {
                    string temppath = Path.Combine(destDirName, subdir.Name);
                    DirectoryCopy(subdir.FullName, temppath, copySubDirs);
                }
            }
        }
    }
}
