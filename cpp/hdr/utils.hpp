/*
 * Copyright(C) 2026, IDS Imaging Development Systems GmbH.
 *
 * Permission to use, copy, modify, and/or distribute this software for
 * any purpose with or without fee is hereby granted.
 *
 * THE SOFTWARE IS PROVIDED “AS IS” AND THE AUTHOR DISCLAIMS ALL
 * WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES
 * OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE
 * FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
 * DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
 * AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
 * OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 */

#pragma once

#include <peak/peak.hpp>
#include <peak_icv/peak_icv.hpp>

#include <sys/stat.h>
#ifdef _WIN32
#    include <direct.h>
#    include <windows.h>
#    define MKDIR(path) _mkdir(path)
#else
#    include <dirent.h>
#    include <unistd.h>
#    define MKDIR(path) mkdir(path, 0755)
#endif

#include <exception>
#include <ostream>
#include <sstream>
#include <string>

namespace utils
{
static void EnsurePathExists(const std::string& path)
{
    std::string current;
    current.reserve(path.size());

    for (const char c : path)
    {
        current += c;
        if (c != '/' && c != '\\')
        {
            continue;
        }

        if (current.size() == 1)
        {
            continue;
        } // skip root "/"

        MKDIR(current.c_str());
    }

    // final directory (in case path doesn't end with /)
    MKDIR(path.c_str());
}

static std::pair<std::string, std::string> SplitArg(const std::string& s)
{
    const size_t eq = s.find('=');
    if (eq == std::string::npos)
    {
        return { s, {} };
    }

    const auto key = s.substr(0, eq);
    const auto value = s.substr(eq + 1);
    return { key, value };
}

template <typename Iterable>
static std::string JoinToString(const Iterable& items, const std::string& sep = ", ")
{
    std::ostringstream oss;
    auto it = std::cbegin(items);
    const auto end = std::cend(items);

    if (it == end)
    {
        return {};
    }

    oss << *it; // first element
    ++it;

    for (; it != end; ++it)
    {
        oss << sep << *it;
    }

    return oss.str();
}

inline std::string JoinPath(const std::string& path, const std::string& filename)
{
    if (path.empty())
    {
        return filename;
    }
    if (filename.empty())
    {
        return path;
    }

    std::string joinedPath;
    joinedPath.reserve(path.size() + 1 + filename.size());

    joinedPath += path;
    if (path.back() != '/')
    {
        joinedPath += '/';
    }
    joinedPath += filename;
    return joinedPath;
}

class ICVLibraryGuard
{
public:
    explicit ICVLibraryGuard(std::ostream& errorStream)
        : m_errorStream(errorStream)
    {
        peak::icv::library::Init();
    }

    ~ICVLibraryGuard()
    {
        try
        {
            peak::icv::library::Exit();
        }
        catch (const std::exception& e)
        {
            m_errorStream << "Error when closing library: " << e.what() << "\n";
        }
    }

private:
    std::ostream& m_errorStream;
};

class APILibraryGuard
{
public:
    explicit APILibraryGuard(std::ostream& errorStream)
        : m_errorStream(errorStream)
    {
        peak::Library::Initialize();
    }

    ~APILibraryGuard()
    {
        try
        {
            peak::Library::Close();
        }
        catch (const std::exception& e)
        {
            m_errorStream << "Error when closing library: " << e.what() << "\n";
        }
    }

private:
    std::ostream& m_errorStream;
};
} // namespace utils
