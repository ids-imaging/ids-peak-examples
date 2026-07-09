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

using System;
using System.Collections.ObjectModel;
using System.Threading;
using System.Threading.Tasks;
using Avalonia.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using IDSImaging.Peak.Examples.AvaloniaSimpleLive.Models;

namespace IDSImaging.Peak.Examples.AvaloniaSimpleLive.ViewModels;

/// <summary>
///     Represents a discovered camera device and its connection metadata.
/// </summary>
public record CameraInfo(string ModelName, string SerialNumber, string TlType, string TLName, bool Openable,
    string DeviceKey);

/// <summary>
///     ViewModel for the camera selection dialog. Continuously polls for available
///     devices and allows the user to select and open one before acquisition starts.
/// </summary>
public partial class CameraSelectionViewModel : ObservableObject
{
    private readonly CancellationTokenSource _cts = new();
    private readonly Task _pollingTask;
    private readonly CameraService _service;

    /// <summary>The list of currently discovered cameras, updated automatically.</summary>
    [ObservableProperty] private ObservableCollection<CameraInfo> _cameras = new();

    /// <summary>
    ///     The camera selected by the user in the list.
    ///     Changing this automatically updates <see cref="CanOpen" /> and
    ///     the executable state of <see cref="ConfirmCommand" />.
    /// </summary>
    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(CanOpen))]
    [NotifyCanExecuteChangedFor(nameof(ConfirmCommand))]
    private CameraInfo? _selectedCamera;

    public CameraSelectionViewModel(CameraService service)
    {
        _service = service;
        _service.DeviceListChanged += OnDeviceListChanged;

        ConfirmCommand = new RelayCommand(
            () => CloseAction?.Invoke(SelectedCamera),
            () => CanOpen);

        // Start a background polling loop.
        // The DeviceListChanged event fires when the DeviceManager detects a change when running Update().
        _pollingTask = Task.Run(PollDeviceListAsync);

        UpdateCameraList();
    }

    /// <summary>Returns true if the selected camera can be opened with control access.</summary>
    public bool CanOpen => SelectedCamera?.Openable == true;

    /// <summary>
    ///     Callback invoked when the user confirms their selection.
    ///     The selected <see cref="CameraInfo" /> is passed as the argument, or null if canceled.
    /// </summary>
    public Action<CameraInfo?>? CloseAction { get; set; }

    /// <summary>Command bound to the Open button. Enabled only when <see cref="CanOpen" /> is true.</summary>
    public RelayCommand ConfirmCommand { get; }

    /// <summary>
    ///     Cancels the polling loop and waits for it to finish.
    ///     Must be called before the dialog is closed to avoid SDK calls after disposal.
    /// </summary>
    public async Task StopPollingAsync()
    {
        _service.DeviceListChanged -= OnDeviceListChanged;
        await _cts.CancelAsync();
        await _pollingTask;
    }

    private async Task PollDeviceListAsync()
    {
        using var timer = new PeriodicTimer(TimeSpan.FromMilliseconds(500));
        try
        {
            while (await timer.WaitForNextTickAsync(_cts.Token))
            {
                _service.UpdateDeviceList();
            }
        }
        catch (OperationCanceledException)
        {
            // Expected when StopPollingAsync cancels the token. Normal shutdown path.
        }
    }

    private void OnDeviceListChanged()
    {
        // DeviceListChanged is raised from the polling thread.
        // Dispatch to the UI thread before modifying the observable collection.
        Dispatcher.UIThread.Post(UpdateCameraList);
    }

    private void UpdateCameraList()
    {
        try
        {
            Cameras = new ObservableCollection<CameraInfo>(_service.GetCameraList());
        }
        catch (Exception)
        {
            // nothing to do
        }
    }
}
