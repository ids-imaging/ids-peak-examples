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
using System.Diagnostics;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Avalonia;
using Avalonia.Media.Imaging;
using Avalonia.Platform;
using Avalonia.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using IDSImaging.Peak.Examples.AvaloniaSimpleLive.Models;
using IDSImaging.Peak.ICV.Types;
using AvaloniaPixelFormat = Avalonia.Platform.PixelFormat;
using CommonPixelFormat = IDSImaging.Peak.Common.Types.PixelFormat;

namespace IDSImaging.Peak.Examples.AvaloniaSimpleLive.ViewModels;

/// <summary>
///     ViewModel for the main camera view. Bridges <see cref="CameraService" /> and the UI,
///     managing the live display bitmap, observable camera parameters, and acquisition control.
/// </summary>
public partial class CameraViewModel : ObservableObject
{
    private readonly CameraService _service;
    private IFileDialogService? _dialogService;

    /// <summary>The bitmap rendered in the live view. Reallocated if image dimensions change.</summary>
    [ObservableProperty] private WriteableBitmap? _displayBitmap;

    /// <summary>Total number of frames successfully copied to <see cref="CameraViewModel.DisplayBitmap" />.</summary>
    [ObservableProperty] private long _frameCounter;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(WindowTitle))]
    private string _cameraName = "No camera connected";

    public string WindowTitle => $"IDSImaging.Peak.Examples.AvaloniaSimpleLive - {CameraName}";

    // Used as a binary semaphore via Interlocked to prevent concurrent frame processing.
    private int _isProcessingFrame;
    private DispatcherTimer? _timer;


    public CameraViewModel(CameraService service)
    {
        _service = service;
        _service.NewFrameReady += OnFrameReceived;

        _service.DeviceDisconnected += () => CameraName = _service.GetCameraName() + " [Disconnected]";
        _service.DeviceReconnected += () => CameraName = _service.GetCameraName();

        // Poll hardware values every second to keep the status bar and parameter
        // controls up to date. Polling avoids SDK callback threading constraints.
        _timer = new DispatcherTimer
        {
            Interval = TimeSpan.FromSeconds(1)
        };

        _timer.Tick += (_, _) =>
        {
            try
            {
                OnPropertyChanged(nameof(ExposureValue));
                OnPropertyChanged(nameof(MasterGain));
                OnPropertyChanged(nameof(RedGain));
                OnPropertyChanged(nameof(GreenGain));
                OnPropertyChanged(nameof(BlueGain));

                foreach (CameraParameter setting in Settings)
                {
                    setting.Update();
                }
            }
            catch (Exception)
            {
                // Prevent hardware communication errors from destroying the polling loop
            }
        };

        _timer.Start();

        SetupParameters();
        SyncHardwareValues();
    }

    /// <summary>Observable collection of camera parameters displayed in the settings panel.</summary>
    public ObservableCollection<CameraParameter> Settings { get; } = [];

    /// <summary>Current exposure time in microseconds, read directly from hardware.</summary>
    public double ExposureValue => _service.GetExposure();

    /// <summary>Current master gain value, or null if not supported by this camera.</summary>
    public double? MasterGain => _service.GetGain(CameraService.GainType.All);

    /// <summary>Current red channel gain, or null if not supported by this camera.</summary>
    public double? RedGain => _service.GetGain(CameraService.GainType.Red);

    /// <summary>Current green channel gain, or null if not supported by this camera.</summary>
    public double? GreenGain => _service.GetGain(CameraService.GainType.Green);

    /// <summary>Current blue channel gain, or null if not supported by this camera.</summary>
    public double? BlueGain => _service.GetGain(CameraService.GainType.Blue);

    /// <summary>Returns true if the camera is currently acquiring images.</summary>
    public bool IsAcquiring => _service.IsStreaming;

    /// <summary>Label text for the start/stop acquisition button.</summary>
    public string StartStopText => IsAcquiring ? "Stop Acquisition" : "Start Acquisition";

    /// <summary>
    ///     Injects the file dialog service. Must be called before <see cref="LoadAsync" /> or
    ///     <see cref="SaveAsync" /> are used. Kept separate to avoid a hard dependency on the
    ///     View layer in the constructor.
    /// </summary>
    public void SetFileDialogService(IFileDialogService fileDialogService)
    {
        _dialogService = fileDialogService;
    }

    /// <summary>
    ///     Stops the polling timer. Should be called when the window is closed to prevent
    ///     SDK calls after the camera has been disposed.
    /// </summary>
    public void StopUpdateTask()
    {
        _timer?.Stop();
        _timer = null;
    }

    private void SetupParameters()
    {
        // Exposure – updating exposure affects the maximum achievable framerate,
        // so framerate limits are refreshed after each change.
        Settings.Add(new DoubleOrIntegerParameter
        {
            Name = "Exposure",
            Unit = "µs",
            ValueChanged = val =>
            {
                _service.SetExposure(val);
                UpdateFramerateLimits();
            },
            UpdateValue = () => _service.GetExposure(),
            UpdateRange = () =>
            {
                (double Min, double Max) values = _service.GetExposureRange();
                return (values.Min, values.Max, 0);
            }
        });

        // Framerate – updating framerate affects the maximum achievable exposure,
        // so exposure limits are refreshed after each change.
        Settings.Add(new DoubleOrIntegerParameter
        {
            Name = "Framerate",
            Unit = "fps",
            ValueChanged = val =>
            {
                _service.SetFramerate(val);
                UpdateExposureLimits();
            },
            UpdateValue = () => _service.GetFramerate(),
            UpdateRange = () =>
            {
                (double Min, double Max) values = _service.GetFrameRateRange();
                return (values.Min, values.Max, 0);
            }
        });

        // Gain
        Settings.Add(new DoubleOrIntegerParameter
        {
            Name = "Master Gain",
            Unit = "x",
            ValueChanged = val => _service.SetGain(CameraService.GainType.All, val),
            UpdateValue = () => _service.GetGain(CameraService.GainType.All) ?? 0,
            UpdateRange = () =>
            {
                (double Min, double Max)? values = _service.GetGainRange(CameraService.GainType.All);
                return (values?.Min ?? 0, values?.Max ?? 0, 0);
            }
        });
    }

    private void OnFrameReceived(Image image)
    {
        // Drop frame if the UI thread is still processing the previous one.
        // This prevents frame queue buildup under high load.
        if (DisplayBitmap == null || Interlocked.CompareExchange(ref _isProcessingFrame, 1, 0) != 0)
        {
            image.Dispose();
            return;
        }

        Dispatcher.UIThread.Post(() =>
        {
            using Image img = image;

            if (img.Size.Width != (uint) DisplayBitmap.Size.Width ||
                img.Size.Height != (uint) DisplayBitmap.Size.Height)
            {
                // Image dimensions changed -> reallocate the bitmap to match the new size.
                try
                {
                    Initialize((int) img.Size.Width, (int) img.Size.Height, GetPixelFormat(img.PixelFormat));
                }
                finally
                {
                    Interlocked.Exchange(ref _isProcessingFrame, 0);
                }

                return;
            }

            try
            {
                using (ILockedFramebuffer lockedBuffer = DisplayBitmap.Lock())
                {
                    unsafe
                    {
                        var destBytes = lockedBuffer.RowBytes * lockedBuffer.Size.Height;
                        var sourceBytes = img.SizeInBytes;
                        if (destBytes != sourceBytes)
                        {
                            throw new InvalidOperationException(
                                $"Buffer size mismatch: dest={destBytes}, source={sourceBytes}");
                        }

                        // Direct memory copy from the Peak ICV image buffer into
                        // the Avalonia WriteableBitmap — avoids any intermediate allocation.
                        Buffer.MemoryCopy(
                            (void*) img.Data,
                            (void*) lockedBuffer.Address,
                            destBytes,
                            sourceBytes);
                    }
                }

                FrameCounter++;
            }
            finally
            {
                Interlocked.Exchange(ref _isProcessingFrame, 0);
            }
        }, DispatcherPriority.Render);
    }

    /// <summary>
    ///     Allocates or reallocates the <see cref="CameraViewModel.DisplayBitmap" /> for the given dimensions and pixel
    ///     format.
    /// </summary>
    public void Initialize(int w, int h, AvaloniaPixelFormat pixelFormat)
    {
        AlphaFormat alphaFormat = pixelFormat == PixelFormats.Rgba8888 || pixelFormat == PixelFormats.Bgra8888
            ? AlphaFormat.Premul
            : AlphaFormat.Opaque;
        DisplayBitmap = new WriteableBitmap(
            new PixelSize(w, h), new Vector(96, 96),
            pixelFormat, alphaFormat);

        CameraName = _service.GetCameraName();
    }

    /// <summary>
    ///     Forces an immediate sync of all parameter values and ranges from the hardware.
    /// </summary>
    public void TriggerUpdate()
    {
        SyncHardwareValues();

        OnPropertyChanged(nameof(IsAcquiring));
        OnPropertyChanged(nameof(StartStopText));
    }

    /// <summary>
    ///     Toggles image acquisition on or off.
    ///     async void is intentional here: Avalonia command bindings do not support
    ///     Task-returning methods directly. StopCapture is offloaded to a background
    ///     thread to avoid blocking the UI while waiting for the acquisition loop to exit.
    /// </summary>
    public async void AsyncToggleAcquisition()
    {
        try
        {
            if (IsAcquiring)
            {
                await Task.Run(() => _service.StopCapture());
            }
            else
            {
                _service.StartCapture();
            }

            OnPropertyChanged(nameof(IsAcquiring));
            OnPropertyChanged(nameof(StartStopText));
        }
        catch (Exception ex)
        {
            // should never happen anyway
            Debug.WriteLine($"Acquisition toggle failed: {ex.Message}");
        }
    }

    /// <summary>
    ///     Resets the camera to its factory default settings and syncs all parameter controls.
    /// </summary>
    public void ResetToDefault()
    {
        _service.ResetToDefault();
        SyncHardwareValues();
    }

    private void UpdateExposureLimits()
    {
        (double Min, double Max) range = _service.GetExposureRange();
        DoubleOrIntegerParameter? exposure =
            Settings.OfType<DoubleOrIntegerParameter>().FirstOrDefault(x => x.Name == "Exposure");
        if (exposure == null)
        {
            return;
        }

        exposure.Max = range.Max;
        exposure.Min = range.Min;

        if (exposure.Value > exposure.Max)
        {
            exposure.Value = exposure.Max;
        }
    }

    private void UpdateFramerateLimits()
    {
        (double Min, double Max) range = _service.GetFrameRateRange();
        DoubleOrIntegerParameter? frameRate =
            Settings.OfType<DoubleOrIntegerParameter>().FirstOrDefault(x => x.Name == "Framerate");
        if (frameRate == null)
        {
            return;
        }

        frameRate.Max = range.Max;
        frameRate.Min = range.Min;

        if (frameRate.Value > frameRate.Max)
        {
            frameRate.Value = frameRate.Max;
        }
    }

    private void SyncHardwareValues()
    {
        foreach (CameraParameter setting in Settings)
        {
            setting.Update();
        }
    }

    /// <summary>
    ///     Maps an IDS Peak IPL pixel format to the corresponding Avalonia pixel format.
    /// </summary>
    /// <remarks>
    ///     Supported mappings:
    ///     <list type="table">
    ///         <listheader>
    ///             <term>IDS Format</term><description>Avalonia (Skia) Format</description>
    ///         </listheader>
    ///         <item>
    ///             <term>RGBa8</term><description>Rgba8888</description>
    ///         </item>
    ///         <item>
    ///             <term>BGRa8</term><description>Bgra8888</description>
    ///         </item>
    ///         <item>
    ///             <term>RGB8</term><description>Rgb24</description>
    ///         </item>
    ///         <item>
    ///             <term>BGR8</term><description>Bgr24</description>
    ///         </item>
    ///         <item>
    ///             <term>Mono8</term><description>Gray8</description>
    ///         </item>
    ///         <item>
    ///             <term>Mono16</term><description>Gray16</description>
    ///         </item>
    ///     </list>
    /// </remarks>
    public static AvaloniaPixelFormat GetPixelFormat(CommonPixelFormat pixelFormat)
    {
        return pixelFormat switch
        {
            CommonPixelFormat.RGBa8 => PixelFormats.Rgba8888,
            CommonPixelFormat.BGRa8 => PixelFormats.Bgra8888,
            CommonPixelFormat.RGB8 => PixelFormats.Rgb24,
            CommonPixelFormat.BGR8 => PixelFormats.Bgr24,
            CommonPixelFormat.Mono8 => PixelFormats.Gray8,
            CommonPixelFormat.Mono16 => PixelFormats.Gray16,
            _ => throw new ArgumentOutOfRangeException(nameof(pixelFormat), pixelFormat, null)
        };
    }

    /// <summary>Opens a file picker and loads camera settings from the selected file.</summary>
    public async Task LoadAsync()
    {
        if (_dialogService is null)
        {
            return;
        }

        var path = await _dialogService.OpenFileAsync("Load Settings", ["cset"]);
        if (path != null)
        {
            _service.LoadSettings(path);
            TriggerUpdate();
        }
    }

    /// <summary>Opens a file picker and saves the current camera settings to the selected file.</summary>
    public async Task SaveAsync()
    {
        if (_dialogService is null)
        {
            return;
        }

        var path = await _dialogService.SaveFileAsync("Save Settings", "cset", ["cset"]);
        if (path != null)
        {
            _service.SaveSettings(path);
        }
    }
}
