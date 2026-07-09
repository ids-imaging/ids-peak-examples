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

using Avalonia.Controls;
using IDSImaging.Peak.Examples.AvaloniaSimpleLive.Models;
using IDSImaging.Peak.Examples.AvaloniaSimpleLive.ViewModels;

namespace IDSImaging.Peak.Examples.AvaloniaSimpleLive.Views;

/// <summary>
///     Dialog window for selecting a camera before acquisition starts.
///     If exactly one openable camera is found at startup, this dialog is skipped entirely.
/// </summary>
public partial class CameraSelectionWindow : Window
{
    /// <summary>
    ///     Parameterless constructor required by the Avalonia designer.
    ///     Do not use at runtime — use <see cref="CameraSelectionWindow(CameraService)" /> instead.
    /// </summary>
    public CameraSelectionWindow()
    {
        InitializeComponent();
    }

    /// <summary>
    ///     Creates the window and wires up the ViewModel with the given camera service.
    ///     The window closes itself via <see cref="CameraSelectionViewModel.CloseAction" />
    ///     when the user confirms their selection.
    /// </summary>
    public CameraSelectionWindow(CameraService service)
    {
        InitializeComponent();

        var vm = new CameraSelectionViewModel(service);
        DataContext = vm;
        ViewModel = vm;

        // Pass Window.Close as the callback so the ViewModel can close the dialog
        // without taking a direct dependency on the View.
        vm.CloseAction = Close;
    }

    /// <summary>
    ///     The ViewModel associated with this window. Exposed so the caller can await
    ///     <see cref="CameraSelectionViewModel.StopPollingAsync" /> after the dialog closes.
    /// </summary>
    public CameraSelectionViewModel? ViewModel { get; private set; }
}
