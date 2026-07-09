// Copyright (C) 2026, IDS Imaging Development Systems GmbH.
//
// Permission to use, copy, modify, and/or distribute this software for
// any purpose with or without fee is hereby granted.
//
// THE SOFTWARE IS PROVIDED “AS IS” AND THE AUTHOR DISCLAIMS ALL
// WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES
// OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE
// FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
// DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
// AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
// OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Platform.Storage;
using IDSImaging.Peak.Examples.AvaloniaSimpleLive.ViewModels;

namespace IDSImaging.Peak.Examples.AvaloniaSimpleLive.Views;

/// <summary>
///     Implements <see cref="IFileDialogService" /> using Avalonia's native file picker API.
///     Requires a parent window to anchor the dialog correctly on all platforms.
/// </summary>
public class FileDialogService(Window parent) : IFileDialogService
{
    /// <summary>
    ///     Opens a file picker dialog and returns the selected file path, or null if canceled.
    /// </summary>
    /// <param name="title">Title shown in the dialog header.</param>
    /// <param name="extensions">Allowed file extensions without leading dots (e.g. "cset").</param>
    public async Task<string?> OpenFileAsync(string title, string[] extensions)
    {
        var options = new FilePickerOpenOptions
        {
            Title = title,
            AllowMultiple = false,
            FileTypeFilter =
            [
                new FilePickerFileType("Allowed Files")
                {
                    Patterns = extensions.Select(e => $"*.{e.TrimStart('.')}").ToArray()
                }
            ]
        };

        IReadOnlyList<IStorageFile> files = await parent.StorageProvider.OpenFilePickerAsync(options);

        return files.Count > 0 ? files[0].Path.LocalPath : null;
    }

    /// <summary>
    ///     Opens a save file picker dialog and returns the chosen file path, or null if canceled.
    /// </summary>
    /// <param name="title">Title shown in the dialog header.</param>
    /// <param name="defaultExtension">Extension appended automatically if the user omits it.</param>
    /// <param name="extensions">Allowed file extensions without leading dots (e.g. "cset").</param>
    public async Task<string?> SaveFileAsync(string title, string defaultExtension, string[] extensions)
    {
        var options = new FilePickerSaveOptions
        {
            Title = title,
            DefaultExtension = defaultExtension,
            FileTypeChoices =
            [
                new FilePickerFileType("Allowed Files")
                {
                    Patterns = extensions.Select(e => $"*.{e.TrimStart('.')}")
                        .ToArray()
                }
            ]
        };

        IStorageFile? file = await parent.StorageProvider.SaveFilePickerAsync(options);

        return file?.Path.LocalPath;
    }
}
