#include <windows.h>
#include <string>
#include <sstream>

// Function to display a message box
void showMessageBox(const std::wstring& message, const std::wstring& title, UINT type) {
    MessageBox(nullptr, message.c_str(), title.c_str(), type);
}

std::wstring stringToWString(const std::string& str) {
    return std::wstring(str.begin(), str.end());
}

int APIENTRY WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    try {
        // Path to Chrome executable
        const std::wstring chromePath = L"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

        // Retrieve command line arguments
        int argc;
        LPWSTR* argv = CommandLineToArgvW(GetCommandLineW(), &argc);

        // Build the command line arguments
        std::wstringstream commandArgs;
        for (int i = 1; i < argc; ++i) {
            commandArgs << L" " << argv[i];
        }
        std::wstring strCommandArgs = commandArgs.str();

        // Prepare the STARTUPINFO and PROCESS_INFORMATION structures
        STARTUPINFO si = { sizeof(STARTUPINFO) };
        si.dwFlags = STARTF_USESHOWWINDOW;
        si.wShowWindow = SW_HIDE; // Hide the console window
        PROCESS_INFORMATION pi = {};

        // Combine the executable path and arguments
        std::wstring wsFullCommand = L"\"" + chromePath + L"\"" + strCommandArgs;

        // Create a mutable copy of the command string for CreateProcess
        WCHAR cmdLine[MAX_PATH * 2]; // Adjust size as needed
        wcscpy_s(cmdLine, wsFullCommand.c_str());

        // Show command for debugging
        showMessageBox(wsFullCommand, L"Command", MB_OK | MB_ICONINFORMATION);

        // Create the process
        if (!CreateProcess(
            nullptr,                          // Application name (nullptr since it's included in the command line)
            cmdLine,                          // Command line - must be modifiable buffer
            nullptr,                          // Process security attributes
            nullptr,                          // Thread security attributes
            FALSE,                            // Inherit handles
            CREATE_NO_WINDOW | DETACHED_PROCESS, // Flags to hide the window and detach the process
            nullptr,                          // Environment
            nullptr,                          // Current directory
            &si,                              // Startup info
            &pi                               // Process info
        )) {
            showMessageBox(L"Error: Failed to launch Chrome. Error code: " + std::to_wstring(GetLastError()), L"Error", MB_OK | MB_ICONERROR);
        }
        else {
            // Close handles to avoid resource leaks
            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);
        }

        LocalFree(argv); // Free memory allocated for CommandLineToArgvW
    }
    catch (const std::exception& e) {
        showMessageBox(stringToWString("Exception: " + std::string(e.what())), L"Exception", MB_OK | MB_ICONERROR);
    }
    catch (...) {
        showMessageBox(L"Unknown error occurred.", L"Exception", MB_OK | MB_ICONERROR);
    }

    return 0;
}