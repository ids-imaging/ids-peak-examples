#pragma once
#include <sstream>
#include <string>

#ifdef _WIN32
#    include <direct.h>
#    include <windows.h>
#    define MKDIR(path) _mkdir(path)
#else
#    include <sys/stat.h>
#    include <dirent.h>
#    include <unistd.h>
#    define MKDIR(path) mkdir(path, 0755)
#endif


namespace utils
{
#ifdef _WIN32
inline bool FindNext(HANDLE handle, WIN32_FIND_DATAA* data)
{
    return FindNextFileA(handle, data) != 0;
}
#endif

inline double MakeDecimal(const std::string& integerPart, const std::string& fractionalPart)
{
    std::string value;
    value.reserve(integerPart.size() + 1 + fractionalPart.size());

    value += integerPart;
    value += '.';
    value += fractionalPart;

    std::istringstream iss(value);
    // forces "C" locale (same as en_US for decimal)
    iss.imbue(std::locale::classic());

    double result;
    iss >> result;

    return result;
}

static std::vector<std::string> ListRegularFiles(const std::string& path)
{
    std::vector<std::string> files;

#ifdef _WIN32
    WIN32_FIND_DATAA data;
    HANDLE handle = FindFirstFileA((path + "\\*").c_str(), &data);
    if (handle == INVALID_HANDLE_VALUE) // NOLINT
    {
        return files;
    }

    do
    {
        if ((data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0)
        {
            continue;
        }

        files.emplace_back(path + "\\" + data.cFileName);
    } while (FindNext(handle, &data));
    FindClose(handle);
#else
    DIR* dir = opendir(path.c_str());
    if (dir == nullptr)
    {
        return files;
    }

    dirent* entry{};
    while ((entry = readdir(dir)) != nullptr)
    {
        const std::string full = path + "/" + entry->d_name;

        struct stat st;
        if (stat(full.c_str(), &st) == 0 && S_ISREG(st.st_mode))
        {
            files.emplace_back(full);
        }
    }
    closedir(dir);
#endif

    return files;
}

static std::string GetFilename(const std::string& path)
{
    const size_t pos = path.find_last_of("/\\");
    return pos == std::string::npos ? path : path.substr(pos + 1);
}
} // namespace utils
