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
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using IDSImaging.Peak.API;
using IDSImaging.Peak.API.Core;
using IDSImaging.Peak.API.Core.Nodes;
using IDSImaging.Peak.API.Exceptions;
using IDSImaging.Peak.API.Std;
using IDSImaging.Peak.Common.Types;
using IDSImaging.Peak.Examples.AvaloniaSimpleLive.ViewModels;
using IDSImaging.Peak.ICV.Pipeline;
using MsBox.Avalonia;
using MsBox.Avalonia.Base;
using MsBox.Avalonia.Enums;
using Buffer = IDSImaging.Peak.API.Core.Buffer;
using Library = IDSImaging.Peak.API.Library;
using Image = IDSImaging.Peak.ICV.Types.Image;

namespace IDSImaging.Peak.Examples.AvaloniaSimpleLive.Models;

/// <summary>
///     Wraps the IDS Peak API to provide camera enumeration, device opening,
///     image acquisition, and parameter control (exposure, gain, framerate, focus).
///     Reconnect handling is included to recover from temporary disconnections.
/// </summary>
public class CameraService : IDisposable
{
    /// <summary>
    ///     Identifies which gain channel to read or write.
    ///     Not all cameras expose all channels — use e.g. <see cref="HasMasterGain" /> to check availability.
    /// </summary>
    public enum GainType
    {
        All,
        Red,
        Green,
        Blue
    }

    private readonly DefaultPipeline _defaultPipeline;
    private CancellationTokenSource? _cts;
    private DataStream? _dataStream;

    private Device? _device;
    private bool _disposed;

    // volatile ensures the background acquisition thread and the UI thread always
    // see a consistent value without needing a lock.
    private volatile bool _isStreaming;
    private NodeMap? _remoteNodeMap;
    private Task? _workerTask;

    public CameraService()
    {
        // The library must be initialized before use.
        // Each call to Initialize must be matched with a corresponding call to Close.
        Library.Initialize();

        // The same for ICV.
        // Each call to Init must be matched with a corresponding call to Exit.
        ICV.Library.Init();

        // WARNING: Do not call Dispose() on the DeviceManager instance.
        // It is a singleton managed by the library — disposing it would break the singleton.
        var dm = DeviceManager.Instance();

        // Subscribe to device events to keep the camera list up to date.
        // These fire independently of whether the device was opened by this application.
        dm.DeviceFoundEvent += (_, _) => DeviceListChanged?.Invoke();
        dm.DeviceLostEvent += (_, _) => DeviceListChanged?.Invoke();
        dm.DeviceDisconnectedEvent += (_, _) => DeviceListChanged?.Invoke();
        dm.DeviceReconnectedEvent += (_, _, _) => DeviceListChanged?.Invoke();

        // Create the default pipeline.
        // This simplifies the conversion of the camera buffer to a usable image.
        _defaultPipeline = new DefaultPipeline();
    }

    /// <summary>
    ///     Indicates whether the acquisition is running or not.
    /// </summary>
    public bool IsStreaming => _isStreaming;

    /// <summary>
    ///     Gets or sets the pixel format used by the camera hardware.
    ///     Changing this also updates <see cref="OutputPixelFormat" /> accordingly.
    /// </summary>
    /// <exception cref="NullReferenceException">Thrown if called before <see cref="OpenCamera" />.</exception>
    public PixelFormat PixelFormat
    {
        get
        {
            if (_remoteNodeMap is null)
            {
                throw new NullReferenceException("RemoteNodeMap not initialized");
            }

            return (PixelFormat) _remoteNodeMap.FindNode<EnumerationNode>("PixelFormat").CurrentEntry()
                .NumericValue();
        }
        set
        {
            _remoteNodeMap?.FindNode<EnumerationNode>("PixelFormat").SetCurrentEntry((long) value);
            SelectOutputFormat(value);
        }
    }

    /// <summary>
    ///     The pixel format that frames will be converted to before being delivered
    ///     via <see cref="NewFrameReady" />. Set automatically based on the camera's
    ///     active <see cref="PixelFormat" />.
    /// </summary>
    public PixelFormat OutputPixelFormat
    {
        get => _defaultPipeline.OutputPixelFormat;
        private set => _defaultPipeline.OutputPixelFormat = value;
    }

    /// <summary>
    ///     Returns true if this camera exposes a master (all-channel) gain selector.
    /// </summary>
    public bool HasMasterGain => SetGainSelector(GainType.All);

    /// <summary>Stops acquisition, releases all camera resources, and closes the Peak library.</summary>
    public void Dispose()
    {
        Dispose(true);
        GC.SuppressFinalize(this);
    }

    /// <summary>Raised when the list of available cameras changes.</summary>
    public event Action? DeviceListChanged;

    /// <summary>Triggers a scan for newly connected or removed devices.</summary>
    public void UpdateDeviceList()
    {
        var dm = DeviceManager.Instance();
        dm.Update();
    }

    /// <summary>
    ///     Raised on the background thread each time a new frame is ready. The caller is responsible for disposing the
    ///     image.
    /// </summary>
    public event Action<Image>? NewFrameReady;

    /// <summary>Raised after the device has been disconnected.</summary>
    public event Action? DeviceDisconnected;

    /// <summary>Raised after the device has successfully reconnected following a disconnection.</summary>
    public event Action? DeviceReconnected;

    ~CameraService()
    {
        Dispose(false);
    }

    protected virtual void Dispose(bool disposing)
    {
        if (_disposed)
        {
            return;
        }

        if (disposing)
        {
            if (_workerTask is { IsCompleted: false })
            {
                StopCapture();
            }

            _cts?.Dispose();

            _dataStream?.Dispose();
            _remoteNodeMap?.Dispose();
            _device?.Dispose();

            // Unsubscribe the reconnect handler to avoid stale callbacks after disposal.
            DeviceManager.Instance().DeviceDisconnectedEvent -= DeviceDisconnectedEvent;
            DeviceManager.Instance().DeviceReconnectedEvent -= DeviceReconnectedEvent;
        }

        ICV.Library.Exit();
        Library.Close();

        _disposed = true;
    }

    /// <summary>
    ///     Scans for available cameras and returns their descriptors.
    /// </summary>
    public List<CameraInfo> GetCameraList()
    {
        var list = new List<CameraInfo>();
        var dm = DeviceManager.Instance();
        dm.Update();
        DeviceDescriptorCollection? devices = dm.Devices();
        foreach (DeviceDescriptor? device in devices)
        {
            list.Add(new CameraInfo(device.ModelName(), device.SerialNumber(), device.TLType(),
                device.ParentInterface().ParentSystem().CTIFullPath(),
                device.IsOpenable(DeviceAccessType.Control), device.Key()));
        }

        return list;
    }

    /// <summary>
    ///     Opens the specified camera with control access and prepares it for acquisition.
    /// </summary>
    public void OpenCamera(CameraInfo selectedCamera)
    {
        var dm = DeviceManager.Instance();
        DeviceDescriptorCollection? devices = dm.Devices();
        DeviceDescriptor? device = devices.First(x => x.Key() == selectedCamera.DeviceKey);

        _device = device.OpenDevice(DeviceAccessType.Control);

        // Retrieve the remote device's primary node map.
        // The node map provides access to GenICam parameters (exposure, gain, etc.)
        // implemented on the camera hardware, following the GenICam SFNC standard.
        _remoteNodeMap = _device.RemoteDevice().NodeMaps()[0];
        _dataStream = _device.DataStreams()[0].OpenDataStream();

        SelectOutputFormat((PixelFormat) _remoteNodeMap.FindNode<EnumerationNode>("PixelFormat").CurrentEntry()
            .NumericValue());

        try
        {
            // Enable automatic reconnect so the SDK attempts to recover the device
            // after a temporary disconnection rather than immediately firing DeviceLostEvent.
            // This feature is not available on all transport layers, so failures are ignored.
            NodeMap? systemNodeMap = _device.ParentInterface().ParentSystem().NodeMaps()[0];
            BooleanNode? reconnectEnableNode = systemNodeMap.TryFindNode<BooleanNode>("ReconnectEnable");
            reconnectEnableNode?.SetValue(true);
        }
        catch (Exception)
        {
            // Reconnect not available on this transport layer. Just ignore.
        }

        dm.DeviceReconnectedEvent += DeviceReconnectedEvent;
        dm.DeviceDisconnectedEvent += DeviceDisconnectedEvent;
    }

    private void DeviceReconnectedEvent(object sender, DeviceDescriptor device, DeviceReconnectInformation info)
    {
        if (info.IsSuccessful())
        {
            // Clean reconnect – camera recovered on its own, nothing to do.
            DeviceReconnected?.Invoke();
            return;
        }

        // If the payload size changed (e.g. resolution was altered during disconnect),
        // the existing buffers are invalid and the stream must be restarted.
        var payloadSize = _remoteNodeMap!.TryFindNode<IntegerNode>("PayloadSize").Value();
        var hasPayloadSizeMismatch = payloadSize != _dataStream!.AnnouncedBuffers()[0].Size();

        if (hasPayloadSizeMismatch)
        {
            StopCapture();
            StartCapture();
        }
        else if (!info.IsRemoteDeviceAcquisitionRunning())
        {
            // The device configuration was restored but acquisition did not restart
            // automatically — start it manually.
            _remoteNodeMap!.FindNode<CommandNode>("AcquisitionStart").Execute();
        }

        DeviceReconnected?.Invoke();
    }

    private void DeviceDisconnectedEvent(object sender, DeviceDescriptor device)
    {
        DeviceDisconnected?.Invoke();
    }

    /// <summary>
    ///     Allocates buffers, locks transport layer parameters, and starts the acquisition loop.
    /// </summary>
    public void StartCapture()
    {
        if (_device is null || IsStreaming)
        {
            return;
        }

        var payloadSize = _remoteNodeMap!.FindNode<IntegerNode>("PayloadSize").Value();
        var minBufferCountRequired = _dataStream!.NumBuffersAnnouncedMinRequired();

        for (var i = 0; i < minBufferCountRequired; ++i)
        {
            Buffer? buff = _dataStream!.AllocAndAnnounceBuffer((uint) payloadSize, IntPtr.Zero);
            _dataStream!.QueueBuffer(buff);
        }

        // Lock transport layer parameters before acquisition to prevent
        // settings changes that could corrupt the stream.
        _remoteNodeMap!.FindNode<IntegerNode>("TLParamsLocked").SetValue(1);
        _dataStream!.StartAcquisition();
        _remoteNodeMap!.FindNode<CommandNode>("AcquisitionStart").Execute();
        _remoteNodeMap!.FindNode<CommandNode>("AcquisitionStart").WaitUntilDone();

        // Dispose the previous CancellationTokenSource before creating a new one
        // to avoid resource leaks when StartCapture is called after StopCapture.
        _cts?.Dispose();

        _cts = new CancellationTokenSource();
        CancellationToken token = _cts.Token;

        _isStreaming = true;

        _workerTask = Task.Run(() => AcquisitionLoop(token), token);
    }

    /// <summary>
    ///     Signals the acquisition loop to stop, waits for it to finish, then
    ///     releases all buffers and unlocks transport layer parameters.
    /// </summary>
    public void StopCapture()
    {
        if (_device is null || !IsStreaming)
        {
            return;
        }

        _cts?.Cancel();

        // KillWait unblocks WaitForFinishedBuffer in the acquisition loop,
        // allowing the background task to exit cleanly.
        _dataStream?.KillWait();
        _workerTask?.Wait(1000);


        _remoteNodeMap!.FindNode<CommandNode>("AcquisitionStop").Execute();
        _remoteNodeMap!.FindNode<CommandNode>("AcquisitionStop").WaitUntilDone();

        _dataStream!.StopAcquisition(AcquisitionStopMode.Default);
        _isStreaming = false;

        _dataStream!.Flush(DataStreamFlushMode.DiscardAll);

        foreach (Buffer? buffer in _dataStream!.AnnouncedBuffers())
        {
            _dataStream!.RevokeBuffer(buffer);
        }

        // Unlock transport layer parameters now that acquisition has stopped.
        _remoteNodeMap!.FindNode<IntegerNode>("TLParamsLocked").SetValue(0);
    }

    /// <summary>Returns the current image dimensions reported by the camera.</summary>
    public (int Width, int Height) ImageDimensions()
    {
        try
        {
            var w = _remoteNodeMap?.FindNode<IntegerNode>("Width").Value() ?? -1;
            var h = _remoteNodeMap?.FindNode<IntegerNode>("Height").Value() ?? -1;

            return ((int) w, (int) h);
        }
        catch (Exception)
        {
            // Camera disconnected or busy -> return safe default
            return (-1, -1);
        }
    }

    /// <summary>Returns the current exposure time in microseconds.</summary>
    public double GetExposure()
    {
        try
        {
            return _remoteNodeMap?.FindNode<FloatNode>("ExposureTime").Value() ?? 0;
        }
        catch (Exception)
        {
            // Camera disconnected or busy -> return safe default
            return 0;
        }
    }

    /// <summary>Sets the exposure time in microseconds, clamped to the camera's hardware limits.</summary>
    public void SetExposure(double value)
    {
        try
        {


            FloatNode? node = _remoteNodeMap?.FindNode<FloatNode>("ExposureTime");
            if (node != null)
            {
                var min = node.Minimum();
                var max = node.Maximum();

                // Clamp to the camera's hardware limits before writing.
                var target = Math.Clamp(value, min, max);

                node.SetValue(target);
            }
        }
        catch (Exception)
        {
            // we can do nothing here...
        }
    }

    /// <summary>
    ///     Returns the exposure range, or (0,0) if not available.
    /// </summary>
    public (double Min, double Max) GetExposureRange()
    {
        try
        {
            FloatNode? node = _remoteNodeMap?.FindNode<FloatNode>("ExposureTime");
            if (node != null)
            {
                return (node.Minimum(), node.Maximum());
            }
            return (0, 0);
        }
        catch (Exception)
        {
            return (0, 0);
        }
    }

    /// <summary>Returns the current acquisition framerate in frames per second.</summary>
    public double GetFramerate()
    {
        try
        {
            return _remoteNodeMap?.FindNode<FloatNode>("AcquisitionFrameRate").Value() ?? 0;
        }
        catch (Exception)
        {
            return 0;
        }
    }

    /// <summary>Sets the acquisition framerate in frames per second, clamped to the camera's hardware limits.</summary>
    public void SetFramerate(double value)
    {
        try
        {
            FloatNode? node = _remoteNodeMap?.FindNode<FloatNode>("AcquisitionFrameRate");
            if (node == null)
            {
                return;
            }

            var min = node.Minimum();
            var max = node.Maximum();

            // Clamp to the camera's hardware limits before writing.
            var target = Math.Clamp(value, min, max);

            node.SetValue(target);
        }
        catch (Exception)
        {
            // we can do nothing here...
        }
    }

    /// <summary>
    ///     Returns the framerate range, or (0,0) if not available.
    /// </summary>
    public (double Min, double Max) GetFrameRateRange()
    {
        try
        {
            FloatNode? node = _remoteNodeMap?.FindNode<FloatNode>("AcquisitionFrameRate");
            if (node != null)
            {
                return (node.Minimum(), node.Maximum());
            }

            return (0, 0);
        }
        catch (Exception)
        {
            return (0, 0);
        }
    }

    private void SelectOutputFormat(PixelFormat value)
    {
        // Peak ICV requires a known output format for pixel format conversion.
        // Bayer, YUV and all 3-channel formats are converted to RGB8.
        // 4-channel formats are converted to RGBa8.
        // Mono formats are kept at 8 or 16 bit depending on bit depth.
        // Float and invalid formats are not supported and left unchanged.
        var info = new PixelFormatInfo(value);
        var numChannels = info.NumberOfChannels;
        if (info.IsFloat)
        {
            return;
        }

        if (numChannels == 4)
        {
            OutputPixelFormat = PixelFormat.RGBa8;
            return;
        }

        if (numChannels == 3 || info.HasChannel(Channel.Bayer) || info.HasChannel(Channel.ChromaU))
        {
            OutputPixelFormat = PixelFormat.RGB8;
            return;
        }

        OutputPixelFormat = info.StorageBitsPerChannel > 8 ? PixelFormat.Mono16 : PixelFormat.Mono8;
    }

    /// <summary>
    ///     Loads the camera's default user set, resetting all parameters to factory defaults.
    ///     Acquisition is stopped and restarted automatically if it was running.
    /// </summary>
    public void ResetToDefault()
    {
        var wasStreaming = IsStreaming;
        if (wasStreaming)
        {
            StopCapture();
        }

        _remoteNodeMap?.FindNode<EnumerationNode>("UserSetSelector").SetCurrentEntry("Default");
        _remoteNodeMap?.FindNode<CommandNode>("UserSetLoad").Execute();
        _remoteNodeMap?.FindNode<CommandNode>("UserSetLoad").WaitUntilDone();

        if (wasStreaming)
        {
            StartCapture();
        }
    }

    private bool SetGainSelector(GainType type)
    {
        // Different camera models expose gain under different GainSelector entry names,
        // e.g. "AnalogAll", "DigitalAll", or just "All". Try common prefixes in order.
        string[] prefixList = ["Analog", "Digital", ""];
        EnumerationNode? gainSelectorNode = _remoteNodeMap?.TryFindNode<EnumerationNode>("GainSelector");
        if (gainSelectorNode is null)
        {
            return false;
        }

        var typeName = type.ToString();
        var allEntries = gainSelectorNode.AvailableEntries().Select(x => x.SymbolicValue()).ToList();

        foreach (var prefix in prefixList)
        {
            var entryToCheck = prefix + typeName;
            if (allEntries.Contains(entryToCheck))
            {
                gainSelectorNode.SetCurrentEntry(entryToCheck);
                return true;
            }
        }

        return false;
    }

    /// <summary>
    ///     Returns the current gain for the specified channel, or null if that channel
    ///     is not available on this camera.
    /// </summary>
    public double? GetGain(GainType gainType)
    {
        try
        {
            if (!SetGainSelector(gainType))
            {
                return null;
            }

            return _remoteNodeMap?.FindNode<FloatNode>("Gain").Value();
        }
        catch (Exception)
        {
            // Safe fallback if hardware communication fails mid-flight
            return null;
        }
    }

    /// <summary>
    ///     Sets the gain for the specified channel, clamped to the camera's hardware limits.
    /// </summary>
    public void SetGain(GainType gainType, double value)
    {
        try
        {
            if (!SetGainSelector(gainType))
            {
                return;
            }

            FloatNode? node = _remoteNodeMap?.FindNode<FloatNode>("Gain");
            if (node == null)
            {
                return;
            }

            var min = node.Minimum();
            var max = node.Maximum();
            var target = Math.Clamp(value, min, max);

            node.SetValue(target);
        }
        catch (Exception)
        {
            // we can do nothing here...
        }
    }

    /// <summary>
    ///     Returns the gain range for the specified channel, or null if not available.
    /// </summary>
    public (double Min, double Max)? GetGainRange(GainType gainType)
    {
        try
        {
            if (!SetGainSelector(gainType))
            {
                return null;
            }

            FloatNode? node = _remoteNodeMap?.FindNode<FloatNode>("Gain");
            if (node != null)
            {
                return (node.Minimum(), node.Maximum());
            }

            return null;
        }
        catch (Exception)
        {
            return null;
        }
    }

    private void AcquisitionLoop(CancellationToken token)
    {
        while (!token.IsCancellationRequested && _dataStream is not null)
        {
            try
            {
                using Buffer buffer = _dataStream.WaitForFinishedBuffer(5000);
                if (buffer.IsIncomplete())
                {
                    _dataStream.QueueBuffer(buffer);
                    continue;
                }

                if (NewFrameReady is not null)
                {
                    Image? converted = _defaultPipeline.Process(buffer.ToImageView());

                    NewFrameReady.Invoke(converted);
                }

                _dataStream.QueueBuffer(buffer);
            }
            catch (ApiTimeoutException)
            {
                // Timeout is expected when no frame arrives within 5s (e.g. low framerate).
                // Just retry.
            }
            catch (ApiAbortedException)
            {
                // KillWait() was called during StopCapture(). Normal shutdown path.
                break;
            }
            catch (Exception)
            {
                // Swallow unexpected errors to keep the acquisition loop alive.
                // In production, consider logging here.
            }
        }
    }

    /// <summary>Loads camera parameters from a previously saved settings file.</summary>

    public async void LoadSettings(string path)
    {
        try
        {
            var wasStreaming = IsStreaming;
            if (wasStreaming)
            {
                StopCapture();
            }
            _remoteNodeMap?.LoadFromFile(path);
            if (wasStreaming)
            {
                StartCapture();
            }
        }
        catch (Exception ex)
        {
            IMsBox<ButtonResult> box =
                MessageBoxManager.GetMessageBoxStandard("Error", $"Loading failed: {ex.Message}");
            await box.ShowAsync();
        }
    }

    /// <summary>Saves the current camera parameters to a settings file.</summary>
    public void SaveSettings(string path)
    {
        _remoteNodeMap?.StoreToFile(path);
    }

    public string GetCameraName()
    {
        if (_device is null)
        {
            return "unknown";
        }
        var model = _device.ModelName();
        var serial = _device.SerialNumber();
        return $"{model} ({serial})";
    }
}
